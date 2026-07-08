#!/usr/bin/env python3
"""
auto_paper_trader_crypto.py  —  scheduled PAPER crypto momentum runner (Alpaca).

Honest scope (read this — it differs from the equity bot on purpose):
  • NO values screen. "Advancing humanity" has no analogue for a token (no earnings,
    no product, no profitability), so this is pure cross-sectional MOMENTUM + a trend
    filter — the only crypto factor with meaningful published evidence.
  • Momentum in crypto is real but FAR less robust than in equities: higher turnover,
    deeper drawdowns, and regimes that flip fast. Treat results with extra skepticism.
  • Crypto trades 24/7, so drawdowns happen while you sleep. The BTC-regime filter and
    per-token trend filter exist to dodge the worst of that, not to eliminate it.
  • Smaller alts = thin liquidity and real slippage. Costs are set higher here for a reason.

Strategy:
  • Universe: broad set of Alpaca-supported USD pairs incl. smaller alts (auto-filtered
    at runtime to what's actually tradable).
  • Signal: blended 30/90-day relative momentum (z-scored), pick top N.
  • Trend filter (absolute momentum): only hold tokens above their own 50-day average.
  • Regime: if BTC is below its 200-day average, go ALL CASH.
  • Sizing: inverse-volatility, per-token cap, cash buffer (risk management).
  • Rebalance: weekly by default (crypto moves faster than the monthly equity strategy).

Safety: PAPER-locked (paper=True), DRY_RUN defaults true, same notifier as the equity bot.

Setup:
  pip install alpaca-py yfinance pandas numpy
  export ALPACA_API_KEY=...  ALPACA_SECRET_KEY=...   # PAPER keys
  export DRY_RUN=true
  python auto_paper_trader_crypto.py
"""
import os, sys, logging, datetime as dt
import numpy as np, pandas as pd

# ───────────────────────── universe (Alpaca USD pairs) ───────────────────────
# Broad incl. smaller/riskier alts. Auto-filtered to tradable assets at runtime.
UNIVERSE = [
    "BTC/USD","ETH/USD","SOL/USD","AVAX/USD","LINK/USD","LTC/USD","BCH/USD",
    "UNI/USD","AAVE/USD","DOT/USD","DOGE/USD","SHIB/USD","CRV/USD","MKR/USD",
    "GRT/USD","SUSHI/USD","XTZ/USD","YFI/USD","BAT/USD",
]
REGIME_ASSET = "BTC/USD"   # crypto beta is dominated by BTC

CONFIG = {
    "top_n": 6, "max_weight": 0.30, "use_regime_filter": True,
    "mom_fast": 30, "mom_slow": 90, "trend_window": 50, "regime_window": 200,
    "vol_lookback": 45,
    "invest_fraction": 0.95,
    "min_trade_usd": 25,
    "cost_bps": 35,                  # higher: crypto fees + alt slippage
    "rebalance_rule": "weekly_mon",  # 'weekly_mon' | 'daily' | 'month_start'
}

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
LOG_FILE = os.environ.get("LOG_FILE", "paper_trader_crypto.log")

# Notifications (optional — same env vars as the equity bot)
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
EMAIL_TO   = os.environ.get("EMAIL_TO", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_PASS = os.environ.get("EMAIL_APP_PASSWORD", "")
SMTP_HOST  = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.environ.get("SMTP_PORT", "587"))
ALWAYS_NOTIFY = os.environ.get("ALWAYS_NOTIFY", "true").lower() != "false"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)])
log = logging.getLogger("crypto")

# ───────────────────────── notifications ─────────────────────────────────────
def send_slack(text):
    if not SLACK_WEBHOOK: return
    try:
        import json, urllib.request
        req = urllib.request.Request(SLACK_WEBHOOK, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e: log.warning("Slack notify failed: %s", e)

def send_email(subject, body):
    if not (EMAIL_TO and EMAIL_FROM and EMAIL_PASS): return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body); msg["Subject"], msg["From"], msg["To"] = subject, EMAIL_FROM, EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls(); s.login(EMAIL_FROM, EMAIL_PASS)
            s.sendmail(EMAIL_FROM, [a.strip() for a in EMAIL_TO.split(",")], msg.as_string())
    except Exception as e: log.warning("Email notify failed: %s", e)

def notify(subject, body):
    tag = "[CRYPTO-PAPER/DRY]" if DRY_RUN else "[CRYPTO-PAPER/LIVE-SIM]"
    send_slack(f"*{tag} {subject}*\n```{body}```")
    send_email(f"{tag} {subject}", body)
    log.info("Notification sent: %s", subject)

