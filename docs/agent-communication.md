# Agent communication protocol

## Architecture

Every transition is a new immutable, typed `AgentMessage`. Agents cannot edit
prior messages. The message bus validates schema, expiry, permissions, routing,
idempotency, and sensitive-field policy before a message is accepted. Invalid
messages go to a dead-letter record with a machine-readable reason.

```mermaid
flowchart LR
  P["Producer"] --> V{"Schema + permission<br/>+ expiry + duplicate"}
  V -->|"valid"| Q["Durable stream"]
  V -->|"invalid"| D["Dead-letter queue"]
  Q --> C["Authorized consumer"]
  C --> N["New immutable message"]
  N --> Q
  Q --> A["Append-only auditor"]
  A --> T["Trace / report / dashboard"]
```

PostgreSQL is the durable source of truth. Redis Streams is the intended
real-time transport. SSE carries read-only updates to the console. The
in-memory implementations are test substitutes, not production durability.

## Envelope schema

| Field | Purpose |
|---|---|
| `message_id` | Globally unique immutable message |
| `message_type` / `schema_version` | Versioned payload contract |
| `trace_id` | Complete source-to-outcome decision chain |
| `correlation_id` | Related business operation |
| `causation_id` | Immediately preceding message |
| `agent_id` / `agent_version` | Accountable producer |
| `strategy_id` | Strategy ownership |
| `asset_class` / `symbol` | Explicit asset binding |
| `created_at` / `data_timestamp` / `expires_at` | UTC lifecycle and freshness |
| `confidence` / `uncertainty` | Bounded declared uncertainty, never hidden reasoning |
| `source_references` | Timestamped, checksummed evidence references |
| `payload` | Type-discriminated Pydantic payload |
| `status` | Created, accepted, rejected, expired, duplicate, or failed |
| `idempotency_key` | Duplicate suppression |

Messages reject credential-like keys. Logs and reports retain structured facts,
metrics, evidence, rules, and decision summaries; they never retain private
chain-of-thought.

## Lifecycle, retry, timeout, and failure behavior

1. Producer creates a frozen message with a timezone-aware data timestamp and
   expiry.
2. Permission routing verifies that the producer may emit that message type.
3. Idempotency claims the key. A repeat becomes `DUPLICATE` and is not replayed.
4. The bus persists before delivering to an authorized consumer.
5. A consumer emits a new message referencing the predecessor.
6. Transient analysis failures retry at most twice with bounded backoff.
7. Risk and execution authorization do not retry an ambiguous action.
8. Expired inputs are rejected, not refreshed implicitly.
9. Unknown broker state prevents resubmission until official reconciliation.
10. Database, queue, audit, broker, or time-sync failure blocks new exposure.

No timeout means approval. If a required agent does not respond, orchestration
emits a failed health/audit event and the decision chain closes without an
order.

## Conflict resolution

The Portfolio Manager owns netting, but each position remains partitioned by
`strategy_lot_id`. A day strategy cannot sell a long-term lot. Opposing intents
produce a `ConflictEvent`; explicit ownership, risk reduction, configured
priority, and cash/exposure rules resolve it. Duplicate proposals are
idempotently suppressed. Unresolved ownership or quantity conflicts are
rejected.

## Equity day-trade flow

```mermaid
sequenceDiagram
  participant M as Market data
  participant S as Equity scanner
  participant A as Analysts
  participant D as Day strategy
  participant P as Portfolio Manager
  participant R as Risk Engine
  participant E as Execution Agent
  participant B as Broker adapter
  participant U as Auditor
  M->>S: MarketObservation
  S->>A: ScannerCandidate
  A->>D: TechnicalAssessment + EventRiskAssessment
  D->>P: TradeIntent (day strategy lot)
  P->>R: ProposedOrder
  R->>R: session, freshness, spread, loss, exposure, ownership
  R->>E: RiskDecision(APPROVED, 15s TTL)
  E->>B: immutable ExecutionRequest + idempotency key
  B-->>E: BrokerAcknowledgement
  E->>B: reconcile official status
  B-->>E: FillUpdate or terminal state
  E->>U: complete trace
```

The first 15 equity-market minutes are blocked by default; the day-entry cutoff,
earnings proximity, position cap, and daily trade count are deterministic risk
inputs.

## Crypto day-trade flow

```mermaid
sequenceDiagram
  participant S as Crypto scanner
  participant A as Analysts
  participant D as Crypto day strategy
  participant P as Portfolio Manager
  participant R as Risk Engine
  participant E as Execution Agent
  participant C as Robinhood Crypto v2
  S->>A: allowlisted ScannerCandidate
  A->>D: fresh technical + event assessments
  D->>P: TradeIntent (spot, limit, GTC)
  P->>R: ProposedOrder
  R->>R: verified total equity, allocation, spread, precision, volatility
  R->>E: APPROVED or smaller high-volatility quantity
  E->>C: signed official API request
  C-->>E: acknowledgement (not a fill)
  E->>C: order reconciliation
```

Only BTC and ETH are initially allowlisted, and only when official discovery
confirms account, symbol, precision, size, and tradability.

## Long-term investment flow

```mermaid
sequenceDiagram
  participant F as Fundamental analyst
  participant T as Technical analyst
  participant N as Event-risk analyst
  participant L as Long-term agent
  participant A as Strategy Allocator
  participant P as Portfolio Manager
  participant R as Risk Engine
  F->>L: facts, calculations, estimates, missing data
  T->>L: trend and invalidation
  N->>L: event risks and source times
  L->>A: thesis, counter-thesis, horizon, uncertainty
  A->>P: capped allocation recommendation
  P->>R: strategy-owned ProposedOrder
  R-->>P: risk decision
```

Ordinary intraday noise does not trigger long-term exits. Thesis invalidation,
scheduled review, event state, position and sector caps remain explicit.

## Rejected-trade flow

```mermaid
sequenceDiagram
  participant P as Portfolio Manager
  participant R as Risk Engine
  participant E as Execution Agent
  participant U as Auditor
  P->>R: ProposedOrder
  R-->>P: REJECTED(CASH_RESERVE_LIMIT)
  R->>U: immutable RiskDecision + context checksum
  Note over E: Receives no execution request
  U-->>U: count trade prevented by safeguard
```

## Kill-switch flow

```mermaid
sequenceDiagram
  participant X as Operator / drawdown service
  participant K as Persistent kill switch
  participant R as Risk Engine
  participant E as Execution Agent
  participant U as Auditor
  X->>K: exact emergency action or 37% drawdown
  K->>K: fsync persistent KILLED state
  K->>R: KillSwitchEvent
  R-->>E: reject every new execution
  K->>U: incident + forensic event
  Note over K: Never resets automatically
```

The emergency-stop API is deterministic and requires authentication plus
`EMERGENCY STOP`. Offline hard-kill reset is deliberately outside all agents and
must follow the incident runbook.
