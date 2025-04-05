import argparse
import logging
import asyncio
import datetime
import json
import os
import typing

import agent
import slots

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Book earliest available tennis court slot"
    )
    parser.add_argument(
        "--show", action="store_true", help="Show browser window during automation"
    )
    parser.add_argument(
        "--slow",
        type=int,
        default=0,
        help="Add delay between actions (in milliseconds)",
    )
    parser.add_argument(
        "--preferences-path",
        type=str,
        default="booking_preferences.json",
        help="File containing booking preferences",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only check availability without making a booking",
    )
    parser.add_argument(
        "--target-date",
        type=lambda d: datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d"),
        help="Date in YYYY-MM-DD format",
    )
    args = parser.parse_args()
    return args


def load_preferences(config_path: str) -> list[dict]:
    logger.info(f"Loading preferences from {config_path}")
    with open(config_path) as f:
        config = json.load(f)
    return slots.SlotPreference.from_preferences_json(config)


def get_active_preference(
    preferences: dict[str, slots.SlotPreference], target_date: str | None = None
) -> typing.Optional[slots.SlotPreference]:
    if target_date is None:
        target_date = datetime.now() + datetime.timedelta(days=7)
    else:
        target_date = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    weekday = target_date.strftime("%A").lower()  # Get day name in lowercase
    logger.info(f"Getting active preference for {target_date=} {weekday=}") 
    return preferences[weekday]


async def main():
    args = parse_args()
    preferences = load_preferences(args.preferences_path)
    active_preference = get_active_preference(preferences, args.target_date)
    target_date = datetime.datetime.strptime(
        args.target_date, "%Y-%m-%d"
    ) or datetime.now() + datetime.timedelta(days=7)
    playwright_params = agent.PlaywrightParams(
        headless=not args.show,
        slow_mo=args.slow,
    )
    try:
        await agent.fetch_and_book_session(
            target_date=target_date,
            preference=active_preference,
            playwright_params=playwright_params,
            dry_run=args.dry_run,
        )
    except Exception as e:
        logger.error(f"Error during booking process: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
