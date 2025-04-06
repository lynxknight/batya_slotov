import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_env():
    """Load credentials and bot token from files and set them as environment variables"""
    try:
        # Get the directory of the current script
        current_dir = Path(__file__).parent.parent

        # Read username
        username_file = current_dir / ".sensitive" / ".username"
        if not username_file.exists():
            raise FileNotFoundError(f"Username file not found at {username_file}")
        with open(username_file, "r") as f:
            username = f.readline().strip()
            if not username:
                raise ValueError("Username file is empty")
            os.environ["TENNIS_USERNAME"] = username

        # Read password
        password_file = current_dir / ".sensitive" / ".password"
        if not password_file.exists():
            raise FileNotFoundError(f"Password file not found at {password_file}")
        with open(password_file, "r") as f:
            password = f.readline().strip()
            if not password:
                raise ValueError("Password file is empty")
            os.environ["TENNIS_PASSWORD"] = password

        # Read Telegram bot token
        token_file = current_dir / ".sensitive" / ".telegram_bot_token"
        if not token_file.exists():
            raise FileNotFoundError(
                f"Telegram bot token file not found at {token_file}"
            )
        with open(token_file, "r") as f:
            token = f.readline().strip()
            if not token:
                raise ValueError("Telegram bot token file is empty")
            os.environ["TENNIS_BOT_TOKEN"] = token

        logger.info("Successfully loaded credentials and bot token from files")

    except Exception as e:
        logger.error(f"Failed to load credentials or bot token: {e}")
        raise
