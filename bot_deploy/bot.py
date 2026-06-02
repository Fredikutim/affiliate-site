import os, math, time, logging, threading, json, re, ssl, traceback, subprocess
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import pandas as pd
import numpy as np

SSL_VERIFY = False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = 'a5OSS4g33V4lmzmMcIhFxwOGpwrcVy8ByKajnm8kda8dGApi14XzmueSSDRbXMyM'
API_SECRET = 'dJuntErBK4xu1WBQkSQ6Aim7MdTq2fM8NOjp5KuCArb90hkGmyD6yS32g7LTCvYo'

# Force no proxy agar tidak dicegat firewall/antivirus
import os
os.environ["NO_PROXY"] = "api.binance.com,api1.binance.com,api2.binance.com,api3.binance.com"
os.environ["no_proxy"] = os.environ["NO_PROXY"]
# Bypass SSL interception: set custom adapter di client nanti


# ─── VPN AUTO-ACTIVATION ───────────────────────────────────────────────────────
VPN_SCRIPT = "D:\\FelixBot\\vpn-manager.ps1"
VPN_AUTO = False  # disable VPN untuk Linux deployment

def ensure_vpn():
    if not VPN_AUTO:
        return
    try:
        r = urlopen("https://api.binance.com/api/v3/ping", timeout=5)
        if r.status == 200:
            return
    except:
        pass
    log.info("[VPN] Binance API tidak reachable — auto-activating Proton VPN...")
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", VPN_SCRIPT, "-Action", "activate"],
            capture_output=True, timeout=30
        )
        time.sleep(3)
        try:
            r = urlopen("https://api.binance.com/api/v3/ping", timeout=5)
            if r.status == 200:
                log.info("[VPN] Proton VPN aktif — Binance API reachable!")
                return
        except:
            pass
        log.warning("[VPN] Gagal: VPN aktif tapi Binance masih blokir")
    except Exception as e:
        log.warning(f"[VPN] Error: {e}")

# ─── KONFIGURASI ────────────────────────────────────────────────────────────────
TIMEOUT = 30
MAX_RETRY = 5
RETRY_INTERVAL = 30

# Scan
MIN_VOLUME_USDT = 5000     # minimal 24h volume untuk di-scan
SCAN_INTERVAL = 60 * 15    # scan ulang tiap 15 menit
CHECK_INTERVAL = 15        # cek posisi tiap 15 detik

# Risk — micro balance ($23.55)
RISK_PER_TRADE = 30.0      # 30% modal per trade (~$7)
GLOBAL_RISK_LIMIT = 60.0   # max 60% modal total
MAX_POSITIONS_SPOT = 1     # 1 posisi aja (modal kecil)
MAX_POSITIONS_FUTURES = 0  # spot dulu, futures mati
LEVERAGE = 1

# Target & Stop
TARGET_PROFIT_MIN = 5.0    # minimal TP (%)
TARGET_PROFIT_MAX = 20.0   # maksimal TP (%)
STOP_LOSS_ATR = 1.5        # SL ketat (1.5x ATR)
TAKE_PROFIT_ATR = 4.0      # TP lebar (4x ATR)
TRAILING_ACTIVATE = 3.0    # trailing aktif setelah profit %
TRAILING_DISTANCE = 2.0    # jarak trailing

# Fallback: kalo Binance API diblokir ISP/antivirus
COINGECKO_FALLBACK = True
MANUAL_BALANCE_USDT = 0  # pakai saldo real dari API

# Scoring untuk deteksi potensi 10%+
VOLUME_SPIKE_THRESHOLD = 2.0
ATR_MIN_PCT = 2.0          # minimal ATR% untuk dianggap volatil
R_HIGH = 30                 # range lookback untuk breakout
TREND_LOOKBACK = 50

# Wallet allocation
SPOT_ALLOCATION = 0.8       # 80% saldo ke spot
FUTURES_ALLOCATION = 0.0    # futures mati (modal kecil)
FUNDING_RESERVE = 0.2       # 20% cadangan
MIN_TRANSFER = 5            # minimal transfer USDT

# ─── SETUP ──────────────────────────────────────────────────────────────────────
LOG_FILE = "bot_log_ultimate.txt"
log_file_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file_abs, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

client = Client(API_KEY, API_SECRET, requests_params={"verify": False, "timeout": TIMEOUT})

# ─── RATE LIMITER ────────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, max_calls=1200, period=60):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = threading.Lock()
    def wait(self):
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                t = self.calls[0] + self.period - now + 1
                log.warning(f"[RL] Rate limit, wait {t:.0f}s")
                time.sleep(t)
                self.calls = []
            self.calls.append(time.time())
rate_limiter = RateLimiter()

def api_call(func, *args, **kwargs):
    rate_limiter.wait()
    for i in range(MAX_RETRY):
        try:
            return func(*args, **kwargs)
        except (BinanceAPIException, BinanceRequestException, ConnectionError) as e:
            log.warning(f"[API] Error ({i+1}/{MAX_RETRY}): {e}")
            time.sleep(RETRY_INTERVAL)
        except Exception as e:
            log.warning(f"[API] {e}")
            if i == MAX_RETRY - 1: raise
            time.sleep(RETRY_INTERVAL)

