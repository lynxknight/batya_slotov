import dataclasses
from bs4 import BeautifulSoup, Tag, NavigableString
from datetime import datetime
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class TagChecker:
    def __init__(self):
        self.stats = Counter()

    def check(self, element: Tag | NavigableString | None) -> bool:
        """Check if an element is not None and is a Tag"""
        if element is None:
            self.stats["none"] += 1
            return False
        if not isinstance(element, Tag):
            self.stats["not_tag"] += 1
            return False
        self.stats["valid"] += 1
        return True

    def __call__(self, element: Tag | NavigableString | None) -> bool:
        return self.check(element)

    def report(self) -> str:
        """Report statistics about tag validation"""
        total = sum(self.stats.values())
        if total == 0:
            return "No tags were checked"
        if self.stats["valid"] == total:
            return "Tag validation stats: All tags were valid"
        return (
            f"Tag validation stats:\n"
            f"  Total tags checked: {total}\n"
            f"  Valid tags: {self.stats['valid']} ({self.stats['valid']/total*100:.1f}%)\n"
            f"  None values: {self.stats['none']} ({self.stats['none']/total*100:.1f}%)\n"
            f"  Not Tag objects: {self.stats['not_tag']} ({self.stats['not_tag']/total*100:.1f}%)"
        )


def parse_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM format"""
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def human_readable_time_to_minutes(time: str) -> int:
    """Convert HH:MM format to minutes since midnight"""
    hours, minutes = map(int, time.split(":"))
    return hours * 60 + minutes


@dataclasses.dataclass
class SlotPreference:
    weekday_lowercase: str
    start_time: int
    preferred_courts: list[int]

    @classmethod
    def from_preferences_json(
        cls, preferences_json: dict
    ) -> dict[str, "SlotPreference"]:
        """
        example preferences_json:
        {
            "preferences": [
                {
                    "weekdays": ["tuesday"],
                    "time": "16:00",
                    "courts": [3, 4]
                },
                {
                    "weekdays": ["saturday"],
                    "time": "08:00",
                    "courts": [3, 4]
            }
            ]
        }
        """
        result: dict[str, SlotPreference] = {}
        preferences = preferences_json["preferences"]
        for pref in preferences:
            weekdays = pref["weekdays"]
            for weekday in weekdays:
                if weekday in result:
                    raise ValueError(f"Duplicate weekday: {weekday}")
                result[weekday] = cls(
                    weekday,
                    human_readable_time_to_minutes(pref["time"]),
                    pref["courts"],
                )
        return result

    def __str__(self) -> str:
        return f"SlotPreference(weekday={self.weekday_lowercase}, start_time={parse_time(self.start_time)}, preferred_courts={self.preferred_courts})"


@dataclasses.dataclass
class Slot:
    slot_key: str  # uses data-test-id internally
    court: int
    start_time: int  # minutes since midnight
    date: datetime | None = None

    def __str__(self) -> str:
        return (
            f"Slot<slot_key={self.slot_key}, court={self.court}, "
            f"date={self.date.strftime('%Y-%m-%d') if self.date else 'None'}, "
            f"start_time={parse_time(self.start_time)}>"
        )

    def __repr__(self) -> str:
        return self.__str__()


def parse_slots(html_content: str) -> list[Slot]:
    soup = BeautifulSoup(html_content, "html.parser")
    available_slots: list[Slot] = []
    tag_checker = TagChecker()

    for resource in soup.find_all("div", class_="resource"):
        if not tag_checker(resource):
            continue

        # Get court number from data-resource-name
        resource_name = resource.get("data-resource-name", "")
        if not isinstance(resource_name, str) or "Court" not in resource_name:
            raise ValueError(f"Invalid or missing data-resource-name: {resource_name}")

        try:
            court_num = int(resource_name.split()[-1])
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"Could not parse court number from data-resource-name: {resource_name}"
            ) from e

        for session in resource.find_all("div", class_="resource-interval"):
            if not tag_checker(session):
                continue
            # Skip if session is unavailable
            if not session.find("span", class_="available-booking-slot"):
                continue

            start_time_str = session.get("data-system-start-time")
            if not isinstance(start_time_str, str):
                continue
            try:
                start_time = int(start_time_str)
            except ValueError:
                continue

            book_interval = session.find("a", class_="book-interval")
            if not tag_checker(book_interval):
                continue
            slot_key = book_interval.get("data-test-id")
            if not isinstance(slot_key, str):
                continue
            available_slots.append(Slot(slot_key, court_num, start_time, date=None))

    logger.info(tag_checker.report())
    return available_slots


def pick_slot(
    available_slots: list[Slot],
    target_time: int,
    preferred_courts: list[int] | None = None,
) -> Slot | None:
    if not preferred_courts:
        preferred_courts = []

    target_slots = [s for s in available_slots if s.start_time == target_time]
    if preferred_courts:
        preferred_slot = next(
            (s for s in target_slots if s.court in preferred_courts), None
        )
        if preferred_slot:
            return preferred_slot

    # Fallback to random available slot at target time
    if target_slots:
        return target_slots[0]

    return None


def find_slot(
    html_content: str,
    target_time: int,
    target_date: datetime,
    preferred_courts: list[int] | None = None,
) -> Slot | None:
    """
    Find available slot based on preferences
    target_time: Target time in minutes since midnight (e.g. 960 for 16:00)
    target_date: affects only "Slot" object contents, datetime object representing the target date,
    preferred_courts: List of preferred court numbers in order of preference
    Returns:
        Slot object if found, None if no slot is available
    """
    available_slots = parse_slots(html_content)
    logger.info(f"Available slots: {available_slots}")
    if len(available_slots) == 0:
        open("debug/13_apr_day_view.html", "w").write(html_content)
        logger.warn("Written debug file as there are no available slots")
    picked_slot = pick_slot(available_slots, target_time, preferred_courts)
    if picked_slot is None:
        return None
    picked_slot.date = target_date
    return picked_slot


def parse_slots_from_old_bookings_list(html_content: str) -> list[Slot]:
    """
    Parse booked slots from the old bookings list HTML page.
    Returns a list of Slot objects representing booked court times.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    booked_slots: list[Slot] = []
    tag_checker = TagChecker()

    # Find the bookings table body
    booking_tbody = soup.find("tbody", id="booking-tbody")
    if not tag_checker(booking_tbody):
        return []

    rows = booking_tbody.find_all("tr") if isinstance(booking_tbody, Tag) else []
    for row in rows:
        if not tag_checker(row):
            continue
        # Get date from the first column
        date_cell = row.find("td", class_="booking-summary")
        if not tag_checker(date_cell):
            continue

        # Parse date from the strong tag
        date_strong = date_cell.find("strong")
        if not tag_checker(date_strong):
            continue

        try:
            date = datetime.strptime(date_strong.text.strip(), "%d/%m/%Y")
        except ValueError:
            continue

        # Get time from the second column
        time_cell = row.find("td", class_="time")
        if not tag_checker(time_cell):
            continue

        time_span = time_cell.find("span", class_="booking-time")
        if not tag_checker(time_span):
            continue

        # Get court from the third column
        resource_cell = row.find("td", class_="resource")
        if not tag_checker(resource_cell):
            continue

        resource_span = resource_cell.find("span", class_="booking-resource")
        if not tag_checker(resource_span):
            continue

        # Parse court number
        court_text = resource_span.text.strip()
        try:
            court_num = int(court_text.split()[-1])
        except (ValueError, IndexError):
            continue

        # Parse time
        time_text = time_span.text.strip()
        start_time = time_text.split("-")[0].strip()
        try:
            hours, minutes = map(int, start_time.split(":"))
            minutes_since_midnight = hours * 60 + minutes
        except (ValueError, IndexError):
            continue

        # Use booking confirmation URL as slot key
        booking_link = date_cell.find("a")
        if not tag_checker(booking_link):
            continue
        href = booking_link.get("href")
        if not isinstance(href, str):
            continue
        slot_key = href.split("/")[-1]

        booked_slots.append(Slot(slot_key, court_num, minutes_since_midnight, date))

    logger.info(tag_checker.report())
    return booked_slots


