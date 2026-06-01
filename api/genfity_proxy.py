import json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler

API_KEY = "genfity_cb5ffbbb8207d3f34764e293d47d54f5a330fd09"
BASE = "https://ai.genfity.com/v1"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8"))
            data = json.dumps(body).encode()
            req = urllib.request.Request(
                BASE + "/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=30)
            result = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(result)
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:500]
            self.reply(502, {"error": {"message": err}})
        except Exception as e:
            self.reply(500, {"error": {"message": str(e)[:200]}})

    def reply(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
