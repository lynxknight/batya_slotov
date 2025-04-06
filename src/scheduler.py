import asyncio
import schedule
import logging
import multiprocessing
import time

import telegram_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)03d - [%(levelname)-8s] - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def schedule_booking():
    """Run the booking task"""
    try:
        await telegram_bot.run_booking_task()
    except Exception as e:
        logger.error(f"Error in booking task: {e}")


def run_bot():
    """Run the Telegram bot in a separate process"""
    asyncio.run(telegram_bot.notifier.start_bot())


async def run_scheduler():
    """Run the scheduler loop"""
    while True:
        logger.info("Running scheduler pending tasks...")
        schedule.run_pending()
        await asyncio.sleep(30)  # Check every 30 seconds


async def main():
    # Start the Telegram bot in a separate process
    logger.info("Starting Telegram bot")
    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.start()

    schedule.every().day.at("00:10").do(
        lambda: asyncio.get_event_loop().create_task(schedule_booking())
    )

    logger.info("Scheduler started")

    try:
        # Run the scheduler
        await run_scheduler()
    except asyncio.CancelledError:
        logger.info("Shutting down...")
        # Cleanup
        bot_process.terminate()
        bot_process.join()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
