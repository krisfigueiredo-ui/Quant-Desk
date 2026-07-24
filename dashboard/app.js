"use strict";

const API = "/api/v1";
const state = {
  overview: null,
  agents: [],
  messages: [],
  scanner: [],
  strategies: [],
  risk: null,
  orders: [],
  settings: null,
  connected: false,
  lastRefresh: null,
};

const pageMeta = {
  overview: ["Portfolio overview", "Verified capital, exposure, benchmark context, and operating health in one view."],
  agents: ["Agent network", "Typed message topology, throughput, health, and auditable decision traces."],
  "day-desk": ["Intraday desk", "Separate equity and crypto candidates, limits, and trade-state monitoring."],
  "long-term": ["Long-horizon book", "Thesis-led holdings, target allocations, review state, and benchmark context."],
  scanner: ["Market scanner", "Deterministically ranked equity and crypto candidates with explicit eligibility."],
  strategies: ["Strategy research", "Validation state, allocation limits, plateau detection, and decay controls."],
  risk: ["Risk controls", "Non-bypassable exposure, loss, drawdown, data-quality, and kill-switch safeguards."],
  orders: ["Order ledger", "Proposals, authorization, broker state, fills, and reconciliation in one chain."],
  audit: ["Decision audit", "Structured agent messages, decision timelines, conversion metrics, and exports."],
  settings: ["System configuration", "Operating mode, adapters, data services, versions, and secret-safe status."],
};

const pageSections = {
  overview: "Monitor",
  agents: "Monitor",
  "day-desk": "Investment desks",
  "long-term": "Investment desks",
  scanner: "Investment desks",
  strategies: "Investment desks",
  risk: "Control & records",
  orders: "Control & records",
  audit: "Control & records",
  settings: "Control & records",
};

const escapeHtml = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const money = (value) => Number(value ?? 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const number = (value, digits = 1) => Number(value ?? 0).toLocaleString("en-US", { maximumFractionDigits: digits });
const pct = (value, digits = 1) => `${(Number(value ?? 0) * 100).toFixed(digits)}%`;
const time = (value) => value ? new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }) : "—";
const badge = (label, tone = "") => `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
const toneForStatus = (status) => {
  const value = String(status).toUpperCase();
  if (["HEALTHY", "ACCEPTED", "APPROVED", "CLEAR", "CONNECTED", "READY", "PAPER"].some((x) => value.includes(x))) return "good";
  if (["REJECTED", "FAILED", "KILLED", "UNAVAILABLE", "ERROR"].some((x) => value.includes(x))) return "bad";
  if (["IDLE", "REVIEW", "NOT_", "SYNTHETIC", "PENDING"].some((x) => value.includes(x))) return "warn";
  return "info";
};
const panel = (title, body, meta = "") => `<section class="panel"><div class="panel-head"><h2>${escapeHtml(title)}</h2><span>${escapeHtml(meta)}</span></div><div class="panel-body">${body}</div></section>`;
const table = (headers, rows, empty = "No records in the current view.") => {
  if (!rows.length) return `<div class="empty-state"><b>No records</b>${escapeHtml(empty)}</div>`;
  return `<div class="table-wrap"><table><thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
};
const metric = (label, value, sub = "", tone = "") => `<div class="metric-card"><div class="metric-label"><span>${escapeHtml(label)}</span></div><div class="metric-value ${tone}">${escapeHtml(value)}</div><div class="metric-sub">${escapeHtml(sub)}</div></div>`;

function lineChart(series) {
  if (!series?.length) return '<div class="empty-state"><b>No time series</b>Waiting for source-backed observations.</div>';
  const width = 800;
  const height = 220;
  const pad = 12;
  const values = series.flatMap((row) => [Number(row.portfolio), Number(row.spy)]).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const scaleX = (index) => pad + (index / Math.max(series.length - 1, 1)) * (width - pad * 2);
  const scaleY = (value) => height - pad - ((value - min) / Math.max(max - min, 1)) * (height - pad * 2);
  const pathFor = (field) => series.map((row, index) => `${index ? "L" : "M"}${scaleX(index).toFixed(1)},${scaleY(Number(row[field])).toFixed(1)}`).join(" ");
  const grid = [0.25, 0.5, 0.75].map((ratio) => `<line x1="0" x2="${width}" y1="${height * ratio}" y2="${height * ratio}"/>`).join("");
  return `<div class="chart-wrap"><div class="legend"><span><i></i>Portfolio</span><span><i class="secondary"></i>SPY</span></div><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Portfolio and SPY comparison"><defs><linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--accent)"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs><g class="chart-grid">${grid}</g><path class="chart-line" pathLength="1" d="${pathFor("portfolio")}"/><path class="chart-line secondary" pathLength="1" d="${pathFor("spy")}"/></svg></div>`;
}

