#!/usr/bin/env python3
"""
auto_paper_trader.py  —  scheduled PAPER-trading runner for the impact strategy.

What it does, once per run:
  1. Checks the market is open (Alpaca clock).
  2. Checks whether today is a rebalance day (default: first trading day of month).
  3. If so: downloads prices, scores the universe, builds target weights,
     and rebalances your *paper* account toward them. Otherwise it just logs status.

Safety rails (read these):
  • PAPER ONLY. The client is hard-locked to paper=True. It cannot touch a live account.
  • DRY_RUN defaults to True — it logs the orders it *would* place and submits nothing.
    Set DRY_RUN=false only once you've watched the dry-run logs and trust them.
  • Regime filter, per-name caps, and a cash buffer are enforced before any order.
  • This is a MONTHLY strategy. Running it daily is fine; it acts only on rebalance days.

Setup:
  pip install alpaca-py yfinance pandas numpy
  export ALPACA_API_KEY=...        # your PAPER keys from alpaca.markets
  export ALPACA_SECRET_KEY=...
  export DRY_RUN=true              # flip to false only when ready
  python auto_paper_trader.py
"""
import os, sys, logging, datetime as dt
import numpy as np, pandas as pd

# ───────────────────────── config (mirror your notebook) ─────────────────────
UNIVERSE = {
    "Clean energy & storage": ["ENPH", "FSLR", "NEE", "BEP", "SEDG", "RUN"],
    "Sustainable transport":  ["TSLA", "RIVN", "ALB"],
    "Healthcare & cures":     ["VRTX", "REGN", "ISRG", "DHR", "TMO", "ILMN"],
    "Scientific tools":       ["A", "MTD", "WAT"],
    "Enabling semiconductors":["NVDA", "TSM", "ASML", "AMD"],
    "Water & resources":      ["XYL", "AWK", "ECL"],
    "Food & ag innovation":   ["DE", "CTVA"],
    "Access & education":     ["DUOL", "COUR"],
}
TICKERS = sorted({t for v in UNIVERSE.values() for t in v})
BENCHMARK = "SPY"

CONFIG = {
    "top_n": 8, "max_weight": 0.20, "use_regime_filter": True,
    "weights": {"momentum": 0.35, "trend": 0.25, "quality": 0.20, "value": 0.20},
    "mom_lookback": 252, "mom_skip": 21, "vol_lookback": 63, "trend_window": 200,
    "invest_fraction": 0.95,   # keep 5% cash buffer
    "min_trade_usd": 50,       # ignore dust rebalances
    "rebalance_rule": "month_start",   # 'month_start' or 'weekly_mon' or 'daily'
}

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
LOG_FILE = os.environ.get("LOG_FILE", "paper_trader.log")

# Notifications (all optional — set only what you want)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
EMAIL_TO   = os.environ.get("EMAIL_TO", "")          # comma-separated ok
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")        # e.g. a gmail address
EMAIL_PASS = os.environ.get("EMAIL_APP_PASSWORD", "")# gmail app password (not your login)
SMTP_HOST  = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.environ.get("SMTP_PORT", "587"))
ALWAYS_NOTIFY = os.environ.get("ALWAYS_NOTIFY", "true").lower() != "false"  # ping even on no-trade days

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)],
)
log = logging.getLogger("paper")