# ─── SSL CONTEXT ─────────────────────────────────────────────────────────────────
_ssl_ctx = ssl.create_default_context() if SSL_VERIFY else ssl._create_unverified_context()

# ─── PREVENT SLEEP ───────────────────────────────────────────────────────────────
def keep_awake():
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    except:
        pass

# ─── LOT FILTERS ─────────────────────────────────────────────────────────────────
DEFAULT_PAIRS = [
    {"symbol": "BTCUSDT","base": "BTC","min_qty": 0.00001,"step_size": 0.00001,"tick_size": 0.01},
    {"symbol": "ETHUSDT","base": "ETH","min_qty": 0.00001,"step_size": 0.00001,"tick_size": 0.01},
    {"symbol": "SOLUSDT","base": "SOL","min_qty": 0.001,"step_size": 0.001,"tick_size": 0.001},
    {"symbol": "BNBUSDT","base": "BNB","min_qty": 0.001,"step_size": 0.001,"tick_size": 0.001},
    {"symbol": "XRPUSDT","base": "XRP","min_qty": 0.1,"step_size": 0.1,"tick_size": 0.0001},
    {"symbol": "ADAUSDT","base": "ADA","min_qty": 0.1,"step_size": 0.1,"tick_size": 0.0001},
    {"symbol": "DOGEUSDT","base": "DOGE","min_qty": 1.0,"step_size": 1.0,"tick_size": 0.00001},
    {"symbol": "AVAXUSDT","base": "AVAX","min_qty": 0.01,"step_size": 0.01,"tick_size": 0.001},
    {"symbol": "DOTUSDT","base": "DOT","min_qty": 0.01,"step_size": 0.01,"tick_size": 0.001},
    {"symbol": "LINKUSDT","base": "LINK","min_qty": 0.01,"step_size": 0.01,"tick_size": 0.001},
    {"symbol": "MATICUSDT","base": "MATIC","min_qty": 0.1,"step_size": 0.1,"tick_size": 0.0001},
    {"symbol": "UNIUSDT","base": "UNI","min_qty": 0.01,"step_size": 0.01,"tick_size": 0.001},
    {"symbol": "SHIBUSDT","base": "SHIB","min_qty": 1000.0,"step_size": 1000.0,"tick_size": 0.00000001},
    {"symbol": "LTCUSDT","base": "LTC","min_qty": 0.001,"step_size": 0.001,"tick_size": 0.01},
    {"symbol": "ATOMUSDT","base": "ATOM","min_qty": 0.01,"step_size": 0.01,"tick_size": 0.001},
]

def get_exchange_info_usdt():
    try:
        info = api_call(client.get_exchange_info)
        if not info or "symbols" not in info or not info["symbols"]:
            log.warning(f"[EXCHANGE] Response kosong, pakai {len(DEFAULT_PAIRS)} default")
            return list(DEFAULT_PAIRS)
        pairs = []
        for s in info["symbols"]:
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING":
                try:
                    min_qty = float(next(f["minQty"] for f in s["filters"] if f["filterType"] == "LOT_SIZE"))
                    step_size = float(next(f["stepSize"] for f in s["filters"] if f["filterType"] == "LOT_SIZE"))
                    tick_size = float(next(f["tickSize"] for f in s["filters"] if f["filterType"] == "PRICE_FILTER"))
                except:
                    min_qty, step_size, tick_size = 0.001, 0.001, 0.001
                pairs.append({"symbol": s["symbol"],"base": s["baseAsset"],"min_qty": min_qty,"step_size": step_size,"tick_size": tick_size})
        if not pairs:
            log.warning(f"[EXCHANGE] 0 pair dari API, pakai default")
            return list(DEFAULT_PAIRS)
        log.info(f"[EXCHANGE] {len(pairs)} USDT pairs ditemukan")
        return pairs
    except Exception as e:
        log.warning(f"[EXCHANGE] Gagal: {e}, pakai {len(DEFAULT_PAIRS)} default")
        return list(DEFAULT_PAIRS)