function heading(page) {
  const [title, description] = pageMeta[page] || pageMeta.overview;
  const asOf = state.lastRefresh ? `REFRESHED ${state.lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "AWAITING DATA";
  document.querySelector("#page-heading").className = "page-heading";
  document.querySelector("#page-heading").innerHTML = `<div><div class="eyebrow">${escapeHtml(pageSections[page])}<i></i>${escapeHtml(page.replace("-", " "))}</div><h1>${escapeHtml(title)}</h1><p>${escapeHtml(description)}</p></div><div class="page-heading-meta">${escapeHtml(asOf)}<br>UTC SOURCE TIMESTAMPS</div>`;
}

function renderOverview() {
  const o = state.overview;
  if (!o) return offlineState();
  const metrics = [
    metric("Verified equity", money(o.total_verified_equity), `Peak ${money(o.peak_equity)}`),
    metric("Cash", money(o.cash), pct(o.cash / o.total_verified_equity) + " reserve"),
    metric("Total exposure", money(o.total_exposure), pct(o.total_exposure / o.total_verified_equity)),
    metric("Daily P&L", money(o.daily_pnl), "Paper fixture", o.daily_pnl >= 0 ? "positive" : "negative"),
    metric("Weekly P&L", money(o.weekly_pnl), "Unrealized + realized", o.weekly_pnl >= 0 ? "positive" : "negative"),
    metric("Drawdown", pct(o.current_drawdown), "5% stage-one threshold", o.current_drawdown <= -.05 ? "negative" : "warning"),
  ].join("");
  const allocation = `<div class="allocation"><div class="donut"></div><div class="legend-list"><div class="legend-row"><i></i><span>Equities</span><b>${pct(o.equity_exposure / o.total_verified_equity)}</b></div><div class="legend-row"><i></i><span>Crypto</span><b>${pct(o.crypto_exposure / o.total_verified_equity)}</b></div><div class="legend-row"><i></i><span>Cash</span><b>${pct(o.cash / o.total_verified_equity)}</b></div></div></div>`;
  const health = `<dl class="definition-list"><div><dt>Operating mode</dt><dd>${badge(o.operating_mode, toneForStatus(o.operating_mode))}</dd></div><div><dt>Kill switch</dt><dd>${badge(o.kill_switch, toneForStatus(o.kill_switch))}</dd></div><div><dt>Broker route</dt><dd>${escapeHtml(o.broker_connectivity)}</dd></div><div><dt>Open positions</dt><dd>${escapeHtml(o.open_positions)}</dd></div><div><dt>Open orders</dt><dd>${escapeHtml(o.open_orders)}</dd></div><div><dt>Active alerts</dt><dd class="${o.active_alerts ? "warning" : ""}">${escapeHtml(o.active_alerts)}</dd></div></dl>`;
  const strategyRows = [
    ["Long-term equity", o.long_term_exposure, "EQUITY", "PAPER"],
    ["Equity intraday", o.day_strategy_exposure, "EQUITY", "PAPER"],
    ["Crypto sleeve", o.crypto_exposure, "CRYPTO", "PAPER"],
  ].map(([name, exposure, asset, mode]) => `<tr><td><strong>${escapeHtml(name)}</strong></td><td class="mono">${money(exposure)}</td><td>${badge(asset, "info")}</td><td>${badge(mode, "warn")}</td></tr>`);
  return `<div class="synthetic-note">SYNTHETIC FIXTURE — representative operations data for UI validation; not account activity or strategy performance.</div><div class="grid metrics-grid section-gap">${metrics}</div><div class="grid two-col section-gap">${panel("Portfolio vs SPY", lineChart(o.series?.equity), "NORMALIZED · INTRADAY")}${panel("Capital allocation", allocation, "VERIFIED EQUITY BASIS")}</div><div class="grid two-col section-gap">${panel("Strategy sleeves", table(["Sleeve", "Exposure", "Asset", "Mode"], strategyRows), "NO LIVE CAPITAL")}${panel("System state", health, `AS OF ${time(o.as_of)}`)}</div>`;
}

function renderAgents() {
  const agents = state.agents;
  const nodes = ["Scanners", "Analysts", "Strategies", "Portfolio", "Risk", "Execution", "Broker", "Audit"].map((name, index, all) => `<div class="topology-node">${escapeHtml(name)}</div>${index < all.length - 1 ? '<span class="topology-arrow">→</span>' : ""}`).join("");
  const cards = agents.map((agent) => `<article class="agent-card"><div class="agent-top"><div><h3>${escapeHtml(agent.name)}</h3><p>${escapeHtml(agent.agent_id)} · v${escapeHtml(agent.version)}</p></div>${badge(agent.status, toneForStatus(agent.status))}</div><div class="agent-metrics"><div><small>Latency</small><b>${escapeHtml(agent.average_latency_ms)} ms</b></div><div><small>Messages</small><b>${escapeHtml(agent.messages_processed)}</b></div><div><small>Errors</small><b>${pct(agent.error_rate)}</b></div></div></article>`).join("");
  const trace = state.messages.map((message) => `<div class="timeline-row ${message.status === "REJECTED" ? "rejected" : ""}"><i class="timeline-marker"></i><span class="timeline-type">${escapeHtml(message.message_type)}</span><span class="timeline-summary"><b>${escapeHtml(message.agent_id)}</b> · ${escapeHtml(message.summary)}</span>${badge(message.status, toneForStatus(message.status))}</div>`).join("");
  const traceId = state.messages[0]?.trace_id || "NO_TRACE";
  return `<div class="grid equal-col">${panel("Live agent topology", `<div class="topology">${nodes}</div>`, "TYPED / EVENT-DRIVEN")}${panel("Trace filters", `<div class="toolbar"><input class="input" value="${escapeHtml(traceId)}" aria-label="Trace ID"><select class="select" aria-label="Message status"><option>All statuses</option><option>Rejected</option><option>Accepted</option></select><button class="button">Apply filter</button></div>`, `${agents.length} AGENTS`)}</div><div class="grid agent-grid section-gap">${cards || '<div class="empty-state">No agent heartbeats.</div>'}</div><div class="section-gap">${panel("Decision trace", `<div class="timeline">${trace}</div>`, traceId.slice(0, 12))}</div>`;
}

function renderDayDesk() {
  const candidates = state.scanner.filter((row) => ["EQUITY", "CRYPTO"].includes(row.asset_class));
  const rows = candidates.map((row) => `<tr><td>${badge(row.asset_class, row.asset_class === "CRYPTO" ? "info" : "")}</td><td><strong>${escapeHtml(row.symbol)}</strong></td><td class="mono">${number(row.score)}</td><td>${escapeHtml(row.trend)}</td><td>${pct(row.volatility)}</td><td>${escapeHtml(row.volume)}</td><td>${escapeHtml(row.liquidity)}</td><td>${badge(row.strategy_eligibility, "warn")}</td><td>${escapeHtml(row.rejection_reason || "—")}</td></tr>`);
  const limits = `<dl class="definition-list"><div><dt>Equity trades today</dt><dd>0 / 3</dd></div><div><dt>Crypto trades / 24h</dt><dd>0 / 3</dd></div><div><dt>Opening window</dt><dd>${badge("BLOCK FIRST 15M", "warn")}</dd></div><div><dt>Equity entry cutoff</dt><dd>Configured server-side</dd></div><div><dt>Daily loss budget</dt><dd class="positive">${pct(state.risk?.remaining_daily_loss_budget)}</dd></div><div><dt>Default order type</dt><dd>LIMIT</dd></div></dl>`;
  return `<div class="grid metrics-grid">${metric("Active equity day trades", "0", "No paper positions")}${metric("Active crypto day trades", "0", "24/7 schedule")}${metric("Equity trade count", "0 / 3", "Restricted-live cap")}${metric("Crypto trade count", "0 / 3", "Rolling 24 hours")}${metric("Daily loss used", pct(Math.abs(state.risk?.daily_loss || 0)), "1.0% maximum")}${metric("Open entries", "0", "No unresolved orders")}</div><div class="grid two-col section-gap">${panel("Ranked intraday candidates", table(["Asset", "Symbol", "Score", "Trend", "Vol", "Volume", "Liquidity", "Eligibility", "Restriction"], rows), "SYNTHETIC · PAPER ONLY")}${panel("Intraday limits", limits, "DETERMINISTIC")}</div><div class="section-gap">${panel("Active day positions", '<div class="empty-state"><b>No active paper day trades</b>Entry, stop, target, holding time, and P&amp;L will appear after a risk-approved paper fill.</div>', "EQUITY + CRYPTO SEPARATED")}</div>`;
}

function renderLongTerm() {
  const rows = state.strategies.filter((s) => s.time_horizon !== "INTRADAY").map((s) => `<tr><td><strong>${escapeHtml(s.name)}</strong><br><span class="mono">${escapeHtml(s.strategy_id)}</span></td><td>${badge(s.asset_class, "info")}</td><td>${escapeHtml(s.time_horizon)}</td><td>${badge(s.operating_mode, "warn")}</td><td>${pct(s.current_allocation)}</td><td>${pct(s.maximum_allocation)}</td><td>${escapeHtml(s.benchmark_comparison)}</td><td>${escapeHtml(s.decay_status)}</td></tr>`);
  const thesis = `<dl class="definition-list"><div><dt>Thesis</dt><dd>Not available — no source-backed holding</dd></div><div><dt>Counter-thesis</dt><dd>Required before a long-term intent</dd></div><div><dt>Next review</dt><dd>Not scheduled</dd></div><div><dt>Event risk</dt><dd>${badge("NO POSITION", "info")}</dd></div><div><dt>Rebalance action</dt><dd>NONE</dd></div></dl>`;
  return `<div class="grid metrics-grid">${metric("Long-term exposure", money(state.overview?.long_term_exposure), "Synthetic fixture")}${metric("Position cap", "5.0%", "Per symbol")}${metric("Sector cap", "20.0%", "Long-term sleeve")}${metric("Crypto long-term cap", "10.0%", "Total capital")}${metric("Validated holdings", "0", "No production data")}${metric("Rebalance state", "IDLE", "No pending action")}</div><div class="section-gap">${panel("Long-term strategy registry", table(["Strategy", "Asset", "Horizon", "Mode", "Allocated", "Maximum", "Benchmark", "Decay"], rows), "NO VALIDATED PERFORMANCE")}</div><div class="grid equal-col section-gap">${panel("Selected holding detail", thesis, "EMPTY STATE")}${panel("Target vs actual allocation", '<div class="empty-state"><b>No verified holdings</b>Target weight, cost basis, return, and thesis invalidation require reconciled position data.</div>', "ACCOUNT RECONCILIATION REQUIRED")}</div>`;
}

function renderScanner() {
  const rows = state.scanner.map((row) => `<tr><td><strong>${escapeHtml(row.symbol)}</strong></td><td>${badge(row.asset_class, "info")}</td><td class="mono">${escapeHtml(row.rank)}</td><td class="mono">${number(row.score)}</td><td>${escapeHtml(row.trend)}</td><td>${number(row.relative_strength, 2)}</td><td>${number(row.momentum, 2)}</td><td>${pct(row.volatility)}</td><td>${escapeHtml(row.liquidity)}</td><td>${badge(row.analyst_status, toneForStatus(row.analyst_status))}</td><td>${row.event_block ? badge("BLOCKED", "bad") : badge("CLEAR", "good")}</td><td>${escapeHtml(row.rejection_reason || "—")}</td></tr>`);
  return `${panel("Universe controls", '<div class="toolbar"><input id="scanner-search" class="input" type="search" placeholder="Search symbol" aria-label="Search scanner"><select class="select" aria-label="Asset class"><option>All asset classes</option><option>Equity</option><option>Crypto</option></select><select class="select" aria-label="Eligibility"><option>All eligibility</option><option>Paper only</option><option>Rejected</option></select><button class="button">Save filter</button></div>', `${state.scanner.length} CANDIDATES`)}<div class="section-gap">${panel("Ranked market candidates", table(["Symbol", "Asset", "Rank", "Score", "Trend", "Rel str", "Momentum", "Vol", "Liquidity", "Analyst", "Event", "Reason"], rows), "SORTABLE SOURCE SNAPSHOT")}</div>`;
}

function renderStrategies() {
  const rows = state.strategies.map((s) => `<tr><td><strong>${escapeHtml(s.name)}</strong><br><span class="mono">${escapeHtml(s.strategy_id)}</span></td><td>v${escapeHtml(s.version)}</td><td>${badge(s.asset_class, "info")}</td><td>${escapeHtml(s.time_horizon)}</td><td>${badge(s.operating_mode, "warn")}</td><td>${pct(s.current_allocation)}</td><td>${pct(s.maximum_allocation)}</td><td>${escapeHtml(s.out_of_sample_metrics ? "AVAILABLE" : "NOT RUN")}</td><td>${badge(s.plateau_status, "warn")}</td><td>${badge(s.decay_status, "warn")}</td></tr>`);
  return `<div class="synthetic-note">No strategy is promoted on unvalidated returns. Backtest, untouched test, walk-forward, cost stress, stability, and adequate samples are required.</div><div class="grid metrics-grid section-gap">${metric("Registered", state.strategies.length, "Research strategies")}${metric("Enabled live", "0", "Live disabled")}${metric("OOS validated", "0", "Results not fabricated")}${metric("Shadow eligible", "0", "Validation pending")}${metric("Plateau suspensions", "0", "Persistent when triggered")}${metric("Decay suspensions", "0", "Manual review required")}</div><div class="section-gap">${panel("Strategy registry", table(["Strategy", "Version", "Asset", "Horizon", "Mode", "Allocation", "Maximum", "OOS", "Plateau", "Decay"], rows), "AUTHENTICATED EDITS ONLY")}</div>`;
}

function renderRisk() {
  const r = state.risk;
  if (!r) return offlineState();
  const thresholds = r.thresholds.map((value, index) => `<div class="threshold ${index === r.thresholds.length - 1 ? "hard" : ""}"><b>${pct(value, 0)}</b><span>${["Notify", "Reduce 50%", "Entries off", "Live suspend", "Preserve", "Hard kill"][index]}</span></div>`).join("");
  const rejectionRows = r.recent_rejections.map((reason, index) => `<tr><td class="mono">R-${String(index + 1).padStart(3, "0")}</td><td>${badge("REJECTED", "bad")}</td><td><strong>${escapeHtml(reason)}</strong></td><td>Synthetic validation trace</td></tr>`);
  const controls = [
    ["Pause new trades", "Block new entries. Does not liquidate holdings.", "pause", "PAUSE NEW TRADES", "warning-button"],
    ["Switch equities to paper", "Requires server workflow; no dashboard endpoint is exposed.", "", "", ""],
    ["Switch crypto to paper", "Requires server workflow; no dashboard endpoint is exposed.", "", "", ""],
    ["Cancel opening orders", "Unavailable until a verified broker capability is present.", "", "", ""],
    ["Reduce risk", "Manual review path; deterministic limits still apply.", "", "", ""],
    ["Disable strategy", "Requires validated configuration workflow and audit record.", "", "", ""],
    ["Disconnect broker", "No authenticated live broker is connected.", "", "", ""],
    ["Emergency stop", "Persistently kills all new execution without an LLM.", "emergency-stop", "EMERGENCY STOP", "danger"],
  ].map(([title, description, action, phrase, style]) => `<div class="control-card"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p><button class="button ${style}" ${action ? `data-control="${action}" data-phrase="${phrase}"` : "disabled"}>${action ? "Open control" : "Unavailable"}</button></div>`).join("");
  return `<div class="grid metrics-grid">${metric("Current drawdown", pct(r.current_drawdown), "Verified equity required", "warning")}${metric("Daily loss", pct(r.daily_loss), "1.0% maximum")}${metric("Weekly loss", pct(r.weekly_loss), "3.0% maximum")}${metric("Position concentration", pct(r.position_concentration), "5.0% maximum")}${metric("Remaining loss budget", pct(r.remaining_daily_loss_budget), "Daily")}${metric("Kill switch", r.kill_switch, "Persistent state", toneForStatus(r.kill_switch) === "good" ? "positive" : "negative")}</div><div class="section-gap">${panel("Drawdown response ladder", `<div class="thresholds">${thresholds}</div>`, "NO AUTOMATIC RESET")}</div><div class="grid two-col section-gap">${panel("Allocation controls", `<dl class="definition-list">${Object.entries(r.asset_class_allocation).map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${pct(value)}</dd></div>`).join("")}</dl>`, "50% CASH MINIMUM")}${panel("Recent risk rejections", table(["ID", "State", "Reason", "Source"], rejectionRows), "SAFEGUARDS ACTIVE")}</div><div class="section-gap">${panel("Operator controls", `<div class="grid control-grid">${controls}</div>`, "AUTH + EXACT PHRASE + AUDIT")}</div>`;
}

