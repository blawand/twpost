
import logging
import os
import json
import asyncio
from pathlib import Path
from twikit import Client
from typing import Optional
from core.twitter_xpff import get_xpff_header, CRYPTO_AVAILABLE

logger = logging.getLogger(__name__)

class TwikitClientManager:
    """Manages Twikit client authentication and session."""
    
    def __init__(self, cookies_path: str = "data/cookies.json"):
        self.cookies_path = Path(cookies_path)
        self.client: Optional[Client] = None
        self.user_data = None
        self.user_agent = os.getenv("TWITTER_USER_AGENT", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

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
                self._inject_xpff_header()
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
                self._inject_xpff_header()
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

    def _inject_xpff_header(self):
        """Inject the X-Xp-Forwarded-For header to bypass anti-bot detection."""
        if not CRYPTO_AVAILABLE:
            logger.warning("⚠️ XPFF header injection skipped (pycryptodome not installed)")
            return
        
        try:
            # Extract guest_id from cookies
            guest_id = None
            
            # 1. Try to get guest_id from the active client cookies first (Most reliable)
            if self.client:
                try:
                    cookies = self.client.get_cookies()
                    guest_id = cookies.get('guest_id')
                except Exception:
                    pass
            
            # 2. If not in active session, check file (Fallback)
            if not guest_id and self.cookies_path.exists():
                with open(self.cookies_path, 'r') as f:
                    cookies_data = json.load(f)

                if isinstance(cookies_data, dict):
                    guest_id = cookies_data.get('guest_id')
                elif isinstance(cookies_data, list):
                    for cookie in cookies_data:
                        if isinstance(cookie, dict) and cookie.get('name') == 'guest_id':
                            guest_id = cookie.get('value')
                            break
            
            if not guest_id:
                logger.warning("⚠️ guest_id not found in cookies, XPFF header not injected")
                return
            
            # Generate and inject the XPFF header
            xpff_headers = get_xpff_header(self.user_agent, guest_id)
            if xpff_headers:
                # Inject into the client's http session headers
                if hasattr(self.client, 'http') and hasattr(self.client.http, 'headers'):
                    self.client.http.headers.update(xpff_headers)
                    logger.info("🛡️ XPFF anti-bot header injected")
                else:
                    logger.debug("Client http session not accessible, XPFF header may not apply")
        except Exception as e:
            logger.warning(f"⚠️ Failed to inject XPFF header: {e}")
