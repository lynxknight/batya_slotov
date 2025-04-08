# Tennis Court Booking

A comprehensive system for automating tennis court bookings with Telegram notifications and scheduling capabilities.

## Features

- Automated tennis court booking
- Telegram bot integration for notifications and commands
- Scheduled booking attempts
- Customizable booking preferences
- Browser automation using Playwright
- Support for multiple users and notifications


## Usage


## What to configure

1. Create a `booking_preferences.json` file with your booking preferences
2. Fill in .sensitive/.password|.username|.telegram_bot_token 

## Project Structure

- `main.py`: CLI interface (mostly for manual testing)
- `scheduler.py`: Core entrypoint. Launches bot and cron that fetches slots at night
- `telegram_bot.py`: Telegram bot implementation and user interaction
- `agent.py`: Browser automation and booking logic
- `slots.py`: Slot management and preferences
- `env.py`: Environment configuration

## Notes

- Works via username/password 
- The Telegram bot requires a valid bot token
- Automated bookings run daily at 00:10
- Multiple users can subscribe to notifications, but credentials are shared per instance

## How to run

See `rebuild_and_run.sh`


## TODO

1) Cancel booking via bot 
2) Multiple accounts in one bot
3) Edit preferences via bot or something like this 
4) store data in persistent storage

Extra:
1) Natural language-based commands