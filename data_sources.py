# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

OPERATORS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def load_rules(config_path: Path) -> List[Dict[str, Any]]:
    env_json = os.getenv("ALERT_RULES_JSON", "").strip()
    if env_json:
        rules = json.loads(env_json)
    else:
        rules = json.loads(config_path.read_text(encoding="utf-8"))
    return rules[:10]


def load_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        return {"last_seen": {}, "history": []}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"last_seen": {}, "history": []}


def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def evaluate_rules(
    rows: List[Dict[str, Any]],
    rules: List[Dict[str, Any]],
    state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    index = {(str(r.get("source")), str(r.get("symbol"))): r for r in rows}
    emitted: List[Dict[str, Any]] = []
    last_seen = state.setdefault("last_seen", {})
    history = state.setdefault("history", [])

    for rule in rules:
        source = str(rule.get("source", ""))
        symbol = str(rule.get("symbol", ""))
        metric = str(rule.get("metric", ""))
        operator = str(rule.get("operator", ">="))
        threshold = _coerce_float(rule.get("value"))
        row = index.get((source, symbol))
        if row is None or operator not in OPERATORS or threshold is None:
            continue

        current = _coerce_float(row.get(metric))
        if current is None:
            continue

        key = str(rule.get("id") or f"{source}:{symbol}:{metric}:{operator}:{threshold}")
        condition = OPERATORS[operator](current, threshold)
        previous = bool(last_seen.get(key, False))
        last_seen[key] = condition

        if condition and not previous:
            event = {
                "id": key,
                "ts": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "symbol": symbol,
                "metric": metric,
                "operator": operator,
                "threshold": threshold,
                "current": current,
                "message": str(rule.get("message") or f"Alert on {symbol}: {metric} {operator} {threshold}"),
            }
            emitted.append(event)
            history.append(event)

    state["history"] = history[-200:]
    return emitted


def format_telegram_message(events: List[Dict[str, Any]]) -> str:
    lines = ["XDECOW Shark alerts"]
    for event in events[:10]:
        lines.append(
            f"- {event['symbol']} on {event['source']}: {event['metric']}={event['current']:.6g} "
            f"({event['operator']} {event['threshold']:.6g})"
        )
    return "\n".join(lines)
