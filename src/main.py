import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.premium_client import PremiumTwitterClient
from features.engagement import EngagementManager
from features.publisher import TwitterPublisher
from utils.logger import setup_logger

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"


def run():
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    setup_logger()
    logger.info("Twitter Automation starting...")

    command = "publisher"
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

    # All commands use the same client
    try:
        client = PremiumTwitterClient.from_env()
    except Exception as e:
        logger.critical("Client initialization failed: %s", e)
        return

    if command == "engage":
        logger.info("Starting Engagement Mode...")

        async def run_engagement():
            engagement = EngagementManager(client)
            await engagement.run()

        asyncio.run(run_engagement())

    elif command == "post":
        publisher = TwitterPublisher(client)

        if len(sys.argv) < 3:
            logger.error('Missing tweet text. Usage: python src/main.py post "Your tweet"')
            return
        tweet_text = sys.argv[2]
        image_path = sys.argv[3] if len(sys.argv) > 3 else None
        if image_path is None:
            publisher.post_single(tweet_text)
        else:
            publisher.post_single(tweet_text, image_path)

    elif command == "publisher":
        publisher = TwitterPublisher(client)
        logger.info("Running Publisher Mode...")
        publisher.run()

    else:
        logger.error("Unknown command: %s", command)

    logger.info("Workflow complete.")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
        sys.exit(130)
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
