import logging
import os
from datetime import datetime, time, timedelta

import pytz
from dateutil import parser
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import supabase
from utils import (
    can_record_sleep_now,
    can_record_wakeup_now,
    get_sleep_date,
    human_readable_duration,
    parse_duration,
)

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEBOT_URL = os.environ.get("TELEBOT_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
TELEBOT_TOKEN = os.environ.get("TELEBOT_TOKEN")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN")
PORT = int(os.environ.get("PORT", "8443"))


# Conversation states
WAKEUP_FORM = 0
EDIT_BEDTIME = 1
EDIT_FALL_ASLEEP = 2
EDIT_ALARM = 3
EDIT_WAKEUP_TIME = 4
EDIT_ENERGY_SCORE = 5
EDIT_CLARITY_SCORE = 6
EDIT_FORM = 7
ADD_ENTRY = 8

# TODO: Allow for timezone customization
DEFAULT_TIMEZONE = pytz.timezone("Asia/Singapore")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command, introduces the bot and its capabilities."""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    # Register user in DB if not already present
    supabase.table("users").upsert({"id": user_id, "username": username}).execute()

    await update.message.reply_text(
        f"Hello {username}! I'm a sleep tracker bot to help you track and review your sleep patterns.\n\n"
        "Please refer to /help for the full list of available commands."
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with available commands."""
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/sleep - Record your bedtime\n"
        "/wakey - Record your wake-up time\n"
        "/view - View your sleep records for the past 7 days\n"
        "/edit - Edit a sleep record\n"
        "/add - Add a new sleep record for a specific date\n"
        "/help - View this help message"
    )


async def sleep_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Records current time as bedtime."""
    user_id = update.effective_user.id
    cur_datetime = datetime.now(DEFAULT_TIMEZONE)

    if not can_record_sleep_now(cur_datetime):
        await update.message.reply_text(
            "Currently, this app only supports recording bedtime after 9pm to prevent accidental entries.\n"
            "Please try again later."
        )
        return ConversationHandler.END

    sleep_date = get_sleep_date(cur_datetime)
    response = (
        supabase.table("sleep_records")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", sleep_date)
        .execute()
    )

    if response.data:
        await update.message.reply_text(
            f"You already logged bedtime for {sleep_date.strftime('%-d %b')} "
            "(sleep date = date which user wakes up, not when bedtime is recorded).\n"
            "Please use /edit instead to change it."
        )
        return ConversationHandler.END

    response = (
        supabase.table("sleep_records")
        .insert(
            {
                "user_id": user_id,
                "date": sleep_date.isoformat(),
                "bed_time": cur_datetime.isoformat(),
            }
        )
        .execute()
    )

    if not response.data:
        await update.message.reply_text(
            "Oops! Something went wrong, please try again later."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"Recorded bedtime at {cur_datetime.strftime('%-I:%M%p').lower()}, good night! 😴"
    )
    return ConversationHandler.END


async def wakey_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record current time as wake up time and ask for details."""

    user_id = update.effective_user.id
    cur_datetime = datetime.now(DEFAULT_TIMEZONE)

    if not can_record_wakeup_now(cur_datetime):
        await update.message.reply_text(
            "Currently, this app only supports recording wake-up time after 3am to prevent accidental entries.\n"
            "Please try again later."
        )
        return ConversationHandler.END

    sleep_date = get_sleep_date(cur_datetime)
    response = (
        supabase.table("sleep_records")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", sleep_date)
        .execute()
    )

    if not response.data:
        # Create a new record with default bedtime if it doesn't exist
        default_bedtime = DEFAULT_TIMEZONE.localize(
            datetime.combine(cur_datetime.date() - timedelta(days=1), time(22, 0))
        )
        supabase.table("sleep_records").insert(
            {
                "user_id": user_id,
                "date": sleep_date.isoformat(),
                "bed_time": default_bedtime.isoformat(),
                "wakeup_time": cur_datetime.isoformat(),
            }
        ).execute()
        context.user_data["bedtime"] = default_bedtime
    else:
        if response.data[0]["is_submitted"]:
            await update.message.reply_text(
                f"You already logged wakeup time for {sleep_date.strftime('%-d %b')}.\n"
                "Please use /edit instead to change it."
            )
            return ConversationHandler.END
        # Else update existing record
        supabase.table("sleep_records").update(
            {
                "wakeup_time": cur_datetime.isoformat(),
            }
        ).eq("user_id", user_id).eq("date", sleep_date).execute()
        context.user_data["bedtime"] = parser.isoparse(
            response.data[0]["bed_time"]
        ).astimezone(DEFAULT_TIMEZONE)

    # Prepare form
    context.user_data["sleep_date"] = sleep_date
    context.user_data["fall_asleep"] = parse_duration("15m")
    context.user_data["alarm"] = DEFAULT_TIMEZONE.localize(
        datetime.combine(cur_datetime.date(), time(7, 0))
    )
    context.user_data["wakeup"] = cur_datetime
    context.user_data["energy"] = 3
    context.user_data["clarity"] = 3

    await send_sleep_form(update, context, new_message=True)
    return WAKEUP_FORM


