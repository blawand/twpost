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
    """Handles AI interactions using the xAI Grok Responses API."""

    BANNED_PHRASE_SNIPPETS = (
        "totally agree",
        "100%",
        "couldn't agree more",
        "absolutely",
        "spot on",
        "insightful",
        "great point",
        "that's why journaling",
        "this is key",
        "game changer",
        "great post",
        "love this",
        "love the",
        "if you're looking for",
        "lynxtrades handles",
    )

    def __init__(self, settings):
        self.settings = settings
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.error("XAI_API_KEY not found in environment variables.")
            raise ValueError("Missing XAI_API_KEY")

        self.model_name = settings.get("twitter_automation", {}) \
                                  .get("action_config", {}) \
                                  .get("llm_settings_for_reply", {}) \
                                  .get("model_name_override", "grok-4-1-fast-reasoning")
        self.api_base_url = os.getenv("XAI_API_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        self.request_timeout_seconds = max(10, self._read_int_env("XAI_TIMEOUT_SECONDS", 180))
        self.disable_env_proxy = self._read_bool_env("XAI_DISABLE_ENV_PROXY", False)
        self.max_reply_chars = max(120, self._read_int_env("ENGAGEMENT_REPLY_MAX_CHARS", 180))
        self.reply_option_count = min(8, max(3, self._read_int_env("ENGAGEMENT_REPLY_OPTION_COUNT", 6)))

        self.system_instruction_text = """
        You write replies for @lynxtradesapp on X.

        Objective priority:
        1) sound human and conversational
        2) earn a reaction (reply, like, profile visit)
        3) mention LynxTrades only when clearly relevant

        Voice:
        - casual trader voice, internet native, lightly gen z, not cringe
        - short and direct, no corporate support tone
        - lowercase is allowed; forced slang is not
        - plain text only, no markdown, no hashtags, no links

        Style rules:
        - 1 to 2 short sentences
        - max 180 characters
        - reference one specific detail from the source tweet
        - add one fresh thought (opinion, lesson, contrarian point, or quick question)
        - avoid generic empathy openers

        Brand policy:
        - do not force LynxTrades mentions
        - mention only when the source tweet is about journaling, risk rules, discipline, or analytics workflow
        - never use hard CTA language

        Hard bans:
        - totally agree, 100%, couldn't agree more, absolutely, spot on, insightful, great point
        - that's why journaling, this is key, game changer, great post, love this, love the
        - if you're looking for, LynxTrades handles
        """

        try:
            project_root = Path(__file__).resolve().parent.parent.parent
            features_path = project_root / "features.md"
            features_context = ""

            if features_path.exists():
                try:
                    with open(features_path, "r", encoding="utf-8") as f:
                        features_context = f.read()
                    logger.info("Loaded features.md context.")
                except Exception as e:
                    logger.warning("Could not read features.md: %s", e)
            else:
                logger.warning("features.md not found at %s", features_path)

            if features_context:
                self.system_instruction_text += f"\n\nCONTEXT - LYNXTRADES FEATURES:\n{features_context}\n"

            logger.info(
                "AI initialized with Grok model=%s base_url=%s",
                self.model_name,
                self.api_base_url,
            )
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
            Lane goal: broad_trending
            - Source is from broader market and business conversations.
            - Prioritize punchy takes and debate-friendly phrasing.
            - Contrarian or sharp question angles are preferred when natural.
            """

        return """
        Lane goal: journal_intent
        - Source is likely about journaling, discipline, risk, or trading psychology.
        - Prioritize practical insight from lived trading experience.
        - Mention LynxTrades only if it naturally resolves the exact pain point.
        """

    def _build_generation_prompt(self, tweet_text: str, user_handle: str, lane_name: str) -> str:
        lane_instruction = self._lane_instruction(lane_name)
        return (
            f"{lane_instruction}\n\n"
            "Source tweet context:\n"
            f"Lane: {lane_name}\n"
            f"Tweet from @{user_handle}: \"{tweet_text}\"\n\n"
            f"Generate {self.reply_option_count} reply candidates.\n"
            "Output JSON only (no markdown/code fences) with this exact schema:\n"
            "{\n"
            "  \"options\": [\n"
            "    {\n"
            "      \"reply\": \"...\",\n"
            "      \"angle\": \"agree_extend|contrarian|pain_mirror|lesson|question\",\n"
            "      \"brand_mention\": true,\n"
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

    def _is_reply_usable(self, reply: str) -> bool:
        if not reply:
            return False
        if len(reply) > self.max_reply_chars:
            return False
        lower = reply.lower()
        if any(phrase in lower for phrase in self.BANNED_PHRASE_SNIPPETS):
            return False
        if "http://" in lower or "https://" in lower or "t.co/" in lower:
            return False
        if "#" in reply:
            return False
        if lower.startswith("hello ") or lower.startswith("hey "):
            return False
        return True

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

    def _pick_best_reply(self, options: List[Dict[str, Any]], best_index: Optional[int]) -> Optional[str]:
        if not options:
            return None

        top_reply = None
        top_score = -10_000.0
        for idx, option in enumerate(options):
            reply = option["reply"]
            score = (
                (option["hook_strength_1to5"] * 2.1)
                + (option["human_sounding_1to5"] * 2.6)
                + (option["specificity_1to5"] * 1.7)
                + (option["conversational_pull_1to5"] * 1.8)
            )

            if option["angle"] == "question":
                score += 0.25
            if "?" in reply:
                score += 0.2
            if option["brand_mention"]:
                score -= 0.35
            if 60 <= len(reply) <= self.max_reply_chars:
                score += 0.25
            if best_index is not None and idx == best_index:
                score += 0.35

            if score > top_score:
                top_score = score
                top_reply = reply

        return top_reply

    async def generate_reply(self, tweet_text: str, user_handle: str, lane_name: str = "journal_intent") -> str:
        """Generates reply options and auto-picks the best one."""

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
            if self._is_reply_usable(fallback):
                return fallback
            return None
        except Exception as e:
            logger.error("Grok generation failed: %s", e)
            return None
