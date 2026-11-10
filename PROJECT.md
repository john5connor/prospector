# PROJECT.md

Working notes and conventions for the prospector project. Setup: `docs/SETUP.md`. Decisions log: `docs/DECISIONS.md`.

## Scope now
Discovery MVP: Manual trigger, mock Places data, normalize, validate, dedupe on `place_id`, persist to Postgres,
log every run. Real Google Places integration, scheduling, qualification, audits and outreach are later work.

## Workflow conventions
- Every run writes a `discovery_runs` row, including runs that find nothing. `status` is one of
  `ok`, `no_results` (source returned nothing), `no_valid_records` (everything failed validation).
- Empty results are handled with `alwaysOutputData` on the source and the validation filter, so the persist step
  always runs. The SQL ignores blank-ID rows. This is deliberate: an empty run is a result, not a non-event.
- Deduplication and counting happen in SQL (`ON CONFLICT (place_id) DO NOTHING`), not in n8n nodes.
- `mockScenario` in the "Discovery Parameters" node (`normal` | `all_invalid` | `empty`) is a test knob for the
  mock source and goes away when the real Places request replaces it. Keep it set to `normal` when committing.

## Places source (built, untested against the real API)
- `source` in "Discovery Parameters" selects `mock` (default) or `places`. A "Source Router" IF node branches.
- Places path: HTTP Request POST `places:searchText`, fixed field mask (id, displayName, formattedAddress, primaryType,
  nationalPhoneNumber, websiteUri, nextPageToken; Enterprise tier), `pageSize` 20, auth via the "Google Places API Key"
  header credential. Never use a wildcard field mask.
- Spend bound: pagination is capped by `maxPages` with a hard ceiling of 3 in the node expression (Text Search returns
  at most 60 results anyway). `requests_made` is logged in `discovery_runs` for every run.
- Tested with `tests/stub_places_server.py` (no paid calls): 3-page pagination, endless-token cap (10 requested,
  3 made), empty response (`no_results`, 1 request). The real API's response shapes are still unverified.
- Credentials: `scripts/sync-n8n-credentials.sh` builds them from `.env`. Until `GOOGLE_PLACES_API_KEY` is set the
  Places credential holds a placeholder. Do not set `source=places` before the key, quotas and restrictions exist.
- Not built yet: a monthly request budget check that aborts a run when exceeded (recommended before scheduling).

## Error handling (planned, not built)
Today a failing node fails the execution, which is visible in n8n's execution list but alerts nobody.
The intended design is "if an error occurs at X, forward it to Y", where Y is an error notification service.
n8n gives two mechanisms, and we expect to use both:

1. **Per-node error output (in-graph).** Set the node's `onError` to `continueErrorOutput`, which adds an error
   output branch. Wire it to a handler, for example a Set node that builds an error payload (workflow, node, message,
   input summary) followed by the notifier. Use this where the workflow can continue or needs a specific
   response, such as one failed Places request out of many.
2. **Error workflow (global).** One shared workflow starting with an Error Trigger node, assigned to each
   workflow through its `errorWorkflow` setting. It catches anything unhandled and sends the alert. It fires for
   production executions only, not manual or test runs.

The error workflow should be the single place that formats and sends notifications, so every in-graph error branch
can forward to it (for example through an Execute Workflow node) and the channel can change in one spot.

**Open decision: the notification service.** Candidates are email, Telegram, Slack, or self-hosted ntfy. Pick one
before building. Whatever we choose needs a credential created out of band (see `docs/SETUP.md`) and should include
workflow name, failing node, error message, execution link and run ID. Secrets and prospect data should stay out of
alert payloads.

Related: when we add scheduling, alerts should also cover "ran but found nothing" (`no_results` /
`no_valid_records`), since those complete successfully and would not trigger an error path.

## Crawl helper (drafted, not wired in, crawling not enabled)
`src/prospector/crawl.py` is the one shared fetch helper that docs/CRAWL_POLICY.md section 7 requires. It enforces
the kill switch (`CRAWL_ENABLED`, re-read from `.env` on every request, fails closed), the bot identity (refuses
while the contact URL/email are empty or TODO), the blocklist (checked before every request, matches subdomains),
robots.txt, the section 4 limits, URL exclusions, and the 30-day re-audit interval. It also logs every request and
refusal. Tables are in `db/migrations/V010__crawl.sql` (applied locally 2026-11-08). Tests: `python3 -m unittest tests.test_crawl`
(local stub server only, ~30 s); database store: `PROSPECTOR_DB_TESTS=1 python3 -m unittest tests.test_crawl_psql` (writes and then deletes `dbtest-*` rows).
- Choices the policy doesn't spell out (owner to confirm): robots.txt answers other than 2xx/404/410 skip the site;
  a Crawl-delay over 60 s skips the site; "same registrable domain" is approximated as the start host minus `www.`
  plus its subdomains (stricter); hosts that resolve to private/non-public IPs are refused.
- Not built: an n8n-callable wrapper (n8n audit nodes must call this helper, not prospect hosts), opt-out
  deletion of stored findings, and Playwright request routing. `playwright_context_options()` only sets the
  user agent; a rendered page also loads CSS/JS/images that robots.txt and the rate limits don't cover.
