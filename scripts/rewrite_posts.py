"""
Rewrite unposted tweets to avoid X spam filter detection.

Key changes:
1. Vary formatting (avoid repetitive bullet patterns)
2. Shorten posts (aim for 180-220 chars when possible)
3. Vary URL placement or omit entirely
4. Make language more conversational
5. Avoid formulaic marketing patterns
"""

import json
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# User specified model
model = genai.GenerativeModel("gemini-3.0-flash-preview")

POSTS_FILE = Path("data/posts.json")
BACKUP_FILE = Path("data/posts_backup.json")

REWRITE_PROMPT = """You are rewriting a tweet to avoid X/Twitter spam detection while keeping the core message.

ORIGINAL TWEET:
{content}

REWRITE RULES:
1. Keep it under 240 characters (aim for 150-220)
2. NO bullet point lists (→, •, -, ✓, etc.) - use flowing prose instead
3. Make it sound like a real person, not marketing copy
4. If the original has "lynxtrades.com", only include it 50% of the time, and vary placement
5. Avoid repetitive patterns like "X vs Y" or "Thing 1. Thing 2. Thing 3."
6. Use contractions (don't, can't, won't)
7. Be casual and conversational
8. Keep the core message/insight but rephrase it creatively
9. Don't use emojis excessively - max 1 or 0

IMPORTANT: Output ONLY the rewritten tweet text, nothing else. No quotes around it.
"""

def load_posts():
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posts(data):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def backup_posts(data):
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def needs_rewrite(content):
    """Check if the post needs rewriting based on spam-trigger patterns."""
    triggers = [
        "→",  # Arrow bullets
        "•",  # Bullet points  
        "✓",  # Check marks
        "✗",  # X marks
        "-\n",  # Dash list items
        ":\n→",  # Colon followed by arrow list
        ":\n•",  # Colon followed by bullet list
        ":\n-",  # Colon followed by dash list
        "\n1.",  # Numbered lists
        "\n2.",
        "\n3.",
    ]
    
    # Check for long formatted posts with lists
    has_trigger = any(trigger in content for trigger in triggers)
    is_long = len(content) > 220
    has_url = "lynxtrades.com" in content.lower()
    
    # Rewrite if it has list formatting or is promotional + long
    return has_trigger or (is_long and has_url)

def rewrite_content(content, post_id):
    """Use Gemini to rewrite the content."""
    try:
        prompt = REWRITE_PROMPT.format(content=content)
        response = model.generate_content(prompt)
        new_content = response.text.strip()
        
        # Remove any quotes that might have been added
        if new_content.startswith('"') and new_content.endswith('"'):
            new_content = new_content[1:-1]
        if new_content.startswith("'") and new_content.endswith("'"):
            new_content = new_content[1:-1]
            
        print(f"  [OK] Post #{post_id}: {len(content)} -> {len(new_content)} chars")
        return new_content
    except Exception as e:
        print(f"  [FAIL] Post #{post_id}: {e}")
        return content  # Return original if rewrite fails

def main():
    print("=" * 60)
    print("Tweet Rewriter - Using Gemini 3.0 Flash Preview")
    print("=" * 60)
    
    # Load and backup
    data = load_posts()
    backup_posts(data)
    
    unposted = [p for p in data["posts"] if not p.get("posted", False)]
    needs_work = [p for p in unposted if needs_rewrite(p["content"])]
    
    print(f"[INFO] Posts needing rewrite: {len(needs_work)}")
    
    if not needs_work:
        print("[OK] No posts need rewriting!")
        return
    
    # Rewrite posts
    rewritten_count = 0
    for i, post in enumerate(needs_work):
        print(f"[{i+1}/{len(needs_work)}] Rewriting post #{post['id']}...")
        
        original = post["content"]
        new_content = rewrite_content(original, post["id"])
        
        # Update if changed
        if new_content != original:
            for p in data["posts"]:
                if p["id"] == post["id"]:
                    p["content"] = new_content
                    p["original_content"] = original
                    rewritten_count += 1
                    break
        
        time.sleep(1.0) # Slower rate limit just in case
    
    save_posts(data)
    print("=" * 60)
    print(f"[DONE] Rewrote {rewritten_count} posts")

if __name__ == "__main__":
    main()
