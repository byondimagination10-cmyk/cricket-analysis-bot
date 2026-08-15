import os
import time
import logging
from threading import Thread
from flask import Flask, request, jsonify
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CRICKET_API_KEY = os.getenv("CRICKET_API_KEY", "").strip()
PUBLIC_BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

BOT_API = f"https://api.telegram.org/bot{TOKEN}"
CRICKET_API = "https://api.cricapi.com/v1/currentMatches"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cricket-bot")

app = Flask(__name__)

MENU = [
    ["🏏 Today's Matches", "📊 Live Match Load"],
    ["🌱 Pitch/Weather", "👤 Player Analysis"],
    ["🧢 Team Analysis", "🔮 Match Prediction"],
]

def tg(method, payload=None):
    r = requests.post(f"{BOT_API}/{method}", json=payload or {}, timeout=25)
    r.raise_for_status()
    return r.json()

def send(chat_id, text, keyboard=True):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = {"keyboard": MENU, "resize_keyboard": True}
    tg("sendMessage", payload)

def get_matches():
    if not CRICKET_API_KEY:
        return []
    r = requests.get(
        CRICKET_API,
        params={"apikey": CRICKET_API_KEY, "offset": 0},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("data", []) if data.get("status") == "success" else []

def score_text(match):
    scores = match.get("score") or []
    if not scores:
        return "Score: unavailable"
    out = []
    for s in scores:
        team = s.get("inning", "")
        r = s.get("r", "-")
        w = s.get("w", "-")
        o = s.get("o", "-")
        out.append(f"{team}: {r}/{w} ({o} ov)")
    return "\n".join(out)

def match_label(m):
    teams = m.get("teams") or []
    name = " vs ".join(teams) if teams else m.get("name", "Match")
    status = m.get("status", "")
    return f"🏏 {name}\n{status}\n{score_text(m)}"

def live_load_line(m):
    # Neutral cricket pressure/load indicator, NOT betting or gambling odds.
    scores = m.get("score") or []
    if not scores:
        return "📈 Live load: score data not available yet."
    s = scores[-1]
    runs = s.get("r")
    wickets = s.get("w")
    overs = s.get("o")
    try:
        runs = float(runs)
        wickets = float(wickets)
        overs = float(overs)
        rr = runs / overs if overs > 0 else 0
        pressure = min(100, max(0, rr * 10 + wickets * 4))
        return (
            f"📈 Live match load: {pressure:.0f}/100\n"
            f"Run rate: {rr:.2f} | Wickets: {int(wickets)}\n"
            "This is a cricket-performance pressure metric, not betting data."
        )
    except Exception:
        return "📈 Live load: calculating from the latest score."

def handle_text(chat_id, text):
    t = (text or "").strip()

    if t.startswith("/start"):
        send(chat_id,
             "Welcome! 🏏\n\nI’m your Cricket Match Analysis Bot.\n"
             "Choose an option below. Live cricket data comes from CricketData/CricAPI when the API key is connected.")
        return

    if t.startswith("/help"):
        send(chat_id,
             "Commands:\n/start - main menu\n/help - help\n/ping - health check\n"
             "/matches - current matches\n/load - neutral live match-performance load")
        return

    if t.startswith("/ping"):
        send(chat_id, "🟢 Bot is online.")
        return

    if t.startswith("/matches") or "Today's Matches" in t:
        if not CRICKET_API_KEY:
            send(chat_id, "⚠️ CRICKET_API_KEY is not connected yet.")
            return
        try:
            matches = get_matches()
            current = [m for m in matches if m.get("matchStarted") and not m.get("matchEnded")]
            if not current:
                send(chat_id, "No live matches found right now.")
            else:
                text_out = "\n\n".join(match_label(m) for m in current[:8])
                send(chat_id, text_out)
        except Exception as e:
            log.exception(e)
            send(chat_id, "⚠️ Cricket data service is temporarily unavailable.")
        return

    if t.startswith("/load") or "Live Match Load" in t:
        if not CRICKET_API_KEY:
            send(chat_id, "⚠️ CRICKET_API_KEY is not connected yet.")
            return
        try:
            matches = get_matches()
            current = [m for m in matches if m.get("matchStarted") and not m.get("matchEnded")]
            if not current:
                send(chat_id, "No live matches found right now.")
            else:
                blocks = []
                for m in current[:8]:
                    teams = " vs ".join(m.get("teams") or ["Match"])
                    blocks.append(f"🏏 {teams}\n{live_load_line(m)}")
                send(chat_id, "\n\n".join(blocks))
        except Exception:
            log.exception("load failed")
            send(chat_id, "⚠️ Could not calculate live load right now.")
        return

    if "Pitch/Weather" in t:
        send(chat_id, "🌱 Pitch/Weather module is ready for venue-based data. It needs a weather/venue provider key before it can show live venue data.")
        return

    if "Player Analysis" in t:
        send(chat_id, "👤 Player Analysis is ready for real player-stat data. No fake statistics are used.")
        return

    if "Team Analysis" in t:
        send(chat_id, "🧢 Team Analysis is ready for real team-stat data. No fake statistics are used.")
        return

    if "Match Prediction" in t:
        send(chat_id, "🔮 Prediction can be generated from real match statistics and conditions. It will not use betting odds or betting recommendations.")
        return

    send(chat_id, "I didn’t understand that. Use the menu below or /help.")

@app.get("/")
def health():
    return jsonify({"ok": True, "service": "cricket-telegram-bot"})

@app.post("/telegram/webhook")
def webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    text = msg.get("text", "")
    chat_id = chat.get("id")
    if chat_id is not None:
        try:
            handle_text(chat_id, text)
        except Exception:
            log.exception("update failed")
    return jsonify({"ok": True})

def configure_webhook():
    if not PUBLIC_BASE_URL:
        log.warning("RENDER_EXTERNAL_URL is missing; webhook was not configured.")
        return
    url = f"{PUBLIC_BASE_URL}/telegram/webhook"
    try:
        result = tg("setWebhook", {"url": url, "drop_pending_updates": True})
        log.info("Webhook result: %s", result)
    except Exception:
        log.exception("Webhook setup failed")

if __name__ == "__main__":
    Thread(target=configure_webhook, daemon=True).start()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
