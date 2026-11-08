"""PsqlStore against the local Postgres (migration 010 applied). Opt-in, because it writes to the database:
    PROSPECTOR_DB_TESTS=1 python3 -m unittest tests.test_crawl_psql -v
Rows it creates use run_id 'dbtest-*' and *.dbtest.invalid / 127.0.0.1 sites, and are deleted afterwards."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from prospector.crawl import CrawlRefused, Fetcher, PsqlStore, blocklist_candidates  # noqa: E402
from tests.test_crawl import FAST, IDENT, Stub  # noqa: E402

RUN = f"dbtest-{int(time.time())}"
SITE = "site.dbtest.invalid"


@unittest.skipUnless(os.environ.get("PROSPECTOR_DB_TESTS") == "1", "set PROSPECTOR_DB_TESTS=1 to run")
class PsqlStoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = PsqlStore()

    def tearDown(self):
        self.db._psql("DELETE FROM crawl_fetch_log WHERE run_id LIKE 'dbtest-%';"
                      "DELETE FROM crawl_blocklist WHERE domain LIKE '%dbtest.invalid' OR reason = 'dbtest';")

    def entry(self, **kw):
        e = {"run_id": RUN, "site": SITE, "url": f"https://{SITE}/", "kind": "page", "status": 200, "bytes": 10,
             "duration_ms": 5, "robots": "allowed", "outcome": "ok", "error": None}
        e.update(kw)
        return e

    def test_blocklist_matches_domain_and_subdomains(self):
        self.db._psql("INSERT INTO crawl_blocklist (domain, reason) VALUES ('dbtest.invalid', 'dbtest');")
        self.assertTrue(self.db.is_blocked(blocklist_candidates("www.shop.dbtest.invalid")))
        self.assertTrue(self.db.is_blocked(blocklist_candidates("dbtest.invalid")))
        self.assertFalse(self.db.is_blocked(blocklist_candidates("otherdbtest.invalid")))

    def test_log_round_trip_with_nulls_and_awkward_text(self):
        url = f"https://{SITE}/it's;a \"test\"?x=1&y='; DROP TABLE crawl_blocklist;--"
        self.db.log(self.entry(url=url, status=None, outcome="refused:excluded_url", error="line1\nline2 'quoted'"))
        self.db.log(self.entry(kind="robots", robots="n/a"))
        rows = self.db._psql(f"SELECT url, coalesce(status::text,'NULL'), outcome, error FROM crawl_fetch_log "
                             f"WHERE run_id = '{RUN}' ORDER BY id;").splitlines()
        self.assertEqual(rows[0], f"{url}|NULL|refused:excluded_url|line1 line2 'quoted'")
        self.assertEqual(rows[1], f"https://{SITE}/|200|ok|")
        self.assertEqual(self.db._psql("SELECT to_regclass('crawl_blocklist') IS NOT NULL;"), "t")

    def test_last_crawled_ignores_current_run_refusals_and_robots(self):
        self.assertIsNone(self.db.last_crawled(SITE, "other"))
        self.db.log(self.entry(kind="robots", robots="n/a"))
        self.db.log(self.entry(outcome="refused:page_limit", status=None))
        self.assertIsNone(self.db.last_crawled(SITE, "other"))          # only successful page fetches count
        self.db.log(self.entry())
        self.assertIsNone(self.db.last_crawled(SITE, RUN))              # same run doesn't block itself
        self.assertAlmostEqual(self.db.last_crawled(SITE, "other"), time.time(), delta=60)

    def test_constraints_reject_bad_rows(self):
        with self.assertRaises(RuntimeError):
            self.db.log(self.entry(kind="other"))
        with self.assertRaises(RuntimeError):
            self.db._psql("INSERT INTO crawl_blocklist (domain, reason) VALUES ('Https://X.dbtest.invalid/', 'dbtest');")

    def test_end_to_end_against_stub(self):
        stub = Stub()
        stub.routes["/robots.txt"] = (200, b"User-agent: *\nDisallow: /private\n", {})
        stub.routes["/"] = (200, b"home", {})
        try:
            f = Fetcher(IDENT, self.db, policy=FAST, enabled=lambda: True, allow_private_hosts=True)
            with f.session(stub.base + "/", run_id=RUN + "-a", owner_requested=True) as s:
                s.fetch("/", 0)
                with self.assertRaisesRegex(CrawlRefused, "^robots_disallowed"):
                    s.fetch("/private/x", 1)
            rows = self.db._psql(f"SELECT kind, coalesce(status::text,''), robots_decision, outcome FROM crawl_fetch_log "
                                 f"WHERE run_id = '{RUN}-a' ORDER BY id;").splitlines()
            self.assertEqual(rows, ["robots|200|n/a|ok", "page|200|allowed|ok",
                                    "page||disallowed|refused:robots_disallowed"])
            with self.assertRaisesRegex(CrawlRefused, "^reaudit_too_soon"):
                f.session(stub.base + "/", run_id=RUN + "-b").__enter__()
            self.db._psql("INSERT INTO crawl_blocklist (domain, reason) VALUES ('127.0.0.1', 'dbtest');")
            stub.hits.clear()
            with self.assertRaisesRegex(CrawlRefused, "^blocklisted"):
                f.session(stub.base + "/", run_id=RUN + "-c", owner_requested=True).__enter__()
            self.assertEqual(stub.hits, [])
        finally:
            stub.server.shutdown()
            stub.server.server_close()


if __name__ == "__main__":
    unittest.main()
