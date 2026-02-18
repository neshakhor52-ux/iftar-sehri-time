import os
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BD_TZ = ZoneInfo("Asia/Dhaka")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATA_FILE = os.getenv("DATA_FILE", "iftar_sehri_2026_bd_districtwise.json")

HELP_TEXT = (
    "✅ ব্যবহার:\n"
    "• /today <district>\n"
    "   উদাহরণ: /today ঢাকা\n"
    "• /date YYYY-MM-DD <district>\n"
    "   উদাহরণ: /date 2026-03-05 ঢাকা\n"
    "• অথবা শুধু জেলার নাম লিখুন: ঢাকা / নারায়ণগঞ্জ / গাজীপুর ...\n\n"
    "ℹ️ ডাটা: ইসলামিক ফাউন্ডেশন (জেলা-ভিত্তিক ২০২৬ রমজান সময়সূচি)\n"
)

def norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "", s)
    # remove common suffixes
    s = s.replace("জেলা", "").replace("গেলা", "").replace(".", "")
    return s

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Build normalized index (so user can type with/without spaces/জেলা)
    idx = {}
    for k in raw.keys():
        idx[norm(k)] = k
        idx[norm(k.replace(" জেলা", ""))] = k
        idx[norm(k.replace(" গেলা", ""))] = k
    return raw, idx

DATA, INDEX = load_data()

def today_iso() -> str:
    return datetime.now(BD_TZ).strftime("%Y-%m-%d")

def find_district(user_text: str):
    key = norm(user_text)
    if key in INDEX:
        return INDEX[key]
    # partial contains match (fallback)
    for nk, real in INDEX.items():
        if key and key in nk:
            return real
    return None

def build_reply(date_iso: str, district_input: str) -> str:
    district = find_district(district_input)
    if not district:
        return (
            f"❌ জেলা পাওয়া যায়নি: {district_input}\n"
            "টিপস: বাংলা জেলা নাম লিখুন (যেমন ঢাকা, নারায়ণগঞ্জ, চট্টগ্রাম)।"
        )

    day = DATA.get(district, {}).get(date_iso)
    if not day:
        return (
            f"⚠️ এই তারিখের ডাটা নেই: {date_iso}\n"
            "রমজান ২০২৬ ডাটা আছে: 2026-02-19 থেকে 2026-03-20"
        )

    return (
        f"📍 {district}\n"
        f"🗓️ {date_iso}\n\n"
        f"🌙 সাহরি শেষ: {day['sehri_end']}\n"
        f"🌅 ফজর আযান: {day['fajr_azan']}\n"
        f"🌇 ইফতার: {day['iftar']}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("জেলার নাম দিন। উদাহরণ: /today ঢাকা")
        return
    district = " ".join(context.args)
    await update.message.reply_text(build_reply(today_iso(), district))

async def date_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: /date YYYY-MM-DD <district>\nউদাহরণ: /date 2026-03-05 ঢাকা")
        return
    date_iso = context.args[0].strip()
    district = " ".join(context.args[1:])
    await update.message.reply_text(build_reply(date_iso, district))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return
    await update.message.reply_text(build_reply(today_iso(), text))

def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing. Set BOT_TOKEN env var.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("date", date_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot running (offline timetable)...")
    app.run_polling()

if __name__ == "__main__":
    main()
