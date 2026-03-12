import asyncio
import json
import logging
import os
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.premium_client import PremiumTwitterClient
from core.llm import LLMHelper

logger = logging.getLogger(__name__)


class EngagementManager:
    """Manages searching for tweets and replying using AI."""

    def __init__(self, client: PremiumTwitterClient):
        self.client = client
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
    def _parse_handle_set(raw: str) -> set:
        return {h.strip().lower().lstrip("@") for h in raw.split(",") if h.strip()}

    # ── Tracker ──────────────────────────────────────────────────

    def _load_tracker(self) -> set:
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

    def _tweet_social_proof(self, tweet) -> Dict[str, int]:
        """Extract engagement metrics from a twitter-cli Tweet object."""
        m = tweet.metrics
        return {
            "like_count": m.likes,
            "retweet_count": m.retweets,
            "reply_count": m.replies,
            "quote_count": m.quotes,
            "view_count": m.views,
            "total_engagement": m.likes + m.retweets + m.replies + m.quotes,
        }

    @staticmethod
    def _parse_datetime(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        raw = str(value).strip()
        if not raw:
            return None

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

    def _is_fresh_tweet(self, tweet) -> bool:
        if not self.require_fresh_tweets:
            return True
        created_at = self._parse_datetime(tweet.created_at)
        if created_at is None:
            logger.debug("Skipping tweet id=%s — no created_at available.", tweet.id)
            return False
        age_minutes = max(0, (datetime.now(timezone.utc) - created_at).total_seconds() / 60.0)
        if age_minutes > self.max_tweet_age_minutes:
            logger.debug("Skipping stale tweet id=%s age=%.1fm (max=%s).", tweet.id, age_minutes, self.max_tweet_age_minutes)
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

    def _is_candidate(self, tweet) -> bool:
        tweet_id = str(tweet.id).strip()
        if not tweet_id or tweet_id in self.replied_ids:
            return False

        handle = tweet.author.screen_name
        if not handle or handle.lower() == self.my_username.lower():
            return False
        if handle.lower() in self.excluded_handles:
            return False

        text = (tweet.text or "").strip()
        if len(text) < self.min_text_length or text.startswith("RT @"):
            return False
        if tweet.is_retweet:
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

    def _score_tweet(self, tweet, lane_name: str) -> float:
        sp = self._tweet_social_proof(tweet)
        text_len = len((tweet.text or "").strip())

        if lane_name == "broad_trending":
            return (
                sp["like_count"] + sp["retweet_count"] * 2.3 + sp["reply_count"] * 2.0
                + sp["quote_count"] * 2.0 + sp["view_count"] * 0.02
                + text_len * 0.05 + random.uniform(0, 2)
            )
        return (
            sp["reply_count"] * 1.4 + sp["like_count"] * 0.9
            + sp["retweet_count"] * 1.2
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

    # ── Search & Trends ──────────────────────────────────────────

    def _get_trending_queries(self) -> List[str]:
        if not self.use_live_trends:
            return []

        seen = set()
        collected: List[str] = []
        for category in self.trend_categories:
            try:
                trends = self.client.get_trends(category=category, count=self.trend_count)
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

    def _fetch_lane_candidates(self, lane: Dict[str, Any]) -> List[Dict[str, Any]]:
        queries = list(lane["keywords"])
        if lane["name"] == "broad_trending":
            trend_queries = self._get_trending_queries()
            if trend_queries:
                queries = trend_queries + queries

        query = random.choice(queries)
        logger.info("Lane=%s query='%s'", lane["name"], query)

        tweets = []
        try:
            tweets = self.client.fetch_search(query, count=self.search_count, product=lane["product"])
            if tweets:
                logger.info("Lane=%s fetched=%s tweets.", lane["name"], len(tweets))
        except Exception as e:
            logger.warning("Lane=%s search failed: %s", lane["name"], e)

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

    def _post_reply(self, tweet_id: str, reply_text: str, handle: str) -> bool:
        try:
            self.client.create_tweet(text=reply_text, reply_to_id=tweet_id)
            logger.info("Replied to @%s.", handle)
            return True
        except Exception as e:
            logger.warning("Reply failed: %s", e)
            return False

    def _like_tweet(self, tweet_id: str, handle: str) -> bool:
        try:
            self.client.like_tweet(tweet_id)
            logger.info("Liked tweet from @%s.", handle)
            return True
        except Exception as e:
            logger.warning("Like failed: %s", e)
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

                candidates = self._fetch_lane_candidates(lane)
                if not candidates:
                    logger.info("Lane=%s had no valid candidates.", lane["name"])
                    continue

                selected = self._select_candidate(candidates)
                if not selected:
                    continue

                tweet = selected["tweet"]
                text = (tweet.text or "").strip()
                handle = tweet.author.screen_name

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
                    success = self._post_reply(str(tweet.id), reply_text, handle)
                    if success:
                        self._like_tweet(str(tweet.id), handle)
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