function renderOrders() {
  const rows = state.orders.map((o) => `<tr><td class="mono">${escapeHtml(o.proposed_order_id).slice(0, 8)}</td><td>${time(o.created_at)}</td><td><strong>${escapeHtml(o.symbol)}</strong></td><td>${badge(o.asset_class, "info")}</td><td>${escapeHtml(o.side)}</td><td class="mono">${escapeHtml(o.quantity)} @ ${money(o.limit_price)}</td><td>${badge(o.risk_decision, toneForStatus(o.risk_decision))}</td><td><strong>${escapeHtml(o.reason)}</strong></td><td class="mono">${escapeHtml(o.trace_id).slice(0, 8)}</td><td>${escapeHtml(o.idempotency_state)}</td></tr>`);
  return `<div class="grid metrics-grid">${metric("Proposed", state.orders.length, "Synthetic trace")}${metric("Risk approved", "0", "No execution requests")}${metric("Submitted", "0", "No broker calls")}${metric("Partial fills", "0", "Reconciliation idle")}${metric("Filled", "0", "No fills")}${metric("Unknown state", "0", "Resubmission blocked")}</div><div class="section-gap">${panel("Order lifecycle", table(["Order", "Created", "Symbol", "Asset", "Side", "Quantity / limit", "Risk", "Reason", "Trace", "Idempotency"], rows), "PROPOSAL → RISK → EXECUTION → BROKER → FILL")}</div><div class="grid equal-col section-gap">${panel("Broker acknowledgements", '<div class="empty-state"><b>No broker acknowledgements</b>No risk-approved request reached an execution adapter.</div>', "PAPER ONLY")}${panel("Fill reconciliation", '<div class="empty-state"><b>No fill records</b>Partial fills and uncertain states will remain non-resubmittable until reconciled.</div>', "FAIL CLOSED")}</div>`;
}

