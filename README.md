# YouTube Shorts Agent

Generates and posts one AI-produced YouTube Short per day, then uses each video's
real analytics to steer what tomorrow's video is about. See
`config.yaml` for content pillars, budget cap, and provider choices, and the plan
this was built from for the full design rationale.

## Pipeline

`analytics pull -> strategy pick -> script (Claude Haiku) -> voiceover (Google Cloud TTS)
-> AI images (Gemini 2.5 Flash Image, aka "Nano Banana") [+ optional AI hero clip (Runway)]
-> ffmpeg assembly -> YouTube upload -> spend ledger update`

Runs once/day via GitHub Actions (free tier — see `.github/workflows/daily_short.yml`).
Estimated real cost: **~$20–30/month**, under the $50 cap configured in `config.yaml`.

## One-time setup

### 1. Google Cloud project + YouTube API access

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create a new project.
2. Enable **YouTube Data API v3**, **YouTube Analytics API**, and **Cloud Text-to-Speech API**
   (APIs & Services → Library).
3. Under **APIs & Services → Credentials**, create an **API key** restricted to Cloud
   Text-to-Speech API only — this is `GOOGLE_TTS_API_KEY`.
4. Also create an **OAuth client ID** of type **Desktop app** (used for YouTube
   upload/analytics — uploading video requires a real Google account's consent, an API key
   alone won't work).
5. Configure the **OAuth consent screen** as External, add your own Google account as a Test User
   (Testing mode is fine — no Google review needed for personal use).
6. Make sure the YouTube channel you want to post to belongs to the Google account you'll
   authorize in the next step.

Note: the image-generation key (next section) is a *separate* key from a *different*
console (Google AI Studio, not Cloud Console) — Google splits "Cloud" API keys from
"Gemini API" keys, and a key restricted to one won't work for the other.

### 2. Get a YouTube refresh token

```bash
pip install -r requirements.txt
python scripts/get_refresh_token.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

This opens a browser — log in as the channel's Google account and grant access. It prints a
refresh token; save it, you'll need it below.

### 3. Get the other API keys

- **Anthropic** (script generation): [console.anthropic.com](https://console.anthropic.com) → API keys.
- **Google Gemini** (image generation, `GOOGLE_IMAGE_API_KEY`): [aistudio.google.com/apikey](https://aistudio.google.com/apikey) →
  Create API key. This is the easiest way to get a correctly-scoped key — it's auto-restricted
  to the Gemini API (Google's older "Generative Language API" Cloud Console entry is being phased
  out of discoverability in favor of this flow). Pick the same Cloud project you made in step 1
  if it offers a choice, so everything lives in one place.
- **Runway** (optional AI hero clip): [dev.runwayml.com](https://dev.runwayml.com) → API keys.

### 4. Configure secrets

**Local dev**: `cp .env.example .env` and fill in all values.

**GitHub Actions**: in the repo's Settings → Secrets and variables → Actions, add:
`ANTHROPIC_API_KEY`, `GOOGLE_TTS_API_KEY`, `GOOGLE_IMAGE_API_KEY`, `RUNWAY_API_KEY`,
`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.

### 5. Fill in `config.yaml`

Set `channel.name` / `channel.handle`. Review `content.pillars`, `budget.monthly_cap_usd`,
and `posting.visibility_on_launch` (leave as `unlisted` until you've verified a real upload).

## Running locally

```bash
pip install -r requirements.txt
python -m src.main --dry-run   # generates output/<run>/final.mp4, skips upload
```

Watch the generated MP4 for pacing, caption sync, and audio/visual quality before enabling
real uploads.

```bash
python -m src.main             # full run including upload (as "unlisted" by default)
```

## Deploying the daily cron

1. Push this repo to GitHub, add the secrets above.
2. Manually trigger `.github/workflows/daily_short.yml` (Actions tab → Run workflow) with
   `dry_run: true` first, confirm it succeeds and the artifact looks right.
3. Run it again with `dry_run: false` to confirm a real (unlisted) upload works end-to-end.
4. In the workflow file, uncomment the `schedule:` block to switch to a fully automated
   daily run, and flip `posting.visibility_on_launch` to `public` in `config.yaml`.

## Monitoring cost & performance

- `data/spend_ledger.json` — running log of estimated spend per API call; the pipeline
  auto-disables the optional AI hero clip once monthly spend crosses
  `budget.hero_clip_cutoff_usd`, and skips the run entirely at `budget.monthly_cap_usd`.
- `data/performance_log.json` — per-video analytics snapshots (views, likes, retention),
  pulled fresh at the start of every run and used by `src/strategy.py` to weight which
  content pillar to favor next.
- `data/content_history.json` — every video ever generated, so topics aren't repeated.

Both `data/*.json` files are committed back to the repo by the workflow after each run, so
they double as a free, versioned database — no external DB service needed.
