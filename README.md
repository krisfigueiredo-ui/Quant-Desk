# Quant Desk

A paper-trading research desk: screen equities and crypto with a factor/momentum model,
paper-trade them on **Alpaca**, guard positions with a daily stop/take-profit manager, and
watch it all from a read-only dashboard.

> Research and **paper trading only**. Not a live-money system, not investment advice, no promise
> of returns. Everything is hard-locked to Alpaca's paper environment.

## What's inside

| Path | What it does |
|------|--------------|
| `bots/auto_paper_trader.py` | Equity factor strategy (momentum/trend/quality/value), monthly rebalance |
| `bots/auto_paper_trader_crypto.py` | Crypto momentum + trend filter, weekly rebalance |
| `bots/exit_manager.py` | Daily stop-loss / take-profit guard across all positions |
| `dashboards/bot_dashboard.html` | Live read-only monitor — open in a browser, paste paper keys |
| `dashboards/kalshi_signals.html` | Kalshi arbitrage signal scanner (public data) |
| `notebooks/impact_quant_strategy.ipynb` | Full research: factors, grades, backtest, costs/decay, Monte Carlo, ML |
| `notebooks/Colab_Launcher.ipynb` | One-tab Colab runner for the bots |
| `.github/workflows/paper_bots.yml` | Schedules the three bots on GitHub Actions |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # edit .env with your Alpaca PAPER keys
set -a && source .env && set +a
python bots/auto_paper_trader.py     # dry run — logs intended orders, submits nothing
```

Get **paper** keys at [alpaca.markets](https://alpaca.markets) → Paper Trading → API Keys.

## Run it hands-off (recommended)

Schedule the bots on GitHub Actions so nothing needs to run on your computer:

1. Push this repo (private).
2. Repo → Settings → Secrets and variables → Actions → add `ALPACA_API_KEY`,
   `ALPACA_SECRET_KEY` (and optional `SLACK_WEBHOOK_URL`, `EMAIL_*`).
3. The workflow ships with `DRY_RUN: "true"`. Watch a summary or two, then set it to `"false"`.

The equity bot acts on the first trading day of each month, crypto on Mondays, and the exit
manager runs daily. Most days you'll just get a "holding" email — silence means something broke.

## The monitor

Open `dashboards/bot_dashboard.html` in any browser and paste your paper keys. It's read-only:
it shows equity, positions (each plotted between its stop and take-profit), and recent orders.
It talks only to `paper-api.alpaca.markets` and contains no order-placement code.

## Safety model

- **Paper-locked:** every client is `paper=True`. Live keys won't authenticate against the paper endpoint.
- **Dry-run first:** `DRY_RUN=true` logs intended trades without submitting.
- **Secrets stay out of git:** `.env` and `*.log` are gitignored; keys are read from the environment.
- **Honest research:** the notebook is built to reveal when a strategy *doesn't* work — near-zero
  information coefficients, failing significance tests, ML losing to the simple rule. Keep it that way.

## Discipline

Paper-trade ~90 days / 100+ trades, then compare results to buy-and-hold before considering real
capital. If the evidence isn't there, that's the finding — and you learned it for free.
