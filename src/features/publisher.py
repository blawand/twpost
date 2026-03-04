
import json
import logging
import os
import random
import time
from pathlib import Path
from datetime import datetime, timezone
import tweepy

logger = logging.getLogger(__name__)

class TwitterPublisher:
    """Manages publishing tweets using the official Tweepy library."""
    
    def __init__(self, client: tweepy.Client, api: tweepy.API = None, config_loader=None):
        self.client = client
        self.api = api  # For media uploads (v1.1)
        self.posts_file = Path("data/posts.json")
        self.tracker_file = Path("data/posted_tracker.json")
        self.config_loader = config_loader
        self.post_max_attempts = max(1, self._read_int_env("PUBLISH_POST_MAX_ATTEMPTS", 4))
        self.retry_base_seconds = max(0.5, self._read_float_env("PUBLISH_RETRY_BASE_SECONDS", 1.5))
        self.retry_max_seconds = max(1.0, self._read_float_env("PUBLISH_RETRY_MAX_SECONDS", 20.0))

    @staticmethod
    def _read_int_env(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning("Invalid %s='%s'. Using default=%s.", name, value, default)
            return default

    @staticmethod
    def _read_float_env(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning("Invalid %s='%s'. Using default=%s.", name, value, default)
            return default

    @staticmethod
    def _is_retryable_post_error(error: Exception) -> bool:
        status_code = getattr(error, "api_codes", None)
        if status_code and any(code in {130, 131} for code in status_code):
            return True

        response = getattr(error, "response", None)
        if response is not None:
            code = getattr(response, "status_code", None)
            if code in {429, 500, 502, 503, 504}:
                return True

        text = str(error).lower()
        retry_tokens = [
            "503",
            "service unavailable",
            "timed out",
            "timeout",
            "connection reset",
            "temporarily unavailable",
            "too many requests",
        ]
        return any(token in text for token in retry_tokens)

    def _create_tweet_with_retry(self, text: str, media_ids=None):
        media_ids = media_ids if media_ids else None
        last_error = None

        for attempt in range(1, self.post_max_attempts + 1):
            try:
                return self.client.create_tweet(text=text, media_ids=media_ids)
            except Exception as e:
                last_error = e
                if not self._is_retryable_post_error(e) or attempt >= self.post_max_attempts:
                    raise

                delay = min(self.retry_max_seconds, self.retry_base_seconds * (2 ** (attempt - 1)))
                delay *= random.uniform(0.85, 1.25)
                logger.warning(
                    "Tweet post attempt %s/%s failed with retryable error: %s. Retrying in %.1fs.",
                    attempt,
                    self.post_max_attempts,
                    e,
                    delay,
                )
                time.sleep(delay)

        if last_error:
            raise last_error

    def load_posts(self):
        if not self.posts_file.exists():
            logger.error(f"❌ Posts file not found: {self.posts_file}")
            return None
        with open(self.posts_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_tracker(self):
        if self.tracker_file.exists():
            with open(self.tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"posted_ids": [], "last_posted_at": None, "total_posted": 0}

    def save_tracker(self, tracker):
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(tracker, f, indent=2)

    def save_posts(self, data):
        with open(self.posts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def run(self):
        """Execute the publishing workflow (synchronous for Tweepy)."""
        logger.info("🚀 Starting Publisher Workflow...")
        
        posts_data = self.load_posts()
        if not posts_data:
            return
        
        tracker = self.load_tracker()
        posted_ids = set(tracker.get("posted_ids", []))
        
        # Find next unposted
        post = None
        for p in posts_data["posts"]:
            if p["id"] not in posted_ids and not p.get("posted", False):
                post = p
                break
        
        if not post:
            logger.info("✅ All posts have been published!")
            return

        logger.info(f"📝 Preparing post #{post['id']} ({post['type']})")
        
        media_ids = []
        if post.get("image") and self.api:
            # Handle image path relative to root
            image_path = Path(post["image"])
            if image_path.exists():
                try:
                    # Use v1.1 API for media upload
                    media = self.api.media_upload(filename=str(image_path))
                    media_ids.append(media.media_id)
                    logger.info(f"✅ Uploaded image: {image_path}")
                except Exception as e:
                    logger.error(f"⚠️ Failed to upload image: {e}")
            else:
                 logger.warning(f"⚠️ Image not found: {image_path}")

        try:
            response = self._create_tweet_with_retry(
                text=post["content"],
                media_ids=media_ids,
            )
            
            tweet_id = response.data['id']
            logger.info(f"✅ Posted tweet #{post['id']} (Tweet ID: {tweet_id})")
            
            # Update state
            tracker["posted_ids"].append(post["id"])
            tracker["last_posted_at"] = datetime.now(timezone.utc).isoformat()
            tracker["total_posted"] = len(tracker["posted_ids"])
            self.save_tracker(tracker)
            
            # Update posts.json source
            for p in posts_data["posts"]:
                if p["id"] == post["id"]:
                    p["posted"] = True
                    p["posted_at"] = datetime.now(timezone.utc).isoformat()
                    p["tweet_id"] = str(tweet_id)
                    break
            self.save_posts(posts_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to post tweet after retries: {e}")
            raise

    def post_single(self, text: str, image_path: str = None):
        """Post a single tweet directly (synchronous)."""
        logger.info(f"📝 Preparing to post: {text[:50]}...")
        
        media_ids = []
        if image_path and self.api:
            img = Path(image_path)
            if img.exists():
                try:
                    media = self.api.media_upload(filename=str(img))
                    media_ids.append(media.media_id)
                    logger.info(f"✅ Uploaded image: {image_path}")
                except Exception as e:
                    logger.error(f"⚠️ Failed to upload image: {e}")
            else:
                 logger.warning(f"⚠️ Image not found: {image_path}")

        try:
            response = self._create_tweet_with_retry(
                text=text,
                media_ids=media_ids,
            )
            tweet_id = response.data['id']
            logger.info(f"✅ Successfully posted tweet: {tweet_id}")
            return response
        except Exception as e:
            logger.error(f"❌ Failed to post tweet after retries: {e}")
            raise e
