import contextlib
import dataclasses
import datetime
import logging
import traceback
import playwright.async_api
import os

import env
import slots
import payment_form

logger = logging.getLogger(__name__)

DEBUG_PATH = "debug/debug.html"


@dataclasses.dataclass
class PlaywrightParams:
    headless: bool = True
    slow_mo: int = 0


@dataclasses.dataclass
class BookingResult:
    success: bool
    slot: slots.Slot | None
    error: Exception | None
    reason: str | None = ""


async def new_context(browser):
    if os.getenv("ZYTE_API_KEY"):
        logger.info("Using Zyte proxy for context")
        return await browser.new_context(
            ignore_https_errors=True,
            proxy={
                "server": "https://api.zyte.com:8014",
                "username": os.getenv("ZYTE_API_KEY"),
            },
        )
    return await browser.new_context()


def parse_time(minutes):
    """Convert minutes since midnight to HH:MM format"""
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def load_credentials():
    """Load username and password from separate files"""
    username = os.getenv("TENNIS_USERNAME")
    password = os.getenv("TENNIS_PASSWORD")

    if not username or not password:
        raise ValueError(
            "TENNIS_USERNAME and TENNIS_PASSWORD environment variables must be set"
        )

    return username, password


async def login(page, username, password):
    logger.info("Login start")
    await page.get_by_role("link", name="Sign in").click()
    logger.info("Sign in clicked")
    await page.get_by_role("button", name="Login").click()
    logger.info("Login clicked")
    await page.get_by_placeholder("Username").fill(username)
    await page.get_by_placeholder("Password").click()
    await page.get_by_placeholder("Password").fill(password)
    await page.get_by_role("button", name="Log in").click()
    # Wait for navigation or login success indicator
    logger.info("Wait for network idle")
    await page.wait_for_load_state("networkidle")
    logger.info("Wait for navigation or login success indicator")
    await page.wait_for_selector("#account-options", timeout=10000)
    # # TODO: check something else, for example with page.expect_navigation() as navigation_info:
    # await playwright.async_api.expect(page.locator("#account-options")).to_contain_text(
    #     "Eduard Zhuk"
    # )


async def booking_confirmation(page):
    await page.wait_for_selector(
        'h1:has-text("Your booking has been confirmed")', timeout=10000
    )
    logger.info("Successfully booked session")


# async def book_slot(page):
#     logger.info("Continue with booking")
#     await page.wait_for_selector('button:has-text("Continue booking")', timeout=2000)
#     await page.get_by_role("button", name="Continue booking").click()
#     logger.info("Wait for confirmation and verify")
#     try:
#         return await booking_confirmation(page)
#     except playwright.async_api.TimeoutError:
#         logger.info(
#             'Confirmation message not found, checking if "paynow" flow is needed'
#         )
#         pass
#     return book_slot_via_paynow(page)


async def book_slot_via_paynow(page, dry_run: bool = False):
    logger.info("Waiting for continue booking button")
    await page.wait_for_selector('button:has-text("Continue booking")', timeout=2000)
    logger.info("Clicking continue booking button")
    await page.get_by_role("button", name="Continue booking").click()
    logger.info("Waiting for paynow button")
    try:
        await page.wait_for_selector("button#paynow", timeout=2000)
    except playwright.async_api.TimeoutError as e:
        logger.info("Paynow button not found, maybe free booking?")
        try:
            await booking_confirmation(page)
        except playwright.async_api.TimeoutError:
            logger.info("No confirmation message found, raise")
            raise e
        else:
            logger.info("Free booking confirmed, return")
            return
    logger.info("Paynow button found")
    button_text = await page.locator("button#paynow").text_content()
    if "pay" in button_text.lower():
        logger.info("Actually need to pay")
        return await book_slot_with_actual_payment(page, dry_run=dry_run)
    logger.info("No need to pay")
    return book_slot_with_free_payment(page, dry_run=dry_run)


async def book_slot_with_actual_payment(page, dry_run: bool = False):
    # assumes that button#paynow exists
    await page.locator("button#paynow").click()
    await payment_form.process_payment(
        page,
        payment_form.Card.from_string(env.Variable.get_tennis_card()),
        dry_run=dry_run,
    )
    if dry_run:
        logger.info("Dry run, skipping confirmation")
        return
    # Wait for confirmation message
    return await booking_confirmation(page)


async def book_slot_with_free_payment(page, dry_run: bool = False):
    if dry_run:
        logger.info("Dry run, skipping booking")
        return
    await page.locator("button#paynow").click()
    # Wait for confirmation message
    return await booking_confirmation(page)


async def accept_cookies(page):
    try:
        await page.get_by_role("button", name="Accept All").click()
        await page.wait_for_timeout(500)
    except:
        logger.info("Assuming cookie banner is not present")
        pass  # Cookie banner might not be present


async def fetch_existing_bookings(page) -> list[slots.Slot]:
    """Fetch all existing bookings from the bookings page"""
    logger.info("Fetching existing bookings")
    await page.goto("https://clubspark.lta.org.uk/PrioryPark2/Booking/Bookings")
    try:
        # #booking-tbody was neded for old layout
        await page.wait_for_selector("#booking-tbody, .block-panel", timeout=1000)
    except Exception:
        logger.info("Waiting for booking list failed, assuming no existing bookings")
        return []

    bookings_html = await page.content()
    return slots.parse_slots_from_bookings_list(bookings_html)