# ───────────────────────── signal engine (momentum/trend only) ───────────────
def _z(s):
    s = s.astype(float); sd = s.std(ddof=0)
    return pd.Series(0.0, index=s.index) if (sd == 0 or np.isnan(sd)) else (s - s.mean()) / sd
def _winz(z, k=3.0): return z.clip(-k, k)
def _norm(sym): return sym.replace("/", "").upper()   # BTC/USD and BTCUSD -> BTCUSD

def compute_signals(prices, cfg):
    px = prices
    cols = [c for c in px.columns if px[c].notna().sum() > cfg["mom_slow"] + 5]
    px = px[cols]
    if px.shape[1] == 0: return pd.DataFrame()
    last = px.iloc[-1]
    mom_fast = px.pct_change(cfg["mom_fast"]).iloc[-1]
    mom_slow = px.pct_change(cfg["mom_slow"]).iloc[-1]
    ma = px.rolling(cfg["trend_window"]).mean().iloc[-1]
    trend = last / ma - 1
    vol = px.pct_change().iloc[-cfg["vol_lookback"]:].std() * np.sqrt(365)
    df = pd.DataFrame({"mom_fast": mom_fast, "mom_slow": mom_slow,
                       "trend": trend, "volatility": vol})
    df["score"] = (_winz(_z(mom_fast)) + _winz(_z(mom_slow))) / 2   # relative momentum
    df["eligible"] = df["trend"] > 0                                # absolute-momentum filter
    return df.sort_values("score", ascending=False)

def build_weights(sig, prices, cfg):
    picks = sig[sig["eligible"]].head(cfg["top_n"]).index.tolist()   # trend-filtered + top momentum
    if not picks: return pd.Series(dtype=float)
    vol = prices[picks].pct_change().iloc[-cfg["vol_lookback"]:].std() * np.sqrt(365)
    inv = (1 / vol.replace(0, np.nan)).fillna(0)
    if inv.sum() == 0: inv = pd.Series(1.0, index=picks)
    w = inv / inv.sum()
    cap = cfg["max_weight"]
    for _ in range(20):
        over = w > cap + 1e-12
        if not over.any(): break
        excess = (w[over] - cap).sum(); w[over] = cap
        under = w < cap - 1e-12
        if not under.any():
            break   # nowhere to place excess -> remainder stays in CASH (sum < 1)
        w[under] += excess * (w[under] / w[under].sum())
    return w.sort_values(ascending=False)   # may sum to <1 by design (rest = cash)

def regime_ok(series, window=200):
    b = series.dropna()
    return True if len(b) < window + 1 else bool(b.iloc[-1] >= b.rolling(window).mean().iloc[-1])

# ───────────────────────── pure rebalance math (unit-tested) ─────────────────
def compute_rebalance_orders(targets, positions, equity, cfg):
    """targets keyed by 'BTC/USD'; positions may be keyed 'BTCUSD' or 'BTC/USD'.
       Normalizes both so a held coin isn't double-bought."""
    invest = equity * cfg["invest_fraction"]
    tgt = {_norm(s): (s, w * invest) for s, w in targets.items()}
    pos = {_norm(s): (s, mv) for s, mv in positions.items()}
    orders, closes = [], []
    for key in sorted(set(tgt) | set(pos)):
        tsym, tusd = tgt.get(key, (None, 0.0))
        psym, pmv  = pos.get(key, (None, 0.0))
        if tusd == 0.0 and pmv > 0:
            closes.append(psym); continue
        delta = tusd - pmv
        if abs(delta) < cfg["min_trade_usd"]: continue
        orders.append((tsym or psym, "buy" if delta > 0 else "sell", round(abs(delta), 2)))
    return orders, closes

def is_rebalance_day(today, rule):
    if rule == "daily": return True
    if rule == "weekly_mon": return today.weekday() == 0
    if rule == "month_start": return today.day <= 3 and today.weekday() < 5
    return today.weekday() == 0

# ───────────────────────── live plumbing ─────────────────────────────────────
def to_yf(sym): return sym.replace("/USD", "-USD")

