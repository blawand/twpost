# LynxTrades Twitter Automation

A robust, hybrid Twitter/X automation bot designed for reliable high-performance. It combines the **Official X API** (via Tweepy) for safe, reliable posting and the **Twikit** library (UI automation) for advanced engagement features like searching and reading.

## Features
- **Hybrid Architecture**:
    - **Posting**: Uses Official X API (v2) for 100% reliability.
    - **Engagement**: Uses `twikit` to search and read tweets (bypassing expensive API tiers).
- **AI-Powered**: Uses **Google Gemini 2.0 Flash** for intelligent reply generation and persona management.
- **Scheduled Posting**: Automatically posts queued content from `data/posts.json`.
- **Engagement Mode**: Intelligently searches for relevant keywords (e.g., "trading journal") and replies with helpful, context-aware advice promoting LynxTrades.
- **Persistence**: Tracks posted tweets and engagement history to avoid duplicates.

## Project Structure
```text
twitter-bot/
├── config/              # Configuration files
│   ├── settings.json    # AI models, delays, and bot settings
│   └── accounts.json    # (Optional) Multi-account setup
├── data/                # Data storage
│   ├── posts.json       # Scheduled tweets DB
│   ├── cookies.json     # Twikit authentication (Sensitive - Git Ignored)
│   ├── posted_tracker.json  # History of posted IDs (Public - Git Tracked)
│   └── engagement_tracker.json # History of replies (Public - Git Tracked)
├── scripts/
│   ├── setup_cookies.py # Helper to extract browser cookies
│   └── export_cookies.py # Export cookies for GitHub Secrets
├── src/                 # Source code
│   ├── main.py          # Entry point
│   ├── core/            # Auth managers (Tweepy & Twikit)
│   └── features/        # Business logic
└── .env.example         # Template for environment variables
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file (copy from `.env.example`) and fill in your keys:

**Required for Posting (Official API):**
- `X_API_KEY`, `X_API_SECRET`
- `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `X_BEARER_TOKEN`

**Required for AI:**
- `GEMINI_API_KEY`

**Required for Engagement (Twikit):**
- `TWITTER_COOKIES` (JSON string) OR `TWITTER_USERNAME`/`PASSWORD`

### 3. Authentication (Twikit)
For engagement features, the bot needs to "log in" as a user. The most reliable method is to inject your browser cookies.
1. Run `python scripts/setup_cookies.py` to manually input cookies from your browser.
2. OR populate `data/cookies.json` directly.

## Usage

### Run the Bot (Auto-Posting)
Checks `data/posts.json` for the next scheduled tweet and posts it using the Official API.
```bash
python src/main.py post "Your tweet text" [optional_image_path]
# OR for automated runs:
python src/main.py publisher
```

### Run Engagement (AI Reply)
Searches for relevant tweets and replies using the AI persona.
```bash
python src/main.py engage
```

## Deployment (GitHub Actions)

The repository is configured for GitHub Actions.
1. **Secrets**: Go to Settings > Secrets and add:
    - `TWITTER_COOKIES` (Run `python scripts/export_cookies.py` to get the value)
    - `X_API_KEY`... (All X credentials)
    - `GEMINI_API_KEY`
2. **Persistence**: The workflow is configured to commit `data/posted_tracker.json` and `engagement_tracker.json` back to the repo, so your bot remembers what it has done.
