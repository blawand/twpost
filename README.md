# LynxTrades Twitter Automation

A Twitter/X automation bot for [@lynxtradesapp](https://x.com/lynxtradesapp). Uses cookie-based GraphQL via [twitter-cli](https://github.com/jackwener/twitter-cli) for all Twitter operations — posting, search, engagement, and trends.

## Features

- **Long Tweet Support**: Twitter Premium notetweet support for tweets >280 characters
- **Image Uploads**: Attach images to tweets via chunked media upload
- **AI-Powered Engagement**: Uses xAI Grok to generate contextual replies to relevant trading conversations
- **Scheduled Posting**: Automatically posts queued content from `data/posts.json`
- **Dual-Lane Engagement**:
  - **Journal Intent Lane**: Targets trading journal, discipline, and psychology conversations
  - **Broad Trending Lane**: Targets economics, business, and market discussions with live trends
- **Persistence**: Tracks posted tweets and engagement history to avoid duplicates
- **Auto-Refreshing Query IDs**: twitter-cli automatically refreshes stale GraphQL query IDs from live JS bundles

## Project Structure

```text
twpost/
├── data/                    # Data storage
│   ├── posts.json           # Scheduled tweets
│   ├── posted_tracker.json  # Post history
│   └── engagement_tracker.json  # Reply history
├── scripts/
│   ├── post_now.py          # Manual posting
│   └── engage_now.py        # Manual engagement
├── src/
│   ├── main.py              # Entry point
│   ├── core/
│   │   ├── premium_client.py  # Extended twitter-cli client (long tweets, media, trends)
│   │   └── llm.py             # xAI Grok integration
│   ├── features/
│   │   ├── publisher.py     # Tweet publishing logic
│   │   └── engagement.py    # AI engagement logic
│   └── utils/
│       └── logger.py        # Logging setup
├── .github/workflows/
│   ├── tweet.yml            # Scheduled posting workflow
│   └── engage.yml           # Engagement workflow
└── .env                     # Environment variables (Git Ignored)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

**Required for Posting:**

- `TWITTER_COOKIES` — JSON string of your browser cookies from x.com (must include `auth_token` and `ct0`)

**Required for AI Engagement:**

- `XAI_API_KEY` — xAI Grok API key

### 3. Cookie Setup

1. Log in to x.com in Chrome
2. Open DevTools (`F12`) > Application > Cookies > `https://x.com`
3. Copy all cookie name/value pairs into a JSON string
4. Set `TWITTER_COOKIES` in your `.env`

## Usage

### Post a Tweet

```bash
# Post next scheduled tweet from posts.json
python scripts/post_now.py

# Post custom text
python scripts/post_now.py "Your tweet text"

# Post with image
python scripts/post_now.py "Your tweet text" path/to/image.jpg

# Via main entrypoint
python src/main.py publisher
python src/main.py post "Your tweet text"
python src/main.py post "Your tweet text" path/to/image.jpg
```

### Run Engagement (AI Reply)

```bash
python src/main.py engage

# With dry run (generates reply but doesn't post)
python scripts/engage_now.py --dry-run
```

### Engagement Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGAGEMENT_MAX_REPLIES` | `1` | Max replies per run |
| `ENGAGEMENT_SEARCH_COUNT` | `15` | Tweets fetched per search query |
| `ENGAGEMENT_DRY_RUN` | `false` | Generate replies without posting |
| `ENGAGEMENT_REQUIRE_FRESH_TWEETS` | `true` | Skip old tweets |
| `ENGAGEMENT_MAX_TWEET_AGE_MINUTES` | `180` | Max tweet age for engagement |
| `ENGAGEMENT_USE_TRENDS` | `true` | Use live X trends for broad lane |
| `ENGAGEMENT_GENERAL_WEIGHT` | `0.45` | Weight for broad-trending lane |
| `ENGAGEMENT_EXCLUDED_HANDLES` | `grok` | Handles to never reply to |
| `ENGAGEMENT_MIN_ENGAGEMENT_OR_VIEWS` | `20` | Minimum engagement threshold |
| `ENGAGEMENT_REPLY_MAX_CHARS` | `180` | Max reply character length |
| `PUBLISH_POST_MAX_ATTEMPTS` | `4` | Max posting retry attempts |

## Deployment (GitHub Actions)

### Secrets Required

- `TWITTER_COOKIES` — Required for all operations
- `XAI_API_KEY` — Required for AI engagement

### How It Works

- **`tweet.yml`**: Runs 5x/day on a schedule. Posts the next tweet from `posts.json` and commits the updated tracker.
- **`engage.yml`**: Runs every 20 minutes. Searches for relevant tweets, generates AI replies, and posts them.
- Both workflows commit tracker files back to the repo for state persistence.

> **Note**: Cookie-based auth tokens expire periodically. If posting starts failing, re-extract your cookies from the browser and update the `TWITTER_COOKIES` secret.
