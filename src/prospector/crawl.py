"""Shared fetch helper for prospect websites. Enforces docs/CRAWL_POLICY.md sections 1-4 and 7.

DRAFT, not wired into any workflow. Every request to a prospect's own website must go through this module;
no audit node or script may call a prospect host directly.

    fetcher = Fetcher.from_env(PsqlStore())
    with fetcher.session("https://example.com/", run_id="r1") as s:   # checks kill switch, identity,
        home = s.fetch("https://example.com/", depth=0)               # blocklist, re-audit interval, robots.txt
        about = s.fetch("/about", depth=1)

Refusals raise CrawlRefused with a stable `reason` (see REASONS). A refusal with reason 'blocked_robots'
means the homepage is disallowed: record the audit as blocked_robots and move on.
Network failures (after the one allowed retry) raise FetchError. HTTP statuses are returned, except
403 and 429, which stop all crawling of that host for the run (CrawlRefused 'host_stopped').

Standard library only. A SiteSession is used by one thread; up to Policy.max_sites_in_flight sessions
(different sites) may run in parallel against one Fetcher.
"""
from __future__ import annotations

import http.client
import ipaddress
import os
import re
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol
from urllib import request as urlreq
from urllib import robotparser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urljoin, urlsplit, urlunsplit

BOT_NAME = "ProspectorAuditBot"
BOT_VERSION = "0.1"
ROOT = Path(__file__).resolve().parents[2]

REASONS = {
    "disabled": "CRAWL_ENABLED is not true",
    "identity": "contact URL/email not filled in",
    "blocklisted": "domain is on crawl_blocklist",
    "reaudit_too_soon": "site was crawled within the re-audit interval",
    "site_in_progress": "another session is already crawling this site",
    "social_site": "social-media/directory sites are never crawled",
    "private_address": "host resolves to a non-public address",
    "robots_unreachable": "robots.txt could not be read; skip this site for the run",
    "crawl_delay_too_long": "robots.txt Crawl-delay exceeds Policy.max_crawl_delay_s",
    "blocked_robots": "homepage is disallowed by robots.txt",
    "robots_disallowed": "URL is disallowed by robots.txt",
    "offsite": "URL is outside the prospect's site",
    "excluded_url": "login/cart/checkout/admin, search or session query, or non-http URL",
    "depth": "deeper than Policy.max_depth from the homepage",
    "page_limit": "Policy.max_pages reached for this site",
    "host_stopped": "host returned 403/429 earlier this run",
    "too_many_redirects": "redirect chain too long",
    "session_closed": "session is not open",
}


@dataclass(frozen=True)
class Policy:
    """Defaults are the values in CRAWL_POLICY.md section 4. Tests may shorten the waits only."""
    delay_s: float = 2.0                # between requests to one host, never concurrent
    max_pages: int = 10                 # page requests per site per run (robots.txt not counted)
    max_depth: int = 2                  # link depth from the homepage
    timeout_s: float = 15.0             # whole request, connect to last byte
    max_bytes: int = 5 * 1024 * 1024    # body read cap; larger declared bodies are not read at all
    retry_wait_s: float = 10.0          # one retry on network error / 5xx
    max_sites_in_flight: int = 3
    reaudit_days: int = 30
    max_redirects: int = 5
    max_crawl_delay_s: float = 60.0     # NOT in the policy: larger Crawl-delay => skip the site (open item)


@dataclass(frozen=True)
class Identity:
    contact_url: str
    contact_email: str

    @property
    def user_agent(self) -> str:
        return f"{BOT_NAME}/{BOT_VERSION} (+{self.contact_url}; {self.contact_email})"

    def problems(self) -> list[str]:
        out = []
        if not self.contact_url.startswith("https://") or "TODO" in self.contact_url.upper():
            out.append("CRAWL_CONTACT_URL must be a real https:// URL")
        if not re.fullmatch(r"[^@\s;()]+@[^@\s;()]+\.[a-z]{2,}", self.contact_email or "", re.I) \
                or "TODO" in self.contact_email.upper():
            out.append("CRAWL_CONTACT_EMAIL must be a real address")
        return out


class CrawlRefused(Exception):
    def __init__(self, reason: str, detail: str = ""):
        assert reason in REASONS, reason
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


class FetchError(Exception):
    """Network failure that persisted through the allowed retry."""


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes
    truncated: bool = False


# ---------------------------------------------------------------- configuration from .env

def read_env_file(path: Path = ROOT / ".env") -> dict:
    vals = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip("\"'")
    except FileNotFoundError:
        pass
    return vals


