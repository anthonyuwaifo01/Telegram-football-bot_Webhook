import os
import random
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, CallbackContext, MessageHandler, Filters

# --- Environment variables ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Your Render URL + /webhook

bot = Bot(token=TOKEN)
app = FastAPI()

# --- State ---
admins = set()  # Telegram user IDs of admins
members = {}  # user_id -> {"name": str, "status": "IN"/"OUT"}
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

# --- Telegram command handlers ---
def start_selection(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("Only admins can start selection.")
        return
    global selection_active
    selection_active = True
    for m in members.values():
        m["status"] = "OUT"
    update.message.reply_text("Player selection started! Members, send /in or /out.")

def end_selection(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("Only admins can end selection.")
        return
    global selection_active
    selection_active = False
    shuffle_teams()
    update.message.reply_text("Selection ended! Here are the teams:\n\n" + format_teams())

def in_command(update: Update, context: CallbackContext):
    if not selection_active:
        update.message.reply_text("Selection is not active.")
        return
    user_id = update.effective_user.id
    members[user_id] = {"name": update.effective_user.first_name, "status": "IN"}
    update.message.reply_text(f"{update.effective_user.first_name} marked as IN!")

def out_command(update: Update, context: CallbackContext):
    if not selection_active:
        update.message.reply_text("Selection is not active.")
        return
    user_id = update.effective_user.id
    members[user_id] = {"name": update.effective_user.first_name, "status": "OUT"}
    update.message.reply_text(f"{update.effective_user.first_name} marked as OUT!")

def status(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("Only admins can see status.")
        return
    in_members = [m["name"] for m in members.values() if m["status"] == "IN"]
    out_members = [m["name"] for m in members.values() if m["status"] == "OUT"]
    update.message.reply_text(f"Selection Active: {selection_active}\nIN: {in_members}\nOUT: {out_members}")

def make_admin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in admins:
        update.message.reply_text("Only admins can make other admins.")
        return
    try:
        new_admin_id = int(context.args[0])
        admins.add(new_admin_id)
        update.message.reply_text(f"User {new_admin_id} is now an admin.")
    except Exception as e:
        update.message.reply_text("Usage: /makeadmin <user_id>")

# --- Setup dispatcher ---
dp = Dispatcher(bot, None, workers=0)
dp.add_handler(CommandHandler("startselection", start_selection))
dp.add_handler(CommandHandler("endselection", end_selection))
dp.add_handler(CommandHandler("in", in_command))
dp.add_handler(CommandHandler("out", out_command))
dp.add_handler(CommandHandler("status", status))
dp.add_handler(CommandHandler("makeadmin", make_admin))

# --- Webhook endpoint for Render ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    dp.process_update(update)
    return {"ok": True}

# --- Set webhook on startup ---
@app.on_event("startup")
async def startup():
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("✅ Webhook set successfully!")

# --- Entrypoint for local dev ---
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=PORT, log_level="info")
