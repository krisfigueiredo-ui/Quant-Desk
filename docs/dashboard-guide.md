# Operations dashboard guide

Start the local console:

```bash
source .venv/bin/activate
python scripts/run_api.py
```

Open `http://127.0.0.1:8000/ops/`. The API is local-only by default. Operations
data comes from `/api/v1`; the browser has no broker endpoints or secrets.

## Pages

1. Executive overview: verified-equity basis, exposure, P&L, benchmark chart,
   drawdown, and system state.
2. Agent operations: 13 agent cards, topology, filters, and typed decision trace.
3. Day-trading desk: separate equity/crypto candidates, schedules, counts, and
   loss budget.
4. Long-term desk: strategy/holding thesis state and allocations.
5. Market scanner: ranked, searchable candidates and rejection reasons.
6. Strategy lab: registry, validation, benchmark, allocation, plateau, and decay.
7. Risk command center: limits, drawdown ladder, rejections, and protected
   controls.
8. Orders and executions: proposal through reconciliation lifecycle.
9. Communication and audit: message metrics, structured trace, and JSON/CSV/HTML
   exports.
10. Settings and integrations: secret-safe status, allowlists, versions, and the
    offline activation boundary.

## Data labels and states

The bundled API returns synthetic fixtures for UI validation and labels them
`SYNTHETIC_FIXTURE`. They are not account activity or performance. If the API
is unavailable, the static console shows an error/empty state and does not
substitute production-looking values. PAPER, live-equity OFF, live-crypto OFF,
and autonomy OFF remain prominent.

The console includes loading, empty, error, connection, freshness, desktop,
mobile, keyboard, dark, and light states. UTC is stored; the browser displays
local time with a timezone label.

## Controls

Pause and emergency stop require a server API token, exact phrase, operational
reason, and audit metric. The token is a password input and is never persisted.
Other controls stay disabled until a genuine authenticated server workflow
exists. Live activation is intentionally absent.

GitHub Pages hosts the console shell and printable synthetic report, but cannot
access a local operations API or broker adapter.
