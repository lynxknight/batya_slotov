import pytest
from slots import parse_slots, pick_slot, Slot


@pytest.fixture
def html_content():
    """Fixture that provides the test HTML content"""
    with open("examples/day_view.html", "r") as f:
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
    <div class="resource">
        <div class="resource-session">
            <div class="unavailable"></div>
            <span class="visuallyhidden">on Court 1</span>
        </div>
    </div>
    """
    slots = parse_slots(html)
    assert len(slots) == 0


def test_parse_slots_missing_court():
    """Test parsing slots with missing court information"""
    html = """
    <div class="resource">
        <div class="resource-session" data-start-time="480" data-slot-key="key1">
            <span>Some content</span>
        </div>
    </div>
    """
    slots = parse_slots(html)
    assert len(slots) == 0


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
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|420", court=1, start_time=420),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|780", court=1, start_time=780),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|840", court=1, start_time=840),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|900", court=1, start_time=900),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|960", court=1, start_time=960),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1020", court=1, start_time=1020),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1080", court=1, start_time=1080),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1140", court=1, start_time=1140),
        Slot(slot_key="booking-ea5042dd-ba18-4c7d-9d09-9173896e035d|2025-04-12|1200", court=1, start_time=1200),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|420", court=2, start_time=420),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|660", court=2, start_time=660),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|960", court=2, start_time=960),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1020", court=2, start_time=1020),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1080", court=2, start_time=1080),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1140", court=2, start_time=1140),
        Slot(slot_key="booking-86caf690-618d-45a0-bd24-175c8c638fb1|2025-04-12|1200", court=2, start_time=1200),
        Slot(slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|840", court=3, start_time=840),
        Slot(slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|1080", court=3, start_time=1080),
        Slot(slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|1140", court=3, start_time=1140),
        Slot(slot_key="booking-e63a21b7-62e5-488d-9cdf-f4c98b6c04cc|2025-04-12|1200", court=3, start_time=1200),
        Slot(slot_key="booking-bb1f7125-f5fd-4b81-af62-51e03bfe51c1|2025-04-12|1080", court=4, start_time=1080),
        Slot(slot_key="booking-bb1f7125-f5fd-4b81-af62-51e03bfe51c1|2025-04-12|1140", court=4, start_time=1140),
        Slot(slot_key="booking-bb1f7125-f5fd-4b81-af62-51e03bfe51c1|2025-04-12|1200", court=4, start_time=1200)
    ]

    assert slots == expected_slots


# Tests for pick_slot function
@pytest.fixture
def sample_slots():
    """Fixture providing sample slot data"""
    return [
        Slot(slot_key="1_1700", court=1, start_time=1020),  # 17:00 on court 1
        Slot(slot_key="1_0800", court=1, start_time=480),  # 8:00 on court 1
        Slot(slot_key="2_1600", court=2, start_time=960),  # 16:00 on court 2
        Slot(slot_key="3_0800", court=3, start_time=480),   # 8:00 on court 3
        Slot(slot_key="3_1600", court=3, start_time=960),   # 16:00 on court 3
        Slot(slot_key="4_0800", court=4, start_time=480),   # 8:00 on court 4
    ]


def test_pick_slot_earliest_no_preferences(sample_slots):
    """Test picking earliest slot without preferences"""
    slot_key, slot_time = pick_slot(sample_slots)
    assert slot_key == "1_0800"  # First 8:00 slot
    assert slot_time == 480


@pytest.mark.parametrize("target_time,expected_key", [
    (480, "1_0800",),    # 8:00 - should get first available
    (960, "2_1600"),    # 16:00
    (1020, "1_1700"),  # 17:00
])
def test_pick_slot_specific_time(sample_slots, target_time, expected_key):
    """Test picking slots at specific times"""
    slot_key, slot_time = pick_slot(sample_slots, target_time=target_time)
    assert slot_key == expected_key
    assert slot_time == target_time


def test_pick_slot_preferred_courts(sample_slots):
    """Test picking slots with court preferences"""
    slot_key, slot_time = pick_slot(sample_slots, preferred_courts=[4])
    assert slot_key == "4_0800"  # Should get 8:00 on court 4
    assert slot_time == 480


@pytest.mark.parametrize("target_time,courts,expected_key", [
    (480, [3], "3_0800"),     # 8:00 on court 3
    (480, [4], "4_0800"),     # 8:00 on court 4
    (960, [3], "3_1600"),     # 16:00 on court 3
])
def test_pick_slot_time_and_courts(sample_slots, target_time, courts, expected_key):
    """Test picking slots with both time and court preferences"""
    slot_key, slot_time = pick_slot(sample_slots, target_time=target_time, preferred_courts=courts)
    assert slot_key == expected_key
    assert slot_time == target_time


def test_pick_slot_nonexistent_time(sample_slots):
    """Test picking slot at non-existent time"""
    slot_key, slot_time = pick_slot(sample_slots, target_time=1440)  # 24:00
    assert slot_key is None
    assert slot_time is None


def test_pick_slot_invalid_courts(sample_slots):
    """Test picking slot with non-existent courts"""
    # Should fall back to earliest available on any court
    slot_key, slot_time = pick_slot(sample_slots, preferred_courts=[10, 11])
    assert slot_key == "key1"
    assert slot_time == 480


def test_pick_slot_empty_list():
    """Test picking slot from empty list"""
    slot_key, slot_time = pick_slot([])
    assert slot_key is None
    assert slot_time is None
