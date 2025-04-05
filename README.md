# Tennis Court Booking Slot Fetcher

This Python script fetches and displays available tennis court booking slots from the LTA ClubSpark booking system using Playwright to handle JavaScript execution.

## Requirements

- Python 3.7+ (required for Playwright compatibility)
- Required packages (install using `pip install -r requirements.txt`):
  - requests
  - beautifulsoup4
  - playwright
  - greenlet

## Installation

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Usage

1. Create a cookies file with your authentication cookies in the format:
   ```
   cookie_name1=cookie_value1
   cookie_name2=cookie_value2
   ```

2. Run the script with:
   ```bash
   python tennis_booking.py YYYY-MM-DD --cookies path/to/cookies.txt
   ```

   For example:
   ```bash
   python tennis_booking.py 2024-04-12 --cookies cookies.txt
   ```

## Output

The script will display available slots for each court in the format:
```
Court: Court 1 (ID: court-id-123)
Available slots:
  07:00 - 08:00 (Session ID: session-id-123, Capacity: 1)
  08:00 - 09:00 (Session ID: session-id-456, Capacity: 2)
```

## Notes

- The script requires valid authentication cookies to access the booking system
- Time slots are displayed in 24-hour format
- Capacity indicates the number of available slots for the given time period
- The script uses Playwright to execute JavaScript and load the full page content 