function download(name, type, content) {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([content], { type }));
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}

function renderAudit() {
  const counts = state.messages.reduce((result, message) => {
    result[message.message_type] = (result[message.message_type] || 0) + 1;
    return result;
  }, {});
  const rejected = state.messages.filter((m) => m.status === "REJECTED").length;
  const rows = state.messages.map((m) => `<tr><td>${time(m.created_at)}</td><td>${escapeHtml(m.message_type)}</td><td><strong>${escapeHtml(m.agent_id)}</strong></td><td>${escapeHtml(m.symbol)}</td><td>${badge(m.status, toneForStatus(m.status))}</td><td>${escapeHtml(m.summary)}</td><td class="mono">${escapeHtml(m.trace_id).slice(0, 8)}</td></tr>`);
  const distribution = Object.entries(counts).map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("");
  return `<div class="grid metrics-grid">${metric("Messages", state.messages.length, "Current fixture trace")}${metric("Risk rejection rate", pct(rejected / Math.max(state.messages.length, 1)), "All message stages")}${metric("Signal → proposal", "100.0%", "Synthetic example")}${metric("Proposal → order", "0.0%", "Risk blocked")}${metric("Order → fill", "N/A", "No submitted order")}${metric("Prevented trades", "1", "Cash reserve safeguard")}</div><div class="grid two-col section-gap">${panel("Message distribution", `<dl class="definition-list">${distribution}</dl>`, "BY MESSAGE TYPE")}${panel("Report exports", '<p class="muted">Exports contain structured decision summaries only. Sensitive values are redacted and no private model chain-of-thought is stored.</p><div class="toolbar"><button id="export-json" class="button">Download JSON</button><button id="export-csv" class="button">Download CSV</button><a class="button" href="../reports/sample-agent-communication.html" target="_blank" rel="noopener">Printable sample</a></div>', "SYNTHETIC SAMPLE")}</div><div class="section-gap">${panel("Raw structured messages", table(["Time", "Type", "Agent", "Symbol", "Status", "Decision summary", "Trace"], rows), "SENSITIVE FIELDS REDACTED")}</div>`;
}

