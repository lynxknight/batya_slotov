import pytest
import datetime
from slots import (
    parse_slots,
    pick_slot,
    Slot,
    parse_slots_from_old_bookings_list,
    parse_slots_from_new_bookings_list,
)


@pytest.fixture
def html_content():
    """Fixture that provides the test HTML content"""
    with open("examples/day_view.html", "r") as f:
        return f.read()


@pytest.fixture
def paid_slots_html():
    """Fixture that provides the paid slots view HTML content"""
    with open("examples/paid_slots_view.html", "r") as f:
        return f.read()


# Tests for parse_slots function
def test_parse_slots_empty():
    """Test parsing empty HTML"""
    slots = parse_slots("")
    assert len(slots) == 0


def test_parse_slots_no_available():
    """Test parsing HTML with no available slots"""
    # Create HTML with only unavailable slots
    html = """
    <div class="resource" data-resource-name="Court 1">
        <div class="resource-session">
            <div class="unavailable"></div>
        </div>
    </div>
    """
    slots = parse_slots(html)
    assert len(slots) == 0


def test_parse_slots_missing_court():
    """Test parsing slots with missing court information"""
    html = """
    <div class="resource" data-resource-name="Court 1">
        <div class="resource-session" data-start-time="480" data-slot-key="key1">
            <span>Some content</span>
        </div>
    </div>
    """
    slots = parse_slots(html)
    assert len(slots) == 0


def test_parse_slots_with_data_attributes():
    """Test parsing slots with court info in data attributes"""
    html = """
    <div class="resource" data-resource-name="Court 3">
        <div class="resource-interval" data-system-start-time="480">
            <span class="available-booking-slot"></span>
            <a class="book-interval" data-test-id="booking-123|2025-04-12|480"></a>
        </div>
    </div>
    <div class="resource" data-resource-name="Court 4">
        <div class="resource-interval" data-system-start-time="540">
            <span class="available-booking-slot"></span>
            <a class="book-interval" data-test-id="booking-456|2025-04-12|540"></a>
        </div>
    </div>
    """
    slots = parse_slots(html)
    assert len(slots) == 2
    assert slots[0].court == 3
    assert slots[1].court == 4


def test_parse_paid_slots_view(paid_slots_html):
    """Test parsing slots from paid slots view HTML"""
    slots = parse_slots(paid_slots_html)
    assert len(slots) == 19, f"Expected 19 slots but got {len(slots)}"

    # Verify first three slots from Court 1
    expected_first_slots = [
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-27|420",
            court=1,
            start_time=420,  # 07:00
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-27|480",
            court=1,
            start_time=480,  # 08:00
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-27|1080",
            court=1,
            start_time=1080,  # 18:00
        ),
    ]

    # Check that first three slots match expected
    for i, expected_slot in enumerate(expected_first_slots):
        assert (
            slots[i] == expected_slot
        ), f"Slot {i} does not match expected: {slots[i]} != {expected_slot}"


def test_parse_slots_valid(html_content):
    """Test parsing valid slots from real HTML"""
    slots = parse_slots(html_content)
    assert len(slots) > 0
    # Verify slot structure
    first_slot = slots[0]
    assert isinstance(first_slot, Slot)
    assert isinstance(first_slot.start_time, int)
    assert isinstance(first_slot.slot_key, str)
    assert isinstance(first_slot.court, int)

    expected_slots = [
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|420",
            court=1,
            start_time=420,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|780",
            court=1,
            start_time=780,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|840",
            court=1,
            start_time=840,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|900",
            court=1,
            start_time=900,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|960",
            court=1,
            start_time=960,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1020",
            court=1,
            start_time=1020,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1080",
            court=1,
            start_time=1080,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1140",
            court=1,
            start_time=1140,
        ),
        Slot(
            slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1200",
            court=1,
            start_time=1200,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|420",
            court=2,
            start_time=420,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|660",
            court=2,
            start_time=660,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|960",
            court=2,
            start_time=960,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1020",
            court=2,
            start_time=1020,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1080",
            court=2,
            start_time=1080,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1140",
            court=2,
            start_time=1140,
        ),
        Slot(
            slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1200",
            court=2,
            start_time=1200,
        ),
        Slot(
            slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|840",
            court=3,
            start_time=840,
        ),
        Slot(
            slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|1080",
            court=3,
            start_time=1080,
        ),
        Slot(
            slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|1140",
            court=3,
            start_time=1140,
        ),
        Slot(
            slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|1200",
            court=3,
            start_time=1200,
        ),
        Slot(
            slot_key="booking-bb1f7125-f5fd-4b81-af62-51e03bfe51c1|2025-04-12|1080",
            court=4,
            start_time=1080,
        ),
        Slot(
            slot_key="booking-bb1f7125-f5fd-4b81-af62-51e03bfe51c1|2025-04-12|1140",
            court=4,
            start_time=1140,
        ),
        Slot(
            slot_key="booking-bb1f7125-f5fd-4b81-af62-51e03bfe51c1|2025-04-12|1200",
            court=4,
            start_time=1200,
        ),
    ]

    assert slots == expected_slots


