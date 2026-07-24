# Quant Desk

Quant Desk is a fail-closed multi-agent quantitative research and trading
operations workspace for US equities and spot cryptocurrency. It combines typed
agent communication, deterministic portfolio/risk controls, paper and shadow
execution, official-adapter boundaries, audit reporting, and an institutional
operations console.

> Development is PAPER only. Live equities, live crypto, and autonomous
> execution are disabled. No strategy performance or benchmark outperformance
> is guaranteed, and this software is not investment advice.

**Static dashboard:** https://krisfigueiredo-ui.github.io/Quant-Desk/

## Safety defaults

```dotenv
TRADING_MODE=PAPER
LIVE_EQUITIES_ENABLED=false
LIVE_CRYPTO_ENABLED=false
AUTONOMOUS_EXECUTION_ENABLED=false
```

The code recognizes BACKTEST, PAPER, SHADOW, RESTRICTED_LIVE, STANDARD_LIVE,
PAUSED, CAPITAL_PRESERVATION, and KILLED. `STANDARD_LIVE` cannot be activated
from environment configuration. Restricted live requires separate offline
asset-specific readiness records and exact phrases; no API or dashboard route
can activate it.

## Architecture

The 13 typed agents cover equity and crypto scanning, technical, fundamental,
and event analysis, day and long-term strategies, strategy allocation,
portfolio management, deterministic risk, narrow execution, position/exit
monitoring, and append-only audit reporting.

Only the Execution Agent can request a broker action. It receives an immutable
proposed order, a fresh Risk Engine approval, a mode authorization, an
idempotency key, and a verified adapter. It cannot select a symbol, increase
quantity, reverse side, widen tolerance, or bypass a rejection.

See:

- [Architecture](docs/architecture.md)
- [Agent communication](docs/agent-communication.md)
- [Permissions matrix](docs/agent-permissions-matrix.md)
- [Risk controls](docs/risk-controls.md)
- [Operations runbook](docs/operations-runbook.md)
- [Live readiness](docs/live-readiness.md)

## Repository map

| Path | Purpose |
|---|---|
| `src/quant_trade_desk` | Typed agents, communication, risk, portfolio, execution, storage, API, reporting |
| `apps/api`, `apps/worker` | Runtime entry points |
| `dashboard` | Ten-view operations console |
| `config` | Conservative versioned configuration examples |
| `migrations` | Alembic schema migration |
| `pine` | TradingView research-input alerts |
| `reports` | Clearly labeled synthetic communication report |
| `tests` | Unit, integration, contract, security, dashboard, and failure-injection tests |
| `bots` | Retained legacy Alpaca paper-only bots |
| `dashboards` | Retained legacy read-only dashboards |
| `notebooks` | Retained research notebooks |

## Local setup

Python 3.11 or newer is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python scripts/verify_live_disabled.py
pytest
python scripts/run_api.py
```

Open `http://127.0.0.1:8000/ops/`. The development API uses clearly labeled
synthetic fixtures; they are not trading activity or performance.

PostgreSQL and Redis for the production-shaped local stack:

```bash
docker compose up -d postgres redis
QUANT_DESK_DATABASE_URL=postgresql+psycopg://quant_desk:quant_desk@localhost:5432/quant_desk \
  alembic upgrade head
```

Do not use the example database password outside local development.

## Broker boundaries

- Equities: a typed bridge for Robinhood’s officially documented Agentic
  Trading MCP. It remains unauthenticated and disabled until actual tool schemas
  and the dedicated account are verified.
- Crypto: official Robinhood Crypto Trading API v2, Ed25519 signing, spot
  limit/GTC only, BTC/ETH initial allowlist, verified precision/size, verified
  total equity, and full reconciliation. It remains disabled.
- PAPER and SHADOW never route to a live adapter.

Details are in [equity execution](docs/equity-execution.md) and
[crypto execution](docs/crypto-execution.md).

## Research honesty

Every new strategy remains `RESEARCH` and disabled. No new historical result is
claimed. `scripts/run_backtest.py` requires an explicit dataset, enforces
chronological train/validation/untouched-test splits, applies costs and stress,
and never promotes automatically. SPY is the primary equity benchmark; BTC and
ETH buy-and-hold are sleeve benchmarks where appropriate.

The retained legacy paper bots still use `paper=True` and `DRY_RUN=true` by
default. They are not wired into restricted-live adapters.

## Validation

```bash
ruff format --check src apps tests scripts
ruff check src apps tests scripts
mypy src apps scripts
pytest
node --check dashboard/app.js
python scripts/generate_communication_report.py --synthetic --sample
python scripts/verify_live_disabled.py
```

GitHub Actions run tests, type and style checks, migration validation, static
dashboard checks, secret scanning, dependency review, and Docker build. They
never run a live broker test.
