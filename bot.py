import os
import random
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = FastAPI()

# --- State ---
admins = {1081255171}
members = {}
selection_active = False
teams = []

# --- Helper functions ---
def shuffle_teams():
    in_members = [m for m in members.values() if m["status"] == "IN"]
    random.shuffle(in_members)
    teams.clear()
    group_size = 6
    while in_members:
        team = in_members[:group_size]
        teams.append(team)
        in_members = in_members[group_size:]

def format_teams():
    result = []
    for idx, team in enumerate(teams, start=1):
        members_list = ", ".join([m["name"] for m in team])
        result.append(f"Team {idx} ({len(team)} players): {members_list}")
    return "\n".join(result)

# --- Telegram handlers ---
async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text("Only admins have the right to use this command.")
        return
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}! Welcome to the Football Bot.\n"
        f"Your chat ID is: {user_id}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text("Only admins have the right to use this command.")
        return
    global selection_active
    selection_active = True
    for m in members.values():
        m["status"] = "OUT"
    await update.message.reply_text("Player selection started! Members, send /in or /out.")

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text("Only admins have the right to use this command.")
        return
    global selection_active
    selection_active = False
    shuffle_teams()
    await update.message.reply_text("Selection ended! Here are the teams:\n\n" + format_teams())

async def in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not selection_active:
        await update.message.reply_text("Selection is not active.")
        return
    user_id = update.effective_user.id
    members[user_id] = {"name": update.effective_user.first_name, "status": "IN"}
    await update.message.reply_text(f"{update.effective_user.first_name} marked as IN!")

async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not selection_active:
        await update.message.reply_text("Selection is not active.")
        return
    user_id = update.effective_user.id
    members[user_id] = {"name": update.effective_user.first_name, "status": "OUT"}
    await update.message.reply_text(f"{update.effective_user.first_name} marked as OUT!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text("Only admins have the right to use this command.")
        return
    in_members = [m["name"] for m in members.values() if m["status"] == "IN"]
    out_members = [m["name"] for m in members.values() if m["status"] == "OUT"]
    await update.message.reply_text(f"Selection Active: {selection_active}\nIN: {in_members}\nOUT: {out_members}")

async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text("Only admins have the right to use this command.")
        return
    try:
        new_admin_id = int(context.args[0])
        admins.add(new_admin_id)
        await update.message.reply_text(f"User {new_admin_id} is now an admin.")
    except:
        await update.message.reply_text("Usage: /makeadmin <user_id>")

# --- Build Application ---
app_bot = Application.builder().token(TOKEN).build()
app_bot.add_handler(CommandHandler("begin", begin))
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("end", end))
app_bot.add_handler(CommandHandler("in", in_command))
app_bot.add_handler(CommandHandler("out", out_command))
app_bot.add_handler(CommandHandler("status", status))
app_bot.add_handler(CommandHandler("makeadmin", make_admin))

# --- Webhook endpoint ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await app_bot.process_update(update)
    return {"ok": True}

# --- Lifespan events ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await app_bot.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    async with app_bot:
        await app_bot.start()
        print("✅ Webhook set successfully!")
        yield
        # Shutdown
        await app_bot.stop()

app = FastAPI(lifespan=lifespan)

# Re-add the webhook endpoint after FastAPI recreation
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await app_bot.process_update(update)
    return {"ok": True}

# --- Local dev ---
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=PORT, log_level="info")
