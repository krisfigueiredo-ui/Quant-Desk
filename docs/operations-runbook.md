# Operations runbook

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d postgres redis
alembic upgrade head
python scripts/verify_live_disabled.py
```

Keep `.env` local. Development does not require brokerage credentials.

## Start

```bash
source .venv/bin/activate
python scripts/run_paper.py
python scripts/run_api.py
```

In a second terminal, `python scripts/run_workers.py` starts the heartbeat worker.
Open `http://127.0.0.1:8000/ops/`. The sample data is explicitly synthetic.

For no-submission observation, set `TRADING_MODE=SHADOW` with every live flag
false and run `python scripts/run_shadow.py`.

## Validation

```bash
ruff format --check src apps tests scripts
ruff check src apps tests scripts
mypy src apps scripts
pytest
node --check dashboard/app.js
python -m compileall -q src apps scripts
QUANT_DESK_DATABASE_URL=sqlite:////tmp/quant-desk-migration.db alembic upgrade head
python scripts/generate_communication_report.py --synthetic --sample
python scripts/verify_live_disabled.py
```

The repository retains legacy scripts that predate strict formatting. CI scopes
the new quality gates to the multi-agent platform plus syntax-compiles legacy
paper bots.

## TradingView validation

Pine alerts must target an authenticated signing relay. The relay validates its
own credential, passes the exact body unchanged, and adds
`X-Quant-Desk-Signature: sha256=<HMAC-SHA256>`. Direct TradingView requests
cannot produce that header and are rejected.

Accepted webhooks are only accepted for review. They still pass fresh market
confirmation, scanner/analyst, strategy, portfolio, Risk Engine, Execution
Agent, adapter, reconciliation, and audit.

## Research validation

`run_backtest.py` requires a supplied CSV with `timestamp`, `split`,
`strategy_return`, `benchmark_return`, and `turnover`. It refuses absent data,
enforces chronological TRAIN/VALIDATION/TEST splits, applies supplied costs and
stress, and never promotes automatically. `run_walk_forward.py` requires at
least three independent result windows.

## Daily operations

- Verify mode, live flags, kill state, data freshness, dependency health, and
  account reconciliation.
- Review agent timeouts, dead letters, permission violations, rejected orders,
  unknown broker states, plateau/decay, and drawdown stage.
- Generate `quant-desk-report --synthetic` only for test data. Production report
  wiring must query the durable database and retain redaction.
- Archive incident and configuration checksums without credentials.

## Shutdown

Pause new trades first, wait for the message queue to drain, reconcile official
order states, stop workers, then stop API and local dependencies. Infrastructure
shutdown is not an exit signal and must not trigger blanket liquidation.
