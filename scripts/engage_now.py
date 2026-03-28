import asyncio
import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.premium_client import PremiumTwitterClient  # noqa: E402
from features.engagement import EngagementManager  # noqa: E402
from utils.logger import setup_logger  # noqa: E402

logger = logging.getLogger("EngageNow")


def main():
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    setup_logger()

    if "--dry-run" in sys.argv:
        os.environ["ENGAGEMENT_DRY_RUN"] = "true"

    try:
        client = PremiumTwitterClient.from_env()
        engagement = EngagementManager(client)
        asyncio.run(engagement.run())
    except Exception as e:
        logger.error("Engagement failed: %s", e)


if __name__ == "__main__":
    main()
