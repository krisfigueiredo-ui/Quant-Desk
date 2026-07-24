"""Daily agent communication report in HTML, JSON, and CSV."""

# ruff: noqa: E501  # Embedded printable CSS is clearer as complete declarations.

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from quant_trade_desk.api.fixtures import (
    agents_fixture,
    messages_fixture,
    orders_fixture,
    overview_fixture,
    risk_fixture,
)
from quant_trade_desk.observability.logging import redact


def build_synthetic_report() -> dict[str, Any]:
    messages = messages_fixture()
    agents = agents_fixture()
    orders = orders_fixture()
    overview = overview_fixture()
    risk = risk_fixture()
    by_agent = Counter(str(row["agent_id"]) for row in messages)
    by_type = Counter(str(row["message_type"]) for row in messages)
    traces: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in messages:
        traces[str(row["trace_id"])].append(row)
    rejected = [row for row in messages if str(row.get("status", "")).upper() == "REJECTED"]
    return {
        "report_metadata": {
            "title": "Quant Desk Agent Communication Report",
            "generated_at": datetime.now(UTC).isoformat(),
            "report_date": date.today().isoformat(),
            "data_mode": "SYNTHETIC_FIXTURE",
            "is_synthetic": True,
            "disclaimer": (
                "This sample contains synthetic validation data and does not "
                "represent real trading activity."
            ),
        },
        "executive_summary": {
            "summary": (
                "The synthetic decision trace was stopped before execution "
                "because the proposed entry would breach the cash-reserve limit."
            ),
            "operating_mode": overview["operating_mode"],
            "live_equities_enabled": False,
            "live_crypto_enabled": False,
            "kill_switch": risk["kill_switch"],
            "recommended_operational_actions": [
                "Keep PAPER mode active.",
                "Review the rejected cash-reserve scenario.",
                "Complete broker capability discovery only with operator participation.",
            ],
        },
        "system_operating_mode": "PAPER",
        "agent_health": agents,
        "broker_health": {
            "paper_adapter": "READY",
            "robinhood_agentic_mcp": "NOT_AUTHENTICATED",
            "robinhood_crypto_api": "NOT_AUTHENTICATED",
        },
        "market_data_health": {
            "status": "SYNTHETIC",
            "freshness": "FIXTURE",
            "execution_eligible": False,
        },
        "total_messages": len(messages),
        "messages_by_agent": dict(sorted(by_agent.items())),
        "messages_by_type": dict(sorted(by_type.items())),
        "full_decision_traces": dict(traces),
        "agent_agreement_and_disagreement": {
            "agreement": [
                "Scanner and technical analyst agreed the fixture was technically qualified."
            ],
            "disagreement": [
                "Strategy intent requested exposure; portfolio/risk rejected the exposure."
            ],
        },
        "conflict_resolution_outcomes": [
            {
                "conflict": "New exposure versus minimum cash reserve",
                "outcome": "Risk veto preserved cash reserve",
            }
        ],
        "risk_approvals": 0,
        "risk_rejections": len(
            [
                row
                for row in messages
                if row["message_type"] == "RiskDecision" and row["status"] == "REJECTED"
            ]
        ),
        "risk_rejection_details": rejected,
        "execution_requests": 0,
        "broker_responses": [],
        "fills": [],
        "failed_or_incomplete_traces": [],
        "average_latency_by_agent_ms": {
            str(agent["agent_id"]): agent["average_latency_ms"] for agent in agents
        },
        "timeout_and_retry_statistics": {"timeouts": 0, "retries": 0},
        "permission_violations": [],
        "trades_prevented_by_safeguards": 1,
        "strategy_performance": {
            "status": "NOT_AVAILABLE",
            "reason": "Synthetic communication sample contains no realized strategy returns.",
        },
        "benchmark_comparison": {
            "status": "NOT_AVAILABLE",
            "reason": "No real or backtest performance is represented by this report.",
        },
        "plateau_and_decay_signals": [],
        "drawdown_status": {
            "current": risk["current_drawdown"],
            "stage": "NORMAL",
        },
        "open_incidents": [],
        "orders": orders,
        "raw_messages_redacted": redact(messages),
    }


