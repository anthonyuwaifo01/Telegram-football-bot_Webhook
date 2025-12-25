import os
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
GROUP_NAME = os.environ.get("GROUP_NAME", "CalgaryUnfitballers")

# --- State ---
admins = {YOUR_USER_ID_HERE}  # Replace with your actual Telegram user ID

# Chat-specific state: {chat_id: {"selection_active": bool, "members": {}, "teams": []}}
chat_states = {}

# --- Helper functions ---
def get_chat_state(chat_id):
    """Get or initialize state for a specific chat"""
    if chat_id not in chat_states:
        chat_states[chat_id] = {
            "selection_active": False,
            "members": {},
            "teams": []
        }
    return chat_states[chat_id]

def shuffle_teams(chat_id):
    state = get_chat_state(chat_id)
    in_members = [m for m in state["members"].values() if m["status"] == "IN"]
    random.shuffle(in_members)
    state["teams"].clear()
    group_size = 6
    while in_members:
        team = in_members[:group_size]
        state["teams"].append(team)
        in_members = in_members[group_size:]

def format_teams(chat_id):
    state = get_chat_state(chat_id)
    teams = state["teams"]
    
    if not teams:
        return "No teams to display."
    
    team_colors = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠"]
    team_names = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"]
    
    result = ["🎲 RANDOM SELECTION", "⚽ THIS WEEK'S TEAMS ⚽", "=" * 30, ""]
    
    total_players = 0
    for idx, team in enumerate(teams):
        color = team_colors[idx % len(team_colors)]
        name = team_names[idx % len(team_names)]
        result.append(f"{color} {name} Team ({len(team)} players)")
        for member in team:
            result.append(f"     • {member['name']}")
        result.append("")
        total_players += len(team)
    
    result.append(f"Total Players: {total_players}")
    result.append(f"Teams Created: {len(teams)}")
    
    return "\n".join(result)

def get_player_count(chat_id):
    state = get_chat_state(chat_id)
    return len([m for m in state["members"].values() if m["status"] == "IN"])

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is an admin (hybrid approach)"""
    user_id = update.effective_user.id
    chat = update.effective_chat
    
    # Always check hardcoded admins list
    if user_id in admins:
        return True
    
    # In groups/supergroups, also check if user is a Telegram group admin
    if chat.type in ["group", "supergroup"]:
        try:
            member = await context.bot.get_chat_member(chat.id, user_id)
            # Check if user is creator or administrator
            if member.status in ["creator", "administrator"]:
                return True
        except Exception as e:
            print(f"Error checking admin status: {e}")
    
    return False

# --- Telegram handlers ---
async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to show welcome and user ID"""
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Only admins have the right to use this command.")
        return
    
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"👋 Hello {update.effective_user.first_name}!\n\n"
        f"🤖 Welcome to the {GROUP_NAME} Football Bot.\n"
        f"🆔 Your chat ID is: `{user_id}`\n\n"
        f"Use /start to begin player selection!"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to start selection"""
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Only admins have the right to use this command.")
        return
    
    chat_id = update.effective_chat.id
    state = get_chat_state(chat_id)
    
    state["selection_active"] = True
    for m in state["members"].values():
        m["status"] = "OUT"
    
    # Create inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ I'm IN", callback_data="in"),
            InlineKeyboardButton("❌ I'm OUT", callback_data="out")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🎉 Welcome {GROUP_NAME}, Time for team Selection!\n\n"
        f"Click the buttons below or reply with:\n"
        f"  • /in - Join this week\n"
        f"  • /out - Skip this week\n\n"
        f"Admin will announce teams later!"
    )
    await update.message.reply_text(message, reply_markup=reply_markup)

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to end selection and create teams"""
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Only admins have the right to use this command.")
        return
    
    chat_id = update.effective_chat.id
    state = get_chat_state(chat_id)
    
    state["selection_active"] = False
    shuffle_teams(chat_id)
    await update.message.reply_text(format_teams(chat_id))

