import json
from http.server import BaseHTTPRequestHandler
import requests

API_KEY = "genfity_67041d941c16155f2b9ada47f66dc1d12fadd580"
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
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            if endpoint == "anthropic":
                headers["anthropic-version"] = "2023-06-01"
            resp = requests.post(BASE + api_path, json=body, headers=headers, timeout=30)
            self.send_response(resp.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp.content)
        except Exception as e:
            self.reply(500, {"error": {"message": str(e)[:300]}})

    def reply(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
