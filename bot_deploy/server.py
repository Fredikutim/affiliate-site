#!/usr/bin/env python3
"""Deploy entry: runs Fredy BinanceBot 24/7 with Flask health endpoint"""
import os, sys, time, logging, threading, json

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.path.insert(0, BASE)

LOG_FILE = os.path.join(BASE, "bot_deploy.log")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
log = logging.getLogger(__name__)

# Patch ctypes for Linux compatibility
import builtins
_orig_import = builtins.__import__
def _safe_import(name, *args, **kwargs):
    if name == 'ctypes' and sys.platform != 'win32':
        import types
        m = types.ModuleType('ctypes')
        class KD: SetThreadExecutionState = staticmethod(lambda x: None)
        class WD: kernel32 = KD()
        class W: windll = WD(); __class__ = type('windll_type', (), {})
        m.windll = W.windll
        return m
    return _orig_import(name, *args, **kwargs)
builtins.__import__ = _safe_import

# Import bot
log.info("Starting Fredy BinanceBot...")
import bot
log.info("Bot module loaded")

bot_thread = None
bot_running = False

def start_bot():
    global bot_thread, bot_running
    if bot_running:
        return
    bot_running = True
    bot_thread = threading.Thread(target=bot.trading_bot, daemon=True, name="bot")
    bot_thread.start()
    log.info("Bot thread launched")

app = None
try:
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route("/")
    @app.route("/health")
    def health():
        return jsonify({
            "status": "running" if (bot_thread and bot_thread.is_alive()) else "starting",
            "uptime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "positions": len(bot.positions) if hasattr(bot, 'positions') else 0
        })

    @app.route("/status")
    def status():
        pos_list = {}
        if hasattr(bot, 'positions'):
            for s, p in bot.positions.items():
                pos_list[s] = {"side": p["side"], "entry": p["entry"], "qty": p["qty"]}
        return jsonify({
            "positions": pos_list,
            "count": len(pos_list),
            "api_blocked": bot.API_BLOCKED if hasattr(bot, 'API_BLOCKED') else False,
            "log": read_tail(LOG_FILE, 30)
        })

    def read_tail(f, n):
        try:
            with open(f) as fh:
                return "".join(fh.readlines()[-n:])
        except:
            return ""
except ImportError:
    log.info("Flask not available — running headless")

if __name__ == "__main__":
    start_bot()

    if app:
        port = int(os.environ.get("PORT", 7860))
        log.info(f"Server on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    else:
        while True:
            time.sleep(120)
            alive = bot_thread and bot_thread.is_alive()
            log.info(f"[PING] Bot alive={alive}")