def get_24hr_tickers():
    try:
        tickers = api_call(client.get_ticker)
        if tickers:
            result = {}
            for t in tickers:
                if not isinstance(t, dict) or "symbol" not in t:
                    continue
                if t["symbol"].endswith("USDT"):
                    try:
                        vol = float(t.get("quoteVolume", 0))
                        if vol >= MIN_VOLUME_USDT:
                            result[t["symbol"]] = {
                                "symbol": t["symbol"],
                                "price": float(t.get("lastPrice", 0)),
                                "change_pct": float(t.get("priceChangePercent", 0)),
                                "high": float(t.get("highPrice", 0)),
                                "low": float(t.get("lowPrice", 0)),
                                "volume_usdt": vol,
                            }
                    except:
                        continue
            if result:
                return result
        log.info("[TICKER] API Binance kosong, pakai CoinGecko fallback")
    except:
        log.info("[TICKER] API Binance gagal, pakai CoinGecko fallback")

    # CoinGecko fallback: batch request untuk semua coin
    try:
        cg_ids = [SYMBOL_TO_CG[p["symbol"]] for p in DEFAULT_PAIRS if p["symbol"] in SYMBOL_TO_CG]
        if not cg_ids:
            return {}
        _cg_rate_limit()
        ids = ",".join(cg_ids)
        ctx = ssl._create_unverified_context()
        req = Request(f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true", headers={"User-Agent": "Mozilla/5.0"})
        r = urlopen(req, context=ctx, timeout=15)
        data = json.loads(r.read())
        if not data:
            return {}
        reverse_map = {v: k for k, v in SYMBOL_TO_CG.items()}
        result = {}
        for cg_id, info in data.items():
            sym = reverse_map.get(cg_id, "")
            vol = float(info.get("usd_24h_vol", 0) or 0)
            if vol >= MIN_VOLUME_USDT:
                result[sym] = {"symbol": sym, "price": float(info.get("usd", 0)), "change_pct": float(info.get("usd_24h_change", 0) or 0), "volume_usdt": vol}
        log.info(f"[CG] Batch ticker: {len(result)} pair")
        return result
    except Exception as e:
        log.warning(f"[CG] Batch ticker gagal: {e}")
        return {}

# ─── KLINES ──────────────────────────────────────────────────────────────────────
API_BLOCKED = False  # flag: true kalo Binance API ngembaliin kosong

def get_klines(symbol, interval="5m", limit=60):
    global API_BLOCKED
    try:
        klines = api_call(client.get_klines, symbol=symbol, interval=interval, limit=limit)
        if not klines or len(klines) < 20:
            if not API_BLOCKED:
                log.warning("[!] Binance API tidak reachable — pastikan VPN aktif")
                API_BLOCKED = True
            raise Exception("Empty response")
        if API_BLOCKED:
            log.info("[+] Binance API normal lagi!")
            API_BLOCKED = False
        df = pd.DataFrame(klines, columns=["t","o","h","l","c","v","tc","qv","n","tbv","tbq","ig"])
        for c in ["o","h","l","c","v"]: df[c] = pd.to_numeric(df[c])
        return df
    except:
        if COINGECKO_FALLBACK:
            return get_klines_coingecko(symbol, interval, limit)
        return None

# ─── COINGECKO FALLBACK ──────────────────────────────────────────────────────────
SYMBOL_TO_CG = {
    "BTCUSDT":"bitcoin","ETHUSDT":"ethereum","SOLUSDT":"solana","BNBUSDT":"binancecoin",
    "XRPUSDT":"ripple","ADAUSDT":"cardano","DOGEUSDT":"dogecoin","AVAXUSDT":"avalanche-2",
    "DOTUSDT":"polkadot","LINKUSDT":"chainlink","MATICUSDT":"matic-network","UNIUSDT":"uniswap",
    "SHIBUSDT":"shiba-inu","LTCUSDT":"litecoin","ATOMUSDT":"cosmos","ETCUSDT":"ethereum-classic",
    "XLMUSDT":"stellar","FILUSDT":"filecoin","TRXUSDT":"tron","NEARUSDT":"near",
    "APTUSDT":"aptos","ARBUSDT":"arbitrum","OPUSDT":"optimism","SUIUSDT":"sui",
    "PEPEUSDT":"pepe","INJUSDT":"injective-protocol","TIAUSDT":"celestia","SEIUSDT":"sei-network",
    "FETUSDT":"fetch-ai","AGIXUSDT":"singularitynet","WIFUSDT":"dogwifcoin","BONKUSDT":"bonk",
    "RUNEUSDT":"thorchain","AAVEUSDT":"aave","MKRUSDT":"maker","CRVUSDT":"curve-dao-token",
    "COMPUSDT":"compound-governance-token","SUSHIUSDT":"sushi","CAKEUSDT":"pancakeswap",
}
CG_CACHE = {"prices": {}, "time": 0}
CG_RATE_LIMIT = threading.Semaphore(1)  # Maks 1 request parallel
CG_LAST_CALL = 0

def _cg_rate_limit():
    global CG_LAST_CALL
    elapsed = time.time() - CG_LAST_CALL
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)
    CG_LAST_CALL = time.time()

def get_klines_coingecko(symbol, interval="5m", limit=60):
    cg_id = SYMBOL_TO_CG.get(symbol)
    if not cg_id:
        return None
    days_map = {"5m": 1, "15m": 2, "1h": 7, "4h": 30, "1d": 90}
    days = days_map.get(interval, 1)
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    try:
        _cg_rate_limit()
        ctx = ssl._create_unverified_context()
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urlopen(req, context=ctx, timeout=15)
        data = json.loads(r.read())
        if not data or len(data) < 20:
            return None
        df = pd.DataFrame(data, columns=["t","o","h","l","c"])
        for c in ["o","h","l","c"]: df[c] = pd.to_numeric(df[c])
        df["v"] = 0
        return df.tail(limit)
    except Exception as e:
        log.warning(f"[CG] {symbol}: {e}")
        return None

