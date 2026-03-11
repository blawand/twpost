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

from twikit import Client
from twitter_cli.client import TwitterClient as GraphQLClient

from core.llm import LLMHelper

logger = logging.getLogger(__name__)


class EngagementManager:
    """Manages searching for tweets and replying using AI."""

    def __init__(
        self,
        twikit_client: Optional[Client],
        graphql_client: Optional[GraphQLClient] = None,
    ):
        self.client = twikit_client
        self.graphql_client = graphql_client
        self.llm = LLMHelper()

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
            5, self._read_int_env("ENGAGEMENT_MAX_TWEET_AGE_MINUTES", 180),
        )
        self.use_live_trends = self._read_bool_env("ENGAGEMENT_USE_TRENDS", True)
        self.trend_count = max(5, self._read_int_env("ENGAGEMENT_TRENDS_COUNT", 20))
        self.max_trend_queries = max(1, self._read_int_env("ENGAGEMENT_TREND_QUERIES", 6))
        self.trend_categories = self._parse_trend_categories(
            os.getenv("ENGAGEMENT_TREND_CATEGORIES", "trending,news")
        )
        self.min_engagement_or_views = max(
            0, self._read_int_env("ENGAGEMENT_MIN_ENGAGEMENT_OR_VIEWS", 20),
        )
        self.excluded_handles = self._parse_handle_set(
            os.getenv("ENGAGEMENT_EXCLUDED_HANDLES", "grok")
        )
        self.dry_run = self._read_bool_env("ENGAGEMENT_DRY_RUN", False)

        self.my_username = os.getenv("TWITTER_HANDLE", "lynxtradesapp").strip().lstrip("@")
        general_lane_weight = self._read_float_env("ENGAGEMENT_GENERAL_WEIGHT", 0.45)
        general_lane_weight = min(max(general_lane_weight, 0.05), 0.95)

        self.lanes: List[Dict[str, Any]] = [
            {
                "name": "journal_intent",
                "weight": 1.0 - general_lane_weight,
                "product": "Latest",
                "keywords": [
                    "trading journal", "trade journal", "journaling trades",
                    "trading discipline", "revenge trading", "trading psychology",
                    "risk management trading", "blown account", "trading plan",
                    "why i lost trading",
                ],
            },
            {
                "name": "broad_trending",
                "weight": general_lane_weight,
                "product": "Top",
                "keywords": [
                    "inflation", "interest rates", "FOMC", "CPI",
                    "S&P 500", "Nasdaq", "earnings season", "recession",
                    "economic growth", "stock market", "trading strategy",
                    "market sentiment", "business news", "small business",
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

    # ── Env Helpers ──────────────────────────────────────────────

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
        categories = [c.strip().lower() for c in raw.split(",") if c.strip().lower() in valid]
        return categories or ["trending", "news"]

    @staticmethod
    def _parse_handle_set(raw: str) -> set[str]:
        return {h.strip().lower().lstrip("@") for h in raw.split(",") if h.strip()}

    @staticmethod
    def _is_network_access_error(error: Exception) -> bool:
        text = str(error).lower()
        tokens = [
            "all connection attempts failed", "failed to establish a new connection",
            "winerror 10013", "connection refused", "temporary failure in name resolution",
            "name or service not known", "nodename nor servname provided",
        ]
        return any(token in text for token in tokens)

    # ── Tracker ──────────────────────────────────────────────────

    def _load_tracker(self) -> set[str]:
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return {str(item) for item in data}
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

    # ── Tweet Analysis ───────────────────────────────────────────

    @staticmethod
    def _safe_int(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)

        text = str(value).strip().replace(",", "")
        if not text:
            return 0

        multiplier = 1
        suffix = text[-1].upper()
        if suffix in ("K", "M", "B"):
            text = text[:-1]
            multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[suffix]

        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0

    @staticmethod
    def _tweet_value(tweet: Any, field_names: List[str]) -> int:
        for name in field_names:
            value = getattr(tweet, name, None)
            if value is not None:
                return EngagementManager._safe_int(value)
        return 0

    def _tweet_social_proof(self, tweet: Any) -> Dict[str, int]:
        like_count = self._tweet_value(tweet, ["favorite_count", "like_count"])
        retweet_count = self._tweet_value(tweet, ["retweet_count"])
        reply_count = self._tweet_value(tweet, ["reply_count"])
        quote_count = self._tweet_value(tweet, ["quote_count"])
        view_count = self._tweet_value(tweet, ["view_count"])
        return {
            "like_count": like_count,
            "retweet_count": retweet_count,
            "reply_count": reply_count,
            "quote_count": quote_count,
            "view_count": view_count,
            "total_engagement": like_count + retweet_count + reply_count + quote_count,
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
                timestamp /= 1000.0
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
        field_names = ["created_at_datetime", "created_at", "date", "timestamp", "time"]
        for name in field_names:
            dt = self._parse_datetime(getattr(tweet, name, None))
            if dt is not None:
                return dt
        for attr in ("_data", "data"):
            raw = getattr(tweet, attr, None)
            if isinstance(raw, dict):
                for name in field_names:
                    dt = self._parse_datetime(raw.get(name))
                    if dt is not None:
                        return dt
        return None

    def _is_fresh_tweet(self, tweet: Any) -> bool:
        if not self.require_fresh_tweets:
            return True
        tweet_id = str(getattr(tweet, "id", "")).strip() or "unknown"
        created_at = self._tweet_created_at(tweet)
        if created_at is None:
            logger.debug("Skipping tweet id=%s — no created_at available.", tweet_id)
            return False
        age_minutes = max(0, (datetime.now(timezone.utc) - created_at).total_seconds() / 60.0)
        if age_minutes > self.max_tweet_age_minutes:
            logger.debug("Skipping stale tweet id=%s age=%.1fm (max=%s).", tweet_id, age_minutes, self.max_tweet_age_minutes)
            return False
        return True

    # ── Candidate Selection ──────────────────────────────────────

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
        if not handle or handle.lower() == self.my_username.lower():
            return False
        if handle.lower() in self.excluded_handles:
            return False

        text = (getattr(tweet, "text", "") or "").strip()
        if len(text) < self.min_text_length or text.startswith("RT @"):
            return False
        if getattr(tweet, "in_reply_to_status_id", None) is not None:
            return False
        if not self._is_fresh_tweet(tweet):
            return False
        if self.min_engagement_or_views > 0:
            sp = self._tweet_social_proof(tweet)
            if max(sp["total_engagement"], sp["view_count"]) < self.min_engagement_or_views:
                return False
        if text.count("@") > 3:
            return False
        return True

    def _score_tweet(self, tweet: Any, lane_name: str) -> float:
        sp = self._tweet_social_proof(tweet)
        user = getattr(tweet, "user", None)
        follower_count = self._safe_int(getattr(user, "followers_count", 0)) if user else 0
        text_len = len((getattr(tweet, "text", "") or "").strip())

        if lane_name == "broad_trending":
            return (
                sp["like_count"] + sp["retweet_count"] * 2.3 + sp["reply_count"] * 2.0
                + sp["quote_count"] * 2.0 + sp["view_count"] * 0.02
                + follower_count * 0.001 + text_len * 0.05 + random.uniform(0, 2)
            )
        return (
            sp["reply_count"] * 1.4 + sp["like_count"] * 0.9
            + sp["retweet_count"] * 1.2 + follower_count * 0.0005
            + random.uniform(0, 1)
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

    def _select_candidate(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        top = candidates[:self.top_candidate_pool]
        weights = [max(0.1, item["score"]) for item in top]
        return random.choices(top, weights=weights, k=1)[0]

    @staticmethod
    def _fit_reply_length(text: str, max_length: int = 280) -> str:
        text = (text or "").strip()
        if len(text) <= max_length:
            return text
        return text[:max_length - 3].rstrip() + "..."

    # ── Search ───────────────────────────────────────────────────

    async def _get_trending_queries(self) -> List[str]:
        if not self.use_live_trends or not self.client:
            return []

        seen = set()
        collected: List[str] = []
        for category in self.trend_categories:
            try:
                trends = await self.client.get_trends(category=category, count=self.trend_count, retry=False)
            except Exception as e:
                logger.warning("Could not fetch %s trends: %s", category, e)
                continue
            for trend in trends:
                name = str(getattr(trend, "name", "") or "").strip()
                if not name or name.lower() in seen or not self._is_relevant_trend(name):
                    continue
                seen.add(name.lower())
                collected.append(name)
                if len(collected) >= self.max_trend_queries:
                    break
            if len(collected) >= self.max_trend_queries:
                break

        if collected:
            logger.info("Live trend queries: %s", ", ".join(collected))
        return collected

    async def _fetch_lane_candidates(self, lane: Dict[str, Any]) -> List[Dict[str, Any]]:
        queries = list(lane["keywords"])
        if lane["name"] == "broad_trending":
            trend_queries = await self._get_trending_queries()
            if trend_queries:
                queries = trend_queries + queries

        query = random.choice(queries)
        logger.info("Lane=%s query='%s'", lane["name"], query)

        tweets: List[Any] = []
        if self.client:
            try:
                tweets = await self.client.search_tweet(query, product=lane["product"], count=self.search_count)
                if tweets:
                    logger.info("Lane=%s fetched=%s tweets via Twikit.", lane["name"], len(tweets))
            except Exception as e:
                logger.warning("Lane=%s Twikit search failed: %s", lane["name"], e)

        if not tweets:
            logger.info("Lane=%s no tweets found.", lane["name"])
            return []

        candidates = []
        for tweet in tweets:
            if self._is_candidate(tweet):
                candidates.append({"tweet": tweet, "score": self._score_tweet(tweet, lane["name"])})
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    # ── Reply & Like ─────────────────────────────────────────────

    async def _post_reply(self, tweet: Any, reply_text: str, handle: str) -> bool:
        # Try GraphQL client first
        if self.graphql_client:
            try:
                self.graphql_client.create_tweet(text=reply_text, reply_to_id=str(tweet.id))
                logger.info("Replied to @%s via GraphQL.", handle)
                return True
            except Exception as e:
                logger.warning("GraphQL reply failed: %s", e)

        # Fallback to Twikit
        if self.client:
            try:
                await self.client.create_tweet(text=reply_text, reply_to=tweet.id)
                logger.info("Replied to @%s via Twikit.", handle)
                return True
            except Exception as e:
                logger.warning("Twikit reply failed: %s", e)

        logger.warning("No client available. Reply not posted.")
        return False

    async def _like_tweet(self, tweet: Any, handle: str) -> bool:
        tweet_id = str(tweet.id)

        if self.graphql_client:
            try:
                self.graphql_client.like_tweet(tweet_id)
                logger.info("Liked tweet from @%s via GraphQL.", handle)
                return True
            except Exception as e:
                logger.warning("GraphQL like failed: %s", e)

        if self.client:
            try:
                await self.client.favorite_tweet(tweet_id)
                logger.info("Liked tweet from @%s via Twikit.", handle)
                return True
            except Exception as e:
                logger.warning("Twikit like failed: %s", e)

        logger.warning("Failed to like tweet id=%s — no client available.", tweet_id)
        return False

    # ── Main Loop ────────────────────────────────────────────────

    async def run(self):
        logger.info("Starting engagement run.")
        logger.info("Dry run: %s", self.dry_run)
        replies_count = 0

        try:
            lane_order = self._pick_lane_order()
            logger.info("Lane order: %s", ", ".join(l["name"] for l in lane_order))

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

                logger.info("Selected lane=%s score=%.2f @%s: '%s'",
                            lane["name"], selected["score"], handle, text[:80].replace("\n", " "))

                delay = random.uniform(self.reply_delay_min, self.reply_delay_max)
                logger.info("Sleeping %.1fs before reply.", delay)
                await asyncio.sleep(delay)

                reply_text = await self.llm.generate_reply(
                    tweet_text=text, user_handle=handle, lane_name=lane["name"],
                )
                reply_text = self._fit_reply_length(reply_text)
                if not reply_text:
                    logger.info("LLM returned empty reply. Trying next lane.")
                    continue

                logger.info("Generated reply: %s", reply_text)

                if self.dry_run:
                    logger.info("Dry run — skipping reply/like for tweet id=%s.", tweet.id)
                    break

                try:
                    success = await self._post_reply(tweet, reply_text, handle)
                    if success:
                        await self._like_tweet(tweet, handle)
                        self.replied_ids.add(str(tweet.id))
                        self._save_tracker()
                        replies_count += 1
                        logger.info("Reply sent. Exiting run.")
                        break
                except Exception as e:
                    if "226" in str(e):
                        logger.error("Blocked with error 226. Stopping.")
                        return
                    logger.error("Failed to reply: %s", e)

        except Exception as e:
            logger.error("Engagement loop failed: %s", e)

        logger.info("Engagement finished. Replied to %s tweets.", replies_count)
