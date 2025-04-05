import contextlib
import dataclasses
import datetime
import logging
import traceback
import playwright.async_api

import slots

logger = logging.getLogger(__name__)

DEBUG_PATH = "debug/debug.html"


@dataclasses.dataclass
class PlaywrightParams:
    headless: bool = True
    slow_mo: int = 0


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


async def login(page, username, password):
    await page.get_by_role("link", name="Sign in").click()
    await page.get_by_role("button", name="Login").click()
    await page.get_by_placeholder("Username").fill(username)
    await page.get_by_placeholder("Password").click()
    await page.get_by_placeholder("Password").fill(password)
    await page.get_by_role("button", name="Log in").click()
    # Wait for navigation or login success indicator
    logger.info("Wait for navigation or login success indicator")
    await page.wait_for_selector("#account-options", timeout=10000)
    # TODO: check something else, for example with page.expect_navigation() as navigation_info:
    await playwright.async_api.expect(page.locator("#account-options")).to_contain_text(
        "Eduard Zhuk"
    )


async def book_slot(page):
    logger.info("Continue with booking")
    await page.wait_for_selector('button:has-text("Continue booking")', timeout=2000)
    await page.get_by_role("button", name="Continue booking").click()
    logger.info("Wait for confirmation and verify")
    await page.wait_for_selector(
        'h1:has-text("Your booking has been confirmed")', timeout=5000
    )
    logger.info("Successfully booked session")


async def accept_cookies(page):
    try:
        await page.get_by_role("button", name="Accept All").click()
        await page.wait_for_timeout(500)
    except:
        pass  # Cookie banner might not be present


async def does_booking_already_exist(page, target_date, target_time):
    logger.info("Checking existing bookings")
    await page.goto("https://clubspark.lta.org.uk/PrioryPark2/Booking/Bookings")
    try:
        await page.wait_for_selector("#booking-tbody", timeout=1000)
    except Exception as e:
        logger.info("Waiting for booking list failed, assuming no existing bookings")
        return False

    bookings_html = await page.content()
    booked_slots = slots.parse_slots_from_bookings_list(bookings_html)
    for booked_slot in booked_slots:
        if (
            booked_slot.date.date() == target_date.date()
            and booked_slot.start_time == target_time
        ):
            return True
    return False


async def setup_booking_page(context, date_str):
    logger.info("Create new page start")
    page = await context.new_page()
    await page.goto(
        f"https://clubspark.lta.org.uk/PrioryPark2/Booking/BookByDate#?date={date_str}&role=guest"
    )
    await page.wait_for_selector(".resource-session", timeout=5000)


@contextlib.asynccontextmanager
async def dump_page_debug_info_on_exception(context, path_to_file=None):
    if path_to_file is None:
        path_to_file = DEBUG_PATH
    # Get the caller's frame (1 level up in the stack)
    try:
        yield
    except Exception as exc:
        with open(path_to_file, "w") as f:
            # Write to file as JSON
            f.write("<!--\n")
            if exc:
                f.write("\nException:\n")
                f.write("\n".join(traceback.format_exception(exc)))
            f.write("-->\n")
            for page in context.pages:
                f.write("<!--\n")
                f.write("Next page")
                f.write("-->\n")
                f.write(await page.content())
        raise


async def fetch_and_book_session(
    preference: slots.SlotPreference,
    target_date: datetime.datetime,
    playwright_params: PlaywrightParams,
    dry_run: bool = False,
) -> slots.Slot | None:
    """
    Fetch available sessions and book the earliest one
    date: YYYY-MM-DD format
    show: Whether to show the browser window during automation
    slow_mo: Number of milliseconds to wait between actions (for visualization)
    no_booking: If True, only check availability without making a booking
    """

    username, password = load_credentials()
    target_time = preference.start_time
    preferred_courts = preference.preferred_courts
    date_str = target_date.strftime("%Y-%m-%d")

    async with playwright.async_api.async_playwright() as p:
        browser = await p.chromium.launch(
            headless=playwright_params.headless, slow_mo=playwright_params.slow_mo
        )
        context = await browser.new_context()

        async with dump_page_debug_info_on_exception(context):
            page = await context.new_page()
            # Initial page load and cookie acceptance
            logger.info("Initial page load start")
            await page.goto(
                f"https://clubspark.lta.org.uk/PrioryPark2/Booking/BookByDate#?date={date_str}&role=guest"
            )

            logger.info("Login process start")
            await accept_cookies(page)
            await login(page, username, password)

            if await does_booking_already_exist(page, target_date, target_time):
                logger.info(
                    f"Already have a booking for {target_date} at {parse_time(target_time)}"
                )
                await browser.close()
                return

            logger.info("Slot booking process start")
            await setup_booking_page(context, date_str)

            # Get the page content and parse available sessions
            logger.info("Get the page content and parse available sessions start")
            html_content = await page.content()
            slot = slots.find_slot(
                html_content,
                target_time,
                target_date=target_date,
                preferred_courts=preferred_courts,
            )
            if not slot:
                # TODO: log which options were close
                logger.warn("Found no slot for preferred time, return")
                return

            logger.info(f"Found available slot at {parse_time(slot.start_time)}")
            logger.info("Click on the earliest available session")
            await page.locator(f'[data-test-id="{slot.slot_key}"]').click()
            if dry_run:
                logger.info("Dry run, skipping booking")
                return None
            await book_slot(page)
            logger.info("Booking process completed")
            return slot
