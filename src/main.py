
import logging
import asyncio
import sys
from dotenv import load_dotenv
from core.config_loader import ConfigLoader
from core.tweepy_client_manager import TweepyClientManager
from core.client_manager import TwikitClientManager
from features.publisher import TwitterPublisher
from features.engagement import EngagementManager
from utils.logger import setup_logger

logger = logging.getLogger(__name__)

def run():
    # 1. Setup
    load_dotenv()
    setup_logger()
    logger.info("🤖 Twitter Automation AI Starting...")
    
    config_loader = ConfigLoader()
    
    # 2. Determine Mode & Initialize Appropriate Client
    command = "publisher" # default
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

    if command == "engage":
        logger.info("▶️ Starting Engagement Mode (Hybrid: Twikit + Official API)...")
        async def run_engagement():
            # Initialize Twikit for searching tweets
            twikit_manager = TwikitClientManager()
            await twikit_manager.initialize_client()
            twikit_client = twikit_manager.get_client()
            
            # Initialize Tweepy for posting replies (bypasses Error 226)
            tweepy_client = None
            try:
                tweepy_manager = TweepyClientManager()
                tweepy_manager.initialize_client()
                tweepy_client = tweepy_manager.get_client()
                logger.info("✅ Official API client ready for posting replies.")
            except Exception as e:
                logger.warning(f"⚠️ Official API not available, falling back to Twikit: {e}")
            
            engagement = EngagementManager(twikit_client, config_loader, tweepy_client)
            await engagement.run()
        
        asyncio.run(run_engagement())
        
    elif command == "post":
        # Initialize Tweepy for Posting
        client_manager = TweepyClientManager()
        try:
            client_manager.initialize_client()
            client = client_manager.get_client()
            api = client_manager.get_api()
        except Exception as e:
            logger.critical(f"❌ Core initialization failed: {e}")
            return

        publisher = TwitterPublisher(client, api, config_loader)
        
        if len(sys.argv) < 3:
            logger.error("❌ Missing tweet text. Usage: python src/main.py post \"Your tweet\"")
            return
        tweet_text = sys.argv[2]
        image_path = sys.argv[3] if len(sys.argv) > 3 else None
        publisher.post_single(tweet_text, image_path)

    elif command == "publisher":
         # Initialize Tweepy for Publisher
        client_manager = TweepyClientManager()
        try:
            client_manager.initialize_client()
            client = client_manager.get_client()
            api = client_manager.get_api()
        except Exception as e:
            logger.critical(f"❌ Core initialization failed: {e}")
            return

        publisher = TwitterPublisher(client, api, config_loader)
        logger.info("▶️ Running Publisher Mode...")
        publisher.run()

    else:
        logger.error(f"❌ Unknown command: {command}")
    
    logger.info("🏁 Workflow complete.")

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user.")
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}", exc_info=True)
