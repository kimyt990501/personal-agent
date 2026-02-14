from src.bot.client import run_bot
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    logger.info("Starting Personal Agent Bot...")
    run_bot()


if __name__ == "__main__":
    main()