def test_parse_slots_invalid_resource_name():
    """Test parsing slots with invalid data-resource-name"""
    # Test missing data-resource-name
    html1 = """
    <div class="resource">
        <div class="resource-session">
            <div class="available"></div>
        </div>
    </div>
    """
    with pytest.raises(ValueError, match="Invalid or missing data-resource-name"):
        parse_slots(html1)

    # Test invalid data-resource-name format
    html2 = """
    <div class="resource" data-resource-name="Invalid Court">
        <div class="resource-session">
            <div class="available"></div>
        </div>
    </div>
    """
    with pytest.raises(
        ValueError, match="Could not parse court number from data-resource-name"
    ):
        parse_slots(html2)

    # Test valid data-resource-name
    html3 = """
    <div class="resource" data-resource-name="Court 1">
        <div class="resource-session">
            <div class="available"></div>
        </div>
    </div>
    """
    slots = parse_slots(html3)
    assert len(slots) == 0  # No available slots in this HTML


# Tests for pick_slot function
@pytest.fixture
def sample_slots():
    """Fixture providing sample slot data"""
    return [
        Slot(slot_key="1_1700", court=1, start_time=1020),  # 17:00 on court 1
        Slot(slot_key="1_0800", court=1, start_time=480),  # 8:00 on court 1
        Slot(slot_key="2_1600", court=2, start_time=960),  # 16:00 on court 2
        Slot(slot_key="3_0800", court=3, start_time=480),  # 8:00 on court 3
        Slot(slot_key="3_1600", court=3, start_time=960),  # 16:00 on court 3
        Slot(slot_key="4_0800", court=4, start_time=480),  # 8:00 on court 4
    ]


@pytest.mark.parametrize(
    "target_time,expected_key",
    [
        (
            480,
            "1_0800",
        ),  # 8:00 - should get first available
        (960, "2_1600"),  # 16:00
        (1020, "1_1700"),  # 17:00
    ],
)
def test_pick_slot_specific_time(sample_slots, target_time, expected_key):
    """Test picking slots at specific times"""
    slot = pick_slot(sample_slots, target_time=target_time)
    assert slot.slot_key == expected_key
    assert slot.start_time == target_time


@pytest.mark.parametrize(
    "target_time,courts,expected_key",
    [
        (480, [3], "3_0800"),  # 8:00 on court 3
        (480, [4], "4_0800"),  # 8:00 on court 4
        (960, [3], "3_1600"),  # 16:00 on court 3
    ],
)
def test_pick_slot_time_and_courts(sample_slots, target_time, courts, expected_key):
    """Test picking slots with both time and court preferences"""
    slot = pick_slot(sample_slots, target_time=target_time, preferred_courts=courts)
    assert slot.slot_key == expected_key
    assert slot.start_time == target_time


def test_pick_slot_nonexistent_time(sample_slots):
    """Test picking slot at non-existent time"""
    slot = pick_slot(sample_slots, target_time=1440)  # 24:00
    assert slot is None


def test_pick_slot_empty_list():
    """Test picking slot from empty list"""
    slot = pick_slot([], target_time=480)
    assert slot is None
    slot = pick_slot([], target_time=480, preferred_courts=[1])
    assert slot is None


@pytest.fixture
def bookings_list_html():
    """Fixture that provides the old bookings list HTML content"""
    with open("examples/bookings_list.html", "r") as f:
        return f.read()


def test_parse_slots_from_old_bookings_list(bookings_list_html):
    """Test parsing booked slots from bookings list HTML"""
    slots = parse_slots_from_old_bookings_list(bookings_list_html)
    assert slots == [
        Slot(
            slot_key="16bfafe5-3314-46c2-9999-4a83e5508deb",
            court=1,
            start_time=420,
            date=datetime.datetime(2025, 4, 8),
        ),
        Slot(
            slot_key="f303a467-da6e-428a-bc68-3680be134cea",
            court=2,
            start_time=480,
            date=datetime.datetime(2025, 4, 17),
        ),
    ]


@pytest.fixture
def new_bookings_html():
    """Fixture that provides the new bookings list HTML content"""
    with open("examples/new_bookings.html", "r") as f:
        return f.read()


def test_parse_slots_from_new_bookings_list(new_bookings_html):
    """Test parsing booked slots from the new bookings list HTML format"""
    slots = parse_slots_from_new_bookings_list(new_bookings_html)
    assert slots == [
        Slot(
            slot_key="3b619e14-899b-402a-a914-f95b6f464961",
            court=3,
            start_time=960,  # 16:00
            date=datetime.datetime(2025, 8, 19, 16, 0),
        ),
        Slot(
            slot_key="52846ae4-f601-437a-b566-1a2d714d6d19",
            court=3,
            start_time=480,  # 08:00
            date=datetime.datetime(2025, 8, 23, 8, 0),
        ),
    ]
