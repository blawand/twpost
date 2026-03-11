
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to path so we can import modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.twitter_client import GraphQLClientManager
from features.publisher import TwitterPublisher
from utils.logger import setup_logger

logger = logging.getLogger("PostNow")

def main():
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)
    setup_logger()
    
    client_manager = GraphQLClientManager()
    
    try:
        client_manager.initialize_client()
        graphql_client = client_manager.get_client()
        
        publisher = TwitterPublisher(graphql_client)

        if len(sys.argv) < 2:
            logger.info("No text provided. Fetching next scheduled tweet from posts.json...")
            publisher.run()
        else:
            tweet_text = sys.argv[1]
            image_path = sys.argv[2] if len(sys.argv) > 2 else None
            publisher.post_single(tweet_text, image_path)
             
    except Exception as e:
        logger.error("Failed to post: %s", e)

if __name__ == "__main__":
    main()