# ───────────────────────── notifications ─────────────────────────────────────
def send_slack(text):
    if not SLACK_WEBHOOK: return
    try:
        import json, urllib.request
        req = urllib.request.Request(
            SLACK_WEBHOOK, data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning("Slack notify failed: %s", e)

def send_email(subject, body):
    if not (EMAIL_TO and EMAIL_FROM and EMAIL_PASS): return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg["Subject"], msg["From"], msg["To"] = subject, EMAIL_FROM, EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls(); s.login(EMAIL_FROM, EMAIL_PASS)
            s.sendmail(EMAIL_FROM, [a.strip() for a in EMAIL_TO.split(",")], msg.as_string())
    except Exception as e:
        log.warning("Email notify failed: %s", e)

def notify(subject, body):
    """Fan out to whatever channels are configured."""
    tag = "[PAPER/DRY]" if DRY_RUN else "[PAPER/LIVE-SIM]"
    send_slack(f"*{tag} {subject}*\n```{body}```")
    send_email(f"{tag} {subject}", body)
    log.info("Notification sent: %s", subject)


# ───────────────────────── factor engine (same as notebook) ──────────────────
def _z(s):
    s = s.astype(float); sd = s.std(ddof=0)
    return pd.Series(0.0, index=s.index) if (sd == 0 or np.isnan(sd)) else (s - s.mean()) / sd
def _winz(z, k=3.0): return z.clip(-k, k)
def _rsi(px, w=14):
    d = px.diff(); up = d.clip(lower=0).rolling(w).mean(); dn = (-d.clip(upper=0)).rolling(w).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def compute_scores(prices, cfg):
    px = prices
    cols = [c for c in px.columns if px[c].notna().sum() > cfg["mom_lookback"] + 5]
    px = px[cols]
    if px.shape[1] == 0: return pd.DataFrame()
    last = px.iloc[-1]
    mom = (px.shift(cfg["mom_skip"]).iloc[-1] / px.shift(cfg["mom_lookback"]).iloc[-1]) - 1
    trend = (last / px.rolling(cfg["trend_window"]).mean().iloc[-1]) - 1
    vol = px.pct_change().iloc[-cfg["vol_lookback"]:].std() * np.sqrt(252)
    r = _rsi(px).iloc[-1]
    good = -(r - 50).abs() / 50; over = (r.clip(lower=60) - 60) / 40
    df = pd.DataFrame({"momentum": mom, "trend": trend, "volatility": vol, "rsi": r})
    w = cfg["weights"]
    df["composite"] = (w["momentum"]*_winz(_z(mom)) + w["trend"]*_winz(_z(trend)) +
                       w["quality"]*_winz(_z(-vol)) + w["value"]*_winz(_z(good) - _z(over)))
    return df.sort_values("composite", ascending=False)

def build_weights(scores, prices, cfg):
    picks = scores.head(cfg["top_n"]).index.tolist()
    if not picks: return pd.Series(dtype=float)
    vol = prices[picks].pct_change().iloc[-cfg["vol_lookback"]:].std() * np.sqrt(252)
    inv = (1 / vol.replace(0, np.nan)).fillna(0); 
    if inv.sum() == 0: inv = pd.Series(1.0, index=picks)
    w = inv / inv.sum()
    for _ in range(10):
        over = w > cfg["max_weight"]
        if not over.any(): break
        ex = (w[over] - cfg["max_weight"]).sum(); w[over] = cfg["max_weight"]; un = ~over
        if un.any(): w[un] += ex * (w[un] / w[un].sum())
    return (w / w.sum()).sort_values(ascending=False)

def regime_ok(bench, ma=200):
    b = bench.dropna()
    return True if len(b) < ma + 1 else bool(b.iloc[-1] >= b.rolling(ma).mean().iloc[-1])

# ───────────────────────── pure rebalance math (unit-tested) ─────────────────
def compute_rebalance_orders(targets, positions, equity, cfg):
    """
    targets:   {symbol: weight}     desired portfolio weights (sum<=1)
    positions: {symbol: mkt_value}  current $ held per symbol
    equity:    float                total account equity
    returns list of (symbol, side, notional_usd) plus full-exit closes.
    """
    invest = equity * cfg["invest_fraction"]
    target_usd = {s: w * invest for s, w in targets.items()}
    orders, closes = [], []
    for sym in sorted(set(target_usd) | set(positions)):
        tgt = target_usd.get(sym, 0.0)
        cur = positions.get(sym, 0.0)
        if tgt == 0.0 and cur > 0:
            closes.append(sym); continue           # fully exit names no longer selected
        delta = tgt - cur
        if abs(delta) < cfg["min_trade_usd"]:
            continue                                # skip dust
        orders.append((sym, "buy" if delta > 0 else "sell", round(abs(delta), 2)))
    return orders, closes

def is_rebalance_day(today, trading_days, rule):
    if rule == "daily": return True
    if rule == "weekly_mon": return today.weekday() == 0
    # month_start: today is the first trading day of its month
    month_days = [d for d in trading_days if d.year == today.year and d.month == today.month]
    return bool(month_days) and today == min(month_days)

# ───────────────────────── live plumbing (Alpaca + yfinance) ─────────────────
def run():
    log.info("=" * 64)
    log.info("Impact strategy paper runner | DRY_RUN=%s", DRY_RUN)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        import yfinance as yf
    except ImportError as e:
        msg = f"Missing dependency: {e}. Run: pip install alpaca-py yfinance"
        log.error(msg); notify("Runner could not start", msg); return

    key, sec = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not sec:
        msg = "ALPACA_API_KEY / ALPACA_SECRET_KEY not set (need paper keys)."
        log.error(msg); notify("Runner could not start", msg); return

    client = TradingClient(key, sec, paper=True)   # hard-locked to paper
    clock = client.get_clock()
    if not clock.is_open:
        log.info("Market closed (next open %s).", clock.next_open)
        if ALWAYS_NOTIFY:
            notify("Market closed — no action",
                   f"{stamp}\nMarket is closed.\nNext open: {clock.next_open}")
        return

    # data
    end = pd.Timestamp.today(); start = end - pd.DateOffset(years=3)
    raw = yf.download(TICKERS + [BENCHMARK], start=start, end=end,
                      auto_adjust=True, progress=False)["Close"].dropna(how="all")
    bench = raw[BENCHMARK].dropna()
    prices = raw[[c for c in raw.columns if c != BENCHMARK]]

    # account snapshot (used in every summary)
    acct = client.get_account(); equity = float(acct.equity)
    positions = {p.symbol: float(p.market_value) for p in client.get_all_positions()}

    # rebalance-day gate
    today = pd.Timestamp(clock.timestamp.date())
    if not is_rebalance_day(today, list(prices.index), CONFIG["rebalance_rule"]):
        log.info("Not a rebalance day (%s rule). Holding.", CONFIG["rebalance_rule"])
        if ALWAYS_NOTIFY:
            held = ", ".join(f"{s} ${v:,.0f}" for s, v in sorted(positions.items())) or "none"
            notify("Holding — not a rebalance day",
                   f"{stamp}\nEquity: ${equity:,.2f}\nRule: {CONFIG['rebalance_rule']}\n"
                   f"Open positions: {held}\nNo trades today.")
        return

    # regime + targets
    regime_line = ""
    if CONFIG["use_regime_filter"] and not regime_ok(bench):
        log.warning("REGIME RISK-OFF (%s below 200d MA). Target = ALL CASH.", BENCHMARK)
        targets = {}; regime_line = f"Regime: RISK-OFF ({BENCHMARK} < 200d MA) → target all cash\n"
    else:
        scores = compute_scores(prices, CONFIG)
        targets = build_weights(scores, prices, CONFIG).to_dict()
        regime_line = f"Regime: risk-on\n"
        log.info("Target weights: %s", {k: round(v, 3) for k, v in targets.items()})

    log.info("Equity $%.2f | %d open positions", equity, len(positions))
    orders, closes = compute_rebalance_orders(targets, positions, equity, CONFIG)

    # build human summary
    tgt_line = ", ".join(f"{k} {v*100:.0f}%" for k, v in targets.items()) or "ALL CASH"
    lines = [stamp, f"Equity: ${equity:,.2f}", regime_line.strip(),
             f"Rebalance day ({CONFIG['rebalance_rule']}).", f"Target: {tgt_line}", ""]

    if not orders and not closes:
        log.info("Already aligned with target. No trades.")
        lines.append("Already aligned — no trades needed.")
        notify("Rebalance day — no trades", "\n".join(lines)); return

    for sym in closes:
        log.info("CLOSE  %s (full exit)", sym)
        lines.append(f"CLOSE  {sym}  (full exit)")
        if not DRY_RUN: client.close_position(sym)
    for sym, side, notional in orders:
        log.info("%-4s   %-5s  $%.2f", side.upper(), sym, notional)
        lines.append(f"{side.upper():<5} {sym:<5} ${notional:,.2f}")
        if not DRY_RUN:
            client.submit_order(MarketOrderRequest(
                symbol=sym, notional=notional,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY))

    tail = "  (DRY RUN — nothing submitted)" if DRY_RUN else ""
    log.info("Done. %d orders, %d closes.%s", len(orders), len(closes), tail)
    lines += ["", f"{len(orders)} orders, {len(closes)} closes." + tail]
    notify(f"Rebalanced — {len(orders)} orders, {len(closes)} closes", "\n".join(lines))

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        # any unexpected failure still reaches you instead of failing silently
        import traceback
        tb = traceback.format_exc()
        log.error("Runner crashed: %s", e)
        notify("Runner CRASHED", f"{dt.datetime.now():%Y-%m-%d %H:%M}\n{e}\n\n{tb[-1500:]}")
        raise

