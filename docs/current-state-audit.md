# Current-State Audit

Date: 2026-07-24

Repository: `krisfigueiredo-ui/Quant-Desk`

Audited revision: `606e78f7e407aa909c4f61cc6acb935e9c31b226` (`origin/main`)

Working branch: `feature/multi-agent-live-trading-desk`

## Executive assessment

Quant Desk is a small, coherent paper-trading research repository rather than a
multi-service trading platform. It contains two scheduled factor/momentum
scripts, a paper-only exit guard, a research notebook, two static operational
dashboards, a read-only local Alpaca proxy, and a GitHub Pages workflow.

The project has useful research logic and a restrained institutional visual
language worth retaining. It has no application database, durable queue,
typed inter-agent protocol, API framework, authentication layer, formal test
suite, execution state machine, portfolio ledger, strategy-lot ownership,
deterministic portfolio risk engine, or live Robinhood adapter.

The safest extension path is additive: retain the existing bots, notebooks,
static dashboards, Kalshi snapshot, and Pages deployment while introducing a
new Python package and operations console. Existing Alpaca integrations remain
paper-only compatibility surfaces. All new broker integrations must fail
closed, and live execution remains disabled.

## Git and repository state

- `origin`: `https://github.com/krisfigueiredo-ui/Quant-Desk.git`
- Default remote branch: `origin/main`
- Audit began from a clean working tree.
- The feature branch was created from `origin/main`.
- The history is short and linear on `main`, beginning with a bulk upload on
  2026-07-07 and followed by dashboard, proxy, workflow, and snapshot cleanup
  on 2026-07-18.
- `origin/claude/fix-repo-webapp` contains a historical
  `.github/workflows/paper_bots.yml` not present on `main`. The README and
  `CLAUDE.md` still refer to that missing workflow.
- No user changes were present to preserve when the feature branch was created.

## Existing architecture

```text
GitHub Actions ──refreshes──> static Kalshi JSON ──read by──> static dashboard
       │
       └──deploys index + dashboards + data to GitHub Pages

Local operator ──starts──> read-only Python HTTP proxy ──reads──> Alpaca paper API
                                              │
                                              └──serves static dashboard

Scheduled/manual Python scripts ──read──> yfinance + Alpaca paper account
                                └──optionally submit PAPER orders only

Jupyter notebook ──downloads──> yfinance ──runs──> research/backtest/ML diagnostics
```

There is no shared domain model between the scripts, no service orchestration,
and no persistent source of truth.

## Technology stack

- Python scripts targeting Python 3.12 in CI
- `pandas`, `numpy`, `yfinance`, and `alpaca-py`
- Jupyter/nbformat, Matplotlib, and scikit-learn for research
- Plain HTML, CSS, and browser JavaScript for the dashboards
- Python standard-library `ThreadingHTTPServer` for the local read-only proxy
- GitHub Actions and GitHub Pages for validation and static deployment
- JSON snapshot storage for Kalshi public market data

No package metadata (`pyproject.toml`), database, migrations, backend framework,
Node/TypeScript frontend, Docker configuration, infrastructure-as-code, or
Pine scripts currently exist.

## Existing features

### Equity paper strategy

`bots/auto_paper_trader.py`:

- Curated, values-oriented 31-name equity universe across eight themes
- SPY benchmark and 200-day regime filter
- Cross-sectional blend of 12-1 momentum, price trend, inverse volatility, and
  an RSI-derived heuristic labeled as value
- Winsorized z-scores, top-eight selection, inverse-volatility weights,
  20% per-name cap, 95% deployment target, and monthly rebalancing
- Paper Alpaca account, `paper=True`, and `DRY_RUN=true` by default
- Optional Slack and email notifications
- Market-order rebalancing and complete closure of names leaving the selection

### Crypto paper strategy

`bots/auto_paper_trader_crypto.py`:

- Alpaca-supported crypto universe with 19 configured pairs
- 30/90-day relative momentum, 50-day asset trend, BTC 200-day regime filter
- Weekly rebalancing, inverse-volatility sizing, 30% per-token cap, and 95%
  deployment target
- Paper Alpaca account and dry-run default
- Market orders with GTC when dry-run is deliberately disabled

### Exit guard

`bots/exit_manager.py`:

- Daily paper-position stop-loss and optional take-profit checks
- Defaults to a 15% stop and 40% take-profit
- Direct full-position closes in paper mode when dry-run is disabled
- Does not distinguish strategy ownership or equity from crypto lots

### Research notebook

