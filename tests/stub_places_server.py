"""Local stub of Places Text Search (New) for testing the n8n workflow without paid calls.
Run: python3 -I tests/stub_places_server.py [port]   Logs each request to stdout.
textQuery 'EMPTY' -> {} ; 'ENDLESS' -> always returns a nextPageToken ; otherwise 3 pages (3+2+2 places).
"""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

def place(i):
    return {"id": f"ChIJstub{i:04d}", "displayName": {"text": f"Stub HVAC {i}"},
            "formattedAddress": f"{i} Test St, Troy, MI", "primaryType": "hvac_contractor",
            "nationalPhoneNumber": f"(248) 555-{i:04d}", "websiteUri": f"https://example.com/{i}"}

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        q, tok = body.get("textQuery", ""), body.get("pageToken")
        pages = {None: (range(1, 4), "p2"), "p2": (range(4, 6), "p3"), "p3": (range(6, 8), None)}
        if q == "EMPTY":
            out = {}
        elif q == "ENDLESS":
            out = {"places": [place(100)], "nextPageToken": "again"}
        else:
            ids, nxt = pages[tok]
            out = {"places": [place(i) for i in ids]}
            if nxt: out["nextPageToken"] = nxt
        print(json.dumps({"query": q, "pageToken": tok, "mask": self.headers.get("X-Goog-FieldMask"),
                          "has_key": bool(self.headers.get("X-Goog-Api-Key"))}), flush=True)
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass

HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8099), H).serve_forever()