def parse_slots_from_new_bookings_list(html_content: str) -> list[Slot]:
    """
    Parse booked slots from the new bookings list HTML page.
    Returns a list of Slot objects representing booked court times.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    booked_slots: list[Slot] = []
    tag_checker = TagChecker()

    for panel in soup.find_all("div", class_="block-panel"):
        if not tag_checker(panel):
            continue

        # Get date and time from h2
        title_div = panel.find("div", class_="block-panel-title")
        if not tag_checker(title_div):
            continue
        h2 = title_div.find("h2")
        if not tag_checker(h2):
            continue

        try:
            # Example: "Tue, 19 Aug 2025, 16:00 - 17:00"
            date_time_str = h2.text.strip()
            date_part, time_part = date_time_str.split(",")[1:]
            time_part = time_part.split("-")[0].strip()
            # combine date and time and parse
            date_str = date_part.strip() + " " + time_part
            dt = datetime.strptime(date_str, "%d %b %Y %H:%M")
            minutes_since_midnight = dt.hour * 60 + dt.minute

        except (ValueError, IndexError):
            continue

        # Get court number
        resource_row = panel.find(
            "span",
            class_="block-panel-row-label",
            string=lambda t: "Resource(s)" in t if t else False,
        )
        if not resource_row:
            continue

        resource_value = resource_row.find_next_sibling(
            "span", class_="block-panel-row-value"
        )
        if not tag_checker(resource_value):
            continue

        court_text = resource_value.text.strip()
        try:
            court_num = int(court_text.split()[-1])
        except (ValueError, IndexError):
            continue

        # Get slot key from booking link
        details_link = panel.find("a", class_="cs-btn")
        if not tag_checker(details_link):
            continue
        href = details_link.get("href")
        if not isinstance(href, str):
            continue
        slot_key = href.split("/")[-1]

        booked_slots.append(Slot(slot_key, court_num, minutes_since_midnight, dt))

    logger.info(tag_checker.report())
    return booked_slots


def parse_slots_from_bookings_list(html_content: str) -> list[Slot]:
    """
    Parse booked slots from the bookings list HTML page.
    Returns a list of Slot objects representing booked court times.
    """
    slots = parse_slots_from_new_bookings_list(html_content)
    if slots:
        return slots
    return parse_slots_from_old_bookings_list(html_content)
