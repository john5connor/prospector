"""Tests for src/prospector/crawl.py against a local stub server (no external requests).
Run: python3 -m unittest tests.test_crawl -v     (from the repo root)"""
import pathlib
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from prospector.crawl import (  # noqa: E402
    BOT_NAME, CrawlRefused, FetchError, Fetcher, Identity, MemoryStore, Policy, blocklist_candidates,
    excluded_reason, identity_from_env, kill_switch, same_site, site_key,
)

IDENT = Identity("https://johnmccarty.dev/bot/", "bot@johnmccarty.dev")
FAST = Policy(delay_s=0.3, retry_wait_s=0.05, timeout_s=3, max_bytes=1000)


class Stub:
    """routes: path -> (status, body, headers). Unknown paths -> 404. Records every hit."""

    def __init__(self):
        stub = self
        self.routes, self.hits = {}, []

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                stub.hits.append({"path": self.path, "ua": self.headers.get("User-Agent"),
                                  "from": self.headers.get("From"), "t": time.monotonic()})
                status, body, headers = stub.routes.get(self.path, (404, b"not found", {}))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                if "no-length" not in headers:
                    self.send_header("Content-Length", headers.get("fake-length", str(len(body))))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.alt = f"http://localhost:{self.server.server_port}"     # same server, different host => off-site

    def paths(self):
        return [h["path"] for h in self.hits]


