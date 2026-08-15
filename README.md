# Cricket Telegram Bot

A small Telegram cricket-analysis bot designed for Render.

## Features
- Today's/live matches from CricketData/CricAPI
- Neutral live match-performance load (score/run-rate/wickets)
- Menu buttons
- Health endpoint
- Telegram webhook
- No Telegram token in source code

## Render environment variables
Set:
- `TELEGRAM_BOT_TOKEN` = your Telegram BotFather token
- `CRICKET_API_KEY` = your free CricketData/CricAPI key

Render automatically provides `RENDER_EXTERNAL_URL` and `PORT`.

## Important
The bot does not provide betting odds, bookmaker data, public betting load, or betting recommendations. The "Live Match Load" feature is a cricket-performance pressure indicator based on live score data.

CricketData's free plan currently advertises 100 API hits/day, so avoid very frequent polling.
