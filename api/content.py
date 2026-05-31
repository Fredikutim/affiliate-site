import os, json
from http.server import BaseHTTPRequestHandler

KV_URL = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")
CONTENT_KEY = "site_content"

DEFAULT = {"hero": {"title": "Solusi Investasi, Crypto & Bisnis", "highlight": "Modern & Terpercaya", "subtitle": "Kumpulan link afiliasi pilihan FREDI SUSANTO BENGALON KUTIM untuk investasi, crypto, belanja, travel, teknologi, dan keuangan digital."}, "sections": [
    {"id": "investasi", "icon": "💰", "title": "Investasi & Saham", "desc": "Mulai investasi dengan platform terpercaya",
     "links": [{"icon": "https://events.rumah123.com/wp-content/uploads/sites/41/2024/07/09091711/aplikasi-investasi-saham-terbaik-indonesia-ajaib.jpg", "name": "Ajaib", "desc": "Investasi & trading saham #1. Daftar pakai kode fred9092961423 dapat 1 lot saham!", "url": "https://referral.ajaib.co.id/ZGpZ"},
               {"icon": "https://i.ibb.co.com/R4YX4ykb/thumbnail-bibit.jpg", "name": "Bibit", "desc": "Cashback reksa dana Rp25.000. Pakai kode referral fredi10", "url": "https://linkto.bibit.id/SJpp/referralbibit"},
               {"icon": "https://i.ibb.co.com/Lz920NHN/gotrade.jpg", "name": "GoTrade", "desc": "Investasi saham US seperti Apple, Nvidia, Tesla mulai dari $1. Kode: 084528", "url": "https://heygotrade.com/referral?code=084528"}]},
    {"id": "crypto", "icon": "₿", "title": "Crypto & Aset Digital", "desc": "Jual beli crypto dan aset digital terpercaya",
     "links": [{"icon": "https://i.ibb.co.com/dssg6MBC/binance.jpg", "name": "Binance", "desc": "Kode referral: CPA_005KZ21YMN. Exchange crypto & trading global terbesar!", "url": "https://www.bmwweb.biz/id/activity/referral-entry/CPA?ref=CPA_005KZ21YMN&utm_medium=web_share_copy"},
               {"icon": "https://play-lh.googleusercontent.com/6CQfcfp68tooMc1-0vyLlCE0E2NpihXkHEIUYl5FHMJRUG76mdP3vyU-jh8GgcJR0Fs", "name": "Indodax", "desc": "Jual beli crypto terpercaya #1 di Indonesia. Daftar sekarang!", "url": "https://indodax.onelink.me/qyYY/referral?deep_link_value=page:register,id:fredisusanto"},
               {"icon": "https://i.ibb.co.com/NdSBz1LQ/Exness-Logo.jpg", "name": "Copy Trade", "desc": "Copy trading sosial terpercaya untuk hasil maksimal", "url": "https://social-trading.pro/a/3xskp6r8ju/?platform=mobile"},
               {"icon": "https://i.ibb.co.com/27tXrhsn/OIP.jpg", "name": "BtcDana", "desc": "Mulai perjalanan menuju kekayaan! Kode undangan: AMBILBONUS", "url": "https://reg.btcdana.org/fx/indonesia/btcDana/activity_collection/register?data=eyJpbnZpdGVJZCI6IkFNQklMQk9OVVMiLCJhY3Rpdml0eUlkIjoiIiwidXNlclNvdXJjZSI6IiJ9"}]},
    {"id": "forex", "icon": "💹", "title": "Forex & Trading", "desc": "Trading forex dan investasi dalam satu tempat",
     "links": [{"icon": "https://play-lh.googleusercontent.com/HPi97LY8tXg54Ys2QTThvQXLNeGLUxdoltW_Fe1v_vZNKS1aF5_n_BfywNNADjMH1pk", "name": "Quick Pro", "desc": "Download Quick Pro now! Platform trading forex paling canggih", "url": "https://quickpro.go.link/i9bAl"},
               {"icon": "https://i.ibb.co.com/dssg6MBC/binance.jpg", "name": "Binance", "desc": "Kode referral: CPA_005KZ21YMN. Exchange crypto & trading global terbesar!", "url": "https://www.bmwweb.biz/id/activity/referral-entry/CPA?ref=CPA_005KZ21YMN&utm_medium=web_share_copy"},
               {"icon": "https://play-lh.googleusercontent.com/6CQfcfp68tooMc1-0vyLlCE0E2NpihXkHEIUYl5FHMJRUG76mdP3vyU-jh8GgcJR0Fs", "name": "Indodax", "desc": "Jual beli crypto terpercaya #1 di Indonesia. Daftar sekarang!", "url": "https://indodax.onelink.me/qyYY/referral?deep_link_value=page:register,id:fredisusanto"},
               {"icon": "https://i.ibb.co.com/NdSBz1LQ/Exness-Logo.jpg", "name": "Social Trading", "desc": "Platform trading sosial terpercaya untuk hasil maksimal", "url": "https://social-trading.pro/a/3xskp6r8ju/?platform=mobile"}]},
    {"id": "belanja", "icon": "🛍️", "title": "Belanja Online", "desc": "Hemat setiap hari dari marketplace favorit",
     "links": [{"icon": "https://i.ibb.co.com/8gMVt4yh/shopee.png", "name": "Shopee", "desc": "Belanja hemat pakai link afiliasi! Kode tim: ZKDPCLV", "url": "https://s.shopee.co.id/5L9B2O2w2u"},
               {"icon": "fas fa-store", "name": "Tokopedia", "desc": "Marketplace lengkap kebutuhan harian Anda", "url": "#"},
               {"icon": "fas fa-box-open", "name": "Lazada", "desc": "Belanja online dengan harga terbaik setiap hari", "url": "#"}]},
    {"id": "keuangan", "icon": "🏦", "title": "Keuangan Digital", "desc": "Transaksi & pembayaran online lebih hemat",
     "links": [{"icon": "fas fa-credit-card", "name": "GoPay", "desc": "Klaim saldo GoPay Rp10.000! Upgrade GoPay Plus gratis sekarang", "url": "https://app.gopay.co.id/NF8p/m1hxthvj"},
               {"icon": "fas fa-arrow-right-arrow-left", "name": "Flip", "desc": "Transfer gratis & top up e-wallet bebas biaya admin! Kode: QDNZ7900", "url": "https://flip.id/s/rqdnz7900"},
               {"icon": "https://i.ibb.co.com/hJ6qqZtS/wondr-bni-logo-png-seeklogo-632166.png", "name": "Wondr by BNI", "desc": "Promo ajak teman, Rp50 Juta & iPhone 17 Pro menanti!", "url": "https://app-wondr.bni.co.id/MIT4/qugxkwil"},
               {"icon": "fas fa-wallet", "name": "DANA", "desc": "Dompet digital untuk transaksi harian yang praktis", "url": "#"},
               {"icon": "fas fa-hand-holding-heart", "name": "OVO", "desc": "Cashback & pembayaran digital favorit Indonesia", "url": "#"},
               {"icon": "fas fa-link", "name": "LinkAja", "desc": "Keuangan digital dari BUMN terpercaya", "url": "#"}]},
    {"id": "travel", "icon": "✈️", "title": "Travel & Akomodasi", "desc": "Rencanakan perjalanan Anda",
     "links": [{"icon": "fas fa-plane", "name": "Traveloka", "desc": "Pesan tiket pesawat, hotel & aktivitas", "url": "#"},
               {"icon": "fas fa-hotel", "name": "Agoda", "desc": "Booking hotel murah di seluruh dunia", "url": "#"},
               {"icon": "fas fa-ticket", "name": "Tiket.com", "desc": "Travel partner for every journey", "url": "#"}]},
    {"id": "teknologi", "icon": "🤖", "title": "Teknologi & AI", "desc": "Inovasi digital untuk bisnis Anda",
     "links": [{"icon": "fas fa-brain", "name": "OpenRouter", "desc": "Akses berbagai model AI gratis & berbayar", "url": "https://openrouter.ai"},
               {"icon": "fas fa-microchip", "name": "OpenAI", "desc": "ChatGPT, GPT-4, DALL-E & lainnya", "url": "#"},
               {"icon": "fas fa-globe", "name": "IDwebhost", "desc": "Hosting & domain murah Indonesia", "url": "#"},
               {"icon": "fas fa-server", "name": "Niagahoster", "desc": "Hosting terbaik untuk website Anda", "url": "#"}]}
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
