"""业务规则 YAML 加载：诊断阈值、问题-模板映射、MCP mock 阈值.

环境变量 SIGNAL_AGENT_BUSINESS_RULES_PATH 指向完整 YAML 时可覆盖内置默认文件。
Docker 典型路径：/app/config/business_rules/default.yaml
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_cache: dict[str, Any] | None = None


def _project_root() -> Path:
    # src/config/business_rules_loader.py -> parents[2] == 仓库根目录
    return Path(__file__).resolve().parents[2]


def _resolve_rules_path() -> Path | None:
    env = os.environ.get("SIGNAL_AGENT_BUSINESS_RULES_PATH", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    cand = _project_root() / "config" / "business_rules" / "default.yaml"
    if cand.is_file():
        return cand
    return None


def reload_business_rules() -> None:
    """清空缓存，便于测试或热读下一请求前重新加载文件."""
    global _cache
    _cache = None


def get_business_rules() -> dict[str, Any]:
    """返回业务规则根对象（version / diagnosis / control_strategy / diagnosis_tool_mock）."""
    global _cache
    if _cache is not None:
        return _cache
    path = _resolve_rules_path()
    if path is None:
        raise RuntimeError(
            "未找到业务规则 YAML。请设置环境变量 SIGNAL_AGENT_BUSINESS_RULES_PATH，"
            "或在项目根目录放置 config/business_rules/default.yaml。"
        )
    with path.open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise RuntimeError(f"业务规则 YAML 格式错误（应为 mapping）: {path}")
    _cache = loaded
    return _cache
