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
            endpoint = body.pop("_endpoint", "chat")
            api_path = "/messages" if endpoint == "anthropic" else "/chat/completions"
            data = json.dumps(body).encode()
            req = urllib.request.Request(
                BASE + api_path,
                data=data,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(result)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:500]
            self.reply(502, {"error": {"message": f"HTTP {e.code}: {err_body}"}})
        except Exception as e:
            self.reply(500, {"error": {"message": str(e)[:300]}})

    def reply(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