def get_price_coingecko(symbol):
    cg_id = SYMBOL_TO_CG.get(symbol)
    if not cg_id:
        return 0
    now = time.time()
    if now - CG_CACHE["time"] < 60 and cg_id in CG_CACHE["prices"]:
        return CG_CACHE["prices"][cg_id]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
    try:
        _cg_rate_limit()
        ctx = ssl._create_unverified_context()
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urlopen(req, context=ctx, timeout=10)
        data = json.loads(r.read())
        price = data.get(cg_id, {}).get("usd", 0)
        CG_CACHE["prices"][cg_id] = price
        CG_CACHE["time"] = now
        return price
    except:
        return 0

def get_ticker_coingecko(symbol):
    cg_id = SYMBOL_TO_CG.get(symbol)
    if not cg_id:
        return None
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}?localization=false&tickers=false&community_data=false&developer_data=false"
    try:
        _cg_rate_limit()
        ctx = ssl._create_unverified_context()
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        r = urlopen(req, context=ctx, timeout=10)
        data = json.loads(r.read())
        if not data or "market_data" not in data:
            return None
        md = data["market_data"]
        vol = md.get("total_volume", {}).get("usd", 0) or 0
        if vol < MIN_VOLUME_USDT:
            return None
        return {
            "price": md.get("current_price", {}).get("usd", 0),
            "change_pct": md.get("price_change_percentage_24h", 0) or 0,
            "high": md.get("high_24h", {}).get("usd", 0) or 0,
            "low": md.get("low_24h", {}).get("usd", 0) or 0,
            "volume_usdt": vol,
        }
    except Exception as e:
        return None

# ─── INDICATORS ──────────────────────────────────────────────────────────────────
def sma(series, period): return series.rolling(window=period).mean()
def ema(series, span): return series.ewm(span=span).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_atr(df, period=14):
    h, l, c = pd.to_numeric(df["h"]), pd.to_numeric(df["l"]), pd.to_numeric(df["c"])
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_bb(series, period=20, std=2):
    m = series.rolling(window=period).mean()
    s = series.rolling(window=period).std()
    return m + s * std, m - s * std

def calc_macd(series, fast=12, slow=26, signal=9):
    e1 = series.ewm(span=fast).mean()
    e2 = series.ewm(span=slow).mean()
    macd = e1 - e2
    sig = macd.ewm(span=signal).mean()
    hist = macd - sig
    return macd, sig, hist

# ─── SCORING ─────────────────────────────────────────────────────────────────────
def score_pair(symbol, ticker, df):
    """Skor potensi 10%+ untuk sebuah pair. Return (score, reasons, atr_val, atr_pct)"""
    if df is None or len(df) < 50:
        return 0, [], 0, 0

    price = float(df["c"].iloc[-1])
    close = pd.to_numeric(df["c"])
    high = pd.to_numeric(df["h"])
    low = pd.to_numeric(df["l"])
    vol = pd.to_numeric(df["v"])

    score = 0
    reasons = []

    # ── 1. Volume surge ──
    avg_vol = vol.tail(20).mean()
    last_vol = vol.iloc[-1]
    vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
    if vol_ratio > VOLUME_SPIKE_THRESHOLD:
        score += 25
        reasons.append(f"Vol surge {vol_ratio:.1f}x")
    elif vol_ratio > 1.5:
        score += 10
        reasons.append(f"Vol {vol_ratio:.1f}x")

    # ── 2. ATR Volatility ──
    atr_s = calc_atr(df)
    atr_val = atr_s.iloc[-1] if not pd.isna(atr_s.iloc[-1]) else 0
    atr_pct = (atr_val / price) * 100 if price > 0 else 0
    if atr_pct >= ATR_MIN_PCT:
        a_score = min(25, atr_pct * 3)
        score += a_score
        reasons.append(f"ATR {atr_pct:.1f}%")

    # ── 3. Breakout detection ──
    recent_high = close.tail(R_HIGH).max()
    if price >= recent_high * 0.98:
        score += 20
        reasons.append("Near range high")
    # Breakout: price above resistance
    if price > sma(close, 50).iloc[-1]:
        score += 10
        reasons.append("Above MA50")

    # ── 4. RSI ──
    rsi_s = calc_rsi(close)
    rsi = rsi_s.iloc[-1] if not pd.isna(rsi_s.iloc[-1]) else 50
    rsi_prev = rsi_s.iloc[-3] if not pd.isna(rsi_s.iloc[-3]) else 50
    if 30 <= rsi <= 50:
        score += 15
        reasons.append(f"RSI {rsi:.0f}")
    elif rsi < 30:
        score += 20
        reasons.append(f"RSI oversold {rsi:.0f}")
    # RSI turning up from oversold
    if rsi_prev <= 30 and rsi > rsi_prev:
        score += 10
        reasons.append("RSI recovery")

    # ── 5. MACD ──
    macd, sig, hist = calc_macd(close)
    if not pd.isna(macd.iloc[-1]) and not pd.isna(sig.iloc[-1]):
        if macd.iloc[-2] <= sig.iloc[-2] and macd.iloc[-1] > sig.iloc[-1]:
            score += 15
            reasons.append("MACD cross up")
        elif macd.iloc[-1] > sig.iloc[-1]:
            score += 5

    # ── 6. Support / Oversold bounce ──
    bb_u, bb_l = calc_bb(close)
    if not pd.isna(bb_l.iloc[-1]) and price <= bb_l.iloc[-1] * 1.02:
        score += 10
        reasons.append("Near lower BB")

    # ── 7. 24h change ──
    chg = abs(ticker.get("change_pct", 0))
    if chg > 5:
        score += 5
    if chg > 10:
        score += 5

    # ── 8. Price momentum (higher lows) ──
    if len(close) >= 20:
        low_10 = close.tail(10).min()
        low_20 = close.tail(20).min()
        if low_10 > low_20:
            score += 5
            reasons.append("Higher lows")

    # ── 9. Volume confirmation ──
    vol_increasing = vol.tail(3).mean() > vol.tail(10).mean()
    if vol_increasing and score > 30:
        score += 5

    return min(100, score), reasons, atr_val, atr_pct

