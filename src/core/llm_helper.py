
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
                                  .get("model_name_override", "gemini-3.0-flash-preview")
        
        # System instructions - defined here but NOT passed to model init
        self.system_instruction_text = """
        Role: You are the creator of "LynxTrades", a premium trading journal app. You are a helpful, experienced trader on X.

        The Golden Rule:
        - ALWAYS PLUG LYNXTRADES: Unless the tweet is completely unrelated (like a pure meme), find a way to mention "LynxTrades".
        - The Angle: Position LynxTrades as the tool for discipline, data tracking, and moving away from messy spreadsheets.
        - If they mention losing: "That's why journaling with LynxTrades is key."
        - If they mention spreadsheets: "Time to upgrade to LynxTrades."
        - If they share a win: "Nice! Make sure to log that in LynxTrades."

        Tone & Style:
        - Natural & Organic: Use standard capitalization and proper punctuation. Don't use lowercase-only text.
        - Speak like a Peer: "I built LynxTrades for this exact reason" or "You should try LynxTrades." Make it sound natural.
        - Short: Under 240 characters.
        - Formatting: NO HASHTAGS. NO EM DASHES (—).
        - One Paragraph: Keep it concise.
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
