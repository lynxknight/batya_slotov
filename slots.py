import dataclasses
from bs4 import BeautifulSoup
from datetime import datetime


def parse_time(minutes):
    """Convert minutes since midnight to HH:MM format"""
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}"


@dataclasses.dataclass
class Slot:
    slot_key: str  # uses data-test-id internally
    court: int
    start_time: int  # minutes since midnight
    date: datetime | None = None

    def __str__(self):
        return (
            f"Slot<slot_key={self.slot_key}, court={self.court}, "
            f"date={self.date.strftime('%Y-%m-%d') if self.date else 'None'}, "
            f"start_time={parse_time(self.start_time)}>"
        )

    def __repr__(self):
        return self.__str__()


def parse_slots(html_content) -> list[Slot]:
    soup = BeautifulSoup(html_content, "html.parser")
    available_slots = []
    for resource in soup.find_all("div", class_="resource"):
        for session in resource.find_all("div", class_="resource-interval"):
            # Skip if session is unavailable
            if not session.find("span", class_="available-booking-slot"):
                continue

            # Get court number from the visuallyhidden span
            court_span = session.find("span", class_="visuallyhidden")
            if not court_span:
                continue
            court_num = int(court_span.text.strip().split()[-1])

            start_time = int(session.get("data-system-start-time"))
            slot_key = session.find("a", class_="book-interval").get("data-test-id")
            available_slots.append(Slot(slot_key, court_num, start_time, date=None))
    return available_slots


def pick_slot(
    available_slots: list[Slot], target_time, preferred_courts: list[int] | None = None
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
    html_content, target_time: int, target_date: datetime, preferred_courts=None
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
    picked_slot = pick_slot(available_slots, target_time, preferred_courts)
    if picked_slot is None:
        return None
    picked_slot.date = target_date
    return picked_slot


def parse_slots_from_bookings_list(html_content) -> list[Slot]:
    """
    Parse booked slots from the bookings list HTML page.
    Returns a list of Slot objects representing booked court times.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    booked_slots = []

    # Find the bookings table body
    booking_tbody = soup.find("tbody", id="booking-tbody")
    if not booking_tbody:
        return []

    for row in booking_tbody.find_all("tr"):
        # Get date from the first column
        date_cell = row.find("td", class_="booking-summary")
        if not date_cell:
            continue

        # Parse date from the strong tag
        date_strong = date_cell.find("strong")
        if not date_strong:
            continue

        try:
            date = datetime.strptime(date_strong.text.strip(), "%d/%m/%Y")
        except ValueError:
            continue

        # Get time from the second column
        time_cell = row.find("td", class_="time")
        if not time_cell:
            continue

        time_span = time_cell.find("span", class_="booking-time")
        if not time_span:
            continue

        # Get court from the third column
        resource_cell = row.find("td", class_="resource")
        if not resource_cell:
            continue

        resource_span = resource_cell.find("span", class_="booking-resource")
        if not resource_span:
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
        if not booking_link:
            continue
        slot_key = booking_link.get("href", "").split("/")[-1]

        booked_slots.append(Slot(slot_key, court_num, minutes_since_midnight, date))

    return booked_slots