async def send_sleep_form(
    update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=True
):

    data = context.user_data

    text = (
        f"🛌 **{'New ' if context.user_data.get('add_entry', None) else ''}Sleep Record for {data['sleep_date'].strftime('%-d %b')}**\n\n"
        f"- 🛏️ Bedtime: {data['bedtime'].strftime('%I:%M %p').lower()}\n"
        f"- ⏱️ Time to fall asleep: {human_readable_duration(data['fall_asleep'])}\n"
        f"- ⏰ First alarm: {data['alarm'].strftime('%I:%M %p').lower()}\n"
        f"- 🌅 Wake-up time: {data['wakeup'].strftime('%I:%M %p').lower()}\n"
        f"- ⚡ Energy score: {data['energy']}\n"
        f"- 🧠 Clarity score: {data['clarity']}\n\n"
        "🔽 *Tap to edit:*"
    )

    keyboard = [
        [
            InlineKeyboardButton("🛏️ Bedtime", callback_data="edit_bedtime"),
            InlineKeyboardButton("⏱️ Fall asleep", callback_data="edit_fall_asleep"),
        ],
        [
            InlineKeyboardButton("⏰ Alarm time", callback_data="edit_alarm"),
            InlineKeyboardButton("🌅 Wake-up time", callback_data="edit_wakeup"),
        ],
        [
            InlineKeyboardButton("⚡ Energy", callback_data="edit_energy"),
            InlineKeyboardButton("🧠 Clarity", callback_data="edit_clarity"),
        ],
        [InlineKeyboardButton("✅ Submit", callback_data="submit_form")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if new_message:
        await update.message.reply_text(
            text, reply_markup=markup, parse_mode="Markdown"
        )
    else:
        await update.callback_query.edit_message_text(
            text=text, reply_markup=markup, parse_mode="Markdown"
        )


# Function to handle the edit action for each form field
async def handle_form_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Wait for user to select a callback button
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "edit_bedtime":
        await query.edit_message_text(
            "Please send your new bedtime in 24-hour format (eg 2230 for 10.30pm, or 0015 for 12.15am)."
        )
        context.user_data["edit_field"] = "bedtime"
        return EDIT_BEDTIME

    elif action == "edit_fall_asleep":
        await query.edit_message_text(
            "Please send the time taken to fall asleep following the example formats. (eg `15m` for 15 mins, `1h30m` for 1 hr 30 mins)."
        )
        context.user_data["edit_field"] = "fall_asleep"
        return EDIT_FALL_ASLEEP

    elif action == "edit_alarm":
        await query.edit_message_text(
            "Please send your new alarm time in 24-hour format (eg 2230 for 10.30pm, or 0015 for 12.15am)."
        )
        context.user_data["edit_field"] = "alarm"
        return EDIT_ALARM

    elif action == "edit_wakeup":
        await query.edit_message_text(
            "Please send your new wake-up time 24-hour format (eg 2230 for 10.30pm, or 0015 for 12.15am)."
        )
        context.user_data["edit_field"] = "wakeup"
        return EDIT_WAKEUP_TIME

    elif action == "edit_energy":
        await query.edit_message_text(
            "Please rate your energy score from 1 to 5 (1 being very tired, 5 being very energetic)."
        )
        context.user_data["edit_field"] = "energy"
        return EDIT_ENERGY_SCORE

    elif action == "edit_clarity":
        await query.edit_message_text(
            "Please send your clarity score from 1 to 5 (1 being bad brainfog, 5 being very clear minded)."
        )
        context.user_data["edit_field"] = "clarity"
        return EDIT_CLARITY_SCORE

    elif action == "submit_form":
        # After the user submits, save data to database or finalize form
        data = context.user_data
        supabase.table("sleep_records").update(
            {
                "bed_time": data["bedtime"].isoformat(),
                "sleep_time": (data["bedtime"] + data["fall_asleep"]).isoformat(),
                "first_alarm_time": data["alarm"].isoformat(),
                "wakeup_time": data["wakeup"].isoformat(),
                "energy_score": data["energy"],
                "clarity_score": data["clarity"],
                "is_submitted": True,
            }
        ).eq("user_id", update.effective_user.id).eq(
            "date", data["sleep_date"].isoformat()
        ).execute()
        await query.edit_message_text("✅ Sleep record submitted!")
        return ConversationHandler.END

    return WAKEUP_FORM  # If no action is matched, call this function again and await the next input


async def handle_edit_bedtime(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the user's input for editing bedtime."""

    user_input = update.message.text

    try:
        new_bedtime = datetime.strptime(user_input, "%H%M").time()
        sleep_date = context.user_data["sleep_date"]
        new_sleep_date = (
            sleep_date - timedelta(days=1) if new_bedtime >= time(20, 0) else sleep_date
        )

        new_bedtime = DEFAULT_TIMEZONE.localize(
            datetime.combine(new_sleep_date, new_bedtime)
        )

        # Update context (only update dataabase upon submission, not now)
        context.user_data["bedtime"] = new_bedtime
        await update.message.reply_text(
            f"Updated bedtime to {new_bedtime.strftime('%I:%M %p').lower()}. Remember to submit the form once done with all changes!"
        )

    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use 24-hour HHMM format."
        )
        return EDIT_BEDTIME  # Restart this function

    await send_sleep_form(update, context, new_message=True)

    return WAKEUP_FORM


async def handle_edit_fall_asleep(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the user's input for editing fall asleep time."""

    user_input = update.message.text

    # Validate and parse the input
    try:
        duration = parse_duration(user_input)

        # Update context
        context.user_data["fall_asleep"] = duration

        await update.message.reply_text(
            f"Updated time to fall asleep to {human_readable_duration(duration)}."
        )

    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use 'XhYm' or 'Xm' format."
        )
        return EDIT_FALL_ASLEEP  # Restart this function

    await send_sleep_form(update, context, new_message=True)

    return WAKEUP_FORM


async def handle_edit_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's input for editing alarm time."""

    user_input = update.message.text

    try:
        alarm_time = datetime.strptime(user_input, "%H%M").time()
        alarm_time = DEFAULT_TIMEZONE.localize(
            datetime.combine(context.user_data["sleep_date"], alarm_time)
        )

        # Update context
        context.user_data["alarm"] = alarm_time

        await update.message.reply_text(
            f"Updated alarm time to {alarm_time.strftime('%I:%M %p').lower()}."
        )

    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use 24-hour HHMM format."
        )
        return EDIT_ALARM  # Restart this function

    await send_sleep_form(update, context, new_message=True)

    return WAKEUP_FORM


async def handle_edit_wakeup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's input for editing wake-up time."""

    user_input = update.message.text

    try:
        wakeup_time = datetime.strptime(user_input, "%H%M").time()
        wakeup_time = DEFAULT_TIMEZONE.localize(
            datetime.combine(context.user_data["sleep_date"], wakeup_time)
        )

        # Update context
        context.user_data["wakeup"] = wakeup_time

        await update.message.reply_text(
            f"Updated wake-up time to {wakeup_time.strftime('%I:%M %p').lower()}."
        )

    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use 24-hour HHMM format."
        )
        return EDIT_WAKEUP_TIME  # Restart this function

    await send_sleep_form(update, context, new_message=True)

    return WAKEUP_FORM


