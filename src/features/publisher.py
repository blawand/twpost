
import json
import logging
import os
import random
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.premium_client import PremiumTwitterClient

logger = logging.getLogger(__name__)

class TwitterPublisher:
    """Manages publishing tweets using twitter-cli GraphQL client."""
    
    def __init__(self, client: PremiumTwitterClient):
        self.client = client
        self.posts_file = Path("data/posts.json")
        self.tracker_file = Path("data/posted_tracker.json")
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
        text = str(error).lower()
        retry_tokens = [
            "503", "service unavailable", "timed out", "timeout",
            "connection reset", "temporarily unavailable",
            "too many requests", "429", "rate_limited",
        ]
        return any(token in text for token in retry_tokens)

    def _upload_media_with_retry(self, image_path: str) -> str:
        """Upload media with retry logic. Returns media_id string."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self.post_max_attempts + 1):
            try:
                media_id = self.client.upload_media(image_path)
                logger.info("Media uploaded successfully: media_id=%s", media_id)
                return media_id
            except Exception as e:
                last_error = e
                if not self._is_retryable_post_error(e) or attempt >= self.post_max_attempts:
                    raise

                delay = min(self.retry_max_seconds, self.retry_base_seconds * (2 ** (attempt - 1)))
                delay *= random.uniform(0.85, 1.25)
                logger.warning(
                    "Media upload attempt %s/%s failed: %s. Retrying in %.1fs.",
                    attempt, self.post_max_attempts, e, delay,
                )
                time.sleep(delay)

        if last_error is not None:
            raise last_error

        raise RuntimeError("Media upload retry loop exited without returning a media ID.")

    def _create_tweet_with_retry(self, text: str, media_ids: Optional[List[str]] = None) -> str:
        """Post a tweet with retry logic. Supports media_ids and long tweets (auto)."""
        last_error: Optional[Exception] = None

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
                    "Tweet post attempt %s/%s failed: %s. Retrying in %.1fs.",
                    attempt, self.post_max_attempts, e, delay,
                )
                time.sleep(delay)

        if last_error is not None:
            raise last_error

        raise RuntimeError("Tweet retry loop exited without returning a tweet ID.")

    def load_posts(self) -> Optional[Dict[str, Any]]:
        if not self.posts_file.exists():
            logger.error("Posts file not found: %s", self.posts_file)
            return None
        with open(self.posts_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_tracker(self) -> Dict[str, Any]:
        if self.tracker_file.exists():
            with open(self.tracker_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"posted_ids": [], "last_posted_at": None, "total_posted": 0}

    def save_tracker(self, tracker: Dict[str, Any]) -> None:
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(tracker, f, indent=2)

    def save_posts(self, data: Dict[str, Any]) -> None:
        with open(self.posts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def run(self) -> None:
        """Post the next unposted tweet from posts.json."""
        logger.info("Starting Publisher Workflow...")
        
        posts_data = self.load_posts()
        if not posts_data:
            return
        
        tracker = self.load_tracker()
        posted_ids = set(tracker.get("posted_ids", []))
        
        post = None
        for p in posts_data["posts"]:
            if p["id"] not in posted_ids and not p.get("posted", False):
                post = p
                break
        
        if not post:
            logger.info("All posts have been published.")
            return

        logger.info("Preparing post #%s (%s)", post["id"], post["type"])

        media_ids: Optional[List[str]] = None
        if post.get("image"):
            image_path = post["image"]
            if os.path.isfile(image_path):
                logger.info("Uploading image: %s", image_path)
                try:
                    media_id = self._upload_media_with_retry(image_path)
                    media_ids = [media_id]
                except Exception as e:
                    logger.error("Failed to upload image '%s': %s. Posting without image.", image_path, e)
            else:
                logger.warning("Image file not found: %s. Posting without image.", image_path)

        try:
            tweet_id = self._create_tweet_with_retry(text=post["content"], media_ids=media_ids)
            logger.info("Posted tweet #%s (Tweet ID: %s)", post["id"], tweet_id)
            
            tracker["posted_ids"].append(post["id"])
            tracker["last_posted_at"] = datetime.now(timezone.utc).isoformat()
            tracker["total_posted"] = len(tracker["posted_ids"])
            self.save_tracker(tracker)
            
            for p in posts_data["posts"]:
                if p["id"] == post["id"]:
                    p["posted"] = True
                    p["posted_at"] = datetime.now(timezone.utc).isoformat()
                    p["tweet_id"] = str(tweet_id)
                    break
            self.save_posts(posts_data)
            
        except Exception as e:
            logger.error("Failed to post tweet after retries: %s", e)
            raise

    def post_single(self, text: str, image_path: Optional[str] = None) -> str:
        """Post a single tweet directly. Supports long tweets and image uploads."""
        logger.info("Preparing to post: %s...", text[:50])

        media_ids: Optional[List[str]] = None
        if image_path:
            if os.path.isfile(image_path):
                logger.info("Uploading image: %s", image_path)
                media_id = self._upload_media_with_retry(image_path)
                media_ids = [media_id]
            else:
                logger.error("Image file not found: %s", image_path)
                raise FileNotFoundError("Image file not found: %s" % image_path)

        try:
            tweet_id = self._create_tweet_with_retry(text=text, media_ids=media_ids)
            logger.info("Successfully posted tweet: %s", tweet_id)
            return tweet_id
        except Exception as e:
            logger.error("Failed to post tweet after retries: %s", e)
            raise e
