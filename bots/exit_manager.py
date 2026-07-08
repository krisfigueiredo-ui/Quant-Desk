#!/usr/bin/env python3
"""
exit_manager.py — daily PAPER position guard for Alpaca (stocks + crypto).

Runs once a day (via the same GitHub Action). For every open position:
  • STOP-LOSS: unrealized loss beyond -stop_pct  -> close it
  • TAKE-PROFIT: unrealized gain beyond +take_pct -> close it (optional)
Everything else is left alone; the strategy bots handle rebalancing.

This is the piece that answers "auto sell things": daily downside guard,
instead of waiting for the weekly/monthly rebalance.

PAPER-locked (paper=True). DRY_RUN defaults true. Same notifier as the bots.
"""
import os, sys, logging, datetime as dt

STOP_PCT  = float(os.environ.get("STOP_PCT",  "0.15"))   # sell if down 15% from entry
TAKE_PCT  = float(os.environ.get("TAKE_PCT",  "0.40"))   # sell if up 40% from entry
USE_TAKE  = os.environ.get("USE_TAKE_PROFIT", "true").lower() != "false"
DRY_RUN   = os.environ.get("DRY_RUN", "true").lower() != "false"
ALWAYS_NOTIFY = os.environ.get("ALWAYS_NOTIFY", "true").lower() != "false"

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")
EMAIL_TO   = os.environ.get("EMAIL_TO", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_PASS = os.environ.get("EMAIL_APP_PASSWORD", "")
SMTP_HOST  = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.environ.get("SMTP_PORT", "587"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("exits")

def send_slack(text):
    if not SLACK_WEBHOOK: return
    try:
        import json, urllib.request
        req = urllib.request.Request(SLACK_WEBHOOK, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e: log.warning("Slack failed: %s", e)

def send_email(subject, body):
    if not (EMAIL_TO and EMAIL_FROM and EMAIL_PASS): return
    try:
        import smtplib; from email.mime.text import MIMEText
        msg = MIMEText(body); msg["Subject"], msg["From"], msg["To"] = subject, EMAIL_FROM, EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls(); s.login(EMAIL_FROM, EMAIL_PASS)
            s.sendmail(EMAIL_FROM, [a.strip() for a in EMAIL_TO.split(",")], msg.as_string())
    except Exception as e: log.warning("Email failed: %s", e)

def notify(subject, body):
    tag = "[EXITS/DRY]" if DRY_RUN else "[EXITS/PAPER]"
    send_slack(f"*{tag} {subject}*\n```{body}```"); send_email(f"{tag} {subject}", body)

# ── pure decision logic (unit-tested) ─────────────────────────────────────────
def exit_decision(entry, current, stop_pct, take_pct, use_take=True):
    """Returns ('STOP'|'TAKE'|None, pnl_pct)."""
    if entry <= 0: return None, 0.0
    pnl = current / entry - 1
    if pnl <= -abs(stop_pct): return "STOP", pnl
    if use_take and pnl >= abs(take_pct): return "TAKE", pnl
    return None, pnl

def run():
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        from alpaca.trading.client import TradingClient
    except ImportError:
        log.error("pip install alpaca-py"); return
    key, sec = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not sec:
        log.error("Missing Alpaca paper keys"); notify("Exit manager could not start", "keys missing"); return

    client = TradingClient(key, sec, paper=True)   # hard-locked to paper
    positions = client.get_all_positions()
    lines = [f"{stamp}", f"Stops: -{STOP_PCT:.0%} | Take-profit: " +
             (f"+{TAKE_PCT:.0%}" if USE_TAKE else "off"), ""]
    actions = 0
    if not positions:
        lines.append("No open positions.")
    for p in positions:
        entry, cur = float(p.avg_entry_price), float(p.current_price)
        verdict, pnl = exit_decision(entry, cur, STOP_PCT, TAKE_PCT, USE_TAKE)
        row = f"{p.symbol:<9} entry {entry:>10.2f}  now {cur:>10.2f}  pnl {pnl:+7.1%}"
        if verdict:
            actions += 1
            lines.append(f"{row}   -> SELL ({'stop-loss' if verdict=='STOP' else 'take-profit'})")
            log.info("SELL %s (%s, pnl %+.1f%%)", p.symbol, verdict, pnl*100)
            if not DRY_RUN:
                try: client.close_position(p.symbol)
                except Exception as e: log.warning("close %s failed: %s", p.symbol, e)
        else:
            lines.append(f"{row}   -> hold")
    tail = "  (DRY RUN — nothing submitted)" if DRY_RUN else ""
    lines += ["", f"{actions} exit(s) triggered.{tail}"]
    log.info("%d exits.%s", actions, tail)
    if actions or ALWAYS_NOTIFY:
        notify(f"Daily position check — {actions} exit(s)", "\n".join(lines))

if __name__ == "__main__":
    try: run()
    except Exception as e:
        import traceback
        notify("Exit manager CRASHED", f"{e}\n\n{traceback.format_exc()[-1200:]}"); raise
