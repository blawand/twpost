"""
Helper script to manually setup cookies.json for Twikit.
Run from the root or scripts folder.
"""

import json
from pathlib import Path

def setup_cookies():
    print("🍪 Manual Cookie Setup for Twikit")
    print("=" * 40)
    
    # Determine path relative to this script
    script_dir = Path(__file__).parent
    # Assuming script is in /scripts, data is in /data
    # If run from root, we need to be careful. 
    # Best to use absolute or relative to script location.
    project_root = script_dir.parent
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        print(f"❌ Data directory not found at {data_dir}. Creating it...")
        data_dir.mkdir(parents=True, exist_ok=True)
        
    output_file = data_dir / "cookies.json"

    print("Since automated login failed (Twitter changes endpoints often),")
    print("we need to copy 2 cookies from your logged-in browser.")
    print("\nInstructions:")
    print("1. Open Twitter/X in your browser (Chrome/Edge/Firefox).")
    print("2. Press F12 to open Developer Tools.")
    print("3. Go to the 'Application' tab (Chrome/Edge) or 'Storage' (Firefox).")
    print("4. Expand 'Cookies' -> 'https://twitter.com' or 'https://x.com'.")
    print("5. Find the values for 'auth_token' and 'ct0'.")
    
    print("\nPaste the values below:")
    auth_token = input("Enter 'auth_token' value: ").strip()
    ct0 = input("Enter 'ct0' value: ").strip()
    
    if not auth_token or not ct0:
        print("❌ Error: Both values are required!")
        return

    # Basic cookie structure
    cookies = {
        "auth_token": auth_token,
        "ct0": ct0
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)
        
    print(f"\n✅ Created {output_file.absolute()}")
    print("You can now run the bot using 'python src/main.py'")

if __name__ == "__main__":
    setup_cookies()
