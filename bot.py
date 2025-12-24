import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =====================================================
# ENVIRONMENT VARIABLES (SET IN RENDER)
# =====================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")  # e.g. https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not RENDER_URL:
    raise RuntimeError("BOT_TOKEN and RENDER_URL must be set")

# =====================================================
# TELEGRAM BOT HANDLERS
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Football Bot is LIVE!\n"
        "Running on webhook (Render Free safe)."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/help - Show this help message"
    )

# =====================================================
# TELEGRAM APPLICATION
# =====================================================
telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))

# =====================================================
# FLASK WEB SERVER (WEBHOOK)
# =====================================================
flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def health_check():
    return "OK", 200

@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

# =====================================================
# STARTUP LOGIC
# =====================================================
async def setup_webhook():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{RENDER_URL}/webhook")
    print("✅ Webhook successfully set")

if __name__ == "__main__":
    asyncio.run(setup_webhook())
    flask_app.run(host="0.0.0.0", port=PORT)
