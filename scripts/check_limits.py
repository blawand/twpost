import json
import re
from pathlib import Path

def get_tweet_length(text):
    # Twitter URL counting: Any URL is counted as 23 characters
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    
    # Remove URLs from text to count remaining chars
    text_no_urls = url_pattern.sub('', text)
    
    # Basic length + (number of URLs * 23)
    length = 0
    for char in text_no_urls:
        if ord(char) > 127: # Basic non-ASCII check (conservative)
            length += 2
        else:
            length += 1
            
    length += (len(urls) * 23)
    return length

def check_posts():
    # Determine path relative to this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    posts_file = project_root / "data" / "posts.json"
    
    if not posts_file.exists():
        print(f"❌ posts.json not found at {posts_file}")
        return

    with open(posts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    over_limit = []
    for post in data.get("posts", []):
        content = post.get("content", "")
        # length = get_tweet_length(content) # Use calculated length
        
        # Twitter's strict length is 280. 
        # But let's use the function we wrote.
        length = get_tweet_length(content)
        
        if length > 280:
            over_limit.append({
                "id": post["id"],
                "length": length,
                "content": content
            })

    if over_limit:
        print(f"⚠️ Found {len(over_limit)} posts over the 280-character limit:")
        for item in over_limit:
            print(f"\nID: {item['id']} (Length: {item['length']})")
            print(f"Content: {item['content']}")
    else:
        print("✅ All posts are within the 280-character limit.")

if __name__ == "__main__":
    check_posts()
