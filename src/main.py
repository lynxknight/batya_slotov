import argparse
import logging
import asyncio
import datetime
import json
import typing

import agent
import slots
import env

# Configure logging
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Tennis court booking automation")
    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute", required=True
    )

    # Common arguments for both commands
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument(
        "--show", action="store_true", help="Show browser window during automation"
    )
    common_args.add_argument(
        "--slow",
        type=int,
        default=0,
        help="Add delay between actions (in milliseconds)",
    )

    # Book command
    book_parser = subparsers.add_parser(
        "book", parents=[common_args], help="Book a tennis court"
    )
    book_parser.add_argument(
        "--slot",
        type=str,
        required=True,
        help="Slot to book in format 'dd/mm/yy hh:mm'",
    )
    book_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only check availability without making a booking",
    )

    # Fetch bookings command
    fetch_parser = subparsers.add_parser(
        "fetch_bookings", parents=[common_args], help="Fetch existing bookings"
    )

    return parser.parse_args()


def parse_slot_datetime(slot_str: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(slot_str, "%d/%m/%Y %H:%M")
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid slot format. Expected 'dd/mm/yyyy hh:mm', got '{slot_str}'"
        ) from e


async def main():
    args = parse_args()
    playwright_params = agent.PlaywrightParams(
        headless=not args.show,
        slow_mo=args.slow,
    )

    try:
        if args.command == "book":
            slot_datetime = parse_slot_datetime(args.slot)
            preference = slots.SlotPreference(
                weekday_lowercase=slot_datetime.strftime("%A").lower(),
                start_time=slots.human_readable_time_to_minutes(
                    slot_datetime.strftime("%H:%M")
                ),
                preferred_courts=[],
            )
            await agent.fetch_and_book_session(
                target_date=slot_datetime,
                preference=preference,
                playwright_params=playwright_params,
                dry_run=args.dry_run,
            )
        elif args.command == "fetch_bookings":
            await agent.fetch_existing_bookings_standalone(
                playwright_params=playwright_params,
            )
    except Exception as e:
        logger.error(f"Error during {args.command} process: {e}")
        raise


if __name__ == "__main__":
    # Load credentials from files
    env.setup_env()
    asyncio.run(main())
