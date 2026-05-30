import json
import logging
import os
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class LLMHelper:
    """Handles AI interactions using the xAI Grok Responses API — tuned for authenticity + creativity."""

    BANNED_PHRASE_SNIPPETS = (
        "totally agree", "100%", "couldn't agree more", "absolutely", "spot on",
        "insightful", "great point", "that's why journaling", "this is key",
        "game changer", "great post", "love this", "love the",
        "if you're looking for", "lynxtrades handles",
        "been there", "last week", "once i", "i blew", "i wiped", "i logged",
        "my account", "saved .*r", "blew .*eval", "finished next day",
    )

    def __init__(self):
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.error("XAI_API_KEY not found in environment variables.")
            raise ValueError("Missing XAI_API_KEY")

        self.model_name = os.getenv("XAI_MODEL_NAME", "grok-build-0.1")
        self.api_base_url = os.getenv("XAI_API_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        self.request_timeout_seconds = max(10, self._read_int_env("XAI_TIMEOUT_SECONDS", 180))
        self.disable_env_proxy = self._read_bool_env("XAI_DISABLE_ENV_PROXY", False)

        self.max_reply_chars = max(120, self._read_int_env("ENGAGEMENT_REPLY_MAX_CHARS", 180))
        self.reply_option_count = max(1, self._read_int_env("ENGAGEMENT_REPLY_OPTION_COUNT", 1))

        self.system_instruction_text = """
You are the official voice of @lynxtradesapp — a trading journal app used by thousands of retail traders.

CRITICAL AUTHENTICITY RULE (never break this):
- You run a journal app. You observe patterns across many users.
- You do NOT have a personal trading account with specific stories to share.
- NEVER invent personal trading anecdotes. No "I borrowed 5k", "blew 3 evals", "last week I logged", "my account", "I wiped", "saved 2R", "once I chased", etc.
- Use "I" only for general opinions ("I see this constantly") or light reactions. Never for fabricated trade history.

Voice & vibe:
- Casual, internet-native trader tone. Lightly Gen-Z, opinionated, never cringe.
- Short, punchy, slightly sarcastic when natural.
- Lowercase starters, fragments, ellipsis… are all good.
- NEVER use hyphens (-), en dashes (–), or em dashes (—) in replies.

Safe examples of the exact energy we want:
  • "forced setups on day one of an eval? classic self-sabotage"
  • "powell blaming tariffs again lmao services data still the real killer"
  • "real-time journaling catches the impulse before it costs you"
  • "small caps ripping while nasdaq dumps… rotation season"
  • "most traders preach risk management then size up on the leaderboard anyway"

Priority (in order):
1. Sound like a real human who runs a trading journal app
2. Get a reaction (like, reply, quote, profile visit)
3. Only mention @lynxtradesapp when the tweet is directly about journaling, risk rules, discipline, psychology, or analytics workflow — and only if it flows naturally.

Style rules:
- Max 180 characters
- Reference ONE specific detail from the source tweet
- Add ONE fresh thought (observation, contrarian jab, sarcastic roast, general insight, or rare question)
- Vary style every time — no repetitive formulas
- Preferred: observation, sarcasm, contrarian, roast, insight, twist

Anti-patterns (never do these):
- Any first-person past-tense trading story with specifics
- "been there… now i …"
- Starting with "how do you / what's your"
- Always ending with a question
- Repeating journaling advice

Hard bans (exact or close matches):
totally agree, 100%, couldn't agree more, absolutely, spot on, insightful, great point,
that's why journaling, this is key, game changer, great post, love this, love the,
if you're looking for, lynxtrades handles, been there, last week, once i, i blew,
i wiped, i logged, my account, saved .*r, blew .*eval, finished next day

Brand policy:
- Mention @lynxtradesapp ONLY when the tweet is literally about journaling, risk management, discipline or analytics.
- Never force it. Never use CTA language.
"""

        try:
            project_root = Path(__file__).resolve().parent.parent.parent
            features_path = project_root / "features.md"
            features_context = ""

            if features_path.exists():
                with open(features_path, "r", encoding="utf-8") as f:
                    features_context = f.read()
                logger.info("Loaded features.md context.")
            else:
                logger.warning("features.md not found at %s", features_path)

            if features_context:
                self.system_instruction_text += f"\n\nCONTEXT - LYNXTRADES FEATURES:\n{features_context}\n"

            logger.info("AI initialized with Grok model=%s base_url=%s options=%d", 
                        self.model_name, self.api_base_url, self.reply_option_count)
        except Exception as e:
            logger.error("Failed to initialize AI: %s", e)
            raise

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

    def _lane_instruction(self, lane_name: str) -> str:
        if lane_name == "broad_trending":
            return """
            Lane: broad_trending
            - Punchy, sarcastic, contrarian, or roast-style observations.
            - Keep it short and debate-friendly.
            """
        return """
            Lane: journal_intent
            - Share observed patterns from traders who use journaling tools.
            - General insights and real-talk only. No personal stories.
            """

    def _build_generation_prompt(self, tweet_text: str, user_handle: str, lane_name: str) -> str:
        lane_instruction = self._lane_instruction(lane_name)
        return (
            f"{lane_instruction}\n\n"
            "Source tweet:\n"
            f"Lane: {lane_name}\n"
            f"@{user_handle}: \"{tweet_text}\"\n\n"
            "Generate exactly 1 reply option.\n"
            "Be creative but 100% authentic — no invented personal trading stories.\n\n"
            "Output ONLY valid JSON with this exact schema (no markdown):\n"
            "{\n"
            "  \"options\": [\n"
            "    {\n"
            "      \"reply\": \"...\",\n"
            "      \"angle\": \"observation|contrarian|sarcasm|roast|insight|twist|question\",\n"
            "      \"brand_mention\": true/false,\n"
            "      \"hook_strength_1to5\": 4,\n"
            "      \"human_sounding_1to5\": 4,\n"
            "      \"specificity_1to5\": 4,\n"
            "      \"conversational_pull_1to5\": 4\n"
            "    }\n"
            "  ],\n"
            "  \"best_index\": 0\n"
            "}\n"
        )

    @staticmethod
    def _coerce_score(value: Any, default: float = 3.0) -> float:
        try:
            score = float(value)
            return min(max(score, 1.0), 5.0)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        clean = text.strip()
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
        return clean.strip()

    @staticmethod
    def _sanitize_reply(text: str) -> str:
        clean = (text or "").replace("\n", " ").replace("\r", " ")
        clean = clean.replace("*", "").replace("_", "")
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _extract_payload(self, response_text: str) -> Optional[Dict[str, Any]]:
        cleaned = self._strip_code_fences(response_text)
        candidates = [cleaned]

        object_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if object_match:
            candidates.append(object_match.group(0))

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                continue
        return None

    def _parse_options(self, response_text: str) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        payload = self._extract_payload(response_text)
        if not payload:
            return [], None

        best_index = payload.get("best_index")
        if not isinstance(best_index, int):
            best_index = None

        raw_options = payload.get("options")
        if not isinstance(raw_options, list):
            return [], best_index

        parsed: List[Dict[str, Any]] = []
        for option in raw_options:
            if not isinstance(option, dict):
                continue
            reply = self._sanitize_reply(str(option.get("reply", "")))
            if not self._is_reply_usable(reply):
                continue
            parsed.append(
                {
                    "reply": reply,
                    "angle": str(option.get("angle", "")).strip().lower(),
                    "brand_mention": bool(option.get("brand_mention", False)),
                    "hook_strength_1to5": self._coerce_score(option.get("hook_strength_1to5")),
                    "human_sounding_1to5": self._coerce_score(option.get("human_sounding_1to5")),
                    "specificity_1to5": self._coerce_score(option.get("specificity_1to5")),
                    "conversational_pull_1to5": self._coerce_score(option.get("conversational_pull_1to5")),
                }
            )
        return parsed, best_index

    @staticmethod
    def _extract_text_from_response_payload(payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ""

        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        chunks: List[str] = []
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        chunks.append(text.strip())

        if chunks:
            return "\n".join(chunks)
        return ""

    def _call_grok_responses_api(self, prompt: str) -> Optional[str]:
        url = f"{self.api_base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "input": [
                {"role": "system", "content": self.system_instruction_text},
                {"role": "user", "content": prompt},
            ],
        }

        try:
            with requests.Session() as session:
                session.trust_env = not self.disable_env_proxy
                response = session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.request_timeout_seconds,
                )
            response.raise_for_status()
            data = response.json()
            text = self._extract_text_from_response_payload(data)
            if not text:
                logger.warning("Grok response payload had no output text.")
                return None
            return text
        except requests.HTTPError as e:
            response_text = ""
            if e.response is not None:
                response_text = e.response.text[:500]
            logger.error("Grok HTTP error: %s response=%s", e, response_text)
            return None
        except Exception as e:
            logger.error("Grok request failed: %s", e)
            return None

    def _is_reply_usable(self, reply: str) -> bool:
        if not reply:
            return False
        if len(reply) > self.max_reply_chars or len(reply) < 15:
            return False
        lower = reply.lower()
        if any(phrase in lower for phrase in self.BANNED_PHRASE_SNIPPETS):
            return False

        if re.search(r'(i|my|me) (blew|wiped|lost|chased|logged|saved|entered|finished|did).*?(account|eval|trade|setup|last week|once)', lower):
            return False
        if re.search(r'(blew|wiped|lost) .*?(account|eval|trade|setup)', lower):
            return False

        if "http" in lower or "t.co" in lower or "#" in reply:
            return False
        if "-" in reply or "–" in reply or "—" in reply:
            return False
        return True

    def _pick_best_reply(self, options: List[Dict[str, Any]], best_index: Optional[int]) -> Optional[str]:
        if not options:
            return None

        top_reply = None
        top_score = -10_000.0

        for idx, option in enumerate(options):
            reply = option["reply"]
            angle = option["angle"]
            lower = reply.lower()

            score = (
                option["hook_strength_1to5"] * 1.8 +
                option["human_sounding_1to5"] * 3.2 +
                option["specificity_1to5"] * 1.6 +
                option["conversational_pull_1to5"] * 2.1
            )

            if angle in ("contrarian", "sarcasm", "roast"):
                score += 1.1
            if angle == "question":
                score -= 0.3
            if 40 <= len(reply) <= 140:
                score += 0.5
            if reply[0].islower() or "..." in reply:
                score += 0.45

            if re.search(r'(i|my|me) (blew|wiped|lost|chased|logged|saved|entered|finished|did).*?(account|eval|trade|setup|last week|once)', lower) or \
               re.search(r'(blew|wiped|lost) .*?(account|eval|trade|setup)', lower):
                score -= 3.0

            if option["brand_mention"]:
                score -= 0.4

            if best_index is not None and idx == best_index:
                score += 0.45

            if score > top_score:
                top_score = score
                top_reply = reply

        return top_reply

    async def generate_reply(self, tweet_text: str, user_handle: str, lane_name: str = "journal_intent") -> str:
        prompt = self._build_generation_prompt(
            tweet_text=tweet_text,
            user_handle=user_handle,
            lane_name=lane_name,
        )
        try:
            response_text = await asyncio.to_thread(self._call_grok_responses_api, prompt)
            if not response_text:
                return None

            options, best_index = self._parse_options(response_text)
            selected = self._pick_best_reply(options, best_index)

            if selected:
                return selected

            fallback = self._sanitize_reply(response_text)
            return fallback if self._is_reply_usable(fallback) else None
        except Exception as e:
            logger.error("Grok generation failed: %s", e)
            return None
