import os, json
from http.server import BaseHTTPRequestHandler

KV_URL = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")
CONTENT_KEY = "site_content"

DEFAULT = {"hero": {"title": "Solusi Bisnis & Investasi", "highlight": "Terpercaya", "subtitle": "Kumpulan link afiliasi terpercaya untuk investasi, belanja, perjalanan, dan teknologi."}, "sections": [
    {"id": "investasi", "icon": "💰", "title": "Investasi & Saham", "desc": "Mulai investasi dengan platform terpercaya",
     "links": [{"icon": "fas fa-chart-line", "name": "Ajaib", "desc": "Beli saham online mudah & aman", "url": "#"},
               {"icon": "fas fa-landmark", "name": "Indodax", "desc": "Jual beli aset crypto terbesar", "url": "#"},
               {"icon": "fas fa-coins", "name": "Binance", "desc": "Exchange crypto global", "url": "#"}]},
    {"id": "crypto", "icon": "₿", "title": "Crypto & Aset Digital", "desc": "Dunia kripto dalam genggaman",
     "links": [{"icon": "fas fa-coins", "name": "Binance", "desc": "Beli, jual & trading crypto", "url": "#"},
               {"icon": "fas fa-indonesian-rupiah-sign", "name": "Indodax", "desc": "Platform crypto #1", "url": "#"},
               {"icon": "fas fa-chart-simple", "name": "Ajaib Saham", "desc": "Investasi saham", "url": "#"}]},
    {"id": "belanja", "icon": "🛍️", "title": "Belanja Online", "desc": "Hemat setiap hari dari marketplace",
     "links": [{"icon": "fas fa-bag-shopping", "name": "Shopee", "desc": "Belanja hemat promo", "url": "#"},
               {"icon": "fas fa-store", "name": "Tokopedia", "desc": "Marketplace lengkap", "url": "#"},
               {"icon": "fas fa-box-open", "name": "Lazada", "desc": "Harga terbaik", "url": "#"}]},
    {"id": "travel", "icon": "✈️", "title": "Travel & Akomodasi", "desc": "Rencanakan perjalanan Anda",
     "links": [{"icon": "fas fa-plane", "name": "Traveloka", "desc": "Tiket & hotel", "url": "#"},
               {"icon": "fas fa-hotel", "name": "Agoda", "desc": "Booking hotel murah", "url": "#"},
               {"icon": "fas fa-ticket", "name": "Tiket.com", "desc": "Travel partner", "url": "#"}]},
    {"id": "teknologi", "icon": "🤖", "title": "Teknologi & AI", "desc": "Inovasi digital untuk bisnis",
     "links": [{"icon": "fas fa-brain", "name": "OpenRouter", "desc": "Akses AI gratis & berbayar", "url": "https://openrouter.ai"},
               {"icon": "fas fa-microchip", "name": "OpenAI", "desc": "ChatGPT & DALL-E", "url": "#"},
               {"icon": "fas fa-robot", "name": "Claude AI", "desc": "AI dari Anthropic", "url": "#"},
               {"icon": "fas fa-globe", "name": "IDwebhost", "desc": "Hosting murah", "url": "#"},
               {"icon": "fas fa-server", "name": "Niagahoster", "desc": "Hosting terbaik", "url": "#"}]},
    {"id": "keuangan", "icon": "🏦", "title": "Keuangan Digital", "desc": "Transaksi & pembayaran online",
     "links": [{"icon": "fas fa-wallet", "name": "DANA", "desc": "Dompet digital", "url": "#"},
               {"icon": "fas fa-credit-card", "name": "GoPay", "desc": "Bayar online", "url": "#"},
               {"icon": "fas fa-hand-holding-heart", "name": "OVO", "desc": "Cashback digital", "url": "#"},
               {"icon": "fas fa-link", "name": "LinkAja", "desc": "Keuangan BUMN", "url": "#"}]}
]}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        send = self.send_response
        send(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if not KV_URL or not KV_TOKEN:
            self.wfile.write(json.dumps(DEFAULT).encode())
            return
        import urllib.request
        try:
            req = urllib.request.Request(f"{KV_URL}/get/{CONTENT_KEY}", headers={"Authorization": f"Bearer {KV_TOKEN}"})
            with urllib.request.urlopen(req, timeout=5) as r:
                v = json.loads(r.read()).get("result")
                if v:
                    self.wfile.write(v.encode())
                else:
                    self.wfile.write(json.dumps(DEFAULT).encode())
        except:
            self.wfile.write(json.dumps(DEFAULT).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
