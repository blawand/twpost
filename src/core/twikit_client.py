
import logging
import os
from pathlib import Path
from typing import Optional

from twikit import Client

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class TwikitClientManager:
    """Manages Twikit client authentication and session."""
    
    def __init__(self, cookies_path: str = "data/cookies.json"):
        raw_cookies_path = Path(cookies_path)
        if raw_cookies_path.is_absolute():
            self.cookies_path = raw_cookies_path
        else:
            self.cookies_path = PROJECT_ROOT / raw_cookies_path
        self.client: Optional[Client] = None

    @staticmethod
    def _is_connectivity_error(error: Exception) -> bool:
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
                logger.info("Injected cookies from environment variable.")
            except Exception as e:
                logger.error("Failed to inject cookies from env: %s", e)

        # 1. Try loading cookies
        if self.cookies_path.exists():
            try:
                self.client.load_cookies(str(self.cookies_path))
                # Validate cookies by making a request
                # This request might also generate a guest_id if we don't have one!
                await self.client.get_user_by_screen_name("X")
                logger.info("Loaded and confirmed cookies from %s", self.cookies_path)
                
                # NOW inject the header (since we might have just got the guest_id)
                # self._inject_xpff_header() # DISABLED: Potentially causing shadowbans
                return self.client
            except Exception as e:
                if self._is_connectivity_error(e):
                    raise RuntimeError(
                        "Twikit could not reach x.com while validating cookies. "
                        "Check local firewall, proxy, VPN, or outbound HTTPS access."
                    ) from e
                logger.warning("Failed to load/validate cookies: %s", e)
        
        # 2. Fallback to login if credentials exist in env
        username = (os.getenv("TWITTER_USERNAME") or "").strip()
        email = (os.getenv("TWITTER_EMAIL") or "").strip()
        password = (os.getenv("TWITTER_PASSWORD") or "").strip()
        
        if username and password:
            logger.info("Logging in with credentials...")
            try:
                await self.client.login(
                    auth_info_1=username,
                    auth_info_2=email,
                    password=password,
                    enable_ui_metrics=True  # Helps bypass 226 error detection
                )
                self.client.save_cookies(str(self.cookies_path))
                logger.info("Login successful, cookies saved.")
                # self._inject_xpff_header() # DISABLED: Potentially causing shadowbans
                return self.client
            except Exception as e:
                if self._is_connectivity_error(e):
                    raise RuntimeError(
                        "Twikit login failed because outbound HTTPS access to x.com is blocked "
                        "or unavailable."
                    ) from e
                logger.error("Login failed: %s", e)
                raise RuntimeError(f"Twikit login failed: {e}") from e
        else:
            raise ValueError("No cookies found and no credentials provided!")

    def get_client(self) -> Client:
        if not self.client:
            raise RuntimeError("Client not initialized! Call initialize_client() first.")
        return self.client