# ─── WALLET MANAGEMENT ───────────────────────────────────────────────────────────
WALLET_CACHE = {"spot": 0, "futures": 0, "funding": 0, "time": 0}

def get_all_balances():
    now = time.time()
    if now - WALLET_CACHE["time"] < 900:
        return WALLET_CACHE["spot"], WALLET_CACHE["futures"], WALLET_CACHE["funding"]

    spot = 0.0
    futures = 0.0
    funding = 0.0
    api_ok = False

    try:
        acct = api_call(client.get_account)
        if acct and "balances" in acct:
            for b in acct["balances"]:
                if b["asset"] == "USDT":
                    spot = float(b["free"]) + float(b["locked"])
                    api_ok = True
                    break
    except:
        pass

    if api_ok:
        try:
            facct = api_call(client.futures_account)
            if facct and "assets" in facct:
                for b in facct["assets"]:
                    if b["asset"] == "USDT":
                        futures = float(b.get("walletBalance", 0))
                        break
        except:
            pass
    else:
        log.warning("[WALLET] API gagal, pakai cache terakhir")
        if WALLET_CACHE["spot"] > 0 or WALLET_CACHE["futures"] > 0:
            return WALLET_CACHE["spot"], WALLET_CACHE["futures"], WALLET_CACHE["funding"]
        spot = MANUAL_BALANCE_USDT
        futures = MANUAL_BALANCE_USDT

    spot_alloc = spot * SPOT_ALLOCATION
    futures_alloc = futures * FUTURES_ALLOCATION
    funding = spot + futures - spot_alloc - futures_alloc

    WALLET_CACHE["spot"] = spot_alloc
    WALLET_CACHE["futures"] = futures_alloc
    WALLET_CACHE["funding"] = funding
    WALLET_CACHE["time"] = now

    return spot_alloc, futures_alloc, funding

def transfer_between_wallets(asset, amount, from_type, to_type):
    """Transfer antar wallet.
    from_type/to_type: 'SPOT', 'FUTURES', 'FUNDING'
    """
    type_map = {
        ("SPOT", "FUTURES"): "MAIN_UMFUTURE",
        ("FUTURES", "SPOT"): "UMFUTURE_MAIN",
        ("SPOT", "FUNDING"): "MAIN_FUNDING",
        ("FUNDING", "SPOT"): "FUNDING_MAIN",
        ("FUNDING", "FUTURES"): "FUNDING_UMFUTURE",
        ("FUTURES", "FUNDING"): "UMFUTURE_FUNDING",
    }
    key = (from_type.upper(), to_type.upper())
    ttype = type_map.get(key)
    if not ttype:
        log.error(f"[TRANSFER] Unknown type: {from_type} → {to_type}")
        return False

    if amount < MIN_TRANSFER:
        log.info(f"[TRANSFER] Amount {amount:.2f} < MIN {MIN_TRANSFER}, skip")
        return False

    try:
        result = api_call(client.make_universal_transfer,
            type=ttype,
            asset=asset,
            amount=str(round(amount, 2)))
        log.info(f"[TRANSFER] {amount:.2f} {asset} {from_type}→{to_type} OK (tranId: {result.get('tranId','?')})")
        WALLET_CACHE["time"] = 0  # invalidate cache
        return True
    except Exception as e:
        log.error(f"[TRANSFER] {from_type}→{to_type} {amount:.2f} {asset} GAGAL: {e}")
        return False

def rebalance_wallets():
    """Atur ulang saldo ke proporsi yang ditentukan"""
    spot, futures, funding = get_all_balances()
    total = spot + futures + funding
    if total < 10:
        log.info(f"[REBALANCE] Total {total:.2f} terlalu kecil, skip")
        return

    target_spot = total * SPOT_ALLOCATION
    target_futures = total * FUTURES_ALLOCATION
    target_funding = total * FUNDING_RESERVE

    log.info(f"[REBALANCE] Spot: {spot:.2f}/{target_spot:.2f} Futures: {futures:.2f}/{target_futures:.2f} Funding: {funding:.2f}/{target_funding:.2f}")

    # funding → futures
    if funding > target_funding + MIN_TRANSFER:
        excess = min(funding - target_funding, total * 0.3)
        if futures < target_futures:
            need = target_futures - futures
            amt = min(excess, need)
            if amt >= MIN_TRANSFER:
                transfer_between_wallets("USDT", amt, "FUNDING", "FUTURES")

    # spot → futures
    if spot > target_spot + MIN_TRANSFER and futures < target_futures:
        excess = spot - target_spot
        need = target_futures - futures
        amt = min(excess, need)
        if amt >= MIN_TRANSFER:
            transfer_between_wallets("USDT", amt, "SPOT", "FUTURES")

    # futures → spot
    if futures > target_futures + MIN_TRANSFER and spot < target_spot:
        excess = futures - target_futures
        need = target_spot - spot
        amt = min(excess, need)
        if amt >= MIN_TRANSFER:
            transfer_between_wallets("USDT", amt, "FUTURES", "SPOT")

    # funding → spot
    if funding > target_funding + MIN_TRANSFER and spot < target_spot:
        excess = funding - target_funding
        need = target_spot - spot
        amt = min(excess, need)
        if amt >= MIN_TRANSFER:
            transfer_between_wallets("USDT", amt, "FUNDING", "SPOT")