def kill_switch(path: Path = ROOT / ".env") -> Callable[[], bool]:
    """Re-read on every request, so setting CRAWL_ENABLED=false in .env stops a running crawl.
    Fails closed: enabled only if every place that sets it (process env, .env) says exactly 'true'."""
    def enabled() -> bool:
        seen = [v for v in (os.environ.get("CRAWL_ENABLED"), read_env_file(path).get("CRAWL_ENABLED")) if v is not None]
        return bool(seen) and all(v.strip().lower() == "true" for v in seen)
    return enabled


def identity_from_env(path: Path = ROOT / ".env") -> Identity:
    env = {**read_env_file(path), **os.environ}
    return Identity(env.get("CRAWL_CONTACT_URL", ""), env.get("CRAWL_CONTACT_EMAIL", ""))


# ---------------------------------------------------------------- URL rules (policy section 2)

SOCIAL_AND_DIRECTORY = (
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "tiktok.com",
    "youtube.com", "pinterest.com", "threads.net", "nextdoor.com", "yelp.com", "google.com", "goo.gl",
    "bbb.org", "angi.com", "angieslist.com", "homeadvisor.com", "thumbtack.com", "yellowpages.com",
    "tripadvisor.com", "houzz.com", "porch.com", "manta.com", "mapquest.com", "foursquare.com",
)
_EXCLUDED_PATH = re.compile(
    r"(^|/)(login|log-in|signin|sign-in|signup|sign-up|register|logout|account|my-account|cart|basket|"
    r"checkout|wp-admin|wp-login\.php|admin|auth|oauth)(/|$|\.)", re.I)
_EXCLUDED_QUERY_KEYS = {
    "q", "s", "search", "query", "keyword", "keywords", "sid", "session", "sessionid", "session_id",
    "phpsessid", "jsessionid", "token", "auth", "key", "code", "state", "password", "add-to-cart", "add_to_cart",
}
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$")


def normalize(url: str) -> tuple[str, str]:
    """Return (url without fragment, lower-case ASCII host). Raises CrawlRefused('excluded_url')."""
    try:
        p = urlsplit(url.strip())
        port = p.port
    except ValueError as e:
        raise CrawlRefused("excluded_url", f"unparseable URL {url!r}") from e
    if p.scheme not in ("http", "https") or p.username or p.password:
        raise CrawlRefused("excluded_url", f"not a plain http(s) URL: {url!r}")
    try:
        host = (p.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as e:
        raise CrawlRefused("excluded_url", f"bad host in {url!r}") from e
    if not _HOST_RE.match(host):
        raise CrawlRefused("excluded_url", f"bad host in {url!r}")
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((p.scheme, netloc, p.path or "/", p.query, "")), host


def site_key(host: str) -> str:
    """The prospect's site. Conservative stand-in for the registrable domain: www.example.com and
    example.com map to example.com and allow its subdomains; shop.example.com allows only itself and below."""
    return host[4:] if host.startswith("www.") else host


def same_site(host: str, site: str) -> bool:
    return host == site or host.endswith("." + site)


def _matches_domain(host: str, domains) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def is_social(host: str) -> bool:
    return _matches_domain(host, SOCIAL_AND_DIRECTORY)


def excluded_reason(url: str) -> Optional[str]:
    p = urlsplit(url)
    if _EXCLUDED_PATH.search(p.path):
        return f"excluded path {p.path!r}"
    keys = {k.lower() for k, _ in parse_qsl(p.query, keep_blank_values=True)}
    if keys & _EXCLUDED_QUERY_KEYS:
        return f"search/session query {sorted(keys & _EXCLUDED_QUERY_KEYS)}"
    return None


def blocklist_candidates(host: str) -> list[str]:
    """www.shop.example.com -> [www.shop.example.com, shop.example.com, example.com]"""
    labels = host.split(".")
    if host.replace(".", "").isdigit():
        return [host]
    return [".".join(labels[i:]) for i in range(len(labels) - 1)] or [host]


# ---------------------------------------------------------------- storage (policy section 7)

class Store(Protocol):
    def is_blocked(self, candidates: list[str]) -> bool: ...
    def last_crawled(self, site: str, exclude_run: str) -> Optional[float]: ...   # unix time
    def log(self, entry: dict) -> None: ...


@dataclass
class MemoryStore:
    """For tests and dry runs. Same interface as PsqlStore."""
    blocklist: set = field(default_factory=set)
    entries: list = field(default_factory=list)

    def is_blocked(self, candidates):
        return any(c in self.blocklist for c in candidates)

    def last_crawled(self, site, exclude_run):
        ts = [e["at"] for e in self.entries if e["site"] == site and e["kind"] == "page"
              and e["outcome"] == "ok" and e["run_id"] != exclude_run]
        return max(ts) if ts else None

    def log(self, entry):
        self.entries.append({**entry, "at": time.time()})


class PsqlStore:
    """crawl_blocklist / crawl_fetch_log (migration 010) via `docker compose exec psql`, like scripts/build_report.py.
    Values are passed as psql variables (:'name' quoting), never interpolated into SQL.
    Any failure raises, so the fetcher fails closed (no blocklist answer => no fetch; no log => session stops)."""

    def __init__(self, root: Path = ROOT):
        env = read_env_file(root / ".env")
        self.root, self.user, self.db = root, env["POSTGRES_USER"], env["PROSPECTOR_DB"]

    def _psql(self, sql: str, **vars) -> str:
        args = ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", self.user, "-d", self.db,
                "-v", "ON_ERROR_STOP=1", "-tA"]
        for k, v in vars.items():
            args += ["-v", f"{k}={'' if v is None else v}"]
        r = subprocess.run(args, input=sql, cwd=self.root, capture_output=True, text=True, timeout=30)
        if r.returncode:
            raise RuntimeError(f"psql failed: {r.stderr.strip()}")
        return r.stdout.strip()

    def is_blocked(self, candidates):
        out = self._psql("SELECT count(*) FROM crawl_blocklist WHERE domain = ANY(string_to_array(:'c', ','));",
                         c=",".join(candidates))
        return int(out) > 0

    def last_crawled(self, site, exclude_run):
        out = self._psql("SELECT extract(epoch FROM max(fetched_at)) FROM crawl_fetch_log WHERE site = :'site' "
                         "AND kind = 'page' AND outcome = 'ok' AND run_id IS DISTINCT FROM :'run';",
                         site=site, run=exclude_run)
        return float(out) if out else None

    def log(self, e):
        self._psql("INSERT INTO crawl_fetch_log (run_id, site, url, kind, status, bytes, duration_ms, robots_decision, "
                   "outcome, error) VALUES (:'run', :'site', :'url', :'kind', NULLIF(:'status','')::int, :'bytes'::int, "
                   ":'ms'::int, :'robots', :'outcome', NULLIF(:'error',''));",
                   run=e["run_id"], site=e["site"], url=e["url"], kind=e["kind"], status=e["status"],
                   bytes=e["bytes"], ms=e["duration_ms"], robots=e["robots"], outcome=e["outcome"],
                   error=(e["error"] or "").replace("\n", " "))


