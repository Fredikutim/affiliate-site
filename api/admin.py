import os, json
from http.server import BaseHTTPRequestHandler
import urllib.request

KV_URL = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin123")
CONTENT_KEY = "site_content"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        if not KV_URL or not KV_TOKEN:
            self._json(200, {"ok": True, "data": self._default_content()})
            return
        try:
            data = self._kv_get(CONTENT_KEY)
            if data:
                self._json(200, {"ok": True, "data": json.loads(data)})
            else:
                self._json(200, {"ok": True, "data": self._default_content()})
        except:
            self._json(200, {"ok": True, "data": self._default_content()})

    def do_POST(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        action = body.get("action", "")
        if action == "login":
            if body.get("password") == ADMIN_PASS:
                self._json(200, {"ok": True})
            else:
                self._json(401, {"ok": False, "error": "Password salah"})
        elif action == "save":
            if body.get("password") != ADMIN_PASS:
                self._json(401, {"ok": False, "error": "Password salah"})
                return
            content = body.get("content", {})
            if KV_URL and KV_TOKEN:
                self._kv_set(CONTENT_KEY, json.dumps(content))
            self._json(200, {"ok": True, "message": "Tersimpan! Deploy ulang..."})
        else:
            self._json(400, {"ok": False, "error": "Unknown action"})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _kv_get(self, key):
        req = urllib.request.Request(f"{KV_URL}/get/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("result")

    def _kv_set(self, key, value):
        req = urllib.request.Request(f"{KV_URL}/set/{key}",
            data=json.dumps(value).encode(),
            headers={"Authorization": f"Bearer {KV_TOKEN}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            pass

    def _default_content(self):
        return {"sections": [
            {"id": "investasi", "icon": "💰", "title": "Investasi & Saham", "desc": "Mulai investasi dengan platform terpercaya",
             "links": [
                {"icon": "fas fa-chart-line", "name": "Ajaib", "desc": "Beli saham online mudah & aman", "url": "#"},
                {"icon": "fas fa-landmark", "name": "Indodax", "desc": "Jual beli aset crypto terbesar di Indonesia", "url": "#"},
                {"icon": "fas fa-coins", "name": "Binance", "desc": "Exchange crypto global terdepan", "url": "#"}
             ]},
            {"id": "crypto", "icon": "₿", "title": "Crypto & Aset Digital", "desc": "Dunia kripto dalam genggaman",
             "links": [
                {"icon": "fas fa-coins", "name": "Binance", "desc": "Beli, jual & trading crypto", "url": "#"},
                {"icon": "fas fa-indonesian-rupiah-sign", "name": "Indodax", "desc": "Platform crypto #1 Indonesia", "url": "#"},
                {"icon": "fas fa-chart-simple", "name": "Ajaib Saham", "desc": "Investasi saham & reksadana", "url": "#"}
             ]},
            {"id": "belanja", "icon": "🛍️", "title": "Belanja Online", "desc": "Hemat setiap hari dari marketplace favorit",
             "links": [
                {"icon": "fas fa-bag-shopping", "name": "Shopee", "desc": "Belanja hemat dengan promo & voucher", "url": "#"},
                {"icon": "fas fa-store", "name": "Tokopedia", "desc": "Marketplace lengkap kebutuhan harian", "url": "#"},
                {"icon": "fas fa-box-open", "name": "Lazada", "desc": "Belanja online dengan harga terbaik", "url": "#"}
             ]},
            {"id": "travel", "icon": "✈️", "title": "Travel & Akomodasi", "desc": "Rencanakan perjalanan Anda",
             "links": [
                {"icon": "fas fa-plane", "name": "Traveloka", "desc": "Pesan tiket pesawat, hotel & aktivitas", "url": "#"},
                {"icon": "fas fa-hotel", "name": "Agoda", "desc": "Booking hotel murah di seluruh dunia", "url": "#"},
                {"icon": "fas fa-ticket", "name": "Tiket.com", "desc": "Travel partner for every journey", "url": "#"}
             ]},
            {"id": "teknologi", "icon": "🤖", "title": "Teknologi & AI", "desc": "Inovasi digital untuk bisnis Anda",
             "links": [
                {"icon": "fas fa-brain", "name": "OpenRouter", "desc": "Akses berbagai model AI gratis & berbayar", "url": "https://openrouter.ai"},
                {"icon": "fas fa-microchip", "name": "OpenAI", "desc": "ChatGPT, GPT-4, DALL-E & lainnya", "url": "#"},
                {"icon": "fas fa-robot", "name": "Claude AI", "desc": "AI assistant canggih dari Anthropic", "url": "#"},
                {"icon": "fas fa-globe", "name": "IDwebhost", "desc": "Hosting & domain murah Indonesia", "url": "#"},
                {"icon": "fas fa-server", "name": "Niagahoster", "desc": "Hosting terbaik untuk website Anda", "url": "#"}
             ]},
            {"id": "keuangan", "icon": "🏦", "title": "Keuangan Digital", "desc": "Transaksi & pembayaran online",
             "links": [
                {"icon": "fas fa-wallet", "name": "DANA", "desc": "Dompet digital untuk transaksi harian", "url": "#"},
                {"icon": "fas fa-credit-card", "name": "GoPay", "desc": "Bayar online dengan GoPay", "url": "#"},
                {"icon": "fas fa-hand-holding-heart", "name": "OVO", "desc": "Cashback & pembayaran digital", "url": "#"},
                {"icon": "fas fa-link", "name": "LinkAja", "desc": "Keuangan digital dari BUMN", "url": "#"}
             ]}
        ]}
