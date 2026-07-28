"""运行问题诊断 agent 的 mock 数据联调脚本.

用法：
    python scripts/run_problem_diagnosis_mock.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 确保以脚本方式执行时也能导入 src 包
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sub_agents.problem_diagnosis import ProblemDiagnosisAgent
from src.support.mcp_tools import MCPToolRegistry, diagnosis_tool


def build_mock_input() -> dict:
    return {
        "intersection_id": "JN-INT-001",
        "profile": {
            "supply": {
                "road_density_km_km2": 6.5,
                "channelization_match_score": 0.52,
                "parking_gap_ratio": 0.28,
            },
            "demand": {
                "demand_supply_ratio": 1.24,
            },
            "state": {
                "saturation": 0.91,
                "avg_speed_kmh": 17.5,
                "avg_delay_s": 122,
                "queue_overflow_ratio": 1.15,
                "green_utilization": 0.41,
                "phase_imbalance_ratio": 0.46,
            },
        },
    }


def main() -> None:
    # 注册 mock MCP diagnosis_tool，模拟“工具已接入”路径
    registry = MCPToolRegistry()
    registry.register("diagnosis_tool", diagnosis_tool)

    agent = ProblemDiagnosisAgent(mcp_tools=registry)
    result = agent.run(build_mock_input())

    print("=== ProblemDiagnosisAgent Mock Run ===")
    print(f"success: {result['success']}")
    print(f"issue_count: {result['meta']['issue_count']}")
    print(f"mcp_used: {result['meta']['mcp_used']}")
    print(f"summary: {result['diagnosis_summary']}")
    print()
    print("Top 3 priority issues:")
    for item in result["priority_order"][:3]:
        print(
            f"- rank={item['rank']} id={item['id']} "
            f"score={item['priority_score']} level={item['priority_level']} "
            f"name={item['name']}"
        )
    print()
    print("Full JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

