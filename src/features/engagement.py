import asyncio
import json
import logging
import os
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import tweepy
from twikit import Client

from core.llm_helper import LLMHelper

logger = logging.getLogger(__name__)


class EngagementManager:
    """Manages searching for tweets and replying using AI."""

    def __init__(
        self,
        client: Optional[Client],
        config_loader,
        tweepy_client: Optional[tweepy.Client] = None
    ):
        self.client = client
        self.tweepy_client = tweepy_client
        self.config = config_loader.get_settings()
        self.llm = LLMHelper(self.config)

        project_root = Path(__file__).resolve().parent.parent.parent
        self.tracker_file = project_root / "data" / "engagement_tracker.json"
        self.replied_ids = self._load_tracker()

        self.max_replies = max(1, self._read_int_env("ENGAGEMENT_MAX_REPLIES", 1))
        self.search_count = max(5, self._read_int_env("ENGAGEMENT_SEARCH_COUNT", 15))
        self.reply_delay_min = self._read_float_env("ENGAGEMENT_DELAY_MIN_SECONDS", 5.0)
        self.reply_delay_max = self._read_float_env("ENGAGEMENT_DELAY_MAX_SECONDS", 15.0)
        self.min_text_length = max(20, self._read_int_env("ENGAGEMENT_MIN_TEXT_LENGTH", 20))
        self.top_candidate_pool = max(1, self._read_int_env("ENGAGEMENT_TOP_POOL", 3))
        self.require_fresh_tweets = self._read_bool_env("ENGAGEMENT_REQUIRE_FRESH_TWEETS", True)
        self.max_tweet_age_minutes = max(
            5,
            self._read_int_env("ENGAGEMENT_MAX_TWEET_AGE_MINUTES", 180),
        )
        self.use_live_trends = self._read_bool_env("ENGAGEMENT_USE_TRENDS", True)
        self.trend_count = max(5, self._read_int_env("ENGAGEMENT_TRENDS_COUNT", 20))
        self.max_trend_queries = max(1, self._read_int_env("ENGAGEMENT_TREND_QUERIES", 6))
        self.trend_categories = self._parse_trend_categories(
            os.getenv("ENGAGEMENT_TREND_CATEGORIES", "trending,news")
        )
        self.min_engagement_or_views = max(
            0,
            self._read_int_env("ENGAGEMENT_MIN_ENGAGEMENT_OR_VIEWS", 20),
        )
        self.excluded_handles = self._parse_handle_set(
            os.getenv("ENGAGEMENT_EXCLUDED_HANDLES", "grok")
        )
        self.prefer_official_search = self._read_bool_env(
            "ENGAGEMENT_PREFER_OFFICIAL_SEARCH",
            True,
        )

        self.my_username = os.getenv("TWITTER_HANDLE", "lynxtradesapp").strip().lstrip("@")
        general_lane_weight = self._read_float_env("ENGAGEMENT_GENERAL_WEIGHT", 0.45)
        general_lane_weight = min(max(general_lane_weight, 0.05), 0.95)

        self.lanes: List[Dict[str, Any]] = [
            {
                "name": "journal_intent",
                "weight": 1.0 - general_lane_weight,
                "product": "Latest",
                "keywords": [
                    "trading journal",
                    "trade journal",
                    "journaling trades",
                    "trading discipline",
                    "revenge trading",
                    "trading psychology",
                    "risk management trading",
                    "blown account",
                    "trading plan",
                    "why i lost trading",
                ],
            },
            {
                "name": "broad_trending",
                "weight": general_lane_weight,
                "product": "Top",
                "keywords": [
                    "inflation",
                    "interest rates",
                    "FOMC",
                    "CPI",
                    "S&P 500",
                    "Nasdaq",
                    "earnings season",
                    "recession",
                    "economic growth",
                    "stock market",
                    "trading strategy",
                    "market sentiment",
                    "business news",
                    "small business",
                ],
            },
        ]
        self.trend_relevance_terms = [
            "economy", "economic", "economics", "inflation", "deflation",
            "cpi", "ppi", "jobs", "payroll", "unemployment", "gdp",
            "fomc", "fed", "powell", "interest rate", "rates",
            "yield", "bond", "treasury", "recession", "soft landing",
            "stock", "stocks", "equity", "equities", "market", "markets",
            "sp500", "s&p", "nasdaq", "dow", "russell", "earnings",
            "guidance", "ipo", "valuation", "business", "startup",
            "bank", "banking", "forex", "fx", "dollar", "usd",
            "crypto", "bitcoin", "ethereum", "gold", "oil", "commodity",
            "tariff", "trade war"
        ]

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
    def _read_bool_env(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        logger.warning("Invalid %s='%s'. Using default=%s.", name, value, default)
        return default

    @staticmethod
    def _parse_trend_categories(raw: str) -> List[str]:
        valid = {"trending", "for-you", "news", "sports", "entertainment"}
        categories = []
        for item in raw.split(","):
            category = item.strip().lower()
            if not category:
                continue
            if category in valid:
                categories.append(category)
        if not categories:
            return ["trending", "news"]
        return categories

    @staticmethod
    def _parse_handle_set(raw: str) -> set[str]:
        handles = set()
        for item in raw.split(","):
            handle = item.strip().lower().lstrip("@")
            if handle:
                handles.add(handle)
        return handles

    def _load_tracker(self) -> set[str]:
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return {str(item) for item in data}
                logger.warning("engagement_tracker.json is not a list. Starting with empty tracker.")
            except Exception as e:
                logger.error("Error loading engagement tracker: %s", e)
        return set()

    def _save_tracker(self):
        try:
            os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
            with open(self.tracker_file, "w", encoding="utf-8") as f:
                json.dump(sorted(self.replied_ids), f, indent=2)
        except Exception as e:
            logger.error("Error saving engagement tracker: %s", e)

    @staticmethod
    def _safe_int(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)

        text = str(value).strip().replace(",", "")
        if not text:
            return 0

        multiplier = 1
        suffix = text[-1].upper()
        if suffix in ("K", "M", "B"):
            text = text[:-1]
            if suffix == "K":
                multiplier = 1_000
            elif suffix == "M":
                multiplier = 1_000_000
            elif suffix == "B":
                multiplier = 1_000_000_000

        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0

    @staticmethod
    def _tweet_value(tweet: Any, field_names: List[str]) -> int:
        for field_name in field_names:
            value = getattr(tweet, field_name, None)
            if value is not None:
                return EngagementManager._safe_int(value)
        return 0

    def _tweet_social_proof(self, tweet: Any) -> Dict[str, int]:
        like_count = self._tweet_value(tweet, ["favorite_count", "like_count"])
        retweet_count = self._tweet_value(tweet, ["retweet_count"])
        reply_count = self._tweet_value(tweet, ["reply_count"])
        quote_count = self._tweet_value(tweet, ["quote_count"])
        view_count = self._tweet_value(tweet, ["view_count"])
        total_engagement = like_count + retweet_count + reply_count + quote_count
        return {
            "like_count": like_count,
            "retweet_count": retweet_count,
            "reply_count": reply_count,
            "quote_count": quote_count,
            "view_count": view_count,
            "total_engagement": total_engagement,
        }

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None

        if isinstance(value, datetime):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 1_000_000_000_000:
                timestamp = timestamp / 1000.0
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except Exception:
                return None

        raw = str(value).strip()
        if not raw:
            return None

        if raw.isdigit():
            return EngagementManager._parse_datetime(int(raw))

        normalized = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    def _tweet_created_at(self, tweet: Any) -> Optional[datetime]:
        field_names = [
            "created_at_datetime",
            "created_at",
            "date",
            "timestamp",
            "time",
        ]
        for field_name in field_names:
            dt = self._parse_datetime(getattr(tweet, field_name, None))
            if dt is not None:
                return dt

        for attr in ("_data", "data"):
            raw_payload = getattr(tweet, attr, None)
            if isinstance(raw_payload, dict):
                for field_name in field_names:
                    dt = self._parse_datetime(raw_payload.get(field_name))
                    if dt is not None:
                        return dt

        return None

    def _is_fresh_tweet(self, tweet: Any) -> bool:
        if not self.require_fresh_tweets:
            return True

        tweet_id = str(getattr(tweet, "id", "")).strip() or "unknown"
        created_at = self._tweet_created_at(tweet)
        if created_at is None:
            logger.debug(
                "Skipping tweet id=%s because created_at was unavailable and freshness is required.",
                tweet_id,
            )
            return False

        age_minutes = (datetime.now(timezone.utc) - created_at).total_seconds() / 60.0
        if age_minutes < 0:
            age_minutes = 0.0
        if age_minutes > self.max_tweet_age_minutes:
            logger.debug(
                "Skipping stale tweet id=%s age=%.1f minutes (max=%s).",
                tweet_id,
                age_minutes,
                self.max_tweet_age_minutes,
            )
            return False

        return True

    def _pick_lane_order(self) -> List[Dict[str, Any]]:
        weights = [max(0.0, lane["weight"]) for lane in self.lanes]
        if sum(weights) <= 0:
            return self.lanes

        first_lane = random.choices(self.lanes, weights=weights, k=1)[0]
        remaining = [lane for lane in self.lanes if lane["name"] != first_lane["name"]]
        random.shuffle(remaining)
        return [first_lane] + remaining

    def _is_candidate(self, tweet: Any) -> bool:
        tweet_id = str(getattr(tweet, "id", "")).strip()
        if not tweet_id or tweet_id in self.replied_ids:
            return False

        user = getattr(tweet, "user", None)
        handle = (getattr(user, "screen_name", "") or "").strip()
        handle_lower = handle.lower()
        if not handle:
            return False
        if handle_lower == self.my_username.lower():
            return False
        if handle_lower in self.excluded_handles:
            logger.debug("Skipping tweet id=%s from excluded handle @%s.", tweet_id, handle)
            return False

        text = (getattr(tweet, "text", "") or "").strip()
        if len(text) < self.min_text_length:
            return False
        if text.startswith("RT @"):
            return False

        in_reply_to_status = getattr(tweet, "in_reply_to_status_id", None)
        if in_reply_to_status is not None:
            return False

        if not self._is_fresh_tweet(tweet):
            return False

        if self.min_engagement_or_views > 0:
            social_proof = self._tweet_social_proof(tweet)
            if (
                max(social_proof["total_engagement"], social_proof["view_count"])
                < self.min_engagement_or_views
            ):
                logger.debug(
                    "Skipping low-social-proof tweet id=%s engagements=%s views=%s min=%s.",
                    tweet_id,
                    social_proof["total_engagement"],
                    social_proof["view_count"],
                    self.min_engagement_or_views,
                )
                return False

        if text.count("@") > 3:
            return False
        return True

    def _score_tweet(self, tweet: Any, lane_name: str) -> float:
        social_proof = self._tweet_social_proof(tweet)
        like_count = social_proof["like_count"]
        retweet_count = social_proof["retweet_count"]
        reply_count = social_proof["reply_count"]
        quote_count = social_proof["quote_count"]
        view_count = social_proof["view_count"]

        user = getattr(tweet, "user", None)
        follower_count = self._safe_int(getattr(user, "followers_count", 0)) if user else 0
        text = (getattr(tweet, "text", "") or "").strip()
        text_len = len(text)

        virality_score = (
            (like_count * 1.0)
            + (retweet_count * 2.3)
            + (reply_count * 2.0)
            + (quote_count * 2.0)
            + (view_count * 0.02)
            + (follower_count * 0.001)
        )

        if lane_name == "broad_trending":
            return virality_score + (text_len * 0.05) + random.uniform(0.0, 2.0)

        return (
            (reply_count * 1.4)
            + (like_count * 0.9)
            + (retweet_count * 1.2)
            + (follower_count * 0.0005)
            + random.uniform(0.0, 1.0)
        )

    def _is_relevant_trend(self, trend_text: str) -> bool:
        normalized = trend_text.lower().strip()
        if not normalized:
            return False
        if any(term in normalized for term in self.trend_relevance_terms):
            return True
        if normalized.startswith("$") and len(normalized) <= 7:
            return True
        return False

    @staticmethod
    def _extract_reply_reference(tweet: Any) -> Optional[str]:
        references = getattr(tweet, "referenced_tweets", None) or []
        for reference in references:
            ref_type = getattr(reference, "type", None)
            ref_id = getattr(reference, "id", None)
            if ref_type == "replied_to" and ref_id is not None:
                return str(ref_id)
            if isinstance(reference, dict):
                if reference.get("type") == "replied_to" and reference.get("id") is not None:
                    return str(reference["id"])
        return None

    def _adapt_official_tweet(
        self,
        tweet: Any,
        users_by_id: Dict[str, Any],
    ) -> Optional[Any]:
        tweet_id = str(getattr(tweet, "id", "") or "").strip()
        if not tweet_id:
            return None

        author_id = str(getattr(tweet, "author_id", "") or "").strip()
        author = users_by_id.get(author_id)
        username = (getattr(author, "username", "") or "").strip() if author else ""
        if not username:
            return None

        user_metrics = getattr(author, "public_metrics", None) or {}
        tweet_metrics = getattr(tweet, "public_metrics", None) or {}

        return SimpleNamespace(
            id=tweet_id,
            text=(getattr(tweet, "text", "") or "").strip(),
            created_at=getattr(tweet, "created_at", None),
            in_reply_to_status_id=self._extract_reply_reference(tweet),
            like_count=self._safe_int(tweet_metrics.get("like_count")),
            retweet_count=self._safe_int(tweet_metrics.get("retweet_count")),
            reply_count=self._safe_int(tweet_metrics.get("reply_count")),
            quote_count=self._safe_int(tweet_metrics.get("quote_count")),
            view_count=self._safe_int(tweet_metrics.get("impression_count")),
            user=SimpleNamespace(
                screen_name=username,
                followers_count=self._safe_int(user_metrics.get("followers_count")),
            ),
        )

    def _build_official_query(self, keyword_query: str) -> str:
        base = keyword_query.strip()
        if not base:
            return "-is:retweet -is:reply lang:en"
        return f"({base}) -is:retweet -is:reply lang:en"

    def _search_tweets_official(self, keyword_query: str) -> List[Any]:
        if not self.tweepy_client:
            return []

        response = self.tweepy_client.search_recent_tweets(
            query=self._build_official_query(keyword_query),
            max_results=max(10, min(self.search_count, 100)),
            expansions=["author_id"],
            tweet_fields=[
                "author_id",
                "created_at",
                "public_metrics",
                "referenced_tweets",
            ],
            user_fields=["username", "public_metrics"],
        )

        if not response or not response.data:
            return []

        users_by_id: Dict[str, Any] = {}
        includes = getattr(response, "includes", None)
        if isinstance(includes, dict):
            for user in includes.get("users", []) or []:
                user_id = str(getattr(user, "id", "") or "").strip()
                if user_id:
                    users_by_id[user_id] = user

        adapted: List[Any] = []
        for tweet in response.data:
            normalized = self._adapt_official_tweet(tweet, users_by_id)
            if normalized:
                adapted.append(normalized)
        return adapted

    async def _get_trending_queries(self) -> List[str]:
        if not self.use_live_trends:
            return []
        if not self.client:
            logger.info("Live trend lookup skipped because Twikit is unavailable.")
            return []

        seen = set()
        collected: List[str] = []

        for category in self.trend_categories:
            try:
                trends = await self.client.get_trends(
                    category=category,
                    count=self.trend_count,
                    retry=False,
                )
            except Exception as e:
                logger.warning("Could not fetch %s trends: %s", category, e)
                continue

            for trend in trends:
                name = str(getattr(trend, "name", "") or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                if not self._is_relevant_trend(name):
                    continue
                seen.add(key)
                collected.append(name)
                if len(collected) >= self.max_trend_queries:
                    break

            if len(collected) >= self.max_trend_queries:
                break

        if collected:
            logger.info("Live trend queries: %s", ", ".join(collected))
        else:
            logger.info("No relevant live trends found for configured categories.")
        return collected

    async def _fetch_lane_candidates(self, lane: Dict[str, Any]) -> List[Dict[str, Any]]:
        queries = list(lane["keywords"])

        if lane["name"] == "broad_trending":
            trend_queries = await self._get_trending_queries()
            if trend_queries:
                queries = trend_queries + queries

        query = random.choice(queries)
        logger.info(
            "Lane=%s searching product=%s query='%s'",
            lane["name"],
            lane["product"],
            query,
        )

        tweets: List[Any] = []
        search_sources: List[str] = []
        if self.prefer_official_search and self.tweepy_client:
            search_sources.append("official")
        if self.client:
            search_sources.append("twikit")
        if not self.prefer_official_search and self.tweepy_client:
            search_sources.append("official")

        if not search_sources:
            logger.error("No search client available. Configure Tweepy or Twikit.")
            return []

        for source in search_sources:
            try:
                if source == "official":
                    tweets = self._search_tweets_official(query)
                else:
                    tweets = await self.client.search_tweet(
                        query,
                        product=lane["product"],
                        count=self.search_count,
                    )
                if tweets:
                    logger.info(
                        "Lane=%s source=%s fetched=%s tweets.",
                        lane["name"],
                        source,
                        len(tweets),
                    )
                    break
                logger.info("Lane=%s source=%s returned no tweets.", lane["name"], source)
            except Exception as e:
                if source == "official":
                    error_text = str(e).lower()
                    if "403" in error_text or "forbidden" in error_text:
                        logger.warning(
                            "Official API search is forbidden. Confirm app read permissions "
                            "and account access tier support recent search."
                        )
                logger.warning("Lane=%s source=%s search failed: %s", lane["name"], source, e)

        if not tweets:
            return []

        candidates: List[Dict[str, Any]] = []
        for tweet in tweets:
            if not self._is_candidate(tweet):
                continue
            candidates.append(
                {
                    "tweet": tweet,
                    "score": self._score_tweet(tweet, lane["name"]),
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates

    def _select_candidate(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None

        top = candidates[: self.top_candidate_pool]
        weights = [max(0.1, item["score"]) for item in top]
        return random.choices(top, weights=weights, k=1)[0]

    @staticmethod
    def _fit_reply_length(text: str, max_length: int = 280) -> str:
        text = (text or "").strip()
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    async def _post_reply(self, tweet: Any, reply_text: str, handle: str) -> bool:
        success = False

        if self.tweepy_client:
            try:
                self.tweepy_client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=str(tweet.id),
                )
                logger.info("Replied to @%s via Official API.", handle)
                success = True
            except Exception as e:
                logger.warning("Official API failed, falling back to Twikit: %s", e)

        if not success:
            if not self.client:
                logger.warning("Twikit fallback unavailable. Reply was not posted.")
                return False
            await self.client.create_tweet(text=reply_text, reply_to=tweet.id)
            logger.info("Replied to @%s via Twikit.", handle)
            success = True

        return success

    async def _like_tweet(self, tweet: Any, handle: str) -> bool:
        tweet_id = str(tweet.id)

        if self.tweepy_client:
            try:
                self.tweepy_client.like(tweet_id=tweet_id)
                logger.info("Liked tweet from @%s via Official API.", handle)
                return True
            except Exception as e:
                logger.warning("Official API like failed, falling back to Twikit: %s", e)

        try:
            if not self.client:
                logger.warning("Twikit fallback unavailable. Like was not sent for tweet id=%s.", tweet_id)
                return False
            await self.client.favorite_tweet(tweet_id)
            logger.info("Liked tweet from @%s via Twikit.", handle)
            return True
        except Exception as e:
            logger.warning("Failed to like tweet id=%s: %s", tweet_id, e)
            return False

    async def run(self):
        logger.info("Starting engagement run.")
        logger.info(
            "Freshness filter: enabled=%s max_age_minutes=%s",
            self.require_fresh_tweets,
            self.max_tweet_age_minutes,
        )
        logger.info(
            "Candidate filters: excluded_handles=%s min_engagement_or_views=%s",
            ",".join(f"@{handle}" for handle in sorted(self.excluded_handles)) or "none",
            self.min_engagement_or_views,
        )
        replies_count = 0

        try:
            lane_order = self._pick_lane_order()
            logger.info(
                "Lane order this run: %s",
                ", ".join(lane["name"] for lane in lane_order),
            )

            for lane in lane_order:
                if replies_count >= self.max_replies:
                    break

                candidates = await self._fetch_lane_candidates(lane)
                if not candidates:
                    logger.info("Lane=%s had no valid candidates.", lane["name"])
                    continue

                selected = self._select_candidate(candidates)
                if not selected:
                    continue

                tweet = selected["tweet"]
                text = (getattr(tweet, "text", "") or "").strip()
                user = getattr(tweet, "user", None)
                handle = (getattr(user, "screen_name", "") or "").strip()

                logger.info(
                    "Selected lane=%s score=%.2f author=@%s text='%s'",
                    lane["name"],
                    selected["score"],
                    handle,
                    text[:80].replace("\n", " "),
                )

                delay = random.uniform(self.reply_delay_min, self.reply_delay_max)
                logger.info("Sleeping %.1fs before reply.", delay)
                await asyncio.sleep(delay)

                reply_text = await self.llm.generate_reply(
                    tweet_text=text,
                    user_handle=handle,
                    lane_name=lane["name"],
                )
                reply_text = self._fit_reply_length(reply_text)
                if not reply_text:
                    logger.info("LLM returned empty reply. Trying next lane.")
                    continue

                logger.info("Generated reply: %s", reply_text)

                try:
                    success = await self._post_reply(tweet, reply_text, handle)
                    if success:
                        liked = await self._like_tweet(tweet, handle)
                        if not liked:
                            logger.warning(
                                "Reply sent but like step failed for tweet id=%s.",
                                tweet.id,
                            )
                        self.replied_ids.add(str(tweet.id))
                        self._save_tracker()
                        replies_count += 1
                        logger.info("One reply sent. Exiting run.")
                        break
                except Exception as e:
                    error_str = str(e)
                    if "226" in error_str:
                        logger.error("Blocked with error 226. Stopping engagement run.")
                        logger.error("Try manual usage for a day, re-login, then retry.")
                        return
                    logger.error("Failed to reply: %s", e)

        except Exception as e:
            logger.error("Engagement loop failed: %s", e)

        logger.info("Engagement finished. Replied to %s tweets.", replies_count)
