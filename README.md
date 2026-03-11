# LynxTrades Twitter Automation

A Twitter/X automation bot for the [@lynxtradesapp](https://x.com/lynxtradesapp) trading journal. Uses **cookie-based GraphQL posting** (via [twitter-cli](https://github.com/jackwener/twitter-cli)) for reliable tweet publishing, and a hybrid **Twikit + Official API + GraphQL** stack for AI-powered engagement.

## Features

- **GraphQL Posting**: Cookie-based posting via Twitter's internal GraphQL API — bypasses the broken official API free tier.
- **AI-Powered Engagement**: Uses **xAI Grok** to generate contextual replies to relevant trading conversations.
- **Scheduled Posting**: Automatically posts queued content from `data/posts.json`.
- **Dual-Lane Engagement**:
  - **Journal Intent Lane**: Targets trading journal, discipline, and psychology conversations.
  - **Broad Trending Lane**: Targets economics, business, and market discussions with higher engagement signals.
- **Persistence**: Tracks posted tweets and engagement history to avoid duplicates.

## Project Structure

```text
twpost/
├── data/                    # Data storage
│   ├── posts.json           # Scheduled tweets DB
│   ├── cookies.json         # Twikit authentication (Git Ignored)
│   ├── posted_tracker.json  # History of posted IDs
│   └── engagement_tracker.json  # History of replies
├── scripts/
│   ├── post_now.py          # Manual posting helper
│   └── engage_now.py        # Manual engagement helper
├── src/
│   ├── main.py              # Entry point
│   ├── core/
│   │   ├── graphql_client_manager.py  # GraphQL posting client (twitter-cli)
│   │   ├── client_manager.py          # Twikit client (engagement search)
│   │   ├── tweepy_client_manager.py   # Official API client (fallback)
│   │   ├── config_loader.py           # Settings loader
│   │   └── llm_helper.py             # xAI Grok integration
│   └── features/
│       ├── publisher.py     # Tweet publishing logic
│       └── engagement.py    # AI engagement logic
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

Create a `.env` file with these variables:

**Required for Posting (GraphQL — cookie-based):**

- `TWITTER_COOKIES` — JSON string of your browser cookies from x.com (must include `auth_token` and `ct0`)

**Required for AI Engagement:**

- `XAI_API_KEY` — xAI Grok API key

**Optional — Official API (fallback for engagement):**

- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `X_BEARER_TOKEN`

**Optional — Twikit (engagement search):**

- `TWITTER_USERNAME`, `TWITTER_PASSWORD`, `TWITTER_EMAIL`

### 3. Cookie Setup

Extract your cookies from Chrome DevTools:

1. Log in to x.com in Chrome
2. Open DevTools (`F12`) → Application → Cookies → `https://x.com`
3. Copy all cookie name/value pairs into a JSON string
4. Set `TWITTER_COOKIES` in your `.env` (see `.env` for format)

## Usage

### Post a Tweet

```bash
# Post next scheduled tweet from posts.json
python scripts/post_now.py

# Post custom text
python scripts/post_now.py "Your tweet text"

# Via main entrypoint
python src/main.py publisher
python src/main.py post "Your tweet text"
```

### Run Engagement (AI Reply)

```bash
python src/main.py engage

# With dry run (generates reply but doesn't post)
python scripts/engage_now.py --dry-run
```

### Engagement Tuning

Key environment variables:

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
| `ENGAGEMENT_PREFER_OFFICIAL_SEARCH` | `true` | Prefer official API for search |
| `ENGAGEMENT_DISABLE_TWIKIT` | `false` | Disable Twikit entirely |
| `ENGAGEMENT_REPLY_MAX_CHARS` | `180` | Max reply character length |
| `PUBLISH_POST_MAX_ATTEMPTS` | `4` | Max posting retry attempts |

## Deployment (GitHub Actions)

### Secrets Required

Go to Settings > Secrets and add:

- `TWITTER_COOKIES` — **Required** for posting and engagement replies/likes
- `XAI_API_KEY` — Required for AI engagement
- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `X_BEARER_TOKEN` — Optional fallback
- `TWITTER_USERNAME`, `TWITTER_PASSWORD`, `TWITTER_EMAIL` — Optional for Twikit search

### How It Works

- **`tweet.yml`**: Runs 5x/day on a schedule. Posts the next tweet from `posts.json` using the GraphQL client and commits the updated tracker.
- **`engage.yml`**: Runs every 20 minutes. Searches for relevant tweets, generates AI replies, and posts them.
- Both workflows commit tracker files back to the repo for state persistence.

> **Note**: Cookie-based auth tokens expire periodically. If posting starts failing, re-extract your cookies from the browser and update the `TWITTER_COOKIES` secret.
