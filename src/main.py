import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from core.twikit_client import TwikitClientManager
from core.twitter_client import GraphQLClientManager
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
    _load_environment()
    setup_logger()
    logger.info("Twitter Automation starting...")

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
                        logger.warning("Twikit unavailable (network): %s", e)
                    else:
                        logger.warning("Twikit unavailable: %s", e)

            graphql_client = None
            try:
                graphql_manager = GraphQLClientManager()
                graphql_manager.initialize_client()
                graphql_client = graphql_manager.get_client()
                logger.info("GraphQL client ready.")
            except Exception as e:
                logger.warning("GraphQL client unavailable: %s", e)

            if not twikit_client and not graphql_client:
                raise RuntimeError(
                    "No engagement client available. Configure TWITTER_COOKIES "
                    "or Twikit cookies/credentials."
                )

            engagement = EngagementManager(twikit_client, graphql_client)
            await engagement.run()

        asyncio.run(run_engagement())

    elif command == "post":
        client_manager = GraphQLClientManager()
        try:
            client_manager.initialize_client()
            graphql_client = client_manager.get_client()
        except Exception as e:
            logger.critical("Core initialization failed: %s", e)
            return

        publisher = TwitterPublisher(graphql_client)

        if len(sys.argv) < 3:
            logger.error('Missing tweet text. Usage: python src/main.py post "Your tweet"')
            return
        tweet_text = sys.argv[2]
        image_path = sys.argv[3] if len(sys.argv) > 3 else None
        publisher.post_single(tweet_text, image_path)

    elif command == "publisher":
        client_manager = GraphQLClientManager()
        try:
            client_manager.initialize_client()
            graphql_client = client_manager.get_client()
        except Exception as e:
            logger.critical("Core initialization failed: %s", e)
            return

        publisher = TwitterPublisher(graphql_client)
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
