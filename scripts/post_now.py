
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.config_loader import ConfigLoader
from core.tweepy_client_manager import TweepyClientManager
from features.publisher import TwitterPublisher
from utils.logger import setup_logger

logger = logging.getLogger("PostNow")

def main():
    # Setup
    load_dotenv()
    setup_logger()
    
    config_loader = ConfigLoader()
    client_manager = TweepyClientManager()
    
    try:
        client_manager.initialize_client()
        client = client_manager.get_client()
        api = client_manager.get_api()
        
        publisher = TwitterPublisher(client, api, config_loader)

        if len(sys.argv) < 2:
            logger.info("🔄 No text provided. Fetching next scheduled tweet from posts.json...")
            publisher.run()
        else:
            tweet_text = sys.argv[1]
            image_path = sys.argv[2] if len(sys.argv) > 2 else None
            publisher.post_single(tweet_text, image_path)
            
    except Exception as e:
        logger.error(f"❌ Failed to post: {e}")

if __name__ == "__main__":
    main()
