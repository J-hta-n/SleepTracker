from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from supabase import create_client, Client

import os

TELEBOT_URL = os.environ.get("TELEBOT_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
TELEBOT_TOKEN = os.environ.get("TELEBOT_TOKEN")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN")
PORT = os.environ.get("PORT")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


AFTER_START = 0
SLEEP = 1
WAKEUP = 2
DETAILS = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Register user id if not already in db
    username = update.message.from_user.username
    user_id = update.message.from_user.id
    supabase.table("users").upsert({"id": user_id, "username": username}).execute()
    # Reply with options
    reply_keyboard = [["Record sleep time", "Record waking time"]]
    await update.message.reply_text(
        "Hi, I'm a sleep tracker bot! What would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="Choose an option",
        ),
    )
    return AFTER_START


async def handle_after_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message when the user presses the button"""
    if update.message.text == "Record sleep time":
        await update.message.reply_text(
            "Please send me your sleep time in HH:MM format."
        )
        return SLEEP
    elif update.message.text == "Record waking time":
        await update.message.reply_text(
            "Please send me your waking time in HH:MM format."
        )
        return WAKEUP
    else:
        await update.message.reply_text("Invalid option. Please try again.")
        return AFTER_START


async def handle_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message when the user presses the button"""
    await update.message.reply_text("Recorded sleep time, good night!")
    return -1


async def handle_wakeup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message when the user presses the button"""
    await update.message.reply_text("Recorded wakeup time, good morning!")
    return -1


if __name__ == "__main__":
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    app = ApplicationBuilder().token(TELEBOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("sleep", handle_sleep),
            CommandHandler("wakeup", handle_wakeup),
        ],
        states={
            AFTER_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_after_start),
            ],
            SLEEP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sleep),
            ],
            WAKEUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wakeup),
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        secret_token=SECRET_TOKEN,
    )
