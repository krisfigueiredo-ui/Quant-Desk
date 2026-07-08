# CLAUDE.md — project guide for Claude Code

## What this is
A **paper-trading research desk**. It screens equities and crypto with a factor/momentum
model, paper-trades them on Alpaca, guards positions with a daily stop/take-profit manager,
and monitors everything from a read-only dashboard. This is research and paper trading —
**not** a live-money system and not investment advice.

## Hard rules (do not violate)
- **Paper only.** Every bot constructs `TradingClient(key, secret, paper=True)`. Never change
  `paper=True` to `False`. Never add a live endpoint.
- **No secrets in code or git.** Keys come from environment variables only. `.env` is gitignored.
  Never hardcode a key, never print a full key, never commit one.
- **`DRY_RUN` defaults to true.** Code must treat missing/true as "log intended orders, submit nothing."
- **The dashboard is read-only.** `dashboards/bot_dashboard.html` must never gain order-placement code.
- **Don't invent an edge.** The research notebook is deliberately built to report when a strategy
  does NOT work (near-zero IC, failing t-stats, ML losing to the simple rule). Preserve that honesty;
  don't tune parameters just to make a backtest look good.

## Layout
```
bots/
  auto_paper_trader.py         # equity factor strategy, monthly rebalance
  auto_paper_trader_crypto.py  # crypto momentum, weekly rebalance
  exit_manager.py              # daily stop-loss / take-profit guard (stocks + crypto)
dashboards/
  bot_dashboard.html           # live read-only monitor (open in browser, paste paper keys)
  kalshi_signals.html          # Kalshi arbitrage signal scanner (public data)
notebooks/
  impact_quant_strategy.ipynb  # full research: factors, grades, backtest, Monte Carlo, ML
  Colab_Launcher.ipynb         # one-tab Colab runner for the bots
research/
  SETUP_paper_trader.md        # setup + scheduling guide
.github/workflows/paper_bots.yml  # schedules all three bots on GitHub's servers
```

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env with your PAPER keys
set -a && source .env && set +a
python bots/auto_paper_trader.py          # dry run by default
python bots/auto_paper_trader_crypto.py
python bots/exit_manager.py
```
Each bot self-gates: the equity bot acts only on the first trading day of the month, crypto only
on Mondays, the exit manager runs daily. Running any of them off-schedule just logs "holding."

## Scheduling
`.github/workflows/paper_bots.yml` runs the three bots on GitHub Actions. Add repo secrets
(`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, and optional Slack/email ones). Jobs ship with
`DRY_RUN: "true"` — flip to `"false"` in the workflow after reviewing the dry-run summaries.

## Common tasks you might be asked to do
- Adjust the universe or factor weights: edit the `UNIVERSE` / `CONFIG` blocks at the top of each bot.
- Change exit thresholds: `STOP_PCT` / `TAKE_PCT` env vars (see `.env.example`).
- Add a notifier or a new schedule: follow the existing patterns in the bot files and the workflow.
- Before committing, confirm no secret is staged: `git diff --cached | grep -iE "PK|secret|key"`.

## Testing changes
There's no formal test suite in the repo (the original build validated logic with synthetic data).
When you change bot math, sanity-check with a quick synthetic-data script rather than live calls,
and keep `DRY_RUN=true` for any end-to-end run.
