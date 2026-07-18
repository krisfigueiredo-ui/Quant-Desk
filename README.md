# Quant Desk

Quant Desk is a paper-trading research workspace for equity and crypto factor strategies, scheduled Alpaca paper execution, position-risk monitoring, and prediction-market liquidity analysis.

**Live dashboard:** https://krisfigueiredo-ui.github.io/Quant-Desk/

> Research and paper trading only. The project has no live-money configuration and does not provide investment advice.

## Repository map

| Path | Purpose |
|---|---|
| `bots/auto_paper_trader.py` | Equity factor strategy with monthly rebalancing |
| `bots/auto_paper_trader_crypto.py` | Crypto momentum and trend strategy with weekly rebalancing |
| `bots/exit_manager.py` | Daily stop-loss and take-profit checks |
| `dashboards/bot_dashboard.html` | Read-only paper-account monitor with a hosted demo mode |
| `dashboards/kalshi_signals.html` | Fee, depth, and freshness checks over public Kalshi quotes |
| `scripts/local_dashboard_server.py` | Local static server and read-only Alpaca proxy |
| `scripts/fetch_kalshi_snapshot.py` | Server-side public market snapshot generator |
| `notebooks/impact_quant_strategy.ipynb` | Factor research, backtests, cost analysis, Monte Carlo, and ML experiments |
| `.github/workflows/paper_bots.yml` | Scheduled dry-run paper bots |
| `.github/workflows/pages.yml` | Dashboard deployment and 15-minute public snapshot refresh |

## Strategy setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add Alpaca **paper** credentials to `.env`, load them into the shell, and run a dry-run strategy:

```bash
set -a
source .env
set +a
python3 bots/auto_paper_trader.py
```

`DRY_RUN=true` is the default. Intended orders are logged but not submitted.

## Account monitor

The GitHub Pages version uses representative data so the dashboard is useful without asking for credentials in a public page. For live paper-account data, start the local read-only proxy:

```bash
set -a
source .env
set +a
python3 scripts/local_dashboard_server.py --port 8000
```

Open `http://127.0.0.1:8000/dashboards/bot_dashboard.html`. Credentials stay in the Python process. The browser only receives account, position, and recent-order responses; the proxy exposes no order-entry route.

## Kalshi snapshot

Browsers cannot reliably call Kalshi's API from GitHub Pages because of cross-origin restrictions. The Pages workflow therefore fetches public top-of-book data server-side every 15 minutes, normalizes current and legacy quote fields, and publishes `data/kalshi_snapshot.json`. The dashboard polls that static snapshot automatically.

Generate a local snapshot with:

```bash
python3 scripts/fetch_kalshi_snapshot.py
python3 -m http.server 8000
```

## GitHub Actions

Add `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` under **Settings → Secrets and variables → Actions**. Notification secrets are optional. The bot workflow remains dry-run until `DRY_RUN` is deliberately changed.

## Safety controls

- Every Alpaca client is configured for the paper environment.
- Automated jobs default to dry-run.
- `.env`, keys, logs, caches, and editor files are ignored by Git.
- The hosted site never requests or stores account credentials.
- Dashboard API access is read-only; no route can place, change, or cancel an order.
