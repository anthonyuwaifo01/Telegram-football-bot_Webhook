import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import uvicorn

# =============================
# ENVIRONMENT VARIABLES
# =============================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")  # e.g. https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not RENDER_URL:
    raise RuntimeError("BOT_TOKEN and RENDER_URL must be set")

# =============================
# TELEGRAM HANDLERS
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Football Bot is LIVE!\n"
        "Running on webhook (Render async safe)."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/help - Show this help message"
    )

# =============================
# TELEGRAM APPLICATION
# =============================
telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))

# =============================
# FASTAPI WEB SERVER
# =============================
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# =============================
# STARTUP EVENT (SET WEBHOOK)
# =============================
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{RENDER_URL}/webhook")
    print("✅ Webhook successfully set")

# =============================
# RUN APP
# =============================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
