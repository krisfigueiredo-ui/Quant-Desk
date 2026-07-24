# CLAUDE.md — Quant Desk contributor guide

## Purpose

Quant Desk is a paper-default multi-agent quantitative research and operations
desk. It contains retained Alpaca paper bots plus a new typed control plane.
Research may propose; deterministic services calculate, authorize, execute, and
audit.

## Non-negotiable rules

- Keep `TRADING_MODE=PAPER`, both live flags false, and autonomy false during
  development and CI.
- Never submit a real order, connect a funded account without the user, store a
  credential, use browser automation for brokerage, or call an unofficial
  broker endpoint.
- Never change legacy Alpaca clients from `paper=True`.
- Never let a dashboard, TradingView alert, analysis agent, Portfolio Manager,
  or Risk Engine call a broker.
- Fail closed on stale/unknown account, market, risk, audit, database, queue,
  time, broker, or order state.
- Acknowledgement is not fill; unknown state blocks resubmission.
- Strategy lots are isolated. A day strategy cannot sell a long-term lot.
- Do not manufacture backtest data, tune against untouched tests, or claim
  benchmark outperformance.
- Live activation and hard-kill reset are offline human procedures, never LLM
  actions.

## Key paths

```text
src/quant_trade_desk/
  agents/ communication/ strategies/ risk/ portfolio/
  execution/ storage/ observability/ api/ reports/ tradingview/
apps/                  API and worker entry points
dashboard/             operations console; no broker calls
config/                conservative examples
migrations/            Alembic
tests/                 unit/integration/contract/security/failure/dashboard
bots/ dashboards/      retained legacy paper-only tools
```

Read `docs/architecture.md`, `docs/agent-communication.md`,
`docs/agent-permissions-matrix.md`, and `docs/risk-controls.md` before changing
control or execution boundaries.

## Validation

Use Python 3.11+:

```bash
source .venv/bin/activate
ruff format --check src apps tests scripts
ruff check src apps tests scripts
mypy src apps scripts
pytest
node --check dashboard/app.js
python scripts/verify_live_disabled.py
```

Legacy bots predate strict Ruff formatting; syntax-compile them rather than
performing unrelated rewrites. Before staging, review the diff and scan for
secrets, account numbers, private records, raw databases, and unredacted logs.

## Execution adapters

Robinhood Agentic equity execution is a typed official-MCP bridge, not an
invented REST client. Robinhood Crypto uses the documented v2 API and Ed25519
signing. Both remain disabled until authenticated capability discovery,
dedicated account verification, reconciliation, observation, and separate
offline readiness records succeed.
