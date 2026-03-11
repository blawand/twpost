
import json
import logging
import os

from twitter_cli.client import TwitterClient

logger = logging.getLogger(__name__)


class GraphQLClientManager:
    """Manages a twitter-cli GraphQL client using cookie-based auth."""

    def __init__(self):
        self.client = None

    def initialize_client(self) -> TwitterClient:
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

        self.client = TwitterClient(
            auth_token=auth_token,
            ct0=ct0,
            cookie_string=cookie_string,
        )
        logger.info("GraphQL client initialized with cookie-based auth.")
        return self.client

    def get_client(self) -> TwitterClient:
        if not self.client:
            raise RuntimeError("Client not initialized! Call initialize_client() first.")
        return self.client