async def in_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Player marks themselves as IN"""
    chat_id = update.effective_chat.id
    state = get_chat_state(chat_id)
    
    if not state["selection_active"]:
        await update.message.reply_text("⚠️ Selection is not active. Wait for admin to start!")
        return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Player"
    state["members"][user_id] = {"name": user_name, "status": "IN"}
    
    count = get_player_count(chat_id)
    player_word = "player" if count == 1 else "players"
    
    await update.message.reply_text(
        f"✅ {user_name} is IN!\n"
        f"Current count: {count} {player_word}"
    )

async def out_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Player marks themselves as OUT"""
    chat_id = update.effective_chat.id
    state = get_chat_state(chat_id)
    
    if not state["selection_active"]:
        await update.message.reply_text("⚠️ Selection is not active. Wait for admin to start!")
        return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Player"
    state["members"][user_id] = {"name": user_name, "status": "OUT"}
    
    count = get_player_count(chat_id)
    player_word = "player" if count == 1 else "players"
    
    await update.message.reply_text(
        f"❌ {user_name} is OUT!\n"
        f"Current count: {count} {player_word}"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to check current status"""
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Only admins have the right to use this command.")
        return
    
    chat_id = update.effective_chat.id
    state = get_chat_state(chat_id)
    
    in_members = [m["name"] for m in state["members"].values() if m["status"] == "IN"]
    out_members = [m["name"] for m in state["members"].values() if m["status"] == "OUT"]
    
    status_emoji = "🟢 ACTIVE" if state["selection_active"] else "🔴 NOT ACTIVE"
    
    message = f"📊 Status: {status_emoji}\n"
    message += f"👥 Players In: {len(in_members)}\n\n"
    
    if in_members:
        message += "✅ Participants:\n"
        for name in in_members:
            message += f"  • {name}\n"
    else:
        message += "No players IN yet.\n"
    
    if out_members:
        message += f"\n❌ Out ({len(out_members)}):\n"
        for name in out_members:
            message += f"  • {name}\n"
    
    await update.message.reply_text(message)

async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to make another user an admin"""
    if not await is_admin(update, context):
        await update.message.reply_text("🚫 Only admins have the right to use this command.")
        return
    
    try:
        new_admin_id = int(context.args[0])
        admins.add(new_admin_id)
        
        chat_id = update.effective_chat.id
        state = get_chat_state(chat_id)
        
        # Try to get the name if they've interacted with the bot
        new_admin_name = "User"
        if new_admin_id in state["members"]:
            new_admin_name = state["members"][new_admin_id]["name"]
        
        await update.message.reply_text(
            f"👑 {new_admin_name} (ID: {new_admin_id}) is now an admin!"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage: /makeadmin <user_id>")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    is_user_admin = await is_admin(update, context)
    
    if is_user_admin:
        message = (
            "🤖 Admin Commands:\n\n"
            "/begin - Show welcome message & get your user ID\n"
            "/start - Start player selection\n"
            "/end - End selection & create teams\n"
            "/status - View current player status\n"
            "/makeadmin <id> - Make someone an admin\n"
            "/help - Show this help message\n\n"
            "👥 Player Commands:\n"
            "/in or in - Mark yourself as IN\n"
            "/out or out - Mark yourself as OUT\n"
            "/help - Show help message"
        )
    else:
        message = (
            "🤖 Player Commands:\n\n"
            "/in or in - Mark yourself as IN\n"
            "/out or out - Mark yourself as OUT\n"
            "/help - Show this help message\n\n"
            "💡 Wait for admin to start selection!"
        )
    
    await update.message.reply_text(message)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    state = get_chat_state(chat_id)
    
    if not state["selection_active"]:
        await query.edit_message_text("⚠️ Selection is not active. Wait for admin to start!")
        return
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name or query.from_user.username or "Player"
    
    if query.data == "in":
        state["members"][user_id] = {"name": user_name, "status": "IN"}
        count = get_player_count(chat_id)
        player_word = "player" if count == 1 else "players"
        
        await query.edit_message_text(
            f"✅ {user_name} is IN!\n"
            f"Current count: {count} {player_word}"
        )
    elif query.data == "out":
        state["members"][user_id] = {"name": user_name, "status": "OUT"}
        count = get_player_count(chat_id)
        player_word = "player" if count == 1 else "players"
        
        await query.edit_message_text(
            f"❌ {user_name} is OUT!\n"
            f"Current count: {count} {player_word}"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages like 'in' or 'out'"""
    text = update.message.text.strip().lower()
    
    if text == "in":
        await in_command(update, context)
    elif text == "out":
        await out_command(update, context)
    else:
        await update.message.reply_text("❓ Unknown command. Send /help for commands.")

# --- Build Application ---
app_bot = Application.builder().token(TOKEN).build()
app_bot.add_handler(CommandHandler("begin", begin))
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("end", end))
app_bot.add_handler(CommandHandler("in", in_command))
app_bot.add_handler(CommandHandler("out", out_command))
app_bot.add_handler(CommandHandler("status", status))
app_bot.add_handler(CommandHandler("makeadmin", make_admin))
app_bot.add_handler(CommandHandler("help", help_command))
app_bot.add_handler(CallbackQueryHandler(button_callback))
app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# --- Lifespan events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize bot and set webhook
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("✅ Webhook set successfully!")
    
    yield
    
    # Shutdown: Stop bot
    await app_bot.stop()
    await app_bot.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# --- Webhook endpoint ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, app_bot.bot)
    await app_bot.process_update(update)
    return {"ok": True}

# --- Local dev ---
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=PORT, log_level="info")
