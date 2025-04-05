import dataclasses
from bs4 import BeautifulSoup

def parse_time(minutes):
    """Convert minutes since midnight to HH:MM format"""
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02d}:{minutes:02d}"

@dataclasses.dataclass
class Slot:
    slot_key: str # uses data-test-id internally
    court: int
    start_time: int

    def __str__(self):
        return f"Slot<slot_key={self.slot_key}, court={self.court}, start_time={parse_time(self.start_time)}>"

    def __repr__(self):
        return self.__str__()

def parse_slots(html_content) -> list[Slot]:
    soup = BeautifulSoup(html_content, 'html.parser')
    available_slots = []
    for resource in soup.find_all('div', class_='resource'):
        for session in resource.find_all('div', class_='resource-interval'):
            # Skip if session is unavailable
            if not session.find('span', class_='available-booking-slot'):
                continue
                
            # Get court number from the visuallyhidden span
            court_span = session.find('span', class_='visuallyhidden')
            if not court_span:
                continue
            court_num = int(court_span.text.strip().split()[-1])
            
            start_time = int(session.get('data-system-start-time'))
            slot_key = session.find('a', class_='book-interval').get('data-test-id')
            available_slots.append(Slot(slot_key, court_num, start_time))
    return available_slots

def pick_slot(available_slots: list[Slot], target_time, preferred_courts: list[int] | None = None) -> Slot | None:
    if not preferred_courts:
        preferred_courts = []

    target_slots = [s for s in available_slots if s.start_time == target_time]
    if preferred_courts:
        preferred_slot = next((s for s in target_slots if s.court in preferred_courts), None)
        if preferred_slot:
            return preferred_slot
            
    # Fallback to random available slot at target time
    if target_slots:
        return target_slots[0]

    return None

def find_slot(html_content, target_time=None, preferred_courts=None) -> Slot | None:
    """
    Find available slot based on preferences
    target_time: Target time in minutes since midnight (e.g. 960 for 16:00)
    preferred_courts: List of preferred court numbers in order of preference
    Returns:
        slot_key: Slot key of the available slot
        slot_time: Time of the available slot in minutes since midnight
    
        None, None if no slot is available
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    available_slots = parse_slots(soup)
    return pick_slot(available_slots, target_time, preferred_courts)
