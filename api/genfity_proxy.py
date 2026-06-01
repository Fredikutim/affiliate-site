import json, urllib.request, urllib.error, ssl
from http.server import BaseHTTPRequestHandler

DEFAULT_KEY = "genfity_67041d941c16155f2b9ada47f66dc1d12fadd580"
BASE = "https://ai.genfity.com/v1"
ctx = ssl._create_unverified_context()

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Genfity-Key")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8"))
            api_key = self.headers.get("X-Genfity-Key", "") or DEFAULT_KEY
            endpoint = body.get("_endpoint", "chat")
            api_path = "/messages" if endpoint == "anthropic" else "/chat/completions"
            if "_endpoint" in body:
                del body["_endpoint"]
            data = json.dumps(body).encode()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            if endpoint == "anthropic":
                headers["anthropic-version"] = "2023-06-01"
            req = urllib.request.Request(BASE + api_path, data=data, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, context=ctx, timeout=55)
            result = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(result)
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:500]
            self.reply(502, {"error": {"message": f"Genfity {e.code}: {err}"}})
        except Exception as e:
            self.reply(500, {"error": {"message": str(e)[:300]}})

    def reply(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