class CrawlTest(unittest.TestCase):
    def setUp(self):
        self.stub = Stub()
        self.stub.routes["/robots.txt"] = (200, b"User-agent: *\nDisallow: /private\n", {})
        self.stub.routes["/"] = (200, b"<html>home</html>", {})
        self.stub.routes["/about"] = (200, b"<html>about</html>", {})
        self.store = MemoryStore()
        self.on = True
        self.fetcher = self.make()

    def tearDown(self):
        self.stub.server.shutdown()
        self.stub.server.server_close()

    def make(self, **kw):
        args = {"policy": FAST, "enabled": lambda: self.on, "allow_private_hosts": True, **kw}
        return Fetcher(IDENT, self.store, **args)

    def session(self, **kw):
        return self.fetcher.session(self.stub.base + "/", run_id="t", **kw)

    def assertRefused(self, reason):
        return self.assertRaisesRegex(CrawlRefused, f"^{reason}")

    # -- policy values and identity

    def test_defaults_match_policy_section_4(self):
        p = Policy()
        self.assertEqual((p.delay_s, p.max_pages, p.max_depth, p.timeout_s, p.max_bytes, p.retry_wait_s,
                          p.max_sites_in_flight, p.reaudit_days), (2.0, 10, 2, 15.0, 5 * 1024 * 1024, 10.0, 3, 30))

    def test_user_agent_and_from_header_sent_everywhere(self):
        with self.session() as s:
            s.fetch("/", 0)
        self.assertEqual(IDENT.user_agent,
                         "ProspectorAuditBot/0.1 (+https://johnmccarty.dev/bot/; bot@johnmccarty.dev)")
        self.assertTrue(all(h["ua"] == IDENT.user_agent and h["from"] == IDENT.contact_email for h in self.stub.hits))
        opts = self.fetcher.playwright_context_options()
        self.assertEqual(opts["user_agent"], IDENT.user_agent)
        self.assertEqual(opts["extra_http_headers"], {"From": IDENT.contact_email})

    def test_placeholder_identity_refused_before_any_request(self):
        for ident in (Identity("TODO-contact-URL", "TODO-contact-email"), Identity("http://x.dev/bot", "bot@x.dev"),
                      Identity("https://x.dev/bot/", "")):
            f = Fetcher(ident, self.store, policy=FAST, enabled=lambda: True, allow_private_hosts=True)
            with self.assertRefused("identity"):
                f.session(self.stub.base + "/", "t").__enter__()
            with self.assertRefused("identity"):
                f.playwright_context_options()
        self.assertEqual(self.stub.hits, [])

    # -- kill switch

    def test_kill_switch_off_blocks_everything(self):
        self.on = False
        with self.assertRefused("disabled"):
            self.session().__enter__()
        self.assertEqual(self.stub.hits, [])
        self.assertEqual(self.store.entries[-1]["outcome"], "refused:disabled")

    def test_kill_switch_flipped_mid_session_stops_next_fetch(self):
        with self.session() as s:
            s.fetch("/", 0)
            self.on = False
            with self.assertRefused("disabled"):
                s.fetch("/about", 1)
        self.assertNotIn("/about", self.stub.paths())

    def test_kill_switch_reads_env_file_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            env = pathlib.Path(d) / ".env"
            ks = kill_switch(env)
            self.assertFalse(ks())                                  # unset => off
            env.write_text("CRAWL_ENABLED=true\n")
            self.assertTrue(ks())
            env.write_text("CRAWL_ENABLED=yes\n")
            self.assertFalse(ks())                                  # only exact 'true'
            env.write_text("CRAWL_ENABLED=true\nCRAWL_CONTACT_URL=https://a.dev/bot/\nCRAWL_CONTACT_EMAIL=b@a.dev\n")
            self.assertEqual(identity_from_env(env), Identity("https://a.dev/bot/", "b@a.dev"))

    # -- robots.txt

    def test_robots_fetched_once_and_first(self):
        with self.session() as s:
            s.fetch("/", 0)
            s.fetch("/about", 1)
        self.assertEqual(self.stub.paths(), ["/robots.txt", "/", "/about"])

    def test_disallowed_path_not_fetched(self):
        self.stub.routes["/private/x"] = (200, b"secret", {})
        with self.session() as s:
            with self.assertRefused("robots_disallowed"):
                s.fetch("/private/x", 1)
        self.assertNotIn("/private/x", self.stub.paths())
        self.assertEqual(self.store.entries[-1]["robots"], "disallowed")

    def test_rules_for_our_agent_apply(self):
        self.stub.routes["/robots.txt"] = (200, f"User-agent: {BOT_NAME}\nDisallow: /about\n".encode(), {})
        with self.session() as s:
            s.fetch("/", 0)
            with self.assertRefused("robots_disallowed"):
                s.fetch("/about", 1)

    def test_homepage_disallowed_means_blocked_robots(self):
        self.stub.routes["/robots.txt"] = (200, b"User-agent: *\nDisallow: /\n", {})
        with self.assertRefused("blocked_robots"):
            self.session().__enter__()
        self.assertEqual(self.stub.paths(), ["/robots.txt"])

    def test_robots_404_allows(self):
        del self.stub.routes["/robots.txt"]
        with self.session() as s:
            self.assertEqual(s.fetch("/about", 1).status, 200)

    def test_robots_5xx_skips_site_after_one_retry(self):
        self.stub.routes["/robots.txt"] = (503, b"down", {})
        with self.assertRefused("robots_unreachable"):
            self.session().__enter__()
        self.assertEqual(self.stub.paths(), ["/robots.txt", "/robots.txt"])

    def test_robots_403_skips_site(self):
        self.stub.routes["/robots.txt"] = (403, b"no", {})
        with self.assertRefused("robots_unreachable"):
            self.session().__enter__()

    def test_crawl_delay_larger_than_policy_is_used(self):
        self.stub.routes["/robots.txt"] = (200, b"User-agent: *\nCrawl-delay: 1\n", {})
        with self.session() as s:
            s.fetch("/", 0)
            s.fetch("/about", 1)
        t = [h["t"] for h in self.stub.hits]
        self.assertGreaterEqual(t[2] - t[1], 0.95)

    def test_huge_crawl_delay_skips_site(self):
        self.stub.routes["/robots.txt"] = (200, b"User-agent: *\nCrawl-delay: 3600\n", {})
        with self.assertRefused("crawl_delay_too_long"):
            self.session().__enter__()

    # -- rate and size limits

    def test_delay_between_requests(self):
        with self.session() as s:
            s.fetch("/", 0)
            s.fetch("/about", 1)
        t = [h["t"] for h in self.stub.hits]
        self.assertTrue(all(b - a >= FAST.delay_s * 0.95 for a, b in zip(t, t[1:])), t)

    def test_page_limit(self):
        self.fetcher = self.make(policy=Policy(delay_s=0, max_pages=3, retry_wait_s=0, timeout_s=3))
        with self.session() as s:
            for _ in range(3):
                s.fetch("/", 0)
            with self.assertRefused("page_limit"):
                s.fetch("/about", 1)

    def test_depth_limit(self):
        with self.session() as s:
            with self.assertRefused("depth"):
                s.fetch("/about", 3)

    def test_5xx_retried_once_4xx_not(self):
        self.stub.routes["/flaky"] = (500, b"err", {})
        with self.session() as s:
            self.assertEqual(s.fetch("/flaky", 1).status, 500)
            self.assertEqual(s.fetch("/missing", 1).status, 404)
        self.assertEqual(self.stub.paths().count("/flaky"), 2)
        self.assertEqual(self.stub.paths().count("/missing"), 1)

    def test_429_and_403_stop_host(self):
        for code in (429, 403):
            self.stub.hits.clear()
            self.stub.routes["/stop"] = (code, b"slow down", {})
            with self.session() as s:
                with self.assertRefused("host_stopped"):
                    s.fetch("/stop", 1)
                with self.assertRefused("host_stopped"):
                    s.fetch("/about", 1)
            self.assertEqual(self.stub.paths().count("/stop"), 1)
            self.assertNotIn("/about", self.stub.paths())

    def test_network_error_raises_fetch_error(self):
        with self.session() as s:
            self.stub.server.shutdown()
            self.stub.server.server_close()
            with self.assertRaises(FetchError):
                s.fetch("/about", 1)

    def test_declared_oversize_body_not_read(self):
        self.stub.routes["/big"] = (200, b"x" * 2000, {})
        with self.session() as s:
            r = s.fetch("/big", 1)
        self.assertTrue(r.truncated)
        self.assertEqual(r.body, b"")
        self.assertEqual(self.store.entries[-1]["outcome"], "too_large")

    def test_undeclared_oversize_body_truncated(self):
        self.stub.routes["/stream"] = (200, b"y" * 200_000, {"no-length": "1", "Connection": "close"})
        with self.session() as s:
            r = s.fetch("/stream", 1)
        self.assertTrue(r.truncated)
        self.assertEqual(len(r.body), FAST.max_bytes)

    def test_max_sites_in_flight(self):
        f = self.make(policy=Policy(delay_s=0, max_sites_in_flight=1, retry_wait_s=0, timeout_s=3))
        first = f.session(self.stub.base + "/", "t").__enter__()
        got = []
        t = threading.Thread(target=lambda: got.append(f.session(self.stub.alt + "/", "t").__enter__()))
        t.start()
        t.join(0.5)
        self.assertEqual(got, [])                   # second site waits for a slot
        first.__exit__(None, None, None)
        t.join(3)
        self.assertEqual(len(got), 1)
        got[0].__exit__(None, None, None)

    def test_same_site_twice_refused(self):
        with self.session():
            with self.assertRefused("site_in_progress"):
                self.session().__enter__()

    # -- what may be fetched

    def test_offsite_and_redirects(self):
        self.stub.routes["/go-off"] = (302, b"", {"Location": self.stub.alt + "/about"})
        self.stub.routes["/go-home"] = (301, b"", {"Location": "/about"})
        with self.session() as s:
            with self.assertRefused("offsite"):
                s.fetch(self.stub.alt + "/about", 1)
            with self.assertRefused("offsite"):
                s.fetch("/go-off", 1)
            r = s.fetch("/go-home", 1)
            self.assertEqual((r.status, r.url), (200, self.stub.base + "/about"))
            self.assertEqual(s.pages_used, 3)       # each redirect hop counts
        self.assertEqual(self.stub.paths(), ["/robots.txt", "/go-off", "/go-home", "/about"])

    def test_excluded_urls(self):
        with self.session() as s:
            for u in ("/cart", "/checkout/step1", "/wp-login.php", "/my-account/", "/?s=hvac", "/x?PHPSESSID=1"):
                with self.assertRefused("excluded_url"):
                    s.fetch(u, 1)
            with self.assertRefused("excluded_url"):
                s.fetch("ftp://127.0.0.1/", 1)
        self.assertEqual(self.stub.paths(), ["/robots.txt"])
        self.assertIsNone(excluded_reason("https://a.com/?page_id=12"))
        self.assertIsNone(excluded_reason("https://a.com/cartography"))

    def test_social_and_directory_never_crawled(self):
        for u in ("https://www.facebook.com/somebiz", "https://m.yelp.com/biz/x", "https://maps.google.com/?cid=1"):
            with self.assertRefused("social_site"):
                self.fetcher.session(u, "t").__enter__()

    def test_private_address_refused_without_test_flag(self):
        f = Fetcher(IDENT, self.store, policy=FAST, enabled=lambda: True)
        with self.assertRefused("private_address"):
            f.session(self.stub.base + "/", "t").__enter__()
        self.assertEqual(self.stub.hits, [])

    # -- blocklist and re-audit

    def test_blocklist_checked_before_any_request(self):
        self.store.blocklist.add("127.0.0.1")
        with self.assertRefused("blocklisted"):
            self.session().__enter__()
        self.assertEqual(self.stub.hits, [])

    def test_blocklist_added_mid_session(self):
        with self.session() as s:
            s.fetch("/", 0)
            self.store.blocklist.add("127.0.0.1")
            with self.assertRefused("blocklisted"):
                s.fetch("/about", 1)

    def test_blocklist_matches_parent_domains(self):
        self.assertEqual(blocklist_candidates("www.shop.example.com"),
                         ["www.shop.example.com", "shop.example.com", "example.com"])
        self.assertEqual(site_key("www.example.com"), "example.com")
        self.assertTrue(same_site("shop.example.com", "example.com"))
        self.assertFalse(same_site("badexample.com", "example.com"))

    def test_reaudit_interval(self):
        with self.session() as s:
            s.fetch("/", 0)
        with self.assertRefused("reaudit_too_soon"):
            self.fetcher.session(self.stub.base + "/", run_id="next").__enter__()
        with self.fetcher.session(self.stub.base + "/", run_id="next", owner_requested=True) as s:
            s.fetch("/", 0)

    def test_every_request_logged(self):
        with self.session() as s:
            s.fetch("/", 0)
            with self.assertRefused("robots_disallowed"):
                s.fetch("/private/a", 1)
        log = [(e["kind"], e["status"], e["outcome"]) for e in self.store.entries]
        self.assertEqual(log, [("robots", 200, "ok"), ("page", 200, "ok"), ("page", None, "refused:robots_disallowed")])
        self.assertTrue(all(e["site"] == "127.0.0.1" and e["run_id"] == "t" for e in self.store.entries))


if __name__ == "__main__":
    unittest.main()
