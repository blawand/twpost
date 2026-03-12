
import json
import logging
import os

from twitter_cli.graphql import FALLBACK_QUERY_IDS
from core.premium_client import PremiumTwitterClient

logger = logging.getLogger(__name__)

# Register CreateNoteTweet query ID so twitter-cli's _graphql_post can resolve it.
# If this goes stale, _graphql_post will auto-refresh from live JS bundles.
FALLBACK_QUERY_IDS.setdefault("CreateNoteTweet", "iCUB42lIfXf9qPKctjE5rQ")


class GraphQLClientManager:
    """Manages a twitter-cli GraphQL client using cookie-based auth."""

    def __init__(self):
        self.client = None

    def initialize_client(self) -> PremiumTwitterClient:
        """Initialize the GraphQL client from environment cookies."""
        
        # Parse auth_token and ct0 from TWITTER_COOKIES JSON or standalone env vars
        auth_token = os.getenv("TWITTER_AUTH_TOKEN", "").strip()
        ct0 = os.getenv("TWITTER_CT0", "").strip()
        cookie_string = None

        # Try extracting from TWITTER_COOKIES JSON if standalone vars are empty
        cookies_json = os.getenv("TWITTER_COOKIES", "").strip().strip("'\"")
        if cookies_json:
            try:
                cookies = json.loads(cookies_json)
                if not auth_token:
                    auth_token = cookies.get("auth_token", "")
                if not ct0:
                    ct0 = cookies.get("ct0", "")
                # Build full cookie string for anti-detection
                cookie_string = "; ".join(
                    f"{k}={v}" for k, v in cookies.items()
                )
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse TWITTER_COOKIES JSON: %s", e)

        if not auth_token or not ct0:
            raise ValueError(
                "Missing auth_token or ct0! Set TWITTER_AUTH_TOKEN + TWITTER_CT0 "
                "in .env, or provide them inside the TWITTER_COOKIES JSON."
            )

        self.client = PremiumTwitterClient(
            auth_token=auth_token,
            ct0=ct0,
            cookie_string=cookie_string,
        )
        logger.info("GraphQL client initialized with cookie-based auth.")
        return self.client

    def get_client(self) -> PremiumTwitterClient:
        if not self.client:
            raise RuntimeError("Client not initialized! Call initialize_client() first.")
        return self.client
