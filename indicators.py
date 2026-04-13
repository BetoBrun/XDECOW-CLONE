# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from typing import Any, Dict, List

import pandas as pd
import requests

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "xdecow-shark-monitor/1.0"})
BINANCE_BASE = "https://fapi.binance.com"
HYPERLIQUID_INFO = "https://api.hyperliquid.xyz/info"


def _safe_get(url: str, params: Dict[str, Any] | None = None) -> Any:
    try:
        response = SESSION.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _safe_post(url: str, payload: Dict[str, Any]) -> Any:
    try:
        response = SESSION.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _binance_klines(symbol: str, interval: str = "15m", limit: int = 120) -> pd.DataFrame:
    data = _safe_get(
        f"{BINANCE_BASE}/fapi/v1/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    if not data:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])
    rows = []
    for item in data:
        rows.append(
            {
                "open_time": int(item[0]),
                "open": _to_float(item[1]),
                "high": _to_float(item[2]),
                "low": _to_float(item[3]),
                "close": _to_float(item[4]),
                "volume": _to_float(item[5]),
            }
        )
    return pd.DataFrame(rows)


def _hyperliquid_candles(coin: str, interval: str = "15m", bars: int = 120) -> pd.DataFrame:
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - bars * 15 * 60 * 1000
    data = _safe_post(
        HYPERLIQUID_INFO,
        {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
            },
        },
    )
    if not data:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])
    rows = []
    for item in data:
        rows.append(
            {
                "open_time": int(item.get("t", 0)),
                "open": _to_float(item.get("o")),
                "high": _to_float(item.get("h")),
                "low": _to_float(item.get("l")),
                "close": _to_float(item.get("c")),
                "volume": _to_float(item.get("v")),
            }
        )
    return pd.DataFrame(rows)


def fetch_binance_bundle(symbol: str) -> Dict[str, Any]:
    ticker = _safe_get(f"{BINANCE_BASE}/fapi/v1/ticker/24hr", params={"symbol": symbol}) or {}
    premium = _safe_get(f"{BINANCE_BASE}/fapi/v1/premiumIndex", params={"symbol": symbol}) or {}
    open_interest = _safe_get(f"{BINANCE_BASE}/fapi/v1/openInterest", params={"symbol": symbol}) or {}
    lsr = _safe_get(
        f"{BINANCE_BASE}/futures/data/globalLongShortAccountRatio",
        params={"symbol": symbol, "period": "15m", "limit": 30},
    ) or []
    taker = _safe_get(
        f"{BINANCE_BASE}/futures/data/takerlongshortRatio",
        params={"symbol": symbol, "period": "15m", "limit": 30},
    ) or []
    klines = _binance_klines(symbol)

    latest_lsr = _to_float(lsr[-1].get("longShortRatio")) if lsr else 0.0
    prev_lsr = _to_float(lsr[-2].get("longShortRatio")) if len(lsr) > 1 else latest_lsr
    lsr_pct_change = ((latest_lsr / prev_lsr) - 1.0) * 100.0 if prev_lsr else 0.0

    latest_taker_buy = _to_float(taker[-1].get("buySellRatio")) if taker else 0.0
    aggression = latest_taker_buy
    dominance_pct = (latest_taker_buy - 1.0) * 100.0 if latest_taker_buy else 0.0

    return {
        "source": "binance",
        "symbol": symbol,
        "price": _to_float(ticker.get("lastPrice")),
        "price_change_pct": _to_float(ticker.get("priceChangePercent")),
        "volume_24h": _to_float(ticker.get("quoteVolume")),
        "open_interest": _to_float(open_interest.get("openInterest")),
        "funding": _to_float(premium.get("lastFundingRate")),
        "premium": _to_float(premium.get("markPrice")) - _to_float(premium.get("indexPrice")),
        "lsr": latest_lsr,
        "lsr_pct_change": lsr_pct_change,
        "aggression": aggression,
        "dominance_pct": dominance_pct,
        "candles": klines.to_dict(orient="records"),
    }


def fetch_hl_bundle(symbol: str) -> Dict[str, Any]:
    meta = _safe_post(HYPERLIQUID_INFO, {"type": "metaAndAssetCtxs"}) or []
    universe = []
    contexts = []
    if isinstance(meta, list) and len(meta) >= 2:
        universe = meta[0].get("universe", []) if isinstance(meta[0], dict) else []
        contexts = meta[1] if isinstance(meta[1], list) else []

    index = None
    for idx, item in enumerate(universe):
        if str(item.get("name", "")).upper() == symbol.upper():
            index = idx
            break

    ctx = contexts[index] if index is not None and index < len(contexts) else {}
    klines = _hyperliquid_candles(symbol)

    return {
        "source": "hyperliquid",
        "symbol": symbol,
        "price": _to_float(ctx.get("markPx") or ctx.get("midPx") or ctx.get("oraclePx")),
        "price_change_pct": _to_float(ctx.get("dayNtlVlm"), 0.0),
        "volume_24h": _to_float(ctx.get("dayNtlVlm")),
        "open_interest": _to_float(ctx.get("openInterest")),
        "funding": _to_float(ctx.get("funding")),
        "premium": _to_float(ctx.get("premium")),
        "lsr": 0.0,
        "lsr_pct_change": 0.0,
        "aggression": 0.0,
        "dominance_pct": 0.0,
        "candles": klines.to_dict(orient="records"),
    }
