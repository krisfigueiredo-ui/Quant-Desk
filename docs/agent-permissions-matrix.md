# Agent permissions matrix

`A` means allowed by the typed permission registry. `D` means denied. Broker
adapters are services, not analytical agents. A permitted action still requires
valid mode, data, risk, account, and kill-switch state.

| Agent | Market data | Account data | Signals | Propose positions | Approve risk | Request execution | Submit | Cancel | Secrets | Config | Activate live | Reset kill |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Equity scanner | A | D | D | D | D | D | D | D | D | D | D | D |
| Crypto scanner | A | D | D | D | D | D | D | D | D | D | D | D |
| Technical analyst | A | D | D | D | D | D | D | D | D | D | D | D |
| Fundamental analyst | A | D | D | D | D | D | D | D | D | D | D | D |
| News/event analyst | A | D | D | D | D | D | D | D | D | D | D | D |
| Day-trading strategy | A | D | A | D | D | D | D | D | D | D | D | D |
| Long-term strategy | A | D | A | D | D | D | D | D | D | D | D | D |
| Strategy Allocator | A | D | D | D | D | D | D | D | D | D | D | D |
| Portfolio Manager | A | A* | D | A | D | D | D | D | D | D | D | D |
| Deterministic Risk Engine | A | A* | D | D | A | D | D | D | D | D | D | D |
| Execution Agent | A* | A* | D | D | D | A | A* | A* | D | D | D | D |
| Position/exit monitor | A | A* | A** | D | D | D | D | D | D | D | D | D |
| Auditor/reporter | A* | A* | D | D | D | D | D | D | D | D | D | D |
| Verified broker adapter | A* | A* | D | D | D | D | A* | A* | runtime only | D | D | D |
| Offline operator workflow | D | A | D | D | D | D | D | D | local prompt | versioned files | A* | A* |

\* Minimum fields only and only when the role requires them. The Execution Agent
never receives credentials; an adapter process reads secrets from its runtime
secret provider.

\** Exit intents only. They remain subject to strategy-lot ownership and the
Risk Engine.

## Deny-by-default enforcement

- Message types are mapped to required permissions.
- Unknown agents and unknown message types are rejected.
- Analysis agents have no adapter object or submit method.
- Only `ExecutionAgent` can invoke a `BrokerAdapter`, and it first verifies an
  immutable approval and authorization.
- The dashboard has no broker URL, credential, or live-activation endpoint.
- Live activation and kill reset are never granted to an agent or LLM.
