# Automating the strategy during work hours — paper first

This runs your impact strategy **on a schedule, unattended, against an Alpaca paper account** (fake money, real prices, real order mechanics). It's the safe version of "trade for me while I'm at work."

## Why this is safer than it sounds

Your strategy **rebalances monthly**. So automation isn't a bot trading all day — it's a job that wakes up, asks *"is the market open AND is today a rebalance day?"*, and only then places orders. Most days it does nothing but log "holding." That's the whole point: set-and-forget, not white-knuckle.

## One-time setup (15 minutes)

1. **Make a free Alpaca account** at alpaca.markets and switch to **Paper Trading**. Generate **paper** API keys.
2. Install deps:
   ```
   pip install alpaca-py yfinance pandas numpy
   ```
3. Put your keys in the environment (never in the code):
   ```
   export ALPACA_API_KEY=your_paper_key
   export ALPACA_SECRET_KEY=your_paper_secret
   export DRY_RUN=true        # logs intended orders, submits nothing
   ```
4. Run it once by hand and read the log:
   ```
   python auto_paper_trader.py
   ```
   With `DRY_RUN=true` it prints the exact orders it *would* place. Watch this for a rebalance cycle or two before trusting it.

When you're satisfied, set `DRY_RUN=false` to let it actually place **paper** orders. (The client is hard-locked to `paper=True` — it cannot touch real money no matter what.)

## Make it run while you're at work

The script is built to be run once per day; it self-checks whether to act. Pick one:

**A — cron on an always-on machine (simplest).** Runs daily at 10:00 ET:
```
0 10 * * 1-5  cd /path/to/folder && /usr/bin/python3 auto_paper_trader.py >> cron.log 2>&1
```
Your laptop must be awake at that time. If it sleeps at the office, use B.

**B — a free/cheap always-on cloud box.** A small VM (Render, Railway, a $5 VPS, an EC2 micro) with the same cron line runs whether your laptop is open or not. Put the keys in the host's environment/secrets, not in the file.

**C — GitHub Actions (no server to manage).** A scheduled workflow runs the script on GitHub's runners. Store keys as repository **Secrets**. Sketch:
```yaml
# .github/workflows/rebalance.yml
on:
  schedule:
    - cron: "0 14 * * 1-5"   # 14:00 UTC ≈ 10:00 ET
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install alpaca-py yfinance pandas numpy
      - run: python auto_paper_trader.py
        env:
          ALPACA_API_KEY: ${{ secrets.ALPACA_API_KEY }}
          ALPACA_SECRET_KEY: ${{ secrets.ALPACA_SECRET_KEY }}
          DRY_RUN: "false"
```

## The discipline that actually matters

Industry guidance for this kind of system is blunt and worth following: **paper-trade for at least ~90 days and 100+ trades, then compare results to buy-and-hold on the same universe** before risking a cent. For a monthly strategy that's a few rebalance cycles — give it real time.

After that window, take the paper results back to **Section 9 of the notebook** (IC, decay haircut, t-stat). If the live paper run still shows ~zero IC and lags buy-and-hold, that's your answer, cheaply learned. If it genuinely clears the bar — uncommon — *then* the conversation about tiny real size, hard caps, a kill switch, and phone alerts begins.

This is paper-trading infrastructure for research. It is not investment advice, and nothing here promises returns.
