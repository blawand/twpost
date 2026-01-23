
import logging
import os
import json
import asyncio
from pathlib import Path
from twikit import Client
from typing import Optional

logger = logging.getLogger(__name__)

class TwikitClientManager:
    """Manages Twikit client authentication and session."""
    
    def __init__(self, cookies_path: str = "data/cookies.json"):
        self.cookies_path = Path(cookies_path)
        self.client: Optional[Client] = None
        self.user_data = None
        self.user_agent = os.getenv("TWITTER_USER_AGENT", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")

    async def initialize_client(self) -> Client:
        """Initialize and authenticate the client."""
        # Load enhanced configuration for anti-bot avoidance
        user_agent = os.getenv("TWITTER_USER_AGENT")  # Optional: match browser
        
        self.client = Client(
            language='en-US',
            user_agent=user_agent
        )
        
        # 0. Inject cookies from ENV if present (for GitHub Actions)
        env_cookies = os.getenv("TWITTER_COOKIES")
        if env_cookies:
            try:
                # Ensure the data directory exists
                self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cookies_path, "w") as f:
                    f.write(env_cookies)
                logger.info("🍪 Injected cookies from environment variable.")
            except Exception as e:
                logger.error(f"❌ Failed to inject cookies from env: {e}")

        # 1. Try loading cookies
        if self.cookies_path.exists():
            try:
                self.client.load_cookies(str(self.cookies_path))
                # Validate cookies by making a request
                # This request might also generate a guest_id if we don't have one!
                await self.client.get_user_by_screen_name("X")
                logger.info(f"🍪 Loaded and confirmed cookies from {self.cookies_path}")
                
                # NOW inject the header (since we might have just got the guest_id)
                # self._inject_xpff_header() # DISABLED: Potentially causing shadowbans
                return self.client
            except Exception as e:
                logger.warning(f"⚠️ Failed to load/validate cookies: {e}")
        
        # 2. Fallback to login if credentials exist in env
        username = os.getenv("TWITTER_USERNAME")
        email = os.getenv("TWITTER_EMAIL")
        password = os.getenv("TWITTER_PASSWORD")
        
        if username and password:
            logger.info("🔐 Logging in with credentials...")
            try:
                await self.client.login(
                    auth_info_1=username,
                    auth_info_2=email,
                    password=password,
                    enable_ui_metrics=True  # Helps bypass 226 error detection
                )
                self.client.save_cookies(str(self.cookies_path))
                logger.info("✅ Login successful, cookies saved.")
                # self._inject_xpff_header() # DISABLED: Potentially causing shadowbans
                return self.client
            except Exception as e:
                logger.error(f"❌ Login failed: {e}")
                raise
        else:
            raise ValueError("No cookies found and no credentials provided!")

    def get_client(self) -> Client:
        if not self.client:
            raise RuntimeError("Client not initialized! Call initialize_client() first.")
        return self.client


