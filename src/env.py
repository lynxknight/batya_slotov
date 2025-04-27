import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)03d - [%(levelname)-8s] - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class Variable:
    TENNIS_USERNAME = "TENNIS_USERNAME"
    TENNIS_PASSWORD = "TENNIS_PASSWORD"
    TENNIS_BOT_TOKEN = "TENNIS_BOT_TOKEN"
    TENNIS_CARD = "TENNIS_CARD"

    @staticmethod
    def get_tennis_username():
        return os.environ.get(Variable.TENNIS_USERNAME)

    @staticmethod
    def get_tennis_password():
        return os.environ.get(Variable.TENNIS_PASSWORD)

    @staticmethod
    def get_tennis_bot_token():
        return os.environ.get(Variable.TENNIS_BOT_TOKEN)

    @staticmethod
    def get_tennis_card():
        return os.environ.get(Variable.TENNIS_CARD)


def setup_env():
    target_envs = [
        Variable.TENNIS_USERNAME,
        Variable.TENNIS_PASSWORD,
        Variable.TENNIS_BOT_TOKEN,
        Variable.TENNIS_CARD,
    ]
    """Load credentials and bot token from files and set them as environment variables"""
    if all(os.environ.get(env) for env in target_envs):
        logger.info("All environment variables are set, skipping setup")
        return
    logger.info("Not all environment variables are set, assume loading from files")
    try:
        # Get the directory of the current script
        current_dir = Path(__file__).parent.parent

        def set_variable(variable, filepath, error_message):
            if variable in os.environ:
                logger.info(f"{variable} already set, skipping")
                return
            logger.info(f"Setting {variable} from {filepath}")
            file_path = current_dir / ".sensitive" / filepath
            if not file_path.exists():
                raise FileNotFoundError(f"{error_message} not found at {file_path}")
            with open(file_path, "r") as f:
                value = f.readline().strip()
                if not value:
                    raise ValueError(f"{error_message} file is empty")
                os.environ[variable] = value

        set_variable(Variable.TENNIS_USERNAME, ".username", "Username file")
        set_variable(Variable.TENNIS_PASSWORD, ".password", "Password file")
        set_variable(
            Variable.TENNIS_BOT_TOKEN, ".telegram_bot_token", "Telegram bot token file"
        )
        set_variable(Variable.TENNIS_CARD, ".card", "Card file")

        logger.info("Successfully loaded credentials and bot token from files")

    except Exception as e:
        logger.error(f"Failed to load credentials or bot token: {e}")
        raise
