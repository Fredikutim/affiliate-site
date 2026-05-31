import os, json
from http.server import BaseHTTPRequestHandler

KV_URL = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "")
CONTENT_KEY = "site_content"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond(200, {"ok": True, "data": self._load()})

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(length) if length > 0 else self.rfile.read()
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            self._respond(400, {"ok": False, "error": "Invalid JSON"})
            return
        action = body.get("action", "")
        if action == "login":
            ok = body.get("password") == ADMIN_PASS
            self._respond(200 if ok else 401, {"ok": ok, "error": "" if ok else "Password salah"})
        elif action == "save":
            if body.get("password") != ADMIN_PASS:
                self._respond(401, {"ok": False, "error": "Password salah"})
                return
            content = body.get("content", {})
            self._save(content)
            self._respond(200, {"ok": True, "message": "Tersimpan!"})
        else:
            self._respond(400, {"ok": False, "error": "Unknown action"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _load(self):
        if not KV_URL or not KV_TOKEN:
            return self._default()
        import urllib.request
        try:
            req = urllib.request.Request(f"{KV_URL}/get/{CONTENT_KEY}",
                headers={"Authorization": f"Bearer {KV_TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                result = json.loads(r.read()).get("result")
                return json.loads(result) if result else self._default()
        except:
            return self._default()

    def _save(self, content):
        if not KV_URL or not KV_TOKEN:
            return
        import urllib.request
        try:
            req = urllib.request.Request(f"{KV_URL}/set/{CONTENT_KEY}",
                data=json.dumps(content).encode("utf-8"),
                headers={"Authorization": f"Bearer {KV_TOKEN}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10):
                pass
        except:
            pass

    def _default(self):
        return {"sections": [
            {"id": "investasi", "icon": "💰", "title": "Investasi & Saham", "desc": "Mulai investasi",
             "links": [{"icon": "fas fa-chart-line", "name": "Ajaib", "desc": "Beli saham online mudah & aman", "url": "#"},
                       {"icon": "fas fa-landmark", "name": "Indodax", "desc": "Jual beli aset crypto", "url": "#"},
                       {"icon": "fas fa-coins", "name": "Binance", "desc": "Exchange crypto global", "url": "#"}]},
            {"id": "crypto", "icon": "₿", "title": "Crypto & Aset Digital", "desc": "Dunia kripto",
             "links": [{"icon": "fas fa-coins", "name": "Binance", "desc": "Beli, jual & trading crypto", "url": "#"},
                       {"icon": "fas fa-indonesian-rupiah-sign", "name": "Indodax", "desc": "Platform crypto #1", "url": "#"},
                       {"icon": "fas fa-chart-simple", "name": "Ajaib Saham", "desc": "Investasi saham", "url": "#"}]},
            {"id": "belanja", "icon": "🛍️", "title": "Belanja Online", "desc": "Hemat setiap hari",
             "links": [{"icon": "fas fa-bag-shopping", "name": "Shopee", "desc": "Belanja hemat promo", "url": "#"},
                       {"icon": "fas fa-store", "name": "Tokopedia", "desc": "Marketplace lengkap", "url": "#"},
                       {"icon": "fas fa-box-open", "name": "Lazada", "desc": "Harga terbaik", "url": "#"}]},
            {"id": "travel", "icon": "✈️", "title": "Travel & Akomodasi", "desc": "Rencanakan perjalanan",
             "links": [{"icon": "fas fa-plane", "name": "Traveloka", "desc": "Tiket & hotel", "url": "#"},
                       {"icon": "fas fa-hotel", "name": "Agoda", "desc": "Booking hotel murah", "url": "#"},
                       {"icon": "fas fa-ticket", "name": "Tiket.com", "desc": "Travel partner", "url": "#"}]},
            {"id": "teknologi", "icon": "🤖", "title": "Teknologi & AI", "desc": "Inovasi digital",
             "links": [{"icon": "fas fa-brain", "name": "OpenRouter", "desc": "Akses AI gratis & berbayar", "url": "https://openrouter.ai"},
                       {"icon": "fas fa-microchip", "name": "OpenAI", "desc": "ChatGPT & DALL-E", "url": "#"},
                       {"icon": "fas fa-robot", "name": "Claude AI", "desc": "AI dari Anthropic", "url": "#"},
                       {"icon": "fas fa-globe", "name": "IDwebhost", "desc": "Hosting murah", "url": "#"},
                       {"icon": "fas fa-server", "name": "Niagahoster", "desc": "Hosting terbaik", "url": "#"}]},
            {"id": "keuangan", "icon": "🏦", "title": "Keuangan Digital", "desc": "Transaksi online",
             "links": [{"icon": "fas fa-wallet", "name": "DANA", "desc": "Dompet digital", "url": "#"},
                       {"icon": "fas fa-credit-card", "name": "GoPay", "desc": "Bayar online", "url": "#"},
                       {"icon": "fas fa-hand-holding-heart", "name": "OVO", "desc": "Cashback digital", "url": "#"},
                       {"icon": "fas fa-link", "name": "LinkAja", "desc": "Keuangan BUMN", "url": "#"}]}
        ]}