def _render_key_values(payload: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<th>{html.escape(str(key).replace('_', ' ').title())}</th>"
        f"<td>{html.escape(json.dumps(value) if isinstance(value, (dict, list)) else str(value))}</td>"
        "</tr>"
        for key, value in payload.items()
    )
    return f'<table class="kv"><tbody>{rows}</tbody></table>'


def _render_trace(messages: list[dict[str, object]]) -> str:
    items = "".join(
        '<li class="trace-item">'
        f'<span class="trace-type">{html.escape(str(row["message_type"]))}</span>'
        f"<span>{html.escape(str(row['agent_id']))}</span>"
        f'<span class="status {str(row["status"]).lower()}">'
        f"{html.escape(str(row['status']))}</span>"
        f"<p>{html.escape(str(row['summary']))}</p>"
        "</li>"
        for row in messages
    )
    return f'<ol class="trace">{items}</ol>'


def render_html(report: dict[str, Any]) -> str:
    metadata = report["report_metadata"]
    summary = report["executive_summary"]
    traces = "".join(
        f"<h3>Trace {html.escape(trace_id)}</h3>{_render_trace(rows)}"
        for trace_id, rows in report["full_decision_traces"].items()
    )
    by_agent = _render_key_values(report["messages_by_agent"])
    by_type = _render_key_values(report["messages_by_type"])
    health_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(agent['name']))}</td>"
        f"<td>{html.escape(str(agent['status']))}</td>"
        f"<td>{html.escape(str(agent['average_latency_ms']))} ms</td>"
        f"<td>{html.escape(str(agent['messages_processed']))}</td>"
        "</tr>"
        for agent in report["agent_health"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(metadata["title"])}</title>