async def handle_edit_energy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's input for editing energy score."""

    user_input = update.message.text

    try:
        energy_score = int(user_input)
        if energy_score < 1 or energy_score > 5:
            raise ValueError("Score must be between 1 and 5.")

        # Update context
        context.user_data["energy"] = energy_score

        await update.message.reply_text(f"Updated energy score to {energy_score}.")

    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please send a number between 1 and 5."
        )
        return EDIT_ENERGY_SCORE  # Restart this function

    await send_sleep_form(update, context, new_message=True)

    return WAKEUP_FORM


async def handle_edit_clarity(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the user's input for editing clarity score."""

    user_input = update.message.text

    try:
        clarity_score = int(user_input)
        if clarity_score < 1 or clarity_score > 5:
            raise ValueError("Score must be between 1 and 5.")

        # Update context
        context.user_data["clarity"] = clarity_score

        await update.message.reply_text(f"Updated clarity score to {clarity_score}.")

    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please send a number between 1 and 5."
        )
        return EDIT_CLARITY_SCORE  # Restart this function

    await send_sleep_form(update, context, new_message=True)

    return WAKEUP_FORM


async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_entry"] = False
    await update.message.reply_text(
        "Which date would you like to edit? (Format: DD/MM)"
    )
    return EDIT_FORM


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Which date would you like to add? (Format: DD/MM)")
    return ADD_ENTRY