# ─── POSITION MANAGEMENT ─────────────────────────────────────────────────────────
positions = {}
all_pairs_cache = []
total_risk_pct = 0

def get_spot_balance(asset="USDT"):
    try:
        return float(api_call(client.get_asset_balance, asset=asset)["free"])
    except:
        return 0.0

def get_spot_qty(symbol):
    base = symbol.replace("USDT", "")
    return get_spot_balance(base)

def get_futures_qty(symbol):
    try:
        pos = api_call(client.futures_position_information, symbol=symbol)
        for p in pos:
            if p["symbol"] == symbol:
                return abs(float(p["positionAmt"]))
    except:
        pass
    return 0.0

def adjust_qty(qty, step_size, min_qty):
    if step_size > 0:
        p = max(0, len(str(step_size).split(".")[-1].rstrip("0")))
        qty = math.floor(qty / step_size) * step_size
        qty = round(qty, p)
    return max(qty, min_qty)

def place_order_spot(symbol, side, qty):
    try:
        fn = api_call(client.order_market_buy if side == "BUY" else client.order_market_sell,
                      symbol=symbol, quantity=qty)
        log.info(f"[SPOT] {side} {qty} {symbol}")
        return fn
    except Exception as e:
        log.error(f"[SPOT] {side} {qty} {symbol} GAGAL: {e}")
        return None

def place_order_futures(symbol, side, qty):
    try:
        fn = api_call(client.futures_create_order,
                      symbol=symbol, side=side, type="MARKET", quantity=qty)
        log.info(f"[FUTURES] {side} {qty} {symbol}")
        return fn
    except Exception as e:
        log.error(f"[FUTURES] {side} {qty} {symbol} GAGAL: {e}")
        return None

def enter_trade(symbol, price, score, reasons, atr_val, mode="SPOT"):
    global total_risk_pct
    if total_risk_pct + RISK_PER_TRADE > GLOBAL_RISK_LIMIT:
        log.warning(f"[ENTRY] {symbol} skip — global risk limit {GLOBAL_RISK_LIMIT}% reached")
        return False

    if mode == "SPOT" and len([p for p in positions if positions[p]["mode"] == "SPOT"]) >= MAX_POSITIONS_SPOT:
        log.warning(f"[ENTRY] {symbol} skip — max SPOT positions ({MAX_POSITIONS_SPOT})")
        return False
    if mode == "FUTURES" and len([p for p in positions if positions[p]["mode"] == "FUTURES"]) >= MAX_POSITIONS_FUTURES:
        log.warning(f"[ENTRY] {symbol} skip — max FUTURES positions ({MAX_POSITIONS_FUTURES})")
        return False

    # Calculate SL/TP
    sl_dist = atr_val * STOP_LOSS_ATR if atr_val > 0 else price * 0.02
    tp_dist = atr_val * TAKE_PROFIT_ATR if atr_val > 0 else price * 0.05
    sl_price = price - sl_dist
    tp_price = price + tp_dist

    # Adjust TP untuk target 10%+ jika ATR kecil
    target_pct = max(TARGET_PROFIT_MIN, min(TARGET_PROFIT_MAX, atr_val / price * 100 * 3 if price > 0 else TARGET_PROFIT_MIN))
    tp_price = max(tp_price, price * (1 + target_pct / 100))

    # Hitung qty berdasarkan risk
    risk_amt = get_available_balance(mode) * (RISK_PER_TRADE / 100)
    rpu = price - sl_price
    if rpu <= 0: rpu = price * 0.02
    raw_qty = risk_amt / rpu

    # Cap ke available balance
    avail = get_available_balance(mode)
    max_qty = avail / price if price > 0 else 0
    raw_qty = min(raw_qty, max_qty)

    # Cari step_size & min_qty
    step_size = get_step_size(symbol)
    min_qty = get_min_qty(symbol)
    qty = adjust_qty(raw_qty, step_size, min_qty)

    if qty <= 0:
        log.warning(f"[ENTRY] {symbol} qty=0, skip")
        return False

    # Place order
    if mode == "SPOT":
        result = place_order_spot(symbol, "BUY", qty)
    else:
        # Set leverage
        try:
            api_call(client.futures_change_leverage, symbol=symbol, leverage=LEVERAGE)
        except:
            pass
        result = place_order_futures(symbol, "BUY", qty)

    if result:
        filled_qty = float(result.get("executedQty", qty))
        if filled_qty <= 0:
            log.warning(f"[ENTRY] {symbol} filled qty=0")
            return False
        positions[symbol] = {
            "side": "BUY",
            "mode": mode,
            "entry": price,
            "qty": filled_qty,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "high": price,
            "low": price,
            "trailing": False,
            "score": score,
            "reasons": reasons,
        }
        total_risk_pct += RISK_PER_TRADE
        log.info(f"[ENTRY] {symbol} {mode} BUY {filled_qty} @ {price:.4f} | SL: {sl_price:.4f} TP: {tp_price:.4f} | Score: {score}")
        log.info(f"[ENTRY] Alasan: {', '.join(reasons)}")
        return True

    return False