<style>
:root{{--bg:#0b0d10;--card:#12161b;--raised:#171c22;--line:#252c36;
--text:#e7eaf0;--muted:#8b949e;--blue:#60a5fa;--green:#22c55e;
--red:#ef4444;--amber:#f59e0b;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 Inter,system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:32px 22px 64px}}
header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;
border-bottom:1px solid var(--line);padding-bottom:22px}}h1{{font-size:24px;margin:0 0 6px}}
h2{{font-size:15px;margin:30px 0 12px}}h3{{font:12px var(--mono);color:var(--muted)}}
.muted{{color:var(--muted)}}.banner{{margin:18px 0;padding:12px 14px;border:1px solid var(--amber);
background:rgba(245,158,11,.08);border-radius:10px;color:#fbbf24;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.card{{background:var(--card);
border:1px solid var(--line);border-radius:12px;padding:17px}}.metric{{font:24px var(--mono)}}
.label{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line)}}
th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}}th{{color:var(--muted);
font-size:11px}}.kv th{{width:36%}}.kv td{{font-family:var(--mono);font-size:12px;word-break:break-word}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.trace{{list-style:none;padding:0;margin:0;
border:1px solid var(--line);border-radius:12px;overflow:hidden}}.trace-item{{display:grid;
grid-template-columns:180px 1fr auto;gap:12px;padding:12px 14px;background:var(--card);
border-bottom:1px solid var(--line)}}.trace-item:last-child{{border-bottom:0}}
.trace-item p{{grid-column:2/-1;margin:0;color:var(--muted)}}.trace-type{{font-family:var(--mono);
color:var(--blue)}}.status{{font:10px var(--mono);padding:3px 7px;border-radius:5px}}
.accepted{{color:var(--green);background:rgba(34,197,94,.1)}}.rejected{{color:var(--red);
background:rgba(239,68,68,.1)}}footer{{margin-top:34px;border-top:1px solid var(--line);
padding-top:18px;color:var(--muted);font-size:11px}}@media(max-width:760px){{.grid,.split{{grid-template-columns:1fr}}
.trace-item{{grid-template-columns:1fr auto}}.trace-type{{grid-column:1/-1}}}}
@media print{{:root{{--bg:#fff;--card:#fff;--line:#ddd;--text:#111;--muted:#555}}
main{{padding:0}}.banner{{border-color:#999;color:#111}}}}
</style>
</head>
<body><main>
<header><div><div class="label">Quant Desk / Communication Audit</div>
<h1>{html.escape(metadata["title"])}</h1>
<div class="muted">{html.escape(metadata["generated_at"])} · UTC</div></div>
<div class="label">Mode<br><span class="metric">{
        html.escape(report["system_operating_mode"])
    }</span></div></header>
<div class="banner">SYNTHETIC FIXTURE — This report is not real trading activity.</div>
<section class="grid">
<div class="card"><div class="label">Messages</div><div class="metric">{
        report["total_messages"]
    }</div></div>
<div class="card"><div class="label">Risk rejections</div><div class="metric">{
        report["risk_rejections"]
    }</div></div>
<div class="card"><div class="label">Trades prevented</div><div class="metric">{
        report["trades_prevented_by_safeguards"]
    }</div></div>
</section>
<h2>Executive summary</h2><div class="card"><p>{html.escape(summary["summary"])}</p>
<p class="muted">{html.escape(metadata["disclaimer"])}</p></div>
<h2>Agent health</h2><table><thead><tr><th>Agent</th><th>Health</th><th>Average latency</th>
<th>Messages</th></tr></thead><tbody>{health_rows}</tbody></table>
<h2>Message distribution</h2><div class="split"><div>{by_agent}</div><div>{by_type}</div></div>
<h2>Full decision traces</h2>{traces}
<h2>Agreement and conflict resolution</h2><div class="split">
<div class="card"><div class="label">Agreement</div><p>{
        html.escape("; ".join(report["agent_agreement_and_disagreement"]["agreement"]))
    }</p></div>
<div class="card"><div class="label">Disagreement</div><p>{
        html.escape("; ".join(report["agent_agreement_and_disagreement"]["disagreement"]))
    }</p></div></div>
<h2>Risk, execution, and fills</h2>{
        _render_key_values(
            {
                "risk_approvals": report["risk_approvals"],
                "risk_rejections": report["risk_rejections"],
                "execution_requests": report["execution_requests"],
                "broker_responses": len(report["broker_responses"]),
                "fills": len(report["fills"]),
                "permission_violations": len(report["permission_violations"]),
            }
        )
    }
<h2>Performance and safeguards</h2>{
        _render_key_values(
            {
                "strategy_performance": report["strategy_performance"],
                "benchmark_comparison": report["benchmark_comparison"],
                "plateau_and_decay_signals": report["plateau_and_decay_signals"],
                "drawdown_status": report["drawdown_status"],
                "open_incidents": report["open_incidents"],
            }
        )
    }
<h2>Recommended operational actions</h2><div class="card"><ol>
{
        "".join(
            f"<li>{html.escape(action)}</li>"
            for action in summary["recommended_operational_actions"]
        )
    }
</ol></div>
<footer>Redacted append-only communication report · JSON and CSV companions available ·
No model chain-of-thought is included.</footer>
</main></body></html>"""


def write_report(
    report: dict[str, Any],
    output_directory: Path,
    *,
    stem: str,
) -> tuple[Path, Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    safe_report = redact(report)
    json_path = output_directory / f"{stem}.json"
    csv_path = output_directory / f"{stem}.csv"
    html_path = output_directory / f"{stem}.html"
    json_path.write_text(
        json.dumps(safe_report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "message_id",
            "message_type",
            "trace_id",
            "correlation_id",
            "causation_id",
            "agent_id",
            "strategy_id",
            "asset_class",
            "symbol",
            "created_at",
            "status",
            "confidence",
            "uncertainty",
            "summary",
            "is_synthetic",
        ]
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(safe_report["raw_messages_redacted"])
    html_path.write_text(render_html(safe_report), encoding="utf-8")
    return html_path, json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", default="reports")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    if not args.synthetic:
        raise SystemExit(
            "Only --synthetic is available until a configured audit database is supplied."
        )
    stem = (
        "sample-agent-communication"
        if args.sample
        else f"agent-communication-{date.today().isoformat()}"
    )
    paths = write_report(
        build_synthetic_report(),
        Path(args.output_directory),
        stem=stem,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
