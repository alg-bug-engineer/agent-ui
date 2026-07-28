"""问题诊断子智能体测试."""

from src.sub_agents.problem_diagnosis import ProblemDiagnosisAgent


def test_problem_diagnosis_rule_engine_detects_multiple_issue_categories():
    """无 MCP 时，规则引擎应识别静态/动态/信控问题并输出优先级."""
    agent = ProblemDiagnosisAgent()
    result = agent.run(
        {
            "profile": {
                "supply": {
                    "road_density_km_km2": 6.2,
                    "channelization_match_score": 0.4,
                },
                "demand": {"demand_supply_ratio": 1.3},
                "state": {
                    "saturation": 0.92,
                    "avg_speed_kmh": 18,
                    "avg_delay_s": 130,
                    "queue_overflow_ratio": 1.2,
                    "green_utilization": 0.35,
                    "phase_imbalance_ratio": 0.48,
                },
            }
        }
    )

    assert result["phase"] == "problem_diagnosis"
    assert result["success"] is True
    assert len(result["issues"]) > 0
    assert len(result["priority_order"]) > 0

    categories = {item["category"] for item in result["issues"]}
    assert "static" in categories
    assert "dynamic" in categories
    assert "signal_control" in categories

    # 排序应按分值降序，且有 rank
    priorities = result["priority_order"]
    assert priorities[0]["priority_score"] >= priorities[-1]["priority_score"]
    assert priorities[0]["rank"] == 1


def test_problem_diagnosis_uses_mcp_result_when_available():
    """有 MCP 结果时应优先采用并标准化输出."""

    class FakeMcp:
        def invoke(self, name: str, **kwargs):
            assert name == "diagnosis_tool"
            return {
                "issues": [
                    {
                        "id": "mcp_congestion_root",
                        "name": "MCP识别拥堵根因",
                        "category": "dynamic",
                        "severity": 0.9,
                        "confidence": 0.95,
                        "evidence": {"source": "mcp"},
                        "reason": "MCP诊断结果",
                    }
                ]
            }

    agent = ProblemDiagnosisAgent(mcp_tools=FakeMcp())
    result = agent.run({"profile": {"supply": {}, "demand": {}, "state": {}}})

    assert result["meta"]["mcp_used"] is True
    assert len(result["issues"]) == 1
    assert result["issues"][0]["id"] == "mcp_congestion_root"
    assert result["priority_order"][0]["id"] == "mcp_congestion_root"
