from datetime import datetime, timedelta
import json
import agent
import logging
import slots

logger = logging.getLogger(__name__)


async def run_booking_task(notifier):
    """Run the booking task. This function can be called directly for retries."""
    # Calculate target date (1 week ahead)
    target_date = datetime.now() + timedelta(days=7)
    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.strftime("%A").lower()

    logger.info(f"Starting booking process for {date_str} ({weekday=})")

    # Check if there are preferences for this weekday
    preferences = slots.SlotPreference.from_preferences_json(
        json.load(open("booking_preferences.json"))
    )
    pref = preferences.get(weekday)
    if pref is None:
        message = f"No booking preferences found for {weekday}. Skipping booking for {date_str}"
        logger.info(message)
        # await notifier.send_message(message, disable_notification=True)
        return

    message = (
        f"Based on preferences for {weekday=}, we should try to book something! {pref}"
    )
    logger.info(message)
    await notifier.send_message(message, disable_notification=True)
    try:
        result = await agent.fetch_and_book_session(
            preference=pref,
            target_date=target_date,
            playwright_params=agent.PlaywrightParams(
                headless=True,
                slow_mo=0,
            ),
        )
    except Exception as e:
        error_msg = f"❌ Failed to book court for {date_str} at {slots.parse_time(pref.start_time)}: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        await notifier.send_message(error_msg)
        await notifier.send_message("You can retry via /retry command")
        return
    if not result.success:
        error_msg = f"❌ Failed to book court for {date_str} at {slots.parse_time(pref.start_time)}: {str(result.error)}"
        logger.error(error_msg)
        await notifier.send_message(error_msg)
        await notifier.send_message("You can retry via /retry command")
        return
    await notifier.send_message(
        f"✅ Successfully booked court for {date_str} at {slots.parse_time(result.slot.start_time)}"
    )
