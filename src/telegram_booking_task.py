from datetime import datetime, timedelta
import json
import agent
import logging
import slots

logger = logging.getLogger(__name__)


async def run_booking_task(notifier, user_id: int | None = None):
    """Run the booking task. This function can be called directly for retries."""
    # Calculate target date (1 week ahead)
    target_date = datetime.now() + timedelta(days=7)

    # Skip if target date is between June 16-27, 2025
    skip_start = datetime(2025, 6, 16)
    skip_end = datetime(2025, 6, 27)
    if skip_start <= target_date <= skip_end:
        logger.info(
            f"Skipping booking for {target_date} as it falls in blackout period"
        )
        return

    date_str = target_date.strftime("%Y-%m-%d")
    weekday = target_date.strftime("%A").lower()

    logger.info(f"Starting booking process for {date_str} ({weekday=})")

    # Check if there are preferences for this weekday
    preferences: dict[str, slots.SlotPreference] = (
        slots.SlotPreference.from_preferences_json(
            json.load(open("booking_preferences.json"))
        )
    )
    pref = preferences.get(weekday)
    if pref is None:
        message = f"No booking preferences found for {weekday}. Skipping booking for {date_str}"
        logger.info(message)
        if user_id is not None:
            logger.info(
                f"Sending message to user {user_id} as retry was manually requested"
            )
            await notifier.send_message(message, user_id)
        return

    message = (
        f"Based on preferences for {weekday=}, we should try to book something! {pref}"
    )
    logger.info(message)
    await notifier.broadcast_message(message, disable_notification=True)
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
        await notifier.broadcast_message(error_msg)
        await notifier.broadcast_message("You can retry via /retry command")
        return
    if not result.success:
        result_details = []
        if result.reason:
            result_details.append(result.reason)
        if result.error:
            result_details.append(str(result.error))
        error_msg = f"❌ Failed to book court for {date_str} at {slots.parse_time(pref.start_time)}: {' - '.join(result_details) if result_details else 'empty result'}"
        logger.error(error_msg)
        await notifier.broadcast_message(error_msg)
        await notifier.broadcast_message("You can retry via /retry command")
        return
    if not result.slot:
        error_msg = f"❌ Booking succeeded but no slot information available for {date_str}. This is unexpected, please take a look."
        logger.error(error_msg)
        await notifier.broadcast_message(error_msg)
        return
    await notifier.broadcast_message(
        f"✅ Successfully booked court for {date_str} at {slots.parse_time(result.slot.start_time)}"
    )
