# Deterministic risk controls

The Risk Engine is the final non-LLM veto. It returns only `APPROVED`,
`REJECTED`, `RISK_REDUCING_ONLY`, or `REQUIRES_MANUAL_REVIEW`, with reason codes
and a checksum of the order, account, market, mode, dependency, drawdown, and
limit context.

## Required checks

- operating-mode and asset-specific activation authorization;
- expected and freshly verified account identity/equity;
- allowlist, supported asset class, strategy authorization, and lot ownership;
- signal and market-data freshness, market session, first-15-minute gate,
  equity day-entry cutoff, earnings proximity, spread, and slippage;
- no duplicate, short, margin, leverage, options, derivatives, or oversell;
- buying power, cash reserve, gross, position, sector, strategy, asset-class,
  correlation, and total deployment caps;
- planned loss per trade, daily/weekly loss, trade counts, and open orders;
- plateau, decay, drawdown, persistent kill switch; and
- database, queue, audit, broker, and time synchronization health.

Crypto day positions use a 1% cap, other crypto positions 2%, and total crypto
allocation 10%. Equity day positions use 2%; equity and long-term positions use
5%. High-volatility crypto context halves an otherwise approved quantity.

## Drawdown ladder

| Drawdown | Deterministic response |
|---:|---|
| 5% | Notify; new size ×0.75; block low confidence |
| 10% | New size ×0.50; disable deteriorating expectancy; incident |
| 15% | No new entries; risk-reducing exits only; formal review |
| 20% | Suspend autonomous live; signals move to paper/shadow; manual reset |
| 25% | Capital preservation; every new entry blocked |
| 37% | Persistent hard kill; cancel unfilled opening orders when verified; forensic incident |

Drawdown uses verified total equity and the highest verified peak. A lower stage
is never skipped merely because the hard-kill threshold has not been reached.
The 37% kill persists through restart and never resets automatically.

## Plateau and decay

Windows of 20, 30, 60, 90, and 126 trading days evaluate benchmark-relative
return, risk-adjusted performance, expectancy, samples, opportunity, new equity
highs, turnover, costs, and slippage. Stage 1 reduces risk 25%; stage 2 reduces
50% and disables negative-expectancy strategies; stage 3 blocks entries, keeps
exit management, and moves the strategy to shadow. A flat week alone does
nothing, and plateau never triggers blanket liquidation.
