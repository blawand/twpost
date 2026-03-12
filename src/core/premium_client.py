
import base64
import json
import logging
import mimetypes
import os

from twitter_cli.client import TwitterClient, _get_cffi_session
from twitter_cli.exceptions import TwitterAPIError
from twitter_cli.graphql import FEATURES
from twitter_cli.parser import _deep_get

logger = logging.getLogger(__name__)

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
    """Extends TwitterClient with long tweet (notetweet) and media upload support."""

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
        mime.addpart(name="command", data="APPEND")
        mime.addpart(name="media_id", data=media_id)
        mime.addpart(name="segment_index", data="0")
        mime.addpart(name="media_data", data=base64.b64encode(file_data).decode("ascii"))

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
