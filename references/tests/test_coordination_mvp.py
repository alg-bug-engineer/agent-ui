"""协调子包 arterial MVP 单测."""

from src.planning.coordination.arterial_mvp import ArterialLink, solve_arterial_two_way_max_bandwidth


def test_two_intersections_symmetric_returns_feasible():
    out = solve_arterial_two_way_max_bandwidth(
        ["A", "B"],
        [ArterialLink(400.0, 40.0)],
        min_cycle_s=70.0,
        max_cycle_s=100.0,
        min_green_s=15.0,
        max_green_s=40.0,
        progression_weight=0.05,
        random_seed=1,
    )
    assert out["ok"] is True
    assert out["cycle_s"] >= 70.0
    assert out["cycle_s"] <= 100.0
    assert out["bandwidth_s"] > 0
    assert len(out["nodes"]) == 2
    assert out["nodes"][0]["offset_s"] == 0.0
    assert "webster_delay_s" in out["nodes"][0]
    assert out["kpis"]["progression_penalty"] >= 0.0


def test_three_nodes_default_spacing_via_corridor():
    from src.planning.corridor import generate_corridor_coordination_plan

    plan = generate_corridor_coordination_plan(
        {
            "corridor_id": "C1",
            "intersection_ids": ["a", "b", "c"],
            "constraints": {"design_speed_kmh": 50.0, "default_link_spacing_m": 300.0},
        }
    )
    assert plan["plan_type"] == "corridor_coordination"
    assert plan["coordination"]["cycle_s"] is not None
    assert plan["coordination"]["bandwidth_s"] > 0
    assert plan["coordination"]["total_delay_s"] is not None
    assert len(plan["coordination"]["nodes"]) == 3