def get_available_balance(mode="SPOT"):
    spot, futures, funding = get_all_balances()
    if mode == "SPOT":
        return spot * 0.95
    else:
        return futures * 0.95

def get_price(symbol):
    """Ambil harga dari Binance API, fallback ke CoinGecko"""
    try:
        t = api_call(client.get_symbol_ticker, symbol=symbol)
        if t and "price" in t:
            return float(t["price"])
    except:
        pass
    if COINGECKO_FALLBACK:
        return get_price_coingecko(symbol)
    return 0

def get_step_size(symbol):
    for p in all_pairs_cache:
        if p["symbol"] == symbol:
            return p["step_size"]
    return 0.001

def get_min_qty(symbol):
    for p in all_pairs_cache:
        if p["symbol"] == symbol:
            return p["min_qty"]
    return 0.001

# ─── EXIT MANAGEMENT ─────────────────────────────────────────────────────────────
def check_exit(symbol, pos, price):
    """Cek apakah posisi harus ditutup"""
    if pos["side"] == "BUY":
        pnl_pct = (price - pos["entry"]) / pos["entry"] * 100

        # TP hit
        if price >= pos["tp_price"]:
            return f"TP {pnl_pct:.1f}%"

        # SL hit
        if price <= pos["sl_price"]:
            return f"SL {pnl_pct:.1f}%"

        # Trailing stop
        if price > pos["high"]:
            pos["high"] = price
        if pnl_pct >= TRAILING_ACTIVATE and not pos["trailing"]:
            pos["trailing"] = True
            pos["sl_price"] = price * (1 - TRAILING_DISTANCE / 100)
            log.info(f"[TRAIL] {symbol} activated at {pnl_pct:.1f}%")
        if pos["trailing"]:
            new_sl = price * (1 - TRAILING_DISTANCE / 100)
            if new_sl > pos["sl_price"]:
                pos["sl_price"] = new_sl
            if price <= pos["sl_price"]:
                return f"TRAIL_HIT {pnl_pct:.1f}%"

        # Early exit if score was low and price goes against
        if pnl_pct < -8:
            return f"STOP {pnl_pct:.1f}%"

    return None

def close_trade(symbol, reason):
    global total_risk_pct
    pos = positions.get(symbol)
    if not pos:
        return

    side = "SELL"
    try:
        price = get_price(symbol)
    except:
        price = pos["entry"]

    pnl = (price - pos["entry"]) if pos["side"] == "BUY" else (pos["entry"] - price)
    pnl_pct = (pnl / pos["entry"]) * 100 if pos["entry"] else 0

    log.info(f"[EXIT] {symbol} {reason} | {pos['mode']} {pos['side']} {pos['qty']} @ {price:.4f} | P&L: {pnl_pct:+.2f}%")

    if pos["mode"] == "SPOT":
        place_order_spot(symbol, side, pos["qty"])
    else:
        place_order_futures(symbol, side, pos["qty"])

    total_risk_pct -= RISK_PER_TRADE
    del positions[symbol]

# ─── MAIN BOT ────────────────────────────────────────────────────────────────────
def format_time(ts):
    return datetime.fromtimestamp(ts/1000).strftime("%H:%M") if ts > 1e12 else datetime.fromtimestamp(ts).strftime("%H:%M")