async def handle_add_form_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_entry"] = True
    try:
        # Parse user input like "02/05"
        user_input = update.message.text.strip()
        day_month = datetime.strptime(user_input, "%d/%m")
        year = datetime.now().year  # or handle year separately later
        selected_date = day_month.replace(year=year)
    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please enter the date in DD/MM format."
        )
        return ADD_ENTRY  # Restart this function

    # Check if there's an entry
    response = (
        supabase.table("sleep_records")
        .select("*")
        .eq("user_id", update.effective_user.id)
        .eq("date", selected_date)
        .execute()
    )
    if response.data:
        await update.message.reply_text(
            f"Sleep log already exists for {selected_date.strftime('%-d %B')}, please use /edit instead to change it."
        )
        return ConversationHandler.END

    # Prepare default form
    # Create a new record with default bedtime if it doesn't exist
    default_bedtime = DEFAULT_TIMEZONE.localize(
        datetime.combine(selected_date - timedelta(days=1), time(22, 0))
    )
    default_sleep_time = DEFAULT_TIMEZONE.localize(
        datetime.combine(selected_date - timedelta(days=1), time(22, 15))
    )
    default_alarm_time = DEFAULT_TIMEZONE.localize(
        datetime.combine(selected_date, time(7, 0))
    )
    default_wakeup = DEFAULT_TIMEZONE.localize(
        datetime.combine(selected_date, time(7, 15))
    )
    context.user_data["bedtime"] = default_bedtime

    # Prepare form
    context.user_data["sleep_date"] = selected_date
    context.user_data["fall_asleep"] = default_sleep_time - default_bedtime
    context.user_data["alarm"] = default_alarm_time
    context.user_data["wakeup"] = default_wakeup
    context.user_data["energy"] = 3
    context.user_data["clarity"] = 3

    await send_sleep_form(update, context, new_message=True)
    return WAKEUP_FORM


async def handle_edit_form_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    try:
        # Parse user input like "02/05"
        day_month = datetime.strptime(user_input, "%d/%m")
        year = datetime.now().year  # or handle year separately later
        selected_date = day_month.replace(year=year)

        # Store date in user_data for later
        context.user_data["edit_date"] = selected_date
        context.user_data["edit_state"] = None

        # Check if there's an entry
        response = (
            supabase.table("sleep_records")
            .select("*")
            .eq("user_id", update.effective_user.id)
            .eq("date", selected_date)
            .execute()
        )
        if not response.data:
            await update.message.reply_text(
                "No sleep log found for that date. Please try again, or use /cancel to exit."
            )
            return EDIT_FORM
        if not response.data[0]["is_submitted"]:
            await update.message.reply_text(
                "This sleep log has not been completed yet. Please use /wakey to submit it instead."
            )
            return ConversationHandler.END
        entry = response.data[0]

        # Prepare form
        bedtime = parser.isoparse(entry["bed_time"]).astimezone(DEFAULT_TIMEZONE)
        sleep_time = parser.isoparse(entry["sleep_time"]).astimezone(DEFAULT_TIMEZONE)
        alarm_time = parser.isoparse(entry["first_alarm_time"]).astimezone(
            DEFAULT_TIMEZONE
        )
        wakeup_time = parser.isoparse(entry["wakeup_time"]).astimezone(DEFAULT_TIMEZONE)
        energy_score = entry["energy_score"]
        clarity_score = entry["clarity_score"]
        context.user_data["sleep_date"] = selected_date
        context.user_data["bedtime"] = bedtime
        context.user_data["fall_asleep"] = sleep_time - bedtime
        context.user_data["alarm"] = alarm_time
        context.user_data["wakeup"] = wakeup_time
        context.user_data["energy"] = energy_score
        context.user_data["clarity"] = clarity_score

        await send_sleep_form(update, context, new_message=True)
    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please enter the date in DD/MM format."
        )
        return EDIT_FORM  # Restart this function
    return WAKEUP_FORM


