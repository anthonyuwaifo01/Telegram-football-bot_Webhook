import os
import random
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# =====================================================
# ENVIRONMENT VARIABLES
# =====================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")  # e.g., https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not RENDER_URL:
    raise RuntimeError("BOT_TOKEN and RENDER_URL must be set")

# =====================================================
# DATA STORAGE
# =====================================================
players_status = {}       # chat_id -> { user_id: "IN"/"OUT" }
selection_active = {}     # chat_id -> True/False
bot_admins = {}           # chat_id -> set(user_ids)

TEAM_COLORS = ["Green", "Red", "Yellow", "Blue", "Orange", "Purple"]

# =====================================================
# HELPERS
# =====================================================
def is_admin(chat_id: int, user_id: int):
    return user_id in bot_admins.get(chat_id, set())

def shuffle_teams(players):
    random.shuffle(players)
    teams = []
    while players:
        team_size = min(6, len(players))
        team = players[:team_size]
        players = players[team_size:]
        teams.append(team)
    return teams

# =====================================================
# TELEGRAM HANDLERS
# =====================================================
async def start_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        await update.message.reply_text("❌ Only admins can start selection.")
        return

    selection_active[chat_id] = True
    players_status[chat_id] = {}
    await update.message.reply_text("✅ Selection started! Members can now send /in or /out")

async def end_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        await update.message.reply_text("❌ Only admins can end selection.")
        return

    if not selection_active.get(chat_id, False):
        await update.message.reply_text("❌ Selection is not active.")
        return

    # Get IN players
    status = players_status.get(chat_id, {})
    in_players = [uid for uid, state in status.items() if state == "IN"]

    if not in_players:
        await update.message.reply_text("No players joined. Selection ended.")
        selection_active[chat_id] = False
        return

    teams = shuffle_teams(in_players)
    msg = "⚽ **Team Selection Results** ⚽\n\n"
    for i, team in enumerate(teams):
        color = TEAM_COLORS[i % len(TEAM_COLORS)]
        mentions = [f"[{uid}](tg://user?id={uid})" for uid in team]
        msg += f"**{color} Team:** " + ", ".join(mentions) + "\n"

    await update.message.reply_markdown(msg)
    selection_active[chat_id] = False

async def in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not selection_active.get(chat_id, False):
        await update.message.reply_text("Selection is not active.")
        return

    players_status[chat_id][user_id] = "IN"
    await update.message.reply_text("✅ You are marked as IN.")

async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if not selection_active.get(chat_id, False):
        await update.message.reply_text("Selection is not active.")
        return

    players_status[chat_id][user_id] = "OUT"
    await update.message.reply_text("❌ You are marked as OUT.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        await update.message.reply_text("❌ Only admins can check status.")
        return

    if not selection_active.get(chat_id, False):
        await update.message.reply_text("❌ Selection is not active.")
        return

    status_dict = players_status.get(chat_id, {})
    if not status_dict:
        await update.message.reply_text("No players have responded yet.")
        return

    in_players = [f"[{uid}](tg://user?id={uid})" for uid, state in status_dict.items() if state == "IN"]
    out_players = [f"[{uid}](tg://user?id={uid})" for uid, state in status_dict.items() if state == "OUT"]

    msg = "**Current Selection Status:**\n\n"
    if in_players:
        msg += "✅ IN:\n" + ", ".join(in_players) + "\n\n"
    if out_players:
        msg += "❌ OUT:\n" + ", ".join(out_players)
    await update.message.reply_markdown(msg)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_admin(chat_id, user_id):
        await update.message.reply_text("❌ Only admins can add other admins.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add_admin @username")
        return

    username = context.args[0].replace("@", "")
    bot_admins.setdefault(chat_id, set()).add(username)
    await update.message.reply_text(f"✅ {username} is now a bot admin.")

# =====================================================
# TELEGRAM APP
# =====================================================
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start_selection", start_selection))
application.add_handler(CommandHandler("end_selection", end_selection))
application.add_handler(CommandHandler("in", in_command))
application.add_handler(CommandHandler("out", out_command))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("add_admin", add_admin))

# =====================================================
# FASTAPI WEBHOOK SERVER
# =====================================================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# =====================================================
# SET WEBHOOK AND START SERVER
# =====================================================
if __name__ == "__main__":
    import uvicorn
    import asyncio

    async def main():
        await application.initialize()
        await application.bot.set_webhook(f"{RENDER_URL}/webhook")
        print("✅ Webhook set successfully!")
        # Start uvicorn server
        uvicorn.run(app, host="0.0.0.0", port=PORT)

    asyncio.run(main())
