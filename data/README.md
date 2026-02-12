# Data directory

This directory contains the persistent state and configuration for the bot.

## Files

### 1. Content & Configuration
- **`posts.json`**: The database of tweets to be posted. This file IS tracked by git. Open it to add or modify your scheduled content.
- **`posted_tracker.json`**: Keeps track of which IDs from `posts.json` have already been published. This file IS tracked by git and updated automatically by the bot.

### 2. Engagement Persistence
- **`engagement_tracker.json`**: Stores IDs of tweets we have already replied to. Prevents spamming the same user twice. This file IS tracked by git.
  - Used by both engagement lanes (`journal_intent` + `broad_trending`).

### 3. Security (Critical)
- **`cookies.json`**: Stores the session cookies for the Twikit client (used for engagement reading).
    - ⚠️ **DANGER**: This file contains your active login session errors.
    - 🔒 **GIT IGNORED**: This file is correctly ignored by `.gitignore` and should NEVER be committed.
    - **CI/CD**: For GitHub Actions, we inject these values via the `TWITTER_COOKIES` secret.

## Usage
- **To add new posts**: Edit `posts.json`.
- **To reset the bot**: You can clear lists in `posted_tracker.json` or `engagement_tracker.json`, but verify you don't repost old content.