function renderSettings() {
  const s = state.settings;
  if (!s) return offlineState();
  const statusList = `<dl class="definition-list">${Object.entries(s).map(([key, value]) => `<div><dt>${escapeHtml(key.replaceAll("_", " "))}</dt><dd>${typeof value === "boolean" ? badge(value ? "TRUE" : "FALSE", value ? "bad" : "good") : escapeHtml(value)}</dd></div>`).join("")}</dl>`;
  const allowlistRows = [["SPY", "Equity", "Paper research"], ["QQQ", "Equity", "Paper research"], ["BTC-USD", "Crypto", "Manual capability discovery required"], ["ETH-USD", "Crypto", "Manual capability discovery required"]].map((row) => `<tr>${row.map((cell, index) => `<td>${index === 0 ? `<strong>${escapeHtml(cell)}</strong>` : escapeHtml(cell)}</td>`).join("")}</tr>`);
  return `<div class="grid equal-col">${panel("Runtime configuration", statusList, "SECRET VALUES NEVER DISPLAYED")}${panel("Activation boundary", '<div class="synthetic-note">Live activation is intentionally absent from this console.</div><p class="muted">Restricted live requires all readiness gates, local offline confirmation, a persisted authorization record, dedicated account verification, and separate exact phrases for equities and crypto. Standard live never activates automatically.</p><button class="button" disabled>Live activation unavailable</button>', "DELIBERATE LOCAL PROCEDURE")}</div><div class="grid equal-col section-gap">${panel("Symbol allowlists", table(["Symbol", "Asset class", "Status"], allowlistRows), "CONFIGURATION VERSION 1.0.0")}${panel("Integration health", '<dl class="definition-list"><div><dt>Robinhood Agentic MCP</dt><dd>NOT AUTHENTICATED</dd></div><div><dt>Robinhood Crypto API</dt><dd>NOT AUTHENTICATED</dd></div><div><dt>TradingView webhook</dt><dd>SIGNED INPUT BOUNDARY</dd></div><div><dt>GitHub deployment</dt><dd>STATIC MONITORING ONLY</dd></div><div><dt>Secrets</dt><dd>ENVIRONMENT COMPATIBLE</dd></div></dl>', "NO BROWSER BROKER CALLS")}</div>`;
}

