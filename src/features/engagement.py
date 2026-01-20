import os
import json
import logging
import asyncio
import random
from pathlib import Path
from typing import Optional
from twikit import Client
import tweepy
from core.llm_helper import LLMHelper

logger = logging.getLogger(__name__)

class EngagementManager:
    """Manages searching for tweets and replying using AI."""
    
    def __init__(self, client: Client, config_loader, tweepy_client: Optional[tweepy.Client] = None):
        self.client = client  # Twikit client for searching
        self.tweepy_client = tweepy_client  # Official API for posting (bypasses 226)
        self.config = config_loader.get_settings()
        self.llm = LLMHelper(self.config)
        
        project_root = Path(__file__).resolve().parent.parent.parent
        self.tracker_file = project_root / 'data' / 'engagement_tracker.json'
        self.replied_ids = self._load_tracker()
        
        self.keywords = [
            "trading journal",
            "trade journal",
            "journaling trades",
            "trading discipline",
            "revenge trading",
            "trading psychology",
            "risk management trading",
            "blown account",
            "trading plan",
            "why i lost trading"
        ]
        
        # 🔧 MORE CONSERVATIVE LIMITS
        self.max_replies = 1  # Reduced from 3
        self.my_username = "lynxtradesapp"

    def _load_tracker(self) -> set:
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading engagement tracker: {e}")
        return set()

    def _save_tracker(self):
        try:
            os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
            with open(self.tracker_file, 'w') as f:
                json.dump(list(self.replied_ids), f)
        except Exception as e:
            logger.error(f"Error saving engagement tracker: {e}")

    async def run(self):
        logger.info("🔎 Starting Engagement Run...")
        
        replies_count = 0
        
        try:
            query = random.choice(self.keywords)
            logger.info(f"Searching for: '{query}'")
            
            tweets = await self.client.search_tweet(query, product='Latest', count=10)
            
            if not tweets:
                logger.info("No tweets found.")
                return

            for tweet in tweets:
                if replies_count >= self.max_replies:
                    break
                
                if tweet.user.screen_name.lower() == self.my_username.lower():
                    continue
                
                if str(tweet.id) in self.replied_ids:
                    continue
                
                text = tweet.text
                handle = tweet.user.screen_name
                
                logger.info(f"Found tweet by @{handle}: {text[:50]}...")
                
                reply_text = await self.llm.generate_reply(text, handle)
                
                if not reply_text:
                    continue
                    
                logger.info(f"🤖 Generated Reply: {reply_text}")
                
                try:
                    # Use Official Twitter API (Tweepy) if available - bypasses Error 226
                    success = False
                    
                    # 1. Try Official API (Tweepy) first
                    if self.tweepy_client:
                        try:
                            self.tweepy_client.create_tweet(
                                text=reply_text,
                                in_reply_to_tweet_id=str(tweet.id)
                            )
                            logger.info(f"✅ Replied to @{handle} (via Official API)")
                            success = True
                        except Exception as e:
                            logger.warning(f"⚠️ Official API failed (Rate Limit?): {e}")
                            logger.info("🔄 Falling back to Twikit...")

                    # 2. Fallback to Twikit if Official API failed or wasn't available
                    if not success:
                        await self.client.create_tweet(
                            text=reply_text,
                            reply_to=tweet.id
                        )
                        logger.info(f"✅ Replied to @{handle} (via Twikit)")
                    
                    self.replied_ids.add(str(tweet.id))
                    self._save_tracker()
                    replies_count += 1
                    
                except Exception as e:
                    error_str = str(e)
                    if "226" in error_str:
                        logger.error(f"❌ BLOCKED: Account flagged as automated. Stopping.")
                        logger.error("💡 Try: 1) Use account manually for a day 2) Re-login 3) Wait 24h")
                        return  # Stop completely, don't retry
                    else:
                        logger.error(f"❌ Failed to reply: {e}")
                
                # Exit after successful reply - GitHub Actions schedule handles the timing
                logger.info("✅ One reply sent - exiting to save GitHub Actions minutes.")

        except Exception as e:
            logger.error(f"❌ Engagement loop failed: {e}")
            
        logger.info(f"🏁 Engagement finished. Replied to {replies_count} tweets.")