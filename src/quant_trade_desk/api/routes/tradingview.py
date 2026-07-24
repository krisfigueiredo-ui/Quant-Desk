"""TradingView webhook endpoint; accepted signals still require full review."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.post("/tradingview/webhook")
async def tradingview_webhook(request: Request) -> dict[str, object]:
    verifier = request.app.state.tradingview_verifier
    if verifier is None:
        raise HTTPException(status_code=503, detail="TradingView input is not configured")
    body = await request.body()
    signature = request.headers.get("X-Quant-Desk-Signature", "")
    source_key = request.client.host if request.client else "unknown"
    try:
        signal = verifier.verify(
            body=body,
            signature=signature,
            source_key=source_key,
        )
    except ValueError as exc:
        request.app.state.metrics.increment(
            "quant_desk_tradingview_rejections_total",
            reason=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from None
    request.app.state.metrics.increment("quant_desk_tradingview_accepted_total")
    return {
        "status": "ACCEPTED_FOR_REVIEW",
        "signal_id": str(signal.signal_id),
        "direct_execution": False,
        "next_step": "market-data confirmation and typed agent review",
    }
