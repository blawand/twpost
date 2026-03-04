# LynxTrades Twitter Automation

A robust Twitter/X automation bot designed for reliable high-performance. It uses the **Official X API** (via Tweepy) for posting and engagement search/replies, with optional **Twikit** fallback for local/manual runs.

## Features

- **Hybrid Architecture**:
  - **Posting**: Uses Official X API (v2) for 100% reliability.
  - **Engagement**: Uses Official X API search/replies/likes by default; Twikit is optional fallback.
- **AI-Powered**: Uses **xAI Grok (Responses API)** for intelligent reply generation and persona management.
- **Scheduled Posting**: Automatically posts queued content from `data/posts.json`.
- **Dual-Lane Engagement Mode**:
  - **Journal Intent Lane**: Targets high-intent trading journal/discipline conversations.
  - **Broad Trending Lane**: Targets broader economics/business/trading topics and prioritizes posts with stronger engagement signals.
- **Persistence**: Tracks posted tweets and engagement history to avoid duplicates.

## Project Structure

```text
twitter-bot/
├── data/                # Data storage
│   ├── posts.json       # Scheduled tweets DB
│   ├── cookies.json     # Twikit authentication (Sensitive - Git Ignored)
│   ├── posted_tracker.json  # History of posted IDs (Public - Git Tracked)
│   └── engagement_tracker.json # History of replies (Public - Git Tracked)
├── scripts/
│   ├── check_limits.py   # Check post length constraints
│   ├── export_cookies.py # Export cookies for GitHub Secrets
│   └── post_now.py       # Manual posting helper
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

- `XAI_API_KEY`

**Optional for Engagement (Twikit fallback only):**

- `TWITTER_COOKIES` (JSON string) OR `TWITTER_USERNAME`/`PASSWORD`

### 3. Optional Authentication (Twikit)

Twikit is no longer required for CI engagement runs. If you still want local fallback via Twikit, inject your browser cookies.

1. Populate `data/cookies.json` directly from your browser session cookies.
2. OR set `TWITTER_COOKIES` in your environment / GitHub secrets.
3. Optional: run `python scripts/export_cookies.py` to print the current local cookie JSON for secrets setup.

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

Optional tuning via environment variables:

- `ENGAGEMENT_GENERAL_WEIGHT` (default `0.45`): share of runs that prioritize the broad-trending lane first.
- `ENGAGEMENT_SEARCH_COUNT` (default `15`): tweets fetched per lane query.
- `ENGAGEMENT_TOP_POOL` (default `3`): top scored candidates sampled from.
- `ENGAGEMENT_MAX_REPLIES` (default `1`): max replies per run.
- `ENGAGEMENT_REQUIRE_FRESH_TWEETS` (default `true`): skip tweets when created-at is unavailable or too old.
- `ENGAGEMENT_MAX_TWEET_AGE_MINUTES` (default `180`): max tweet age allowed for engagement.
- `ENGAGEMENT_USE_TRENDS` (default `true`): use live X trends for the broad lane query source.
- `ENGAGEMENT_TREND_CATEGORIES` (default `trending,news`): trend categories to pull from (`trending`, `for-you`, `news`, `sports`, `entertainment`).
- `ENGAGEMENT_TRENDS_COUNT` (default `20`): number of trends fetched per category.
- `ENGAGEMENT_TREND_QUERIES` (default `6`): max relevant trend topics kept per run.
- `ENGAGEMENT_EXCLUDED_HANDLES` (default `grok`): comma-separated handles to never reply to (supports values with or without `@`).
- `ENGAGEMENT_MIN_ENGAGEMENT_OR_VIEWS` (default `20`): require at least this many total engagements (`likes + replies + reposts + quotes`) or views before engaging.
- `ENGAGEMENT_REPLY_OPTION_COUNT` (default `1`): number of candidate replies generated before auto-picking.
- `ENGAGEMENT_REPLY_MAX_CHARS` (default `180`): hard cap for generated reply length.
- `ENGAGEMENT_PREFER_OFFICIAL_SEARCH` (default `true`): when `true`, search via official API before Twikit.
- `ENGAGEMENT_DISABLE_TWIKIT` (default `false`): when `true`, disables Twikit entirely.
- `XAI_TIMEOUT_SECONDS` (default `180`): HTTP timeout for each Grok request.
- `XAI_API_BASE_URL` (default `https://api.x.ai/v1`): override xAI endpoint (useful for regional routing/proxies).
- `XAI_DISABLE_ENV_PROXY` (default `false`): when `true`, ignores `HTTP_PROXY`/`HTTPS_PROXY` vars for Grok calls.
- `PUBLISH_POST_MAX_ATTEMPTS` (default `4`): max attempts for posting a tweet before failing the run.
- `PUBLISH_RETRY_BASE_SECONDS` (default `1.5`): exponential backoff base delay for retryable post errors.
- `PUBLISH_RETRY_MAX_SECONDS` (default `20`): cap for retry delay between post attempts.

## Deployment (GitHub Actions)

The repository is configured for GitHub Actions.

1. **Secrets**: Go to Settings > Secrets and add:
   - `X_API_KEY`... (All X credentials)
   - `XAI_API_KEY`
   - Engagement workflow is configured with `ENGAGEMENT_REPLY_OPTION_COUNT=1` for single-output replies.
   - Engagement workflow defaults to `ENGAGEMENT_DISABLE_TWIKIT=true` to avoid Cloudflare blocking on GitHub runner IPs.
2. **Persistence**: The workflow is configured to commit `data/posted_tracker.json` and `engagement_tracker.json` back to the repo, so your bot remembers what it has done.
