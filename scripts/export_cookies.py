"""
Export Cookies for GitHub Secrets

This script reads your local cookies.json file and prints exactly what you need
to paste into your GitHub Secret 'TWITTER_COOKIES'.
"""

import json
from pathlib import Path
import os

def export_cookies():
    # Helper to find project root from this script's location
    project_root = Path(__file__).resolve().parent.parent
    cookies_path = project_root / 'data' / 'cookies.json'
    
    if not cookies_path.exists():
        print(f"❌ Error: Cookies file not found at {cookies_path}")
        print("   Please run the bot locally once to generate cookies first.")
        return

    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies_data = f.read()
            
            # Verify it's valid JSON
            json.loads(cookies_data)
            
            print("\n✅ Cookies found! Copy the line below (everything between the lines):")
            print("-" * 50)
            print(cookies_data)
            print("-" * 50)
            print("\n👉 Go to GitHub -> Settings -> Secrets and variables -> Actions")
            print("👉 Create a new repository secret named: TWITTER_COOKIES")
            print("👉 Paste the content above as the value.")
            
    except Exception as e:
        print(f"❌ Error reading cookies: {e}")

if __name__ == "__main__":
    export_cookies()