function offlineState() {
  return '<div class="error-state"><b>Operations API unavailable</b>The static console never substitutes fake production data. Start the local API to load clearly labeled synthetic validation fixtures.<br><code>python scripts/run_api.py</code></div>';
}

const renderers = {
  overview: renderOverview,
  agents: renderAgents,
  "day-desk": renderDayDesk,
  "long-term": renderLongTerm,
  scanner: renderScanner,
  strategies: renderStrategies,
  risk: renderRisk,
  orders: renderOrders,
  audit: renderAudit,
  settings: renderSettings,
};

function currentPage() {
  const requested = window.location.hash.replace("#", "");
  return renderers[requested] ? requested : "overview";
}

function render() {
  const page = currentPage();
  document.querySelectorAll("#primary-nav a").forEach((item) => {
    const active = item.dataset.page === page;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  heading(page);
  document.querySelector("#page-content").innerHTML = renderers[page]();
  document.querySelector(".sidebar").classList.remove("open");
  bindDynamicEvents(page);
}

function bindDynamicEvents(page) {
  if (page === "risk") {
    document.querySelectorAll("[data-control]").forEach((button) => button.addEventListener("click", () => openControl(button.dataset.control, button.dataset.phrase)));
  }
  if (page === "audit") {
    document.querySelector("#export-json")?.addEventListener("click", () => download("quant-desk-messages-synthetic.json", "application/json", JSON.stringify(state.messages, null, 2)));
    document.querySelector("#export-csv")?.addEventListener("click", () => {
      const fields = ["message_id", "message_type", "agent_id", "symbol", "created_at", "status", "summary", "trace_id"];
      const csv = [fields.join(","), ...state.messages.map((row) => fields.map((field) => `"${String(row[field] ?? "").replaceAll('"', '""')}"`).join(","))].join("\n");
      download("quant-desk-messages-synthetic.csv", "text/csv", csv);
    });
  }
  if (page === "scanner") {
    const search = document.querySelector("#scanner-search");
    search?.addEventListener("input", () => {
      const query = search.value.trim().toLowerCase();
      document.querySelectorAll(".table-wrap tbody tr").forEach((row) => {
        row.hidden = Boolean(query) && !row.textContent.toLowerCase().includes(query);
      });
    });
  }
}

async function loadData() {
  const endpoints = ["overview", "agents", "messages", "scanner", "strategies", "risk", "orders", "settings"];
  document.querySelector("#connection-state").innerHTML = '<i class="dot dot-amber"></i><span>API connecting</span>';
  const results = await Promise.allSettled(endpoints.map(async (endpoint) => {
    const response = await fetch(`${API}/${endpoint}`, { headers: { Accept: "application/json" }, cache: "no-store" });
    if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
    return [endpoint, await response.json()];
  }));
  let successful = 0;
  results.forEach((result) => {
    if (result.status === "fulfilled") {
      const [endpoint, payload] = result.value;
      state[endpoint] = payload;
      successful += 1;
    }
  });
  state.connected = successful === endpoints.length;
  state.lastRefresh = new Date();
  const o = state.overview;
  document.querySelector("#environment-mode").textContent = o?.operating_mode || "OFFLINE";
  document.querySelector("#data-mode").textContent = o?.data_mode || "NO DATA";
  document.querySelector("#connection-state").innerHTML = state.connected ? '<i class="dot dot-green"></i><span>API connected</span>' : `<i class="dot dot-red"></i><span>API partial / offline (${successful}/${endpoints.length})</span>`;
  render();
}

const controlDialog = document.querySelector("#control-dialog");
const commandDialog = document.querySelector("#command-dialog");
const commandSearch = document.querySelector("#command-search");
const commandResults = document.querySelector("#command-results");
let pendingControl = null;
function openControl(action, phrase) {
  pendingControl = action;
  document.querySelector("#control-title").textContent = action === "emergency-stop" ? "Emergency stop" : "Pause new trades";
  document.querySelector("#control-description").textContent = `Enter the exact phrase “${phrase}”. The token and phrase are sent only to the local server and are never persisted in the browser.`;
  document.querySelector("#control-phrase").placeholder = phrase;
  document.querySelector("#control-feedback").textContent = "";
  controlDialog.showModal();
}

document.querySelector("#control-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const feedback = document.querySelector("#control-feedback");
  feedback.textContent = "Submitting deterministic control…";
  try {
    const response = await fetch(`${API}/controls/${pendingControl}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${document.querySelector("#control-token").value}` },
      body: JSON.stringify({ confirmation_phrase: document.querySelector("#control-phrase").value, reason: document.querySelector("#control-reason").value }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    feedback.className = "form-feedback positive";
    feedback.textContent = `${payload.status}: control recorded.`;
    setTimeout(() => { controlDialog.close(); loadData(); }, 700);
  } catch (error) {
    feedback.className = "form-feedback";
    feedback.textContent = `Control rejected: ${error.message}`;
  } finally {
    document.querySelector("#control-token").value = "";
  }
});

document.querySelector("#control-cancel").addEventListener("click", () => controlDialog.close());

function renderCommandResults(query = "") {
  const normalized = query.trim().toLowerCase();
  const results = Object.entries(pageMeta).filter(([page, [title, description]]) => (
    `${page} ${title} ${description} ${pageSections[page]}`.toLowerCase().includes(normalized)
  ));
  commandResults.innerHTML = results.length ? results.map(([page, [title, description]], index) => `
    <button class="command-result${index === 0 ? " active" : ""}" type="button" role="option" aria-selected="${index === 0}" data-command-page="${page}">
      <span class="command-index">${String(Object.keys(pageMeta).indexOf(page) + 1).padStart(2, "0")}</span>
      <span><b>${escapeHtml(title)}</b><small>${escapeHtml(description)}</small></span>
      <kbd>↵</kbd>
    </button>
  `).join("") : '<div class="command-empty">No matching workspace view</div>';
  commandResults.querySelectorAll("[data-command-page]").forEach((button) => button.addEventListener("click", () => {
    window.location.hash = button.dataset.commandPage;
    commandDialog.close();
  }));
}

function openCommandDialog() {
  renderCommandResults();
  if (!commandDialog.open) commandDialog.showModal();
  commandSearch.value = "";
  requestAnimationFrame(() => commandSearch.focus());
}

document.querySelector("#command-button").addEventListener("click", openCommandDialog);
document.querySelector("#command-close").addEventListener("click", () => commandDialog.close());
commandSearch.addEventListener("input", () => renderCommandResults(commandSearch.value));
commandSearch.addEventListener("keydown", (event) => {
  const results = [...commandResults.querySelectorAll("[data-command-page]")];
  if (!results.length) return;
  const currentIndex = Math.max(results.findIndex((item) => item.classList.contains("active")), 0);
  let nextIndex = currentIndex;
  if (event.key === "ArrowDown") nextIndex = (currentIndex + 1) % results.length;
  else if (event.key === "ArrowUp") nextIndex = (currentIndex - 1 + results.length) % results.length;
  else if (event.key === "Enter") {
    event.preventDefault();
    results[currentIndex].click();
    return;
  } else return;
  event.preventDefault();
  results.forEach((item, index) => {
    item.classList.toggle("active", index === nextIndex);
    item.setAttribute("aria-selected", String(index === nextIndex));
  });
  results[nextIndex].scrollIntoView({ block: "nearest" });
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    if (commandDialog.open) commandDialog.close();
    else openCommandDialog();
  }
});

document.querySelector("#refresh-button").addEventListener("click", loadData);
document.querySelector("#nav-toggle").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));
document.querySelector("#theme-toggle").addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("quant-desk-theme", theme);
});
window.addEventListener("hashchange", render);
setInterval(() => {
  document.querySelector("#utc-clock").textContent = `${new Date().toISOString().slice(11, 19)} UTC`;
}, 1000);
document.documentElement.dataset.theme = localStorage.getItem("quant-desk-theme") || "light";
loadData();