`notebooks/impact_quant_strategy.ipynb` includes:

- Transparent factor scoring and action grades
- Target allocation and trade-list calculation
- Monthly walk-forward-style historical portfolio construction
- Transaction-cost deduction based on turnover
- SPY and equal-weight-universe comparisons
- CAGR, volatility, Sharpe, Sortino, drawdown, and hit-rate metrics
- Factor information-coefficient analysis
- Publication-decay haircuts and t-stat diagnostics
- Block-bootstrap Monte Carlo paths
- Expanding-window, embargoed logistic-regression and gradient-boosting tests

The notebook is intentionally skeptical, but it does not implement a truly
untouched test set, point-in-time membership, delisting treatment, realistic
limit-order fills, partial fills, latency, bid/ask histories, or corporate
action audit records.

### Dashboards

`index.html` links to:

- `dashboards/bot_dashboard.html`: responsive paper-account monitor with
  representative hosted demo data and automatic discovery of the read-only
  local Alpaca proxy
- `dashboards/kalshi_signals.html`: public-snapshot integrity screen for
  two-sided price gaps, depth, fees, and freshness

The visual system uses a dark neutral background, compact cards, thin borders,
muted typography, blue accents, green/red state colors, monospace values,
responsive grids, focus indicators, and reduced-motion support. This language
should be retained.

### Integrations

- Alpaca paper trading through `alpaca-py`
- Alpaca paper read-only REST proxy
- Yahoo Finance through `yfinance`
- Kalshi public Trade API v2 snapshot fetch
- Optional Slack webhook and SMTP notifications
- GitHub Pages deployment

There is no Robinhood integration, TradingView receiver, database, Redis,
Prometheus endpoint, or secret manager.

## Existing tests and CI

- There is no `tests/` directory.
- The `pylint.yml` workflow compiles Python sources and validates notebook JSON.
  Despite its name, it does not run Pylint.
- The Pages workflow refreshes Kalshi data and deploys the static site.
- No unit, integration, contract, security, failure-injection, visual,
  migration, frontend build, dependency-review, or Docker tests exist.
- No live broker test runs in CI.

## Weaknesses and technical debt

1. Execution, signal generation, sizing, account reads, and notification logic
   are coupled in single scripts.
2. Strategies can call broker submission methods directly.
3. Full-position closes can mix unrelated strategy ownership.
4. There is no idempotency key, duplicate-order guard, durable order lifecycle,
   fill reconciliation, or unknown-state quarantine.
5. Risk controls are local strategy settings rather than portfolio authority.
6. Equity and crypto scripts each target 95% account deployment, which can
   conflict and exceed a combined risk budget.
7. The crypto asset-discovery exception path fails open to the full configured
   universe.
8. Market-data timestamps and quality are not propagated into decisions.
9. The equity bot calls an RSI-derived price heuristic “value”; it is not a
   fundamental valuation factor.
10. Logging is unstructured and may include upstream exception text.
11. The proxy returns exception messages to the browser and lacks explicit
    security headers, rate limits, authentication, and request-size controls.
12. Static dashboard demo mode falls back silently when the proxy fails.
13. The README refers to a workflow missing from `main`.
14. Python dependencies are broad lower bounds with no lock or audit policy.
15. Configuration is embedded in source files and has no schema or version.

## Security concerns

- The existing `.gitignore` and environment-only credential pattern are sound
  foundations.
- The Alpaca proxy is bound to localhost and exposes only GET routes, but it
  should not reflect raw exception details and should add security headers.
- Slack and SMTP code can send operational content to third parties without
  a structured redaction boundary.
- No centralized secret redaction, audit integrity check, signed webhook,
  replay prevention, authorization policy, CSRF policy, or rate limiter exists.
- No branch-protection, dependency review, CodeQL, or secret-scanning workflow
  is represented in the repository.
- No current tracked file contains an obvious credential; placeholder keys in
  `.env.example` are non-secret.

## Data-quality concerns

- `yfinance` is convenient research data, not an execution-quality,
  point-in-time, contractually supported source.
- The hand-curated equity universe introduces selection and survivorship bias.
- Delisted securities and historical index membership are absent.
- The scripts do not validate timestamps, exchange sessions, quote spreads,
  or corporate actions before producing orders.
- The Kalshi snapshot is a sampled static view and must remain labeled as such.
- No provenance table links data versions to decisions.
- The committed Kalshi snapshot can be stale by design and must never be
  presented as live execution data.

## Official Robinhood capability review

Reviewed on 2026-07-24:

