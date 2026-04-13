# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _to_frame(bundle: Dict[str, Any]) -> pd.DataFrame:
    candles = bundle.get("candles") or []
    frame = pd.DataFrame(candles)
    if frame.empty:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["close"]).reset_index(drop=True)
    return frame


def _calc_indicators(frame: pd.DataFrame) -> Dict[str, float | None]:
    if frame.empty or len(frame) < 21:
        return {
            "dist_sma21": None,
            "phi_score": None,
            "activity_zscore": None,
            "volume_heat": None,
        }

    close = frame["close"].astype(float)
    volume = frame["volume"].astype(float)

    sma8 = close.rolling(8).mean().iloc[-1]
    sma13 = close.rolling(13).mean().iloc[-1]
    sma21 = close.rolling(21).mean().iloc[-1]
    sma34 = close.rolling(34).mean().iloc[-1] if len(close) >= 34 else np.nan
    sma55 = close.rolling(55).mean().iloc[-1] if len(close) >= 55 else np.nan
    sma89 = close.rolling(89).mean().iloc[-1] if len(close) >= 89 else np.nan
    last_close = float(close.iloc[-1])

    dist_sma21 = ((last_close / sma21) - 1.0) * 100.0 if sma21 else None
    phi_terms = [x for x in [sma8, sma13, sma21, sma34, sma55, sma89] if pd.notna(x)]
    phi_score = sum(1 for a, b in zip(phi_terms, phi_terms[1:]) if a > b)

    vol_window = volume.tail(min(30, len(volume)))
    vol_mean = float(vol_window.mean()) if len(vol_window) else 0.0
    vol_std = float(vol_window.std(ddof=0)) if len(vol_window) else 0.0
    activity_zscore = ((float(volume.iloc[-1]) - vol_mean) / vol_std) if vol_std else 0.0
    volume_heat = (float(volume.iloc[-1]) / vol_mean) if vol_mean else 0.0

    return {
        "dist_sma21": round(dist_sma21, 4) if dist_sma21 is not None else None,
        "phi_score": float(phi_score),
        "activity_zscore": round(float(activity_zscore), 4),
        "volume_heat": round(float(volume_heat), 4),
    }


def build_snapshot(bundles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for bundle in bundles:
        frame = _to_frame(bundle)
        indicators = _calc_indicators(frame)
        row = {
            "timestamp": now,
            "source": bundle.get("source"),
            "symbol": bundle.get("symbol"),
            "price": bundle.get("price"),
            "price_change_pct": bundle.get("price_change_pct"),
            "volume_24h": bundle.get("volume_24h"),
            "open_interest": bundle.get("open_interest"),
            "funding": bundle.get("funding"),
            "premium": bundle.get("premium"),
            "lsr": bundle.get("lsr"),
            "lsr_pct_change": bundle.get("lsr_pct_change"),
            "aggression": bundle.get("aggression"),
            "dominance_pct": bundle.get("dominance_pct"),
            **indicators,
        }
        row["score"] = _composite_score(row)
        rows.append(row)
    rows.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    return rows


def _composite_score(row: Dict[str, Any]) -> float:
    parts = [
        abs(float(row.get("price_change_pct") or 0.0)) * 0.5,
        abs(float(row.get("dist_sma21") or 0.0)) * 0.5,
        abs(float(row.get("activity_zscore") or 0.0)) * 10.0,
        abs(float(row.get("funding") or 0.0)) * 10000.0,
        abs(float(row.get("dominance_pct") or 0.0)) * 0.2,
        abs(float(row.get("lsr_pct_change") or 0.0)) * 0.2,
        float(row.get("phi_score") or 0.0) * 2.0,
    ]
    return round(sum(parts), 4)


def build_history_payload(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "rows": rows,
    }
