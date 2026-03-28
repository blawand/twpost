
import base64
import json
import logging
import mimetypes
import os
from types import SimpleNamespace

from twitter_cli.client import TwitterClient, _get_cffi_session
from twitter_cli.exceptions import TwitterAPIError
from twitter_cli.graphql import FALLBACK_QUERY_IDS, FEATURES
from twitter_cli.parser import _deep_get

logger = logging.getLogger(__name__)

# Register CreateNoteTweet query ID so twitter-cli's _graphql_post can resolve it.
# If this goes stale, _graphql_post will auto-refresh from live JS bundles.
FALLBACK_QUERY_IDS.setdefault("CreateNoteTweet", "iCUB42lIfXf9qPKctjE5rQ")

# Feature flags required for CreateNoteTweet (long-form tweets)
NOTE_TWEET_FEATURES = {
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "articles_preview_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "responsive_web_media_download_video_enabled": False,
    "premium_content_api_read_enabled": False,
}


class PremiumTwitterClient(TwitterClient):
    """Extends TwitterClient with long tweets, media upload, and trends."""

    # ── Initialization ──────────────────────────────────────────

    @staticmethod
    def _load_auth_payload():
        """Load the preferred single-secret auth payload, with legacy fallback."""
        raw_value = os.getenv("TWITTER_AUTH", "").strip()
        source_name = "TWITTER_AUTH"
        if not raw_value:
            raw_value = os.getenv("TWITTER_COOKIES", "").strip()
            source_name = "TWITTER_COOKIES"
        if not raw_value:
            return None, None

        # Accept both the recommended raw JSON value and an accidental
        # KEY=VALUE paste from .env / GitHub UI.
        if "=" in raw_value:
            maybe_name, maybe_value = raw_value.split("=", 1)
            if maybe_name.strip() in {"TWITTER_AUTH", "TWITTER_COOKIES"}:
                raw_value = maybe_value.strip()

        raw_value = raw_value.strip("'\"")

        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse %s JSON: %s", source_name, e)
            return None, source_name

        if not isinstance(payload, dict):
            logger.warning("%s must be a JSON object.", source_name)
            return None, source_name

        return payload, source_name

    @classmethod
    def from_env(cls):
        """Create a PremiumTwitterClient from environment variables."""
        auth_token = os.getenv("TWITTER_AUTH_TOKEN", "").strip()
        ct0 = os.getenv("TWITTER_CT0", "").strip()

        auth_payload, payload_source = cls._load_auth_payload()
        if auth_payload:
            if not auth_token:
                auth_token = (auth_payload.get("auth_token") or "").strip()
            if not ct0:
                ct0 = (auth_payload.get("ct0") or "").strip()
            if any(key not in {"auth_token", "ct0"} for key in auth_payload):
                logger.info(
                    "%s contains short-lived browser cookies or extra fields; using only auth_token and ct0.",
                    payload_source,
                )

        if not auth_token or not ct0:
            raise ValueError(
                "Missing auth_token or ct0! Set TWITTER_AUTH with a JSON object "
                'like {"auth_token":"...","ct0":"..."}, or use the legacy '
                "TWITTER_COOKIES / TWITTER_AUTH_TOKEN / TWITTER_CT0 variables."
            )

        client = cls(
            auth_token=auth_token,
            ct0=ct0,
        )
        logger.info("PremiumTwitterClient initialized.")
        return client

    # ── Media Upload ────────────────────────────────────────────

    def upload_media(self, file_path):
        """Upload a media file (image) to Twitter. Returns the media_id string.

        Uses Twitter's chunked upload API (INIT -> APPEND -> FINALIZE).
        Supported image types: JPEG, PNG, GIF, WEBP.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError("Media file not found: %s" % file_path)

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "image/jpeg"

        file_size = os.path.getsize(file_path)
        upload_url = "https://upload.twitter.com/i/media/upload.json"
        session = _get_cffi_session()

        # ── INIT ──
        init_params = {
            "command": "INIT",
            "total_bytes": str(file_size),
            "media_type": mime_type,
            "media_category": "tweet_image",
        }
        headers = self._build_headers(url=upload_url, method="POST")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        resp = session.post(upload_url, headers=headers, data=init_params, timeout=30)
        if resp.status_code >= 400:
            raise TwitterAPIError(resp.status_code, "Media upload INIT failed: %s" % resp.text[:500])
        init_data = json.loads(resp.text)
        media_id = str(init_data["media_id_string"])
        logger.info("Media upload INIT complete: media_id=%s", media_id)

        # ── APPEND (single segment for images) ──
        with open(file_path, "rb") as f:
            file_data = f.read()

        append_headers = self._build_headers(url=upload_url, method="POST")
        append_headers.pop("Content-Type", None)

        from curl_cffi import CurlMime
        mime = CurlMime()
        mime.addpart(name="command", data=b"APPEND")
        mime.addpart(name="media_id", data=media_id.encode())
        mime.addpart(name="segment_index", data=b"0")
        mime.addpart(name="media_data", data=base64.b64encode(file_data))

        resp = session.post(upload_url, headers=append_headers, multipart=mime, timeout=60)
        if resp.status_code >= 400:
            raise TwitterAPIError(resp.status_code, "Media upload APPEND failed: %s" % resp.text[:500])
        logger.info("Media upload APPEND complete for media_id=%s", media_id)

        # ── FINALIZE ──
        finalize_params = {
            "command": "FINALIZE",
            "media_id": media_id,
        }
        finalize_headers = self._build_headers(url=upload_url, method="POST")
        finalize_headers["Content-Type"] = "application/x-www-form-urlencoded"

        resp = session.post(upload_url, headers=finalize_headers, data=finalize_params, timeout=30)
        if resp.status_code >= 400:
            raise TwitterAPIError(resp.status_code, "Media upload FINALIZE failed: %s" % resp.text[:500])
        logger.info("Media upload FINALIZE complete for media_id=%s", media_id)

        self._write_delay()
        return media_id

    # ── Tweet Creation (with long tweet + media support) ────────

    def create_tweet(self, text, reply_to_id=None, media_ids=None):
        """Post a new tweet. Returns the new tweet ID.

        Uses CreateNoteTweet for tweets >280 chars (Twitter Premium).
        Supports media attachments via media_ids (from upload_media).
        """
        media_entities = []
        if media_ids:
            media_entities = [{"media_id": mid, "tagged_users": []} for mid in media_ids]

        variables = {
            "tweet_text": text,
            "media": {"media_entities": media_entities, "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "dark_request": False,
        }

        if reply_to_id:
            variables["reply"] = {
                "in_reply_to_tweet_id": reply_to_id,
                "exclude_reply_user_ids": [],
            }

        # Long tweets (>280 chars) require a separate GraphQL operation
        if len(text) > 280:
            variables["notetweet"] = {
                "tweet_text_length": len(text),
                "richtext_options": {
                    "richtext_tags": [],
                },
            }
            data = self._graphql_post("CreateNoteTweet", variables, NOTE_TWEET_FEATURES)
            self._write_delay()
            result = _deep_get(data, "data", "notetweet_create", "tweet_results", "result")
            if result:
                return result.get("rest_id", "")
            raise TwitterAPIError(0, "Failed to create note tweet")
        else:
            data = self._graphql_post("CreateTweet", variables, FEATURES)
            self._write_delay()
            result = _deep_get(data, "data", "create_tweet", "tweet_results", "result")
            if result:
                return result.get("rest_id", "")
            raise TwitterAPIError(0, "Failed to create tweet")

    # ── Trends ──────────────────────────────────────────────────

    def get_trends(self, category="trending", count=20):
        """Fetch trending topics from Twitter's guide API.

        Returns a list of SimpleNamespace objects with a 'name' attribute.

        Parameters
        ----------
        category : str
            One of 'trending', 'news', 'sports', 'entertainment'.
        count : int
            Number of trends to fetch.
        """
        tab_id = category.lower()
        if tab_id in ("news", "sports", "entertainment"):
            tab_id += "_unified"

        url = "https://x.com/i/api/2/guide.json"
        params = {
            "count": str(count),
            "include_page_configuration": "true",
            "initial_tab_id": tab_id,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query_string}"

        data = self._api_get(full_url)

        trends = []
        try:
            # Navigate the guide response to find trend entries
            timeline = _deep_get(data, "timeline", "instructions") or []
            for instruction in timeline:
                entries = instruction.get("addEntries", {}).get("entries", [])
                for entry in entries:
                    entry_id = entry.get("entryId", "")
                    prefix = "trends" if category == "trending" else "Guide"
                    if not entry_id.startswith(prefix):
                        continue
                    items = _deep_get(entry, "content", "timelineModule", "items") or []
                    for item in items:
                        trend_info = _deep_get(item, "item", "content", "trend")
                        if trend_info and "name" in trend_info:
                            trends.append(SimpleNamespace(name=trend_info["name"]))
        except Exception as e:
            logger.warning("Failed to parse trends: %s", e)

        return trends
