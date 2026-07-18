#!/usr/bin/env python3
"""Fetch a browser-safe snapshot of public Kalshi market data.

GitHub Pages cannot call the Kalshi Trade API directly because the API does
not allow cross-origin browser requests. This script runs server-side in
GitHub Actions, normalizes the public response, and writes the static JSON
consumed by dashboards/kalshi_signals.html.
"""

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API = "https://external-api.kalshi.com/trade-api/v2"
USER_AGENT = "Quant-Desk/1.0 (+https://github.com/krisfigueiredo-ui/Quant-Desk)"


def get_json(url, timeout=15):
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def cents(value):
    """Normalize current dollar-string or legacy integer-cent prices."""
    number = float(value)
    return round(number * 100 if number <= 1 else number, 2)


def levels(book, current_key, legacy_key):
    raw = book.get(current_key) or book.get(legacy_key) or []
    normalized = []
    for level in raw:
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            continue
        normalized.append([cents(level[0]), float(level[1])])
    return normalized


def normalize_orderbook(payload):
    book = payload.get("orderbook_fp") or payload.get("orderbook") or payload
    return {
        "yes": levels(book, "yes_dollars", "yes"),
        "no": levels(book, "no_dollars", "no"),
    }


def quote_level(market, side):
    """Read the public top-of-book quote from current or legacy fields."""
    price = market.get(f"{side}_bid_dollars")
    if price is None:
        price = market.get(f"{side}_bid", 0)
    size = market.get(f"{side}_bid_size_fp")
    if size is None:
        size = market.get(f"{side}_bid_size", 0)
    try:
        bid_price, bid_size = cents(price), float(size)
    except (TypeError, ValueError):
        bid_price, bid_size = 0, 0

    # A binary NO bid is equivalent to 100c minus the best YES ask (and
    # vice versa). Current market payloads commonly publish only one bid
    # side, so derive its economic equivalent from the opposite ask.
    if bid_price <= 0 or bid_size <= 0:
        opposite = "no" if side == "yes" else "yes"
        ask = market.get(f"{opposite}_ask_dollars")
        if ask is None:
            ask = market.get(f"{opposite}_ask", 0)
        ask_size = market.get(f"{opposite}_ask_size_fp")
        if ask_size is None:
            ask_size = market.get(f"{opposite}_ask_size", 0)
        try:
            derived_price = 100 - cents(ask)
            derived_size = float(ask_size)
            if derived_price > 0 and derived_size > 0:
                return round(derived_price, 2), derived_size
        except (TypeError, ValueError):
            pass
    return bid_price, bid_size


def build_snapshot(limit):
    markets = []
    failures = 0
    cursor = ""
    seen = quoted_yes = quoted_no = 0

    # New listings often have empty books. Walk several pages and keep only
    # markets with executable size on both sides of the public top of book.
    for _ in range(5):
        params = {"limit": 1000, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        market_payload = get_json(f"{API}/markets?{urllib.parse.urlencode(params)}")
        for market in market_payload.get("markets", []):
            seen += 1
            ticker = market.get("ticker")
            if not ticker:
                continue
            yes_price, yes_size = quote_level(market, "yes")
            no_price, no_size = quote_level(market, "no")
            quoted_yes += int(yes_price > 0 and yes_size > 0)
            quoted_no += int(no_price > 0 and no_size > 0)
            if yes_price > 0 and no_price > 0 and yes_size > 0 and no_size > 0:
                markets.append(
                    {
                        "ticker": ticker,
                        "title": market.get("title") or market.get("subtitle") or ticker,
                        "orderbook": {
                            "yes": [[yes_price, yes_size]],
                            "no": [[no_price, no_size]],
                        },
                    }
                )
            if len(markets) >= limit:
                break
        if len(markets) >= limit:
            break
        cursor = market_payload.get("cursor") or ""
        if not cursor:
            break

    generated = datetime.now(timezone.utc)
    return {
        "generated_at": generated.isoformat().replace("+00:00", "Z"),
        "generated_at_ms": int(generated.timestamp() * 1000),
        "source": "Kalshi Trade API v2 public market data",
        "market_count": len(markets),
        "failed_orderbooks": failures,
        "markets_examined": seen,
        "markets_with_yes_bid": quoted_yes,
        "markets_with_no_bid": quoted_no,
        "markets": markets,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/kalshi_snapshot.json")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    snapshot = build_snapshot(max(1, min(args.limit, 100)))
    if not snapshot["markets"]:
        raise SystemExit(
            "Kalshi returned no usable two-sided order books "
            f"({snapshot['markets_examined']} examined; "
            f"YES bids: {snapshot['markets_with_yes_bid']}; "
            f"NO bids: {snapshot['markets_with_no_bid']})"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {snapshot['market_count']} markets to {output} "
        f"({snapshot['failed_orderbooks']} order books unavailable)"
    )


if __name__ == "__main__":
    main()
