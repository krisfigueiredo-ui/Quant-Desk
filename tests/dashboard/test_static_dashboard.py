"""Static dashboard safety and navigation contract tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_exposes_all_required_operations_pages() -> None:
    source = (ROOT / "dashboard" / "index.html").read_text()
    required_pages = {
        "overview",
        "agents",
        "day-desk",
        "long-term",
        "scanner",
        "strategies",
        "risk",
        "orders",
        "audit",
        "settings",
    }
    for page in required_pages:
        assert f'data-page="{page}"' in source


def test_browser_bundle_has_no_direct_broker_or_live_activation_path() -> None:
    source = (ROOT / "dashboard" / "app.js").read_text()
    assert "trading.robinhood.com" not in source
    assert "paper-api.alpaca.markets" not in source
    assert "ENABLE RESTRICTED LIVE" not in source
    assert "controls/emergency-stop" not in source
    assert "${API}/controls/${pendingControl}" in source


def test_dashboard_prominently_labels_paper_and_synthetic_data() -> None:
    html = (ROOT / "dashboard" / "index.html").read_text()
    script = (ROOT / "dashboard" / "app.js").read_text()
    assert "PAPER ENVIRONMENT" in html
    assert "Equities live: OFF" in html
    assert "Crypto live: OFF" in html
    assert "SYNTHETIC FIXTURE" in script
