import asyncio
import traceback
from playwright.async_api import async_playwright, expect
import argparse
from datetime import datetime
import inspect
import json
import slots

DEBUG_PATH = "debug/debug.html"

def parse_time(minutes):
    """Convert minutes since midnight to HH:MM format"""
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def load_credentials():
    """Load username and password from .creds file"""
    with open(".creds", "r") as f:
        lines = f.readlines()
        if len(lines) < 2:
            raise ValueError(
                "Credentials file must contain username on first line and password on second line"
            )
        return lines[0].strip(), lines[1].strip()


async def write_debug(path_to_file, page, exc: Exception = None):
    # Get the caller's frame (1 level up in the stack)
    frame = inspect.currentframe().f_back
    # Get a copy of the caller's local variables
    caller_locals = frame.f_locals.copy()

    # Convert non-serializable objects to strings
    serializable_locals = {
        k: (
            v
            if isinstance(v, (int, float, str, list, dict, bool, type(None)))
            else str(v)
        )
        for k, v in caller_locals.items()
        if "html_content" not in k and "password" not in k
    }
    with open(path_to_file, "w") as f:
        # Write to file as JSON
        f.write("<!--\n")
        f.write("Python context:\n")
        f.write("Locals:\n")
        json.dump(serializable_locals, f, indent=2)
        if exc:
            f.write("\nException:\n")
            f.write(traceback.format_exception(exc))
        f.write("-->\n")
        f.write(await page.content())


async def login(page, username, password):
    await page.get_by_role("link", name="Sign in").click()
    await page.get_by_role("button", name="Login").click()
    await page.get_by_placeholder("Username").fill(username)
    await page.get_by_placeholder("Password").click()
    await page.get_by_placeholder("Password").fill(password)
    await page.get_by_role("button", name="Log in").click()
    # Wait for navigation or login success indicator
    print("Wait for navigation or login success indicator")
    await page.wait_for_selector("#account-options", timeout=10000)
    await expect(page.locator("#account-options")).to_contain_text("Eduard Zhuk")


async def book_slot(page):
    print("Continue with booking")
    await page.wait_for_selector('button:has-text("Continue booking")', timeout=2000)
    await page.get_by_role("button", name="Continue booking").click()
    print("Wait for confirmation and verify")
    await page.wait_for_selector(
        'h1:has-text("Your booking has been confirmed")', timeout=5000
    )
    print(f"Successfully booked session")


async def accept_cookies(page):
    try:
        await page.get_by_role("button", name="Accept All").click()
        await page.wait_for_timeout(500)
    except:
        pass  # Cookie banner might not be present


async def fetch_and_book_session(
    date: str, show: bool = False, slow_mo: int = 0, no_booking: bool = False
) -> None:
    """
    Fetch available sessions and book the earliest one
    date: YYYY-MM-DD format
    show: Whether to show the browser window during automation
    slow_mo: Number of milliseconds to wait between actions (for visualization)
    no_booking: If True, only check availability without making a booking
    """

    username, password = load_credentials()

    # TODO: fix on higher level (date should define target time outside this function)
    # Determine target time and court preferences based on day of week
    target_date = datetime.strptime(date, "%Y-%m-%d")
    weekday = target_date.weekday()
    preferred_courts = [3, 4]  # Courts 3 and 4 are always preferred

    # Tuesday is 1, Saturday is 5
    target_time = None
    if weekday == 1:  # Tuesday
        target_time = 960  # 16:00 (16 * 60)
    elif weekday == 5:  # Saturday
        target_time = 480  # 8:00 (8 * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not show, slow_mo=slow_mo)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Initial page load and cookie acceptance
            print("Initial page load start")
            await page.goto(
                f"https://clubspark.lta.org.uk/PrioryPark2/Booking/BookByDate#?date={date}&role=guest"
            )

            print("Login process start")
            await accept_cookies(page)
            await login(page, username, password)

            print("Slot booking process start")
            page = await context.new_page()
            await page.goto(
                f"https://clubspark.lta.org.uk/PrioryPark2/Booking/BookByDate#?date={date}&role=guest"
            )
            await page.wait_for_selector(".resource-session", timeout=5000)
            await page.wait_for_timeout(1000)

            # Get the page content and parse available sessions
            print("Get the page content and parse available sessions start")
            html_content = await page.content()
            slot = slots.find_slot(html_content, target_time, preferred_courts)

            if slot:
                print(f"Found available session at {parse_time(slot.start_time)}")
                print("Click on the earliest available session")
                session_selector = f'[data-test-id="{slot.slot_key}"]'
                await page.locator(session_selector).click()
                if not no_booking:
                    await book_slot(page)
                    print("Booking process completed")
                else:
                    print("Skipping booking as --no-booking was specified")
            else:
                print("No available sessions found")
        except Exception as exc:
            await write_debug(".debug.html", page, exc)
            raise

        await write_debug(".debug.html", page)
        await browser.close()


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
        "--no-booking",
        action="store_true",
        help="Only check availability without making a booking",
    )
    parser.add_argument(
        "date",
        type=lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d"),
        help="Date in YYYY-MM-DD format",
    )
    args = parser.parse_args()
    return args


async def main():
    args = parse_args()
    try:
        await fetch_and_book_session(args.date, args.show, args.slow, args.no_booking)
    except Exception as e:
        print(f"Error during booking process: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
