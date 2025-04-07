import asyncio
import schedule
import logging
import multiprocessing

import env
import telegram_bot

logger = logging.getLogger(__name__)


async def schedule_booking():
    """Run the booking task"""
    try:
        await telegram_bot.run_booking_task()
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error in booking task: {e}")


async def run_scheduler():
    """Run the scheduler loop"""
    while True:
        logger.info("Running scheduler pending tasks...")
        schedule.run_pending()
        await asyncio.sleep(30)  # Check every 30 seconds


async def main(bot_process: multiprocessing.Process):
    logger.info("Starting scheduler")

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
        env.setup_env()
        logger.info("Starting Telegram bot")
        bot_process = multiprocessing.Process(
            target=telegram_bot.get_notifier().start_bot
        )
        bot_process.start()
        asyncio.run(main(bot_process))
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