async def fetch_existing_bookings_standalone(
    playwright_params: PlaywrightParams | None = None,
) -> list[slots.Slot]:
    """Standalone function to fetch existing bookings with full setup"""
    username, password = load_credentials()
    if playwright_params is None:
        logger.info("No playwright params provided, using default")
        playwright_params = PlaywrightParams(headless=True, slow_mo=0)

    async with playwright.async_api.async_playwright() as p:
        browser = await p.chromium.launch(
            headless=playwright_params.headless,
            slow_mo=playwright_params.slow_mo,
        )
        context = await new_context(browser)

        logger.info("Browser set up")
        async with dump_page_debug_info_on_exception(context):
            page = await context.new_page()
            logger.info("New page created")
            await page.goto(
                f"https://clubspark.lta.org.uk/PrioryPark2/Booking/BookByDate"
            )
            logger.info("Initial page loaded")

            await accept_cookies(page)
            logger.info("Cookies accepted")
            await login(page, username, password)
            logger.info("Logged in, going to fetch bookings")

            return await fetch_existing_bookings(page)


async def does_booking_already_exist(page, target_date, target_time):
    """Check if a booking already exists for the given date and time"""
    booked_slots = await fetch_existing_bookings(page)
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
    await page.wait_for_timeout(3000)
    return page


@contextlib.asynccontextmanager
async def dump_page_debug_info_on_exception(context, debug_folder=None):
    if debug_folder is None:
        debug_folder = "debug"
    # Get the caller's frame (1 level up in the stack)
    try:
        yield
    except Exception as exc:
        debug_html_path = os.path.join(debug_folder, "debug.html")
        with open(debug_html_path, "w") as f:
            # Write to file as JSON
            f.write("<!--\n")
            if exc:
                f.write("\nException:\n")
                f.write("\n".join(traceback.format_exception(exc)))
            f.write("-->\n")
            debug_images = []
            for i, page in enumerate(context.pages):
                f.write("<!--\n")
                f.write(f"Page {i}")
                f.write("-->\n")
                f.write(await page.content())
                image_path = os.path.join(debug_folder, f"page_{i}.png")
                try:
                    await page.screenshot(path=image_path)
                    debug_images.append(image_path)
                except Exception as ex:
                    logger.warn("failed to store screenshot ")
                    logger.exception(ex)
            logger.info("trying to set debug images")
            for img in debug_images:
                from telegram_bot import get_notifier

                logger.info(f"sending image {img}...")
                try:
                    await get_notifier().send_debug_picture_to_owner(img)
                except Exception as exc2:
                    logger.exception(exc2)
                else:
                    logger.info(f"sent image {img}")
        raise


async def fetch_and_book_session(
    preference: slots.SlotPreference,
    target_date: datetime.datetime,
    playwright_params: PlaywrightParams,
    dry_run: bool = False,
) -> BookingResult:
    """
    Fetch available sessions and book the earliest one
        date: YYYY-MM-DD format
        show: Whether to show the browser window during automation
        slow_mo: Number of milliseconds to wait between actions (for visualization)
        no_booking: If True, only check availability without making a booking
    Returns:
        BookingResult with success status, slot info if available, and error/reason if unsuccessful
    """

    username, password = load_credentials()
    target_time = preference.start_time
    preferred_courts = preference.preferred_courts
    date_str = target_date.strftime("%Y-%m-%d")

    async with playwright.async_api.async_playwright() as p:
        browser = await p.chromium.launch(
            headless=playwright_params.headless, slow_mo=playwright_params.slow_mo
        )
        context = await new_context(browser)

        async with dump_page_debug_info_on_exception(context):
            login_page = await context.new_page()
            # Initial page load and cookie acceptance
            logger.info("Initial page load start")
            await login_page.goto(
                f"https://clubspark.lta.org.uk/PrioryPark2/Booking/BookByDate#?date={date_str}&role=guest"
            )

            logger.info("Login process start")
            await accept_cookies(login_page)
            await login(login_page, username, password)

            if await does_booking_already_exist(login_page, target_date, target_time):
                logger.info(
                    f"Already have a booking for {target_date} at {parse_time(target_time)}"
                )
                return BookingResult(
                    success=False,
                    slot=None,
                    error=None,
                    reason=f"Already have a booking for {target_date.strftime('%Y-%m-%d')} at {parse_time(target_time)}",
                )

            logger.info("Slot booking process start")
            booking_page = await setup_booking_page(context, date_str)

            # Get the page content and parse available sessions
            logger.info("Get the page content and parse available sessions start")
            html_content = await booking_page.content()
            slot = slots.find_slot(
                html_content,
                target_time,
                target_date=target_date,
                preferred_courts=preferred_courts,
            )
            if not slot:
                # TODO: log which options were close
                logger.warn("Found no slot for preferred time, return")
                return BookingResult(
                    success=False,
                    slot=None,
                    error=None,
                    reason=f"Found no slot at {date_str} for preferred time {slots.parse_time(preference.start_time)}",
                )

            logger.info(f"Found available slot at {parse_time(slot.start_time)}")
            logger.info("Click on the earliest available session")
            await booking_page.locator(f'[data-test-id="{slot.slot_key}"]').click()
            await book_slot_via_paynow(booking_page, dry_run=dry_run)
            logger.info("Booking process completed")
            return BookingResult(success=True, slot=slot, error=None)
