import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import AsyncMock, MagicMock, patch
import slots
from telegram_booking_task import run_booking_task


@pytest.fixture
def mock_notifier():
    notifier = AsyncMock()
    notifier.broadcast_message = AsyncMock()
    notifier.send_message = AsyncMock()
    return notifier


@pytest.fixture
def mock_preferences_file(tmp_path):
    preferences = {
        "preferences": [{"weekdays": ["tuesday"], "time": "16:00", "courts": [3, 4]}]
    }
    prefs_file = tmp_path / "booking_preferences.json"
    prefs_file.write_text(json.dumps(preferences))
    return prefs_file


@pytest.fixture
def mock_credentials(monkeypatch):
    monkeypatch.setenv("TENNIS_USERNAME", "test_user")
    monkeypatch.setenv("TENNIS_PASSWORD", "test_pass")


@pytest.mark.asyncio
async def test_run_booking_task_success(
    mock_notifier, mock_preferences_file, mock_credentials, monkeypatch
):
    # Mock the current date to be a Tuesday
    mock_date = datetime(2024, 1, 2)  # This is a Tuesday
    with patch("telegram_booking_task.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_date

        # Mock successful booking result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.slot = slots.Slot("test_key", 3, 960, mock_date)  # 16:00

        # Mock the agent's fetch_and_book_session
        with patch(
            "telegram_booking_task.agent.fetch_and_book_session", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_result

            # Run the booking task
            await run_booking_task(mock_notifier)

            # Verify the success message was sent
            mock_notifier.broadcast_message.assert_any_call(
                "✅ Successfully booked court for 2024-01-09 at 16:00"
            )


@pytest.mark.asyncio
async def test_run_booking_task_failure(
    mock_notifier, mock_preferences_file, mock_credentials, monkeypatch
):
    # Mock the current date to be a Tuesday
    mock_date = datetime(2024, 1, 2)  # This is a Tuesday
    with patch("telegram_booking_task.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_date

        # Mock failed booking result
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "Found no slot at 2024-01-09 for preferred time 16:00"
        mock_result.error = None

        # Mock the agent's fetch_and_book_session
        with patch(
            "telegram_booking_task.agent.fetch_and_book_session", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_result

            # Run the booking task
            await run_booking_task(mock_notifier)

            # Verify the error message was sent
            mock_notifier.broadcast_message.assert_any_call(
                "❌ Failed to book court for 2024-01-09 at 16:00: Found no slot at 2024-01-09 for preferred time 16:00"
            )
            # Verify the retry message was sent
            mock_notifier.broadcast_message.assert_any_call(
                "You can retry via /retry command"
            )


@pytest.mark.asyncio
async def test_run_booking_task_no_preferences(
    mock_notifier, tmp_path, mock_credentials, monkeypatch
):
    # Create empty preferences file
    preferences = {"preferences": []}

    # Mock json.load to return our preferences
    with patch("telegram_booking_task.json.load", return_value=preferences):
        # Mock the current date to be a Tuesday
        mock_date = datetime(2024, 1, 2)  # This is a Tuesday
        with patch("telegram_booking_task.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_date

            # Run the booking task with a user_id
            await run_booking_task(mock_notifier, user_id=123)

            # Verify the no preferences message was sent via send_message
            mock_notifier.send_message.assert_called_with(
                "No booking preferences found for tuesday. Skipping booking for 2024-01-09",
                123,
            )

            # Verify that broadcast_message was not called
            mock_notifier.broadcast_message.assert_not_called()


@pytest.mark.asyncio
async def test_run_booking_task_exception(
    mock_notifier, mock_preferences_file, mock_credentials, monkeypatch
):
    # Mock the current date to be a Tuesday
    mock_date = datetime(2024, 1, 2)  # This is a Tuesday
    with patch("telegram_booking_task.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_date

        # Mock the agent's fetch_and_book_session to raise an exception
        with patch(
            "telegram_booking_task.agent.fetch_and_book_session", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")

            # Run the booking task
            await run_booking_task(mock_notifier)

            # Verify the error message was sent
            mock_notifier.broadcast_message.assert_any_call(
                "❌ Failed to book court for 2024-01-09 at 16:00: Network error"
            )
            # Verify the retry message was sent
            mock_notifier.broadcast_message.assert_any_call(
                "You can retry via /retry command"
            )
