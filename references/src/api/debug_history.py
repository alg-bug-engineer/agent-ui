"""调试接口执行历史（进程内环形缓存，最近 N 条）."""

from __future__ import annotations

import os
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

# 可通过环境变量覆盖，默认保留 50 条
_MAX = max(1, int(os.environ.get("DEBUG_HISTORY_MAX", "50")))
_history: deque[dict[str, Any]] = deque(maxlen=_MAX)


def _summary(kind: str, data: dict[str, Any]) -> str:
    if kind == "loop":
        return (
            f"loop_id={data.get('loop_id')} "
            f"meets_target={data.get('meets_target')} "
            f"phases={len(data.get('phases') or [])}"
        )
    if kind == "diagnosis_template":
        top = data.get("top_issue") or {}
        n_tpl = len(data.get("selected_templates") or [])
        return (
            f"top={top.get('id', '?')} "
            f"lvl={top.get('priority_level', '?')} "
            f"templates={n_tpl}"
        )
    if kind == "multiscenario_benchmark":
        s = data.get("summary") or ""
        n = len(data.get("rows") or [])
        return f"scenarios={n} | {s[:160]}{'…' if len(s) > 160 else ''}"
    return kind


def push_debug_history(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    """写入一条历史记录（新记录在前）."""
    entry = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "summary": _summary(kind, data),
        "data": data,
    }
    _history.appendleft(entry)
    return entry


def get_debug_history(limit: int = 20) -> list[dict[str, Any]]:
    """返回最近 limit 条（含完整 data，供前端展开）."""
    lim = max(1, min(limit, _MAX))
    return list(_history)[:lim]


def clear_debug_history() -> None:
    """清空历史."""
    _history.clear()


def history_capacity() -> int:
    return _MAX
