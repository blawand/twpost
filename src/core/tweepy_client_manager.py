
import logging
import os
import tweepy
from typing import Optional

logger = logging.getLogger(__name__)

class TweepyClientManager:
    """Manages Tweepy client authentication using official X API keys."""
    
    def __init__(self):
        self.client: Optional[tweepy.Client] = None
        self.api: Optional[tweepy.API] = None  # For media uploads (v1.1)

    def initialize_client(self) -> tweepy.Client:
        """Initialize and authenticate the Tweepy client."""
        
        # Load credentials from environment
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        bearer_token = os.getenv("X_BEARER_TOKEN")
        
        if not all([api_key, api_secret, access_token, access_token_secret]):
            raise ValueError(
                "Missing X API credentials! Please set X_API_KEY, X_API_SECRET, "
                "X_ACCESS_TOKEN, and X_ACCESS_TOKEN_SECRET in your .env file."
            )
        
        # Create the v2 Client for tweeting
        self.client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=False
        )
        
        # Create v1.1 API for media uploads (not available in v2)
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_token_secret
        )
        self.api = tweepy.API(auth)
        
        logger.info("✅ Tweepy client initialized with official X API credentials.")
        return self.client

    def get_client(self) -> tweepy.Client:
        if not self.client:
            raise RuntimeError("Client not initialized! Call initialize_client() first.")
        return self.client
    
    def get_api(self) -> tweepy.API:
        """Get the v1.1 API for media uploads."""
        if not self.api:
            raise RuntimeError("API not initialized! Call initialize_client() first.")
        return self.api
