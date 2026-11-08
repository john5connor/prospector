# Crawl Policy (DRAFT, not approved)

Status: **DRAFT.** No audit code may fetch a prospect's site until the owner approves this file
and fills the two `TODO` values. Applies to every automated request to a prospect's own website
(audit stage, spec 4.3). It does not cover Google APIs, which are governed by their terms and quotas.

## 1. Identity
- User agent: `ProspectorAuditBot/0.1 (+TODO-contact-URL-explaining-the-bot; TODO-contact-email)`
- The contact page must say who runs the bot, why it visits, and how to opt out. Opt-out requests are
  honored within 1 business day by adding the domain to `crawl_blocklist` (see section 7).
- Do not use a browser-impersonating user agent. Playwright runs with this same user agent.

## 2. What may be fetched
- Public pages only, over HTTP(S) GET (and the PageSpeed Insights API, which fetches on Google's side).
- Starting URL = the prospect's own `website_url`, plus: homepage, and links found on it that stay on the same
  registrable domain and look like contact / services / about / booking pages.
- Never: logins, carts/checkout, forms submissions (no POST), URLs with query strings that look like search or
  session tokens, file downloads over 5 MB, or anything behind authentication.
- Social-media and directory URLs (Facebook, Yelp, etc.) are **never crawled** by this bot. Their terms restrict
  automated access. Those prospects are reviewed by a human or via an official API only.

## 3. robots.txt
- Fetch `/robots.txt` once per host per run before any other request.
- Respect `Disallow` rules that apply to our user agent or `*`, and any `Crawl-delay` (use the larger of that and
  the delay in section 4).
- robots.txt 404 means allowed. robots.txt unreachable (5xx/timeout) means skip the site this run and log it.
- If the homepage itself is disallowed, no audit of that site. Mark `audit_status = 'blocked_robots'`.

## 4. Rate and size limits
| Limit | Value |
|---|---|
| Delay between requests to the same host | 2 s (never concurrent to one host) |
| Max pages per site per run | 10 |
| Max crawl depth | 2 from the homepage |
| Per-request timeout | 15 s |
| Max response body read | 5 MB |
| Retries | 1 retry on network error/5xx after 10 s, then give up. No retry on 4xx. 429 or 403: stop crawling that host for the run |
| Max sites in flight | 3 (different hosts only) |
| Re-audit interval for the same site | no more than once per 30 days unless the owner requests it |

## 5. What is stored
Keep derived findings, not copies of sites.
- Stored: normalized findings `{check, severity, evidence, screenshot_ref}`, PageSpeed scores, HTTP status/SSL
  facts, detected CMS/tech, and mobile screenshots used as evidence in that prospect's report.
- Not stored: full page HTML archives, copies of images or text for reuse, personal data found on pages
  (staff names, personal emails). Contact emails used for outreach come from the site's own published contact
  info and are kept only on the outreach record.
- Screenshots and findings are deleted if the prospect opts out or 12 months after the last audit, whichever
  is first.

## 6. Use of the results
- Findings feed the report for that business only. Reports are private, unguessable URLs shown to that business.
- Previews use stock imagery, never the prospect's own photos or copy (spec 4.5).
- Nothing found by the crawl is posted publicly.

## 7. Enforcement in code
- One shared fetch helper enforces sections 1-4. No audit node makes direct HTTP calls to prospect hosts.
- Table `crawl_blocklist(domain, reason, added_at)` is checked before every fetch.
- Every fetch is logged: URL, status, bytes, duration, robots decision. The log is the audit trail.
- A kill switch (`CRAWL_ENABLED=false` in `.env`) stops all prospect-site fetching.

## 8. Open items for the owner
1. Fill in the user agent contact URL and email (a page and mailbox that you control; I won't use your personal email).
2. Confirm limits in section 4 (10 pages, 2 s delay, 30-day re-audit).
3. Confirm the 12-month retention in section 5.
4. Approve or change: social URLs are never crawled by the bot.