async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View sleep statistics for the past 7 days."""
    user_id = update.effective_user.id

    # Calculate date range
    end_date = datetime.now(DEFAULT_TIMEZONE).date()
    start_date = end_date - timedelta(days=6)  # 7 days including today

    # Query sleep records for the past 7 days
    response = (
        supabase.table("sleep_records")
        .select("*")
        .eq("user_id", user_id)
        .gte("date", start_date.isoformat())
        .lte("date", end_date.isoformat())
        .order("date", desc=True)
        .execute()
    )

    records = response.data

    if not records:
        await update.message.reply_text("No sleep records found for the past 7 days.")
        return ConversationHandler.END

    # Calculate statistics and format response
    stats_text = "📊 *Your sleep records for the past 7 days*\n\n"

    for entry in records:
        if not entry["is_submitted"]:
            continue
        date = entry["date"]
        bedtime = parser.isoparse(entry["bed_time"]).astimezone(DEFAULT_TIMEZONE)
        sleep_time = parser.isoparse(entry["sleep_time"]).astimezone(DEFAULT_TIMEZONE)
        alarm_time = parser.isoparse(entry["first_alarm_time"]).astimezone(
            DEFAULT_TIMEZONE
        )
        wakeup_time = parser.isoparse(entry["wakeup_time"]).astimezone(DEFAULT_TIMEZONE)
        energy_score = entry["energy_score"]
        clarity_score = entry["clarity_score"]

        # Calculate sleep duration if both times are available
        duration_text = human_readable_duration(wakeup_time - sleep_time)

        # Format the record
        stats_text += f"*{date}*\n"
        stats_text += f"🛌 Bedtime: {bedtime.strftime('%-I.%M%p').lower()} (took {human_readable_duration(sleep_time - bedtime)} to fall asleep)\n"
        stats_text += f"⏰ Wake-up time: {wakeup_time.strftime('%-I.%M%p').lower()} (alarm time: {alarm_time.strftime('%-I.%M%p').lower()}, snoozed for {human_readable_duration(wakeup_time-alarm_time)})\n"
        stats_text += f"💤 Duration: {duration_text}\n"
        stats_text += f"🔋 Energy: {'⭐' * energy_score} ({energy_score}/5)\n"
        stats_text += f"🧠 Clarity: {'⭐' * clarity_score} ({clarity_score}/5)\n"

        stats_text += "\n"

    # Calculate averages if there are complete records
    complete_records = [r for r in records if r.get("bedtime") and r.get("wakeup_time")]
    if complete_records:
        total_duration_seconds = 0
        total_energy = 0
        total_clarity = 0
        energy_count = 0
        clarity_count = 0

        for record in complete_records:
            bedtime = record.get("bedtime")
            wakeup_time = record.get("wakeup_time")

            # Calculate duration
            try:
                bedtime_dt = datetime.strptime(bedtime, "%H:%M")
                wakeup_dt = datetime.strptime(wakeup_time, "%H:%M")
                if wakeup_dt < bedtime_dt:
                    wakeup_dt += datetime.timedelta(days=1)
                duration = wakeup_dt - bedtime_dt
                total_duration_seconds += duration.seconds
            except Exception:
                pass

            # Sum up ratings
            if record.get("energy_score"):
                total_energy += record.get("energy_score")
                energy_count += 1

            if record.get("clarity_score"):
                total_clarity += record.get("clarity_score")
                clarity_count += 1

        # Calculate average duration
        if complete_records:
            avg_duration_seconds = total_duration_seconds / len(complete_records)
            avg_hours, remainder = divmod(int(avg_duration_seconds), 3600)
            avg_minutes, _ = divmod(remainder, 60)
            stats_text += f"*Average sleep duration: {avg_hours}h {avg_minutes}m*\n"

        # Calculate average ratings
        if energy_count:
            avg_energy = total_energy / energy_count
            stats_text += f"*Average energy rating: {avg_energy:.1f}/5*\n"

        if clarity_count:
            avg_clarity = total_clarity / clarity_count
            stats_text += f"*Average clarity rating: {avg_clarity:.1f}/5*\n"

    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    # Initialize the bot
    app = ApplicationBuilder().token(TELEBOT_TOKEN).build()

    # Define conversation handlers
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("sleep", sleep_command),
            CommandHandler("wakey", wakey_command),
            CommandHandler("edit", edit_command),
            CommandHandler("view", view_command),
            CommandHandler("add", add_command),
            CommandHandler("help", help_command),
        ],
        states={
            WAKEUP_FORM: [CallbackQueryHandler(handle_form_edit)],
            EDIT_BEDTIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_bedtime)
            ],
            EDIT_FALL_ASLEEP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_fall_asleep)
            ],
            EDIT_ALARM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_alarm)
            ],
            EDIT_WAKEUP_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_wakeup)
            ],
            EDIT_ENERGY_SCORE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_energy)
            ],
            EDIT_CLARITY_SCORE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_clarity)
            ],
            EDIT_FORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_form_input)
            ],
            ADD_ENTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_form_input)
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    # Start the webhook
    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            secret_token=SECRET_TOKEN,
        )
    else:
        # Fallback to polling
        app.run_polling()


if __name__ == "__main__":
    main()
