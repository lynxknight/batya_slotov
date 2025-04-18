import logging
import json
import os
import functools
from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

import agent
import env
import telegram_booking_task
import slots

logger = logging.getLogger(__name__)

# List of authorized user IDs
AUTHORIZED_USERS = (388546127, 1182153)


def ensure_access(func):
    """Decorator to ensure only authorized users can access the command"""

    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            logger.warning(f"Unauthorized access attempt from user {user_id=}")
            await update.message.reply_text(
                "⛔️ You are not authorized to use this bot."
            )
            return
        logger.info(f"Auth check passed for {user_id=}")
        return await func(self, update, context)

    return wrapper


class TelegramNotifier:
    def __init__(self):
        self.bot_token = self._load_telegram_token()
        self.application = None

    def _load_telegram_token(self):
        """Load Telegram bot token from environment variable"""
        token = os.getenv("TENNIS_BOT_TOKEN")
        if not token:
            raise ValueError("TENNIS_BOT_TOKEN environment variable must be set")

        logger.info(f"Loaded bot token: {token[:5]}...")
        return token

    @property
    def subscribed_users(self):
        """Get the current set of subscribed users from file"""
        try:
            with open("subscribed_users.json", "r") as f:
                users = set(json.load(f))
                logger.info(f"Loaded {len(users)} subscribed users")
                return users
        except FileNotFoundError:
            logger.info("No subscribed users file found, returning empty set")
            return set()

    def _save_subscribed_users(self, users):
        """Save subscribed users to file"""
        with open("subscribed_users.json", "w") as f:
            json.dump(list(users), f)
            logger.info(f"Saved {len(users)} subscribed users")

    @ensure_access
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command"""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        user_id = update.effective_user.id

        # Get current users and add new one
        users = self.subscribed_users
        users.add(user_id)
        self._save_subscribed_users(users)

        await update.message.reply_text(
            "🎾 Welcome to the Tennis Booking Bot!\n\n"
            "I'll keep you updated about court bookings. "
            "You'll receive notifications about booking attempts and results.\n\n"
            "Use /stop to stop receiving updates.\n"
            "Use /retry to retry the last booking attempt."
        )
        logger.info(f"User {user_id} subscribed successfully")

    @ensure_access
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /stop command"""
        user_id = update.effective_user.id
        logger.info(f"Received /stop command from user {user_id}")

        # Get current users and remove the one unsubscribing
        users = self.subscribed_users
        if user_id in users:
            users.remove(user_id)
            self._save_subscribed_users(users)
            await update.message.reply_text("You've been unsubscribed from updates.")
            logger.info(f"User {user_id} unsubscribed successfully")
        else:
            await update.message.reply_text("You weren't subscribed to updates.")
            logger.info(f"User {user_id} tried to unsubscribe but wasn't subscribed")

    @ensure_access
    async def retry_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /retry command"""
        user_id = update.effective_user.id
        logger.info(f"Received /retry command from user {user_id}")

        if user_id not in self.subscribed_users:
            logger.info(
                f"User {user_id} tried to retry but wasn't subscribed. Allow, but it is weird. {self.subscribed_users=}"
            )

        await update.message.reply_text("🔄 Retrying the last booking attempt...")
        await telegram_booking_task.run_booking_task(self)

    @ensure_access
    async def view_schedule_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle the /view_schedule command"""
        user_id = update.effective_user.id
        logger.info(f"Received /view_schedule command from user {user_id}")

        try:
            # Load preferences from file
            with open("booking_preferences.json", "r") as f:
                preferences_json = json.load(f)

            # Convert to SlotPreference objects
            preferences = slots.SlotPreference.from_preferences_json(preferences_json)

            # Format message
            message = "Your schedule and preferences:\n\n"
            for weekday, pref in preferences.items():
                time_str = slots.parse_time(pref.start_time)
                courts_str = ", ".join(map(str, pref.preferred_courts))
                message += f"• {weekday.capitalize()}: {time_str} (prefer courts {courts_str})\n"

            await update.message.reply_text(message)
            logger.info(f"Sent preferences to user {user_id}")

        except Exception as e:
            error_msg = f"❌ Failed to load preferences: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            await update.message.reply_text(error_msg)

    @ensure_access
    async def view_bookings_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle the /view_bookings command"""
        user_id = update.effective_user.id
        logger.info(f"Received /view_bookings command from user {user_id}")

        try:
            logger.info(f"Trying to fetch bookings for {user_id}")
            await update.message.reply_text("Fetching bookings...")
            booked_slots = await agent.fetch_existing_bookings_standalone()
            logger.info(f"Fetched {len(booked_slots)} bookings for {user_id}")

            if not booked_slots:
                await update.message.reply_text("No existing bookings found.")
                return

            # Format message
            message = "Current Bookings:\n\n"
            for slot in booked_slots:
                date_str = slot.date.strftime("%A, %d %B %Y")
                time_str = slots.parse_time(slot.start_time)
                message += f"• {date_str} at {time_str} on Court {slot.court}\n"

            await update.message.reply_text(message)
            logger.info(f"Sent bookings to user {user_id}")

        except Exception as e:
            error_msg = f"Failed to fetch bookings: {str(e)}"
            logger.exception(e)
            await update.message.reply_text(error_msg)

    @ensure_access
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command"""
        help_text = """Available commands:

/start - Subscribe to receive booking notifications and updates
/stop - Unsubscribe from booking notifications
/retry - manually run booking attempt
/view_schedule - Displays your schedule
/view_bookings - List existing bookings
/help - Show this help message

"""

        await update.message.reply_text(help_text)
        logger.info(f"Sent help message to user {update.effective_user.id}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any message"""
        logger.info(
            f"Received message from user {update.effective_user.id}: {update.message.text}"
        )

    async def send_message(
        self, message: str, disable_notification: bool = False
    ) -> bool:
        """Send message to all subscribed users"""
        try:
            bot = Bot(token=self.bot_token)
            users = self.subscribed_users
            logger.info(f"Sending message to {len(users)} users")

            # Send to all subscribed users
            for user_id in users:
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        disable_notification=disable_notification,
                    )
                    logger.info(f"Message sent successfully to user {user_id}")
                except Exception as e:
                    logger.exception(e)
                    logger.error(f"Failed to send message to user {user_id}: {e}")

            return True

        except Exception as e:
            logger.exception(e)
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def start_bot(self):
        """Start the bot application"""
        try:
            logger.info("Starting bot application")
            self.application = ApplicationBuilder().token(self.bot_token).build()

            logger.info("Adding command handlers")
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("stop", self.stop_command))
            self.application.add_handler(CommandHandler("retry", self.retry_command))
            self.application.add_handler(
                CommandHandler("view_schedule", self.view_schedule_command)
            )
            self.application.add_handler(
                CommandHandler("view_bookings", self.view_bookings_command)
            )
            self.application.add_handler(CommandHandler("help", self.help_command))

            logger.info("Starting polling")
            self.application.run_polling()
        except Exception as e:
            logger.exception(e)
            logger.error(f"Error in start_bot: {e}")
            raise

    async def stop_bot(self):
        """Stop the bot application"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
    async def send_debug_picture_to_owner(self, photo_path):
        """Send message to all subscribed users"""
        try:
            bot = Bot(token=self.bot_token)

            # Send to all subscribed users
            try:
                await bot.send_photo(
                    chat_id=1182153,
                    photo=
                )
                logger.info(f"Message sent successfully to user {user_id}")
            except Exception as e:
                logger.exception(e)
                logger.error(f"Failed to send message to user {user_id}: {e}")



async def run_booking_task():
    """Wrapper to run the booking task in a new event loop"""
    await telegram_booking_task.run_booking_task(get_notifier())


# Create a global instance
_notifier: TelegramNotifier | None = None


def get_notifier():
    global _notifier
    if _notifier is None:
        env.setup_env()
        _notifier = TelegramNotifier()
    return _notifier


if __name__ == "__main__":
    try:
        env.setup_env()
        get_notifier().start_bot()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