- Robinhood Agentic Trading overview:
  <https://robinhood.com/us/en/support/articles/agentic-trading-overview/>
- Robinhood Trading MCP tool overview:
  <https://robinhood.com/us/en/support/articles/trading-with-your-agent/>
- Robinhood Crypto Trading API:
  <https://docs.robinhood.com/crypto/trading/>

Official documentation states that the Trading MCP can read all Robinhood
accounts but can place trades only in a dedicated Agentic account. The
documented equity surface includes account/portfolio reads, equity positions,
quotes, tradability, order review, order placement, cancellation, order
history, technical indicators, earnings data, and scans. Current Agentic order
support is documented for long equities and options; this project prohibits
options.

The Robinhood Trading MCP is not connected in this development environment, so
its authenticated `tools/list` schemas and account-scoped capabilities could
not be inspected. The application therefore must not assume a persistent
server can call a desktop/Codex MCP session. The implementation will expose a
capability-discovery contract and a human-operated/bridge boundary that remains
disabled until an authenticated runtime supplies and verifies the exact tools.

The official Crypto Trading API v2 documents Ed25519 request signing using the
API key, Unix timestamp, request path, HTTP method, and exact body. It exposes
account, trading-pair, holdings, best-price, estimated-price, order, and
cancellation endpoints. Only uppercase USD pairs marked
`is_api_tradable=true` are eligible. The API requires an account number,
client-provided UUID for idempotency, precision/minimum/maximum rules, and
reconciliation. No credential or funded account was connected during this
audit.

## Files retained unchanged

- `notebooks/impact_quant_strategy.ipynb`
- `notebooks/Colab_Launcher.ipynb`
- `data/kalshi_snapshot.json`
- `research/SETUP_paper_trader.md`
- Existing commit history

The existing bots and dashboards will remain available; where edited, changes
will be compatibility- and safety-oriented rather than wholesale replacement.

## Files expected to be modified

- `README.md`
- `CLAUDE.md`
- `.env.example`
- `.gitignore`
- `requirements.txt`
- `index.html`
- `.github/workflows/pylint.yml`
- `.github/workflows/pages.yml` only if the static deployment needs the new
  operations console

## New files expected

- `pyproject.toml`, `docker-compose.yml`, `CONTRIBUTING.md`, `SECURITY.md`
- `src/quant_trade_desk/` package for configuration, communication, agents,
  strategies, risk, portfolio, execution, storage, API, observability, reports,
  and TradingView intake
- `apps/api/` and `apps/worker/` entrypoints
- `dashboard/` operations console assets
- Versioned example configuration under `config/`
- Scripts for API/workers/backtests/reports/reconciliation/emergency stop
- Unit, integration, contract, security, failure-injection, dashboard, and
  end-to-end tests
- Documentation for architecture, communication, permissions, broker
  boundaries, risk, operations, incidents, and live readiness
- CI validation and security workflows
- Sample synthetic communication report

## Migration risks

- Existing paper scripts use direct broker calls; routing them through the new
  architecture immediately would be a behavioral rewrite. They will remain
  compatibility tools while the new desk starts in PAPER mode.
- Adding a database creates schema-management and deployment obligations.
- Redis/PostgreSQL may not be available to every local user; SQLite and an
  in-memory bus are required only as explicit development fallbacks.
- Live broker capability discovery cannot be completed without user-driven
  authentication and account verification.
- The static Pages site cannot safely host authenticated control surfaces.
  It will remain a read-only demonstration; authenticated operations run
  locally or in a separately secured deployment.
- Strategy results in the current notebook are not sufficient evidence for
  live capital allocation.

## Recommended implementation sequence

1. Establish packaging, configuration, typed messages, audit storage, and
   deterministic operating-mode controls.
2. Implement portfolio ledger, strategy-lot ownership, risk limits, drawdown,
   plateau/decay states, kill-switch persistence, and failure-closed decisions.
3. Implement paper/shadow adapters and a narrow execution state machine.
4. Add disabled Robinhood capability adapters and documented bridge boundaries.
5. Add deterministic agent shells, orchestration, scanning/assessment models,
   strategy registry, portfolio conflict resolution, and position monitoring.
6. Add FastAPI read/stream/control surfaces plus signed TradingView intake.
7. Extend the dashboard using the existing visual language and explicit
   synthetic/paper/live labeling.
8. Add report generation, metrics, health, and failure-injection tests.
9. Add CI, Docker development services, security review, and full docs.
10. Run local verification. Do not activate or call any live broker surface.
