"""多场景问题诊断 + 策略模板选择 对比报告（mock）.

用法：
    python scripts/run_multiscenario_diagnosis_report.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sub_agents.control_strategy import ControlStrategyAgent
from src.sub_agents.problem_diagnosis import ProblemDiagnosisAgent
from src.support.mcp_tools import MCPToolRegistry, diagnosis_tool


def build_scenarios() -> dict[str, dict]:
    return {
        "school_peak": {
            "scenario_name": "学校上下学高峰",
            "scenario_type": "school_peak",
            "scope": {"type": "intersection", "ids": ["SCH-INT-01"]},
            "intersection_id": "SCH-INT-01",
            "profile": {
                "supply": {
                    "road_density_km_km2": 7.2,
                    "channelization_match_score": 0.45,
                    "parking_gap_ratio": 0.18,
                },
                "demand": {"demand_supply_ratio": 1.18},
                "state": {
                    "saturation": 0.88,
                    "avg_speed_kmh": 16.0,
                    "avg_delay_s": 115,
                    "queue_overflow_ratio": 1.10,
                    "green_utilization": 0.47,
                    "phase_imbalance_ratio": 0.44,
                },
            },
        },
        "hospital_morning": {
            "scenario_name": "医院早高峰就诊",
            "scenario_type": "hospital_morning",
            "scope": {"type": "region", "ids": ["HOS-REG-01"]},
            "intersection_id": "HOS-INT-03",
            "profile": {
                "supply": {
                    "road_density_km_km2": 6.8,
                    "channelization_match_score": 0.58,
                    "parking_gap_ratio": 0.36,
                },
                "demand": {"demand_supply_ratio": 1.27},
                "state": {
                    "saturation": 0.93,
                    "avg_speed_kmh": 15.2,
                    "avg_delay_s": 135,
                    "queue_overflow_ratio": 1.22,
                    "green_utilization": 0.38,
                    "phase_imbalance_ratio": 0.41,
                },
            },
        },
        "event_dispersal": {
            "scenario_name": "大型活动散场",
            "scenario_type": "event_dispersal",
            "scope": {"type": "corridor", "ids": ["EVT-COR-01"]},
            "intersection_id": "EVT-INT-09",
            "profile": {
                "supply": {
                    "road_density_km_km2": 7.8,
                    "channelization_match_score": 0.63,
                    "parking_gap_ratio": 0.24,
                },
                "demand": {"demand_supply_ratio": 1.34},
                "state": {
                    "saturation": 0.95,
                    "avg_speed_kmh": 13.5,
                    "avg_delay_s": 150,
                    "queue_overflow_ratio": 1.30,
                    "green_utilization": 0.42,
                    "phase_imbalance_ratio": 0.37,
                },
            },
        },
    }


def run() -> tuple[list[dict], str]:
    registry = MCPToolRegistry()
    registry.register("diagnosis_tool", diagnosis_tool)

    diagnosis_agent = ProblemDiagnosisAgent(mcp_tools=registry)
    strategy_agent = ControlStrategyAgent()

    rows: list[dict] = []
    scenarios = build_scenarios()
    for sid, payload in scenarios.items():
        diag = diagnosis_agent.run(payload)
        strategy = strategy_agent.run(
            {
                "scenario_type": payload["scenario_type"],
                "scope": payload["scope"],
                "priority_order": diag["priority_order"],
            }
        )
        top_issue = (diag["priority_order"] or [{}])[0]
        top_template = (strategy["selected_templates"] or [{}])[0]
        rows.append(
            {
                "scenario_id": sid,
                "scenario_name": payload["scenario_name"],
                "issue_count": diag["meta"]["issue_count"],
                "top_issue": top_issue.get("name", ""),
                "top_issue_id": top_issue.get("id", ""),
                "top_issue_level": top_issue.get("priority_level", ""),
                "top_template": top_template.get("template_id", ""),
                "top_template_level": top_template.get("control_level", ""),
                "templates": strategy["selected_templates"],
                "diagnosis": diag,
                "strategy": strategy,
            }
        )

    report_md = build_markdown_report(rows)
    return rows, report_md


def build_markdown_report(rows: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 多场景问题诊断与策略模板选择对比报告（Mock）",
        "",
        f"- 生成时间：`{now}`",
        f"- 场景数量：`{len(rows)}`",
        "",
        "## 汇总表",
        "",
        "| 场景 | 问题数 | Top问题 | 等级 | Top策略模板 | 控制层级 |",
        "|---|---:|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['scenario_name']} | {r['issue_count']} | {r['top_issue']} "
            f"(`{r['top_issue_id']}`) | {r['top_issue_level']} | "
            f"`{r['top_template']}` | {r['top_template_level']} |"
        )

    lines += ["", "## 场景详情", ""]
    for r in rows:
        lines += [
            f"### {r['scenario_name']}",
            "",
            f"- Top问题：`{r['top_issue_id']}`（{r['top_issue_level']}）",
            f"- Top模板：`{r['top_template']}`（{r['top_template_level']}）",
            "- 推荐模板：",
        ]
        for t in r["templates"]:
            lines.append(
                f"  - `{t['template_id']}` | issue=`{t['recommended_by_issue']}` "
                f"| score={t['recommend_score']}"
            )
        lines += ["", "```json", json.dumps(r["strategy"]["strategy_instruction"], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def main() -> None:
    rows, report_md = run()
    report_path = ROOT / "docs" / "mock-多场景问题诊断策略对比报告.md"
    report_path.write_text(report_md, encoding="utf-8")

    print("=== 多场景诊断与策略模板选择（Mock）===")
    for r in rows:
        print(
            f"- {r['scenario_name']}: top_issue={r['top_issue_id']}({r['top_issue_level']}), "
            f"top_template={r['top_template']}"
        )
    print(f"\n报告已生成: {report_path}")


if __name__ == "__main__":
    main()

