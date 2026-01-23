
import os
import logging
from google import genai
from google.genai import types
from pathlib import Path

logger = logging.getLogger(__name__)

class LLMHelper:
    """Handles AI interactions using Google Gen AI SDK."""
    
    def __init__(self, settings):
        self.settings = settings
        # Load API Key from ENV
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY not found in environment variables!")
            raise ValueError("Missing GEMINI_API_KEY")

        # Get model name from settings
        self.model_name = settings.get("twitter_automation", {}) \
                                  .get("action_config", {}) \
                                  .get("llm_settings_for_reply", {}) \
                                  .get("model_name_override", "gemma-3-27b-it")
        
        # System instructions - defined here but NOT passed to model init
        self.system_instruction_text = """
        You're a nice trader who built LynxTrades - a free trading journal app. You're replying to tweets on X.

        VOICE:
        - Sound like a real person, not a brand. Lowercase sometimes is fine. Sentence fragments are fine. Use proper grammar.
        - Be chill. Not enthusiastic. You've seen it all in the markets.
        - Don't be "helpful support". Be "helpful trader who found a better way".
        - PLAIN TEXT ONLY. NO MARKDOWN. NO *asterisks*, NO **bold**, NO _italics_.
        - NO hashtags.

        BANNED PHRASES (Instant reject if used):
        - "Totally agree" / "100%" / "Couldn't agree more" / "Absolutely" / "Spot on" / "Insightful" / "Great point"
        - "That's why journaling..." / "This is key" / "Game changer"
        - "Love this" / "Love the" / "Great post"
        - "messy spreadsheets"
        - Any variation of "I built LynxTrades to solve this" (too robotic)

        MENTIONING LYNXTRADES:
        - Only mention it if it DIRECTLY solves the specific pain point mentioned.
        - Keep it subtle. "This is why I made LynxTrades free" or "LynxTrades handles this".
        - Never "You should try..." or "Check out...".
        - If the tweet is just general trading chatter, just reply as a trader. No plug needed.

        RESPONSE STRUCTURE:
        - Max 180 characters. Short is better.
        - No "Hello" or "Hey". Just dive in.
        - Focus on ONE specific detail they mentioned.
        """

        try:
            # Load features.md context
            project_root = Path(__file__).resolve().parent.parent.parent
            features_path = project_root / 'features.md'
            features_context = ""
            
            if features_path.exists():
                try:
                    with open(features_path, 'r', encoding='utf-8') as f:
                        features_context = f.read()
                    logger.info("📚 Loaded features.md context")
                except Exception as e:
                    logger.warning(f"⚠️ Could not read features.md: {e}")
            else:
                logger.warning(f"⚠️ features.md not found at {features_path}")

            # Append features context to system instructions
            if features_context:
                self.system_instruction_text += f"\n\nCONTEXT - LYNXTRADES FEATURES:\n{features_context}\n"

            # Initialize client
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"🧠 AI Initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI: {e}")
            raise

    async def generate_reply(self, tweet_text: str, user_handle: str) -> str:
        """Generates a reply based on the helpful trader persona."""
        
        # Merge system instruction into the prompt manually
        full_prompt = f"{self.system_instruction_text}\n\nInput Context:\nTweet from @{user_handle}: \"{tweet_text}\"\n\nTask: Write a single reply."
        
        try:
            # Direct generation
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            
            if response and response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            logger.error(f"⚠️ Gemini Generation failed: {e}")
            return None