def run():
    log.info("=" * 64)
    log.info("Crypto momentum paper runner | DRY_RUN=%s", DRY_RUN)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
        from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass
        import yfinance as yf
    except ImportError as e:
        m = f"Missing dependency: {e}. Run: pip install alpaca-py yfinance"
        log.error(m); notify("Crypto runner could not start", m); return

    key, sec = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not sec:
        m = "ALPACA_API_KEY / ALPACA_SECRET_KEY not set (need paper keys)."
        log.error(m); notify("Crypto runner could not start", m); return

    client = TradingClient(key, sec, paper=True)   # hard-locked to paper

    # crypto is 24/7 — no market-hours gate. Only a weekly rebalance cadence.
    today = pd.Timestamp(dt.datetime.utcnow().date())
    if not is_rebalance_day(today, CONFIG["rebalance_rule"]):
        log.info("Not a rebalance day (%s). Holding.", CONFIG["rebalance_rule"])
        if ALWAYS_NOTIFY:
            notify("Holding — not a rebalance day",
                   f"{stamp} UTC\nRule: {CONFIG['rebalance_rule']}\nNo crypto trades today.")
        return

    # filter universe to assets Alpaca actually lists as tradable crypto
    try:
        tradable = {a.symbol for a in client.get_all_assets(
            GetAssetsRequest(asset_class=AssetClass.CRYPTO)) if a.tradable}
        universe = [s for s in UNIVERSE if s in tradable or _norm(s) in {_norm(t) for t in tradable}]
        if not universe: universe = UNIVERSE  # fallback if filter returns nothing odd
    except Exception as e:
        log.warning("Asset filter failed (%s); using full universe.", e); universe = UNIVERSE
    log.info("Universe (%d): %s", len(universe), ", ".join(universe))

    # data via yfinance
    syms = universe + ([REGIME_ASSET] if REGIME_ASSET not in universe else [])
    yf_map = {to_yf(s): s for s in syms}
    end = pd.Timestamp.today(); start = end - pd.DateOffset(days=400)
    raw = yf.download(list(yf_map), start=start, end=end, auto_adjust=True, progress=False)["Close"]
    raw = raw.rename(columns=yf_map).dropna(how="all")
    regime_series = raw[REGIME_ASSET].dropna()
    prices = raw[[c for c in raw.columns if c in universe]]

    # regime
    if CONFIG["use_regime_filter"] and not regime_ok(regime_series, CONFIG["regime_window"]):
        log.warning("REGIME RISK-OFF (BTC below %dd MA). Target = ALL CASH.", CONFIG["regime_window"])
        targets, regime_line = {}, "Regime: RISK-OFF (BTC < 200d MA) -> all cash"
    else:
        sig = compute_signals(prices, CONFIG)
        targets = build_weights(sig, prices, CONFIG).to_dict()
        regime_line = "Regime: risk-on"
        log.info("Targets: %s", {k: round(v, 3) for k, v in targets.items()})

    acct = client.get_account(); equity = float(acct.equity)
    positions = {p.symbol: float(p.market_value) for p in client.get_all_positions()}
    log.info("Equity $%.2f | %d open positions", equity, len(positions))

    orders, closes = compute_rebalance_orders(targets, positions, equity, CONFIG)
    tgt_line = ", ".join(f"{k} {v*100:.0f}%" for k, v in targets.items()) or "ALL CASH"
    lines = [f"{stamp} UTC", f"Equity: ${equity:,.2f}", regime_line,
             f"Rebalance ({CONFIG['rebalance_rule']}).", f"Target: {tgt_line}", ""]

    if not orders and not closes:
        log.info("Already aligned. No trades.")
        lines.append("Already aligned — no trades needed.")
        notify("Rebalance day — no trades", "\n".join(lines)); return

    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    for sym in closes:
        log.info("CLOSE  %s (full exit)", sym); lines.append(f"CLOSE  {sym}")
        if not DRY_RUN:
            try: client.close_position(sym)
            except Exception as e: log.warning("close %s failed: %s", sym, e)
    for sym, side, notional in orders:
        log.info("%-4s  %-9s $%.2f", side.upper(), sym, notional)
        lines.append(f"{side.upper():<4} {sym:<9} ${notional:,.2f}")
        if not DRY_RUN:
            client.submit_order(MarketOrderRequest(
                symbol=sym, notional=notional,
                side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.GTC))   # crypto: GTC, not DAY

    tail = "  (DRY RUN — nothing submitted)" if DRY_RUN else ""
    log.info("Done. %d orders, %d closes.%s", len(orders), len(closes), tail)
    lines += ["", f"{len(orders)} orders, {len(closes)} closes." + tail]
    notify(f"Rebalanced — {len(orders)} orders, {len(closes)} closes", "\n".join(lines))

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        import traceback
        tb = traceback.format_exc(); log.error("Runner crashed: %s", e)
        notify("Crypto runner CRASHED", f"{dt.datetime.now():%Y-%m-%d %H:%M}\n{e}\n\n{tb[-1500:]}")
        raise
