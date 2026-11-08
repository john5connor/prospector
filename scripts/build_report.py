#!/usr/bin/env python3
"""Build a one-page HTML report per qualified prospect into data/reports/<token>/index.html (local only).
Usage: python3 scripts/build_report.py [prospect_id ...]   (default: all qualified prospects)
Nothing is published or sent; hosting is a separate, owner-approved step."""
import html, json, os, secrets, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
env = {k: v for k, v in (l.strip().split('=', 1) for l in open(ROOT / '.env') if '=' in l and not l.startswith('#'))}
def psql(sql):
    r = subprocess.run(['docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', env['POSTGRES_USER'], '-d', env['PROSPECTOR_DB'],
                        '-v', 'ON_ERROR_STOP=1', '-tA', '-c', sql], cwd=ROOT, capture_output=True, text=True, check=True)
    return r.stdout.strip()
ids = [int(a) for a in sys.argv[1:]]
where = f"p.id IN ({','.join(map(str, ids))})" if ids else "q.qualified"
rows = json.loads(psql(f"""SELECT COALESCE(json_agg(t), '[]') FROM (
  SELECT p.id, p.name, p.address, p.rating, p.review_count, a.id AS run_id, a.ran_at::date AS measured, a.scores, a.metrics,
    (SELECT json_agg(f ORDER BY CASE f.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, f.id)
       FROM findings f WHERE f.audit_run_id = a.id) AS findings
  FROM prospects p JOIN qualifications q ON q.prospect_id = p.id
  JOIN LATERAL (SELECT * FROM audit_runs WHERE prospect_id = p.id AND kind='pagespeed' AND status='ok' ORDER BY ran_at DESC LIMIT 1) a ON true
  WHERE {where}) t""") or '[]')
CSS = "body{font:16px/1.5 system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;color:#1a1a1a}h1{font-size:1.5rem;margin:.2em 0}.sub{color:#555}.card{border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:14px 0}.high{border-left:6px solid #c62828}.medium{border-left:6px solid #ef8f00}.low{border-left:6px solid #888}.tag{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:#555}.ev{color:#555;font-size:.9rem}footer{color:#666;font-size:.85rem;margin-top:28px;border-top:1px solid #ddd;padding-top:10px}"
for r in rows:
    fs = r['findings'] or []
    names = {f['check_name'] for f in fs}
    fs = [f for f in fs if not (f['check_name'] == 'seo' and names & {'meta-description', 'title'})][:3]
    if not fs: print(f"skip {r['name']}: no findings"); continue
    existing = psql(f"SELECT token FROM reports WHERE prospect_id={r['id']}")
    token = existing or secrets.token_urlsafe(24)
    cards = ''.join(f"<div class='card {html.escape(f['severity'])}'><div class='tag'>{html.escape(f['severity'])} priority</div><p><strong>{html.escape(f['business_impact_text'])}</strong></p><p class='ev'>What we measured: {html.escape(f['evidence'] or '')}</p></div>" for f in fs)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Website check-up: {html.escape(r['name'])}</title><style>{CSS}</style></head><body>
<p class="tag">Private website check-up</p><h1>{html.escape(r['name'])}</h1>
<p class="sub">{html.escape(r['address'] or '')}</p>
<p>We looked at your public website on a phone-sized screen. Here are the {len(fs)} things most likely to cost you customers.</p>
{cards}
<footer>Measured automatically with Google PageSpeed Insights (mobile) on {r['measured']}. Scores can vary between runs, so treat these as a snapshot, not a verdict.
This page is private and was prepared for {html.escape(r['name'])} only. Prepared by: TODO (sender name and postal address are added before any outreach).</footer></body></html>"""
    d = ROOT / 'data' / 'reports' / token; d.mkdir(parents=True, exist_ok=True); (d / 'index.html').write_text(page)
    fid = ','.join(str(f['id']) for f in fs)
    psql(f"INSERT INTO reports (prospect_id, token, finding_ids, audit_run_id, local_path) VALUES ({r['id']}, '{token}', ARRAY[{fid}], {r['run_id']}, 'data/reports/{token}/index.html') "
         f"ON CONFLICT (prospect_id) DO UPDATE SET finding_ids=EXCLUDED.finding_ids, audit_run_id=EXCLUDED.audit_run_id, local_path=EXCLUDED.local_path, generated_at=now()")
    print(f"{r['name']}: {len(fs)} findings -> data/reports/{token}/index.html")
