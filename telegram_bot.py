import asyncio
import logging
import json
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
import agent
import telegram_booking_task
import slots

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.bot_token = self._load_telegram_token()
        self.application = None

    def _load_telegram_token(self):
        """Load Telegram bot token from .telegram file"""
        with open(".telegram_bot_token", "r") as f:
            token = f.readline().strip()
            if not token:
                raise ValueError(
                    "Telegram config file must contain bot token on first line"
                )
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

    async def retry_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /retry command"""
        user_id = update.effective_user.id
        logger.info(f"Received /retry command from user {user_id}")

        if user_id not in self.subscribed_users:
            await update.message.reply_text(
                "❌ You need to be subscribed to use the /retry command."
            )
            logger.info(f"User {user_id} tried to retry but wasn't subscribed")
            return

        await update.message.reply_text("🔄 Retrying the last booking attempt...")
        await telegram_booking_task.run_booking_task(self)

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
            await update.message.reply_text(error_msg)

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
                await update.message.reply_text("📅 No existing bookings found.")
                return

            # Format message
            message = "📅 Your Current Bookings:\n\n"
            for slot in booked_slots:
                date_str = slot.date.strftime("%A, %d %B %Y")
                time_str = slots.parse_time(slot.start_time)
                message += f"• {date_str} at {time_str} on Court {slot.court}\n"

            await update.message.reply_text(message)
            logger.info(f"Sent bookings to user {user_id}")

        except Exception as e:
            error_msg = f"❌ Failed to fetch bookings: {str(e)}"
            logger.error(error_msg)
            await update.message.reply_text(error_msg)

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
                    logger.error(f"Failed to send message to user {user_id}: {e}")
                    # Remove user if we can't send messages to them
                    users.remove(user_id)
                    self._save_subscribed_users(users)

            return True

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def start_bot(self):
        """Start the bot application"""
        try:
            logger.info("Starting bot application")
            self.application = Application.builder().token(self.bot_token).build()

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
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )

            logger.info("Starting polling")
            self.application.run_polling()
        except Exception as e:
            logger.error(f"Error in start_bot: {e}")
            raise

    async def stop_bot(self):
        """Stop the bot application"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()


async def run_booking_task():
    """Wrapper to run the booking task in a new event loop"""
    global notifier
    await telegram_booking_task.run_booking_task(notifier)


# Create a global instance
notifier = TelegramNotifier()

if __name__ == "__main__":
    try:
        notifier.start_bot()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
