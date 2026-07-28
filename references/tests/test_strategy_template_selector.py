"""策略模板选择器测试."""

from src.sub_agents.control_strategy import ControlStrategyAgent


def test_select_templates_from_priority_order():
    agent = ControlStrategyAgent()
    priority_order = [
        {"id": "signal_queue_overflow", "priority_score": 0.9, "priority_level": "P0"},
        {"id": "dynamic_demand_supply_imbalance", "priority_score": 0.85, "priority_level": "P0"},
        {"id": "static_road_network_sparse", "priority_score": 0.45, "priority_level": "P3"},
    ]

    result = agent.run({"priority_order": priority_order, "scope": {"type": "intersection"}})
    selected = result["selected_templates"]

    assert result["phase"] == "control_strategy"
    assert result["success"] is True
    assert len(selected) > 0
    assert selected[0]["template_id"] == "intersection_bottleneck_anti_spillback"
    assert "selected_templates" in result["strategy_instruction"]["realtime_patch"]

