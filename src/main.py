import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.client_manager import TwikitClientManager
from core.config_loader import ConfigLoader
from core.tweepy_client_manager import TweepyClientManager
from features.engagement import EngagementManager
from features.publisher import TwitterPublisher
from utils.logger import setup_logger

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"


def _read_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def _load_environment():
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)


def _is_network_access_error(error: Exception) -> bool:
    text = str(error).lower()
    tokens = [
        "all connection attempts failed",
        "failed to establish a new connection",
        "winerror 10013",
        "connection refused",
        "temporary failure in name resolution",
        "name or service not known",
        "nodename nor servname provided",
    ]
    return any(token in text for token in tokens)


def run():
    # 1. Setup
    _load_environment()
    setup_logger()
    logger.info("Twitter Automation AI starting...")

    config_loader = ConfigLoader()

    # 2. Determine mode and initialize client(s)
    command = "publisher"
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

    if command == "engage":
        logger.info("Starting Engagement Mode...")

        async def run_engagement():
            twikit_client = None
            disable_twikit = _read_bool_env("ENGAGEMENT_DISABLE_TWIKIT", False)

            if disable_twikit:
                logger.info("Twikit disabled by ENGAGEMENT_DISABLE_TWIKIT.")
            else:
                try:
                    twikit_manager = TwikitClientManager()
                    await twikit_manager.initialize_client()
                    twikit_client = twikit_manager.get_client()
                    logger.info("Twikit client ready.")
                except Exception as e:
                    if _is_network_access_error(e):
                        logger.warning(
                            "Twikit unavailable due to network access failure. "
                            "Check outbound HTTPS access to x.com: %s",
                            e,
                        )
                    else:
                        logger.warning("Twikit unavailable; continuing without it: %s", e)

            tweepy_client = None
            try:
                tweepy_manager = TweepyClientManager()
                tweepy_manager.initialize_client()
                tweepy_client = tweepy_manager.get_client()
                logger.info("Official API client ready.")
            except Exception as e:
                logger.warning("Official API client unavailable: %s", e)

            if not twikit_client and not tweepy_client:
                raise RuntimeError(
                    "No engagement client available. Configure official API credentials "
                    "or provide valid Twikit cookies/credentials."
                )

            engagement = EngagementManager(twikit_client, config_loader, tweepy_client)
            await engagement.run()

        asyncio.run(run_engagement())

    elif command == "post":
        client_manager = TweepyClientManager()
        try:
            client_manager.initialize_client()
            client = client_manager.get_client()
            api = client_manager.get_api()
        except Exception as e:
            logger.critical("Core initialization failed: %s", e)
            return

        publisher = TwitterPublisher(client, api, config_loader)

        if len(sys.argv) < 3:
            logger.error('Missing tweet text. Usage: python src/main.py post "Your tweet"')
            return
        tweet_text = sys.argv[2]
        image_path = sys.argv[3] if len(sys.argv) > 3 else None
        publisher.post_single(tweet_text, image_path)

    elif command == "publisher":
        client_manager = TweepyClientManager()
        try:
            client_manager.initialize_client()
            client = client_manager.get_client()
            api = client_manager.get_api()
        except Exception as e:
            logger.critical("Core initialization failed: %s", e)
            return

        publisher = TwitterPublisher(client, api, config_loader)
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
