# Multi-Agent Desk Implementation Plan

Date: 2026-07-24  
Branch: `feature/multi-agent-live-trading-desk`

## Outcome

Extend Quant Desk into a typed, auditable, event-driven quantitative trading
operations platform while preserving the existing paper-research tools. The
new system defaults to PAPER, treats live execution as unavailable until an
explicit offline activation procedure succeeds, and makes the deterministic
risk engine the non-bypassable authority.

This implementation builds a production-oriented safety foundation and a local
operations console. It does not claim that any strategy has an edge, does not
connect a funded account, and does not submit an order.

## Safety invariants

The following defaults are constants, configuration defaults, startup
assertions, dashboard labels, and test expectations:

```text
TRADING_MODE=PAPER
LIVE_EQUITIES_ENABLED=false
LIVE_CRYPTO_ENABLED=false
AUTONOMOUS_EXECUTION_ENABLED=false
```

- Only the deterministic execution service may call a broker adapter.
- The risk engine cannot call an adapter.
- Analysis, strategy, and portfolio agents cannot submit orders.
- PAPER and SHADOW modes cannot construct a live execution route.
- Live equity and crypto permissions are independent.
- Unsupported or undiscovered broker capabilities are rejected.
- Missing/stale market, account, database, queue, audit, clock, or broker state
  blocks new exposure.
- A hard kill persists through restart and has no online automatic reset.
- Existing Alpaca tools remain paper-only.

## Architecture

### Domain and configuration

- Pydantic v2 schemas for versioned events, agent contracts, orders, broker
  capabilities, risk context, account state, market state, health, and reports
- Versioned YAML example configuration for agents, strategies, risk limits,
  universes, brokers, and plateau rules
- Strict environment parsing with conservative defaults

### Communication

- Event envelope with message, trace, correlation, causation, idempotency,
  source, time, confidence, uncertainty, and schema-version fields
- In-memory development bus and durable SQL outbox/inbox semantics
- Redis Streams interface when configured
- Append-only audit records and dead-letter storage
- Idempotent message intake and expired-message rejection
- Server-Sent Events for read-only dashboard updates

### Agents

Create explicit definitions and deterministic service shells for:

1. Equity Market Scanner
2. Crypto Market Scanner
3. Technical Analyst
4. Fundamental and Quality Analyst
5. News and Event-Risk Analyst
6. Day-Trading Strategy Agent
7. Long-Term Investment Agent
8. Strategy Allocator
9. Portfolio Manager
10. Deterministic Risk Engine
11. Execution Agent
12. Position and Exit Monitor
13. Auditor and Communication Reporter

Every definition declares IDs, versions, inputs, outputs, prohibitions,
timeouts, retries, health, and metrics. Agent reasoning exposed to the system
is limited to structured evidence and decision summaries.

### Portfolio and risk

- Strategy-lot ledger and ownership-aware netting
- Conservative global, equity, crypto, day, long-term, sector, correlation,
  liquidity, spread, order-count, and loss limits
- Drawdown state machine at 5%, 10%, 15%, 20%, 25%, and 37%
- Plateau stages and strategy-decay quarantine
- Persistent kill switch and emergency-stop script independent of an LLM
- Machine-readable APPROVED, REJECTED, RISK_REDUCING_ONLY, and
  REQUIRES_MANUAL_REVIEW decisions

### Execution

- Shared typed `BrokerAdapter`
- Deterministic paper and shadow adapters
- Robinhood Agentic MCP capability bridge that accepts only runtime-discovered
  tool schemas; no desktop-session assumptions
- Robinhood Crypto API v2 signing and discovery client, disabled by default
- Narrow execution agent that revalidates an immutable proposed order and risk
  authorization without changing symbol, side, quantity, account, or tolerance
- Order-state machine with partial-fill, unknown-state, and reconciliation rules

### Data, API, and operations

- SQLAlchemy models and Alembic-ready metadata; SQLite for local tests and
  PostgreSQL configuration for production
- FastAPI endpoints for health, readiness, overview, agents, messages, traces,
  strategies, risk, orders, reports, and settings
- Signed TradingView webhook with size, timestamp, replay, signature,
  idempotency, symbol, and rate checks
- Authenticated, server-authorized control endpoints with typed confirmations
- JSON logs, Prometheus text metrics, redaction, health, and readiness

### Dashboard

Add a multi-page-feeling operations console under `dashboard/` using the
existing dark visual language:

- Executive Overview
- Agent Operations
- Day-Trading Desk
- Long-Term Desk
- Market Scanner
- Strategy Lab
- Risk Command Center
- Orders and Executions
- Communication and Audit Report
- Settings and Integrations

The console uses typed JSON/SSE APIs, responsive navigation, keyboard/focus
support, explicit stale/error/empty states, and persistent simulation labels.
No browser code can call a broker.

### Research and reporting

- Strategy registry and validation status
- Backtest metric utilities, split policy, transaction-cost stress,
  parameter-stability and bootstrap interfaces
- Daily communication report in HTML, JSON, and CSV
- Synthetic sample data labeled on every report surface
- No fabricated backtest results; unsupported validation remains NOT READY

## Test plan

### Unit

- Message validation, expiry, idempotency, and permissions
- Risk limits, drawdown stages, plateau/decay, and kill persistence
- Portfolio lot ownership and conflict resolution
- Execution immutability, mode gates, and capability gates
- Crypto signing, pair constraints, precision, and stale clocks
- TradingView signature, replay, duplicate, stale, and allowlist checks

### Integration and contract

- SQL audit and order lifecycle
- API authorization and dashboard-control boundaries
- Paper/shadow execution routes
- Broker adapter contract suites
- Report generation and trace completeness

### Failure injection

- Database, queue, audit, broker, market-data, and time-sync failures
- Partial fills, unknown order status, duplicate/replayed messages
- Persistent 37% kill switch across service restart

### Verification commands

```bash
python -m compileall -q bots scripts src apps
ruff check .
ruff format --check .
mypy src
pytest
python scripts/generate_communication_report.py --synthetic
python scripts/verify_live_disabled.py
```

The dashboard is then started locally, exercised with synthetic fixtures, and
checked for page loading and API/SSE connectivity. No broker credential is
required for verification.

## Delivery sequence

1. Documentation audit and plan
2. Package/configuration/message foundation
3. Risk, portfolio, persistence, and execution boundary
4. Agents, strategy registry, orchestration, and position monitor
5. API, TradingView intake, observability, and reports
6. Operations console
7. CI, Docker, security, and operations documentation
8. Full verification and final implementation report
9. Intentional commits, push, and draft pull request if authentication permits

## Explicitly deferred until user participation

- Connecting/authenticating the Robinhood Trading MCP
- Inspecting authenticated MCP `tools/list` schemas and account capabilities
- Creating or verifying a dedicated Agentic account
- Creating Robinhood Crypto API credentials
- Verifying jurisdiction/account eligibility
- Loading any production secret
- Paper/shadow observation periods with real account data
- Entering any restricted-live activation phrase
- Enabling either live adapter
- Standard-live activation