# ---------------------------------------------------------------- fetcher

class _NoRedirect(urlreq.HTTPRedirectHandler):
    """Redirects come back as responses so each hop is checked (same site, robots, blocklist, page count)."""
    def redirect_request(self, *args, **kwargs):
        return None


class Fetcher:
    def __init__(self, identity: Identity, store: Store, *, policy: Policy = Policy(),
                 enabled: Optional[Callable[[], bool]] = None, allow_private_hosts: bool = False,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.identity, self.store, self.policy = identity, store, policy
        self.enabled = enabled or kill_switch()
        self.allow_private_hosts = allow_private_hosts      # tests only: lets the stub server on 127.0.0.1 through
        self.sleep, self.clock = sleep, clock
        self._slots = threading.BoundedSemaphore(policy.max_sites_in_flight)
        self._lock = threading.Lock()
        self._active_sites: set[str] = set()
        self._host_locks: dict[str, threading.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._opener = urlreq.build_opener(_NoRedirect)

    @classmethod
    def from_env(cls, store: Store, **kw) -> "Fetcher":
        return cls(identity_from_env(), store, **kw)

    def headers(self) -> dict:
        return {"User-Agent": self.identity.user_agent, "From": self.identity.contact_email}

    def playwright_context_options(self) -> dict:
        """Pass to browser.new_context(**opts) so Playwright sends the same identity (policy section 1).
        Playwright pages must still be opened only for URLs this helper has already allowed; see PROJECT.md."""
        self.check_ready()
        h = self.headers()
        return {"user_agent": h.pop("User-Agent"), "extra_http_headers": h}

    def check_ready(self) -> None:
        if not self.enabled():
            raise CrawlRefused("disabled")
        if problems := self.identity.problems():
            raise CrawlRefused("identity", "; ".join(problems))

    def session(self, start_url: str, run_id: str, owner_requested: bool = False) -> "SiteSession":
        return SiteSession(self, start_url, run_id, owner_requested)

    def _host_lock(self, host: str) -> threading.Lock:
        with self._lock:
            return self._host_locks.setdefault(host, threading.Lock())


class SiteSession:
    def __init__(self, fetcher: Fetcher, start_url: str, run_id: str, owner_requested: bool):
        self.f, self.p = fetcher, fetcher.policy
        self.start_url, self.run_id, self.owner_requested = start_url, run_id, owner_requested
        self.site = ""
        self.open = False
        self.pages_used = 0
        self.robots: dict[str, robotparser.RobotFileParser] = {}   # by origin
        self.delays: dict[str, float] = {}                          # by host
        self.stopped_hosts: set[str] = set()
        self.checked_hosts: set[str] = set()
        self._slot = self._registered = False

    # -- lifecycle

    def __enter__(self) -> "SiteSession":
        url, host = normalize(self.start_url)
        self.site = site_key(host)
        try:
            self.f.check_ready()
        except CrawlRefused as e:
            self._log(url, "page", outcome=f"refused:{e.reason}", error=e.detail)
            raise
        if is_social(host):
            self._refuse("social_site", url, host)
        self.f._slots.acquire()
        self._slot = True
        try:
            with self.f._lock:
                if self.site in self.f._active_sites:
                    self._refuse("site_in_progress", url, self.site)
                self.f._active_sites.add(self.site)
                self._registered = True
            if self.f.store.is_blocked(blocklist_candidates(host)):
                self._refuse("blocklisted", url, host)
            if not self.owner_requested:
                last = self.f.store.last_crawled(self.site, self.run_id)
                if last and time.time() - last < self.p.reaudit_days * 86400:
                    self._refuse("reaudit_too_soon", url, f"last crawl {int((time.time() - last) / 86400)} days ago")
            self.start_url = url
            home = urljoin(url, "/")
            if not self._robots_for(home).can_fetch(BOT_NAME, home):
                self._refuse("blocked_robots", home, robots="disallowed")
            self.open = True
            return self
        except BaseException:
            self._release()
            raise

    def __exit__(self, *exc) -> None:
        self._release()

    def _release(self) -> None:
        self.open = False
        if self._registered:
            with self.f._lock:
                self.f._active_sites.discard(self.site)
            self._registered = False
        if self._slot:
            self.f._slots.release()
            self._slot = False

    # -- public

    def fetch(self, url: str, depth: int) -> Response:
        """GET one page. depth = link distance from the homepage (homepage = 0). Follows redirects
        hop by hop; every hop is re-checked and counts toward the page limit."""
        if not self.open:
            raise CrawlRefused("session_closed")
        if depth > self.p.max_depth:
            self._refuse("depth", urljoin(self.start_url, url), f"depth {depth}")
        current = urljoin(self.start_url, url)
        for _ in range(self.p.max_redirects + 1):
            current, host = self._check_target(current)
            if self.pages_used >= self.p.max_pages:
                self._refuse("page_limit", current, f"{self.pages_used} pages used")
            self.pages_used += 1
            resp = self._get(current, host, "page", stop_on=(403, 429))
            loc = resp.headers.get("location")
            if resp.status in (301, 302, 303, 307, 308) and loc:
                current = urljoin(current, loc)
                continue
            return resp
        self._refuse("too_many_redirects", current)

    # -- checks

    def _check_target(self, url: str) -> tuple[str, str]:
        url, host = normalize(url)
        if not same_site(host, self.site):
            self._refuse("offsite", url, host)
        if why := excluded_reason(url):
            self._refuse("excluded_url", url, why)
        if host in self.stopped_hosts:
            self._refuse("host_stopped", url, host)
        if not self._robots_for(url).can_fetch(BOT_NAME, url):
            self._refuse("robots_disallowed", url, robots="disallowed")
        return url, host

    def _check_address(self, url: str, host: str) -> None:
        if host in self.checked_hosts or self.f.allow_private_hosts:
            return
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            self._refuse("robots_unreachable", url, f"DNS: {e}")
        for info in infos:
            if not ipaddress.ip_address(info[4][0].split("%")[0]).is_global:
                self._refuse("private_address", url, info[4][0])
        self.checked_hosts.add(host)

    def _robots_for(self, url: str) -> robotparser.RobotFileParser:
        """Fetched once per origin per session, before any other request to it (policy section 3).
        200 => parse; 404/410 => allow all; anything else (other 4xx, 5xx after retry, network, off-site
        redirect) => skip the site this run."""
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin in self.robots:
            return self.robots[origin]
        host = p.hostname or ""
        self._check_address(url, host)
        current = origin + "/robots.txt"
        for _ in range(self.p.max_redirects + 1):
            try:
                resp = self._get(current, urlsplit(current).hostname, "robots")
            except FetchError as e:
                self._refuse("robots_unreachable", current, str(e), kind="robots")
            loc = resp.headers.get("location")
            if resp.status in (301, 302, 303, 307, 308) and loc:
                current, rhost = normalize(urljoin(current, loc))
                if not same_site(rhost, self.site):
                    self._refuse("robots_unreachable", current, "robots.txt redirects off-site", kind="robots")
                self._check_address(current, rhost)
                continue
            break
        else:
            self._refuse("robots_unreachable", current, "too many redirects", kind="robots")
        rp = robotparser.RobotFileParser()
        if 200 <= resp.status < 300:
            rp.parse(resp.body.decode("utf-8", "replace").splitlines())
        elif resp.status in (404, 410):
            rp.parse([])            # parse() marks it read; empty rules allow everything
        else:
            self._refuse("robots_unreachable", current, f"HTTP {resp.status}", kind="robots")
        delay = rp.crawl_delay(BOT_NAME)
        if delay and float(delay) > self.p.max_crawl_delay_s:
            self._refuse("crawl_delay_too_long", current, f"Crawl-delay {delay}", kind="robots")
        self.delays[host] = max(self.p.delay_s, float(delay or 0))
        self.robots[origin] = rp
        return rp

    # -- requests

    def _get(self, url: str, host: str, kind: str, stop_on: tuple = ()) -> Response:
        """One logical request: at most one retry, after Policy.retry_wait_s, on network error or 5xx."""
        for attempt in (1, 2):
            resp, err = self._request(url, host, kind)
            if resp is not None and resp.status in stop_on:
                self.stopped_hosts.add(host)
                raise CrawlRefused("host_stopped", f"{host} returned HTTP {resp.status}")
            if not (err or resp.status >= 500) or attempt == 2:
                break
            self.f.sleep(self.p.retry_wait_s)
        if err:
            raise FetchError(f"{url}: {err}")
        return resp

    def _request(self, url: str, host: str, kind: str) -> tuple[Optional[Response], Optional[str]]:
        if not self.f.enabled():
            self._refuse("disabled", url, kind=kind)
        if self.f.store.is_blocked(blocklist_candidates(host)):
            self._refuse("blocklisted", url, host, kind=kind)
        with self.f._host_lock(host):
            last = self.f._last_request.get(host)
            if last is not None:
                wait = last + self.delays.get(host, self.p.delay_s) - self.f.clock()
                if wait > 0:
                    self.f.sleep(wait)
            start = self.f.clock()
            resp, err, outcome = None, None, "ok"
            try:
                req = urlreq.Request(url, method="GET", headers={
                    **self.f.headers(), "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5"})
                try:
                    r = self.f._opener.open(req, timeout=self.p.timeout_s)
                except HTTPError as e:
                    r = e
                with r:
                    resp, outcome = self._read(r, url, start)
            except (URLError, OSError, http.client.HTTPException, ValueError) as e:
                err, outcome = f"{type(e).__name__}: {e}", "error"
            finally:
                self.f._last_request[host] = self.f.clock()
        self._log(url, kind, status=resp.status if resp else None, nbytes=len(resp.body) if resp else 0,
                  ms=int((self.f.clock() - start) * 1000), outcome=outcome, error=err,
                  robots="n/a" if kind == "robots" else "allowed")
        return resp, err

    def _read(self, r, url: str, start: float) -> tuple[Response, str]:
        headers = {k.lower(): v for k, v in r.headers.items()} if r.headers else {}
        status = r.getcode()
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self.p.max_bytes:
            return Response(url, status, headers, b"", truncated=True), "too_large"
        chunks, size = [], 0
        while r.fp is not None and size <= self.p.max_bytes:
            if self.f.clock() - start > self.p.timeout_s:
                raise TimeoutError(f"exceeded {self.p.timeout_s}s")
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        body = b"".join(chunks)
        if len(body) > self.p.max_bytes:
            return Response(url, status, headers, body[: self.p.max_bytes], truncated=True), "truncated"
        return Response(url, status, headers, body), "ok"

    # -- audit trail

    def _log(self, url, kind, *, status=None, nbytes=0, ms=0, outcome, error=None, robots="n/a"):
        self.f.store.log({"run_id": self.run_id, "site": self.site, "url": url, "kind": kind, "status": status,
                          "bytes": nbytes, "duration_ms": ms, "robots": robots, "outcome": outcome, "error": error})

    def _refuse(self, reason, url, detail="", *, kind="page", robots="n/a"):
        self._log(url, kind, outcome=f"refused:{reason}", error=detail or None, robots=robots)
        raise CrawlRefused(reason, detail)