def trading_bot():
    keep_awake()
    log.info("="*60)
    log.info("=== BOT ULTIMATE — ALL COINS, SPOT+FUTURES, AUTO TRANSFER ===")
    log.info("="*60)
    log.info(f"Risk/trade: {RISK_PER_TRADE}% | Global limit: {GLOBAL_RISK_LIMIT}%")
    log.info(f"Target profit: {TARGET_PROFIT_MIN}-{TARGET_PROFIT_MAX}% | SL: {STOP_LOSS_ATR}x ATR")
    log.info(f"Max positions: SPOT {MAX_POSITIONS_SPOT} | FUTURES {MAX_POSITIONS_FUTURES}")
    log.info(f"Wallet allocation: SPOT {SPOT_ALLOCATION*100:.0f}% | FUTURES {FUTURES_ALLOCATION*100:.0f}% | FUNDING {FUNDING_RESERVE*100:.0f}%")
    log.info("[!] ISP Indonesia blokir api.binance.com")
    log.info("[!] Bot akan auto-aktifkan VPN Proton jika diperlukan")
    log.info("[!] Kalo VPN gagal, pakai data CoinGecko + saldo manual")
    ensure_vpn()

    all_pairs = get_exchange_info_usdt()
    if not all_pairs:
        log.info("[!] API kosong, pakai 15 default pair")
        all_pairs = list(DEFAULT_PAIRS)

    last_scan = 0
    scored_pairs = []  # list of (symbol, score, reasons, atr)
    last_rebalance = 0

    all_pairs_cache.clear()
    all_pairs_cache.extend(all_pairs)

    while True:
        try:
            now = time.time()
            spot_bal, futures_bal, funding_bal = get_all_balances()
            total_bal = spot_bal + futures_bal + funding_bal
            active_pos = len(positions)

            # Rebalance tiap 30 menit
            if now - last_rebalance > 1800:
                rebalance_wallets()
                last_rebalance = now

            # ── EXIT MANAGEMENT ──
            for sym in list(positions.keys()):
                pos = positions[sym]
                price = get_price(sym)
                reason = check_exit(sym, pos, price)
                if reason:
                    close_trade(sym, reason)
                    time.sleep(1)

            # ── SCAN ──
            if now - last_scan > SCAN_INTERVAL and active_pos < (MAX_POSITIONS_SPOT + MAX_POSITIONS_FUTURES):
                log.info("[SCAN] Mencari peluang di SEMUA coin Binance...")
                tickers = get_24hr_tickers()
                log.info(f"[SCAN] {len(tickers)} pair dengan volume > ${MIN_VOLUME_USDT:,}")

                scored = []
                for pair_info in all_pairs:
                    sym = pair_info["symbol"]
                    if sym in positions:
                        continue
                    if sym not in tickers:
                        continue

                    df = get_klines(sym, "5m", TREND_LOOKBACK)
                    score, reasons, atr_val, atr_pct = score_pair(sym, tickers[sym], df)

                    if score >= 30:
                        price = tickers[sym]["price"]
                        change = tickers[sym].get("change_pct", 0)
                        scored.append((sym, score, reasons, atr_val, atr_pct, price, change))

                # Sort by score descending
                scored.sort(key=lambda x: x[1], reverse=True)
                scored_pairs = scored[:20]  # top 20

                log.info(f"[SCAN] Top 5 peluang:")
                for i, s in enumerate(scored[:5]):
                    log.info(f"  {i+1}. {s[0]} score={s[1]} | ATR {s[4]:.1f}% | 24h {s[6]:+.1f}% | {', '.join(s[2][:3])}")

                # ── ENTRY ──
                can_enter_spot = len([p for p in positions if positions[p]["mode"] == "SPOT"]) < MAX_POSITIONS_SPOT
                can_enter_futures = len([p for p in positions if positions[p]["mode"] == "FUTURES"]) < MAX_POSITIONS_FUTURES
                total_can_enter = active_pos < (MAX_POSITIONS_SPOT + MAX_POSITIONS_FUTURES)

                if total_can_enter and total_bal > 5:
                    for sym, score, reasons, atr_val, atr_pct, price, change in scored[:10]:
                        if sym in positions:
                            continue
                        if not total_can_enter:
                            break

                        # Spot only (micro balance)
                        if can_enter_spot and spot_bal > 5:
                            mode = "SPOT"
                            can_enter_spot = False
                        else:
                            continue

                        if enter_trade(sym, price, score, reasons, atr_val, mode):
                            total_can_enter = False
                            log.info(f"[SCAN] Entry {sym} {mode} score={score}")
                            time.sleep(2)

                last_scan = now

            # ── STATUS ──
            pos_list = []
            for s, p in positions.items():
                pnl = 0
                cur = get_price(s)
                if cur > 0:
                    pnl = (cur - p["entry"]) / p["entry"] * 100
                else:
                    cur = p["entry"]
                pos_list.append(f"{s}={p['mode']}{p['side'][0]}@{p['entry']:.4f}({pnl:+.1f}%)")

            pos_str = ", ".join(pos_list) if pos_list else "KOSONG"
            block_tag = " [API BLOKIR]" if API_BLOCKED else ""
            status = f"[STATUS] Posisi: {active_pos}/{MAX_POSITIONS_SPOT+MAX_POSITIONS_FUTURES} | Risk: {total_risk_pct:.1f}/{GLOBAL_RISK_LIMIT}% | Balance: SPOT {spot_bal:.2f} FUT {futures_bal:.2f} FUND {funding_bal:.2f}{block_tag}"
            log.info(f"{status} | {pos_str}")

            # Top peluang
            if scored_pairs:
                top = scored_pairs[0]
                log.info(f"[TOPMOST] {top[0]} score={top[1]} ATR {top[4]:.1f}%")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            log.info("[!] Bot dihentikan user")
            for sym in list(positions.keys()):
                close_trade(sym, "FORCE_CLOSE")
            break
        except Exception as e:
            log.error(f"[-] Loop error: {e}")
            traceback.print_exc()
            time.sleep(30)

if __name__ == "__main__":
    try:
        trading_bot()
    finally:
        log.info("=== BOT ULTIMATE SELESAI ===")
