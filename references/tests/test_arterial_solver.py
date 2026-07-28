"""干线绿波完整求解器单测.

覆盖：
- 关键路口选择（供需均衡评分）
- 公共周期夹紧
- 非关键路口绿时分配
- 单向带宽计算
- 双向带宽与偏移优化
- 双停抑制
- 策略枚举
- 完整流程（含 rich data 路径）
- HTTP API 新字段
"""

import numpy as np
from fastapi.testclient import TestClient

from src.api.main import app
from src.planning.coordination.arterial_mvp import ArterialLink
from src.planning.coordination.arterial_solver import (
    _allocate_non_critical_greens,
    _clamp_cycle,
    _compute_balance_score,
    _compute_oneway_bandwidth,
    _count_double_stops,
    _select_critical_intersection,
    solve_corridor_full,
    solve_offsets,
)
from src.planning.corridor import generate_corridor_coordination_plan


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _make_two_phase_intersection(iid: str, flow_a: int = 600, flow_b: int = 400) -> dict:
    return {
        "intersection_id": iid,
        "phaseStageInfoList": [
            {
                "phaseStageId": "A",
                "phaseStageName": "南北直行",
                "phaseDirInfoDTOList": [
                    {"dir8No": 1, "turnDirNo": 2, "turnFlowTotal": flow_a, "laneCount": 2},
                    {"dir8No": 5, "turnDirNo": 2, "turnFlowTotal": flow_a - 50, "laneCount": 2},
                ],
            },
            {
                "phaseStageId": "B",
                "phaseStageName": "东西直行",
                "phaseDirInfoDTOList": [
                    {"dir8No": 3, "turnDirNo": 2, "turnFlowTotal": flow_b, "laneCount": 2},
                    {"dir8No": 7, "turnDirNo": 2, "turnFlowTotal": flow_b - 20, "laneCount": 2},
                ],
            },
        ],
    }


def _make_three_node_request(strategy: str = "bidirectional") -> dict:
    return {
        "corridor_id": "TEST-3",
        "intersection_ids": ["N1", "N2", "N3"],
        "links": [
            {"distance_m": 400, "forward_speed_kmh": 50},
            {"distance_m": 350, "forward_speed_kmh": 50},
        ],
        "intersections": [
            _make_two_phase_intersection("N1", 600, 400),
            _make_two_phase_intersection("N2", 500, 500),
            _make_two_phase_intersection("N3", 700, 300),
        ],
        "constraints": {
            "min_cycle_s": 70,
            "max_cycle_s": 120,
            "strategy": strategy,
            "target_non_coord_intensity": 0.8,
            "design_speed_kmh": 50,
        },
    }


# ---------------------------------------------------------------------------
# 关键路口选择
# ---------------------------------------------------------------------------

class TestCriticalIntersection:
    def test_balance_score_equal_saturation(self):
        sp = {
            "phaseStageTimingList": [
                {"phaseStageId": "A", "phaseSaturation": 0.7},
                {"phaseStageId": "B", "phaseSaturation": 0.7},
            ]
        }
        assert _compute_balance_score(sp) < 0.01

    def test_balance_score_unequal(self):
        sp = {
            "phaseStageTimingList": [
                {"phaseStageId": "A", "phaseSaturation": 0.9},
                {"phaseStageId": "B", "phaseSaturation": 0.3},
            ]
        }
        assert abs(_compute_balance_score(sp) - 0.6) < 0.01

    def test_select_most_balanced(self):
        sp_results = [
            {"cycleTime": 90, "phaseStageTimingList": [
                {"phaseSaturation": 0.9}, {"phaseSaturation": 0.3}]},
            {"cycleTime": 85, "phaseStageTimingList": [
                {"phaseSaturation": 0.7}, {"phaseSaturation": 0.7}]},
            {"cycleTime": 100, "phaseStageTimingList": [
                {"phaseSaturation": 0.5}, {"phaseSaturation": 0.8}]},
        ]
        idx, iid, score = _select_critical_intersection(sp_results, ["A", "B", "C"])
        assert idx == 1
        assert iid == "B"
        assert score < 0.01

    def test_tiebreak_by_cycle(self):
        sp_results = [
            {"cycleTime": 90, "phaseStageTimingList": [
                {"phaseSaturation": 0.7}, {"phaseSaturation": 0.7}]},
            {"cycleTime": 100, "phaseStageTimingList": [
                {"phaseSaturation": 0.7}, {"phaseSaturation": 0.7}]},
        ]
        idx, _, _ = _select_critical_intersection(sp_results, ["A", "B"])
        assert idx == 1


# ---------------------------------------------------------------------------
# 公共周期夹紧
# ---------------------------------------------------------------------------

class TestClampCycle:
    def test_within_range(self):
        assert _clamp_cycle(90, 60, 120) == 90

    def test_clamp_above(self):
        assert _clamp_cycle(150, 60, 120) == 120

    def test_clamp_below(self):
        assert _clamp_cycle(50, 60, 120) == 60

    def test_per_intersection_limits(self):
        c = _clamp_cycle(100, 60, 120, [(70, 110), (80, 105)])
        assert 80 <= c <= 105


# ---------------------------------------------------------------------------
# 非关键路口绿时分配
# ---------------------------------------------------------------------------

class TestNonCriticalGreens:
    def test_coordinated_gets_surplus(self):
        sp = {
            "cycleTime": 90,
            "phaseStageTimingList": [
                {"phaseStageId": "A", "greenTime": 40, "splitRatio": 0.44, "phaseSaturation": 0.7, "phaseStageName": "A"},
                {"phaseStageId": "B", "greenTime": 30, "splitRatio": 0.33, "phaseSaturation": 0.6, "phaseStageName": "B"},
            ],
        }
        alloc = _allocate_non_critical_greens(sp, 90.0, "A", 0.8)
        assert alloc["coordinated_green_s"] > 0
        assert len(alloc["phase_stage_timing"]) == 2
        total_green = sum(p["green_s"] for p in alloc["phase_stage_timing"])
        assert total_green <= 90.0

    def test_empty_stages(self):
        alloc = _allocate_non_critical_greens({"cycleTime": 90, "phaseStageTimingList": []}, 90.0, "A")
        assert alloc["coordinated_green_s"] == 0.0


# ---------------------------------------------------------------------------
# 单向带宽
# ---------------------------------------------------------------------------

class TestOnewayBandwidth:
    def test_two_nodes_perfect_alignment(self):
        cycle = 90.0
        greens = np.array([30.0, 30.0])
        tau = np.array([28.0])
        offsets = np.array([0.0, 28.0])
        bw = _compute_oneway_bandwidth(offsets, greens, tau, cycle)
        assert bw > 25.0

    def test_two_nodes_full_misalignment(self):
        cycle = 90.0
        greens = np.array([30.0, 30.0])
        tau = np.array([28.0])
        offsets = np.array([0.0, 73.0])
        bw = _compute_oneway_bandwidth(offsets, greens, tau, cycle)
        assert bw < 5.0

    def test_single_node(self):
        bw = _compute_oneway_bandwidth(np.array([0.0]), np.array([30.0]), np.array([]), 90.0)
        assert bw == 30.0


# ---------------------------------------------------------------------------
# 双停统计
# ---------------------------------------------------------------------------

class TestDoubleStop:
    def test_metric_is_nonnegative(self):
        cycle = 90.0
        offsets = np.array([0.0, 20.0, 40.0])
        greens = np.array([60.0, 60.0, 60.0])
        tau = np.array([20.0, 20.0])
        ds = _count_double_stops(offsets, greens, tau, cycle)
        assert ds >= 0.0
        assert np.isfinite(ds)

    def test_single_node_zero(self):
        ds = _count_double_stops(np.array([0.0]), np.array([30.0]), np.array([]), 90.0)
        assert ds == 0.0


# ---------------------------------------------------------------------------
# 偏移优化
# ---------------------------------------------------------------------------

class TestSolveOffsets:
    def test_two_nodes_returns_array(self):
        greens = np.array([30.0, 30.0])
        tau_f = np.array([28.0])
        tau_b = np.array([28.0])
        offsets = solve_offsets(2, greens, 90.0, tau_f, tau_b, strategy="bidirectional")
        assert offsets[0] == 0.0
        assert len(offsets) == 2

    def test_oneway_forward(self):
        greens = np.array([30.0, 30.0])
        tau_f = np.array([28.0])
        tau_b = np.array([28.0])
        offsets = solve_offsets(2, greens, 90.0, tau_f, tau_b, strategy="oneway_forward")
        assert len(offsets) == 2

    def test_three_nodes_bidirectional_no_double_stop(self):
        greens = np.array([30.0, 30.0, 30.0])
        tau_f = np.array([20.0, 20.0])
        tau_b = np.array([20.0, 20.0])
        offsets = solve_offsets(3, greens, 90.0, tau_f, tau_b,
                               strategy="bidirectional_no_double_stop")
        assert offsets[0] == 0.0
        assert len(offsets) == 3


# ---------------------------------------------------------------------------
# 完整求解
# ---------------------------------------------------------------------------

class TestSolveCorridorFull:
    def test_two_nodes_no_rich_data(self):
        result = solve_corridor_full(
            ["A", "B"],
            [{"intersection_id": "A"}, {"intersection_id": "B"}],
            [ArterialLink(400, 50)],
            min_cycle_s=70,
            max_cycle_s=110,
        )
        assert result["ok"] is True
        assert result["cycle_s"] >= 70
        assert result["cycle_s"] <= 110
        assert len(result["nodes"]) == 2
        assert result["bandwidth_s"] >= 0
        assert result["bandwidth_forward_s"] >= 0
        assert result["bandwidth_reverse_s"] >= 0
        assert "adjacent_double_stop_proxy" in result["kpis"]
        assert result["meta"]["critical_intersection_id"] in ("A", "B")

    def test_three_nodes_with_phases(self):
        result = solve_corridor_full(
            ["N1", "N2", "N3"],
            [
                _make_two_phase_intersection("N1", 600, 400),
                _make_two_phase_intersection("N2", 500, 500),
                _make_two_phase_intersection("N3", 700, 300),
            ],
            [ArterialLink(400, 50), ArterialLink(350, 50)],
            min_cycle_s=70,
            max_cycle_s=120,
            strategy="bidirectional",
        )
        assert result["ok"] is True
        assert len(result["nodes"]) == 3
        for node in result["nodes"]:
            assert node["cycle_s"] > 0
            assert node["main_coordination_offset_s"] >= 0
            assert node["main_coordination_phase_id"] != ""
            assert node["green_ratio"] > 0
            assert len(node["phase_stage_timing_list"]) >= 2
            assert node["first_optimization"]["cycle_s"] > 0
            assert node["second_optimization"]["cycle_s"] > 0
            assert len(node["first_optimization"]["phase_stage_timing_list"]) >= 2
            assert len(node["second_optimization"]["phase_stage_timing_list"]) >= 2

    def test_empty_ids(self):
        result = solve_corridor_full([], [], [])
        assert result["ok"] is False

    def test_strategy_oneway_forward(self):
        result = solve_corridor_full(
            ["A", "B"],
            [_make_two_phase_intersection("A"), _make_two_phase_intersection("B")],
            [ArterialLink(400, 50)],
            strategy="oneway_forward",
        )
        assert result["ok"] is True
        assert result["strategy"] == "oneway_forward"

    def test_strategy_bidirectional_no_double_stop(self):
        result = solve_corridor_full(
            ["A", "B", "C"],
            [_make_two_phase_intersection("A"), _make_two_phase_intersection("B"),
             _make_two_phase_intersection("C")],
            [ArterialLink(300, 50), ArterialLink(300, 50)],
            strategy="bidirectional_no_double_stop",
        )
        assert result["ok"] is True
        assert "adjacent_double_stop_proxy" in result["kpis"]


# ---------------------------------------------------------------------------
# corridor.py 路由
# ---------------------------------------------------------------------------

class TestCorridorRouting:
    def test_mvp_path(self):
        plan = generate_corridor_coordination_plan({
            "corridor_id": "MVP",
            "intersection_ids": ["A", "B"],
            "constraints": {"design_speed_kmh": 50, "default_link_spacing_m": 400},
        })
        assert plan["plan_type"] == "corridor_coordination"
        assert plan["coordination"]["bandwidth_s"] > 0
        for node in plan["coordination"]["nodes"]:
            assert "main_coordination_offset_s" in node
            assert "phase_stage_timing_list" in node

    def test_full_solver_path(self):
        plan = generate_corridor_coordination_plan(_make_three_node_request())
        assert plan["plan_type"] == "corridor_coordination"
        coord = plan["coordination"]
        assert coord["bandwidth_s"] >= 0
        assert coord["bandwidth_forward_s"] >= 0
        assert coord["bandwidth_reverse_s"] >= 0
        assert coord["strategy"] == "bidirectional"
        assert len(coord["nodes"]) == 3
        for node in coord["nodes"]:
            assert "main_coordination_offset_s" in node
            assert "main_coordination_phase_id" in node
            assert "phase_stage_timing_list" in node
            assert node["cycle_s"] > 0
            assert "first_optimization" in node
            assert "second_optimization" in node

    def test_full_solver_with_strategy_flag(self):
        plan = generate_corridor_coordination_plan(
            _make_three_node_request("oneway_forward"))
        assert plan["coordination"]["strategy"] == "oneway_forward"


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

class TestCorridorHTTPAPI:
    def test_corridor_with_intersections(self):
        client = TestClient(app)
        response = client.post("/v1/planning/corridor", json=_make_three_node_request())
        assert response.status_code == 200
        data = response.json()
        plan = data["plan"]
        coord = plan["coordination"]
        assert coord["cycle_s"] is not None
        assert coord["bandwidth_s"] >= 0
        assert "bandwidth_forward_s" in coord
        assert "bandwidth_reverse_s" in coord
        nodes = coord["nodes"]
        assert len(nodes) == 3
        for node in nodes:
            assert "main_coordination_offset_s" in node
            assert "phase_stage_timing_list" in node
            assert "first_optimization" in node
            assert "second_optimization" in node

    def test_corridor_mvp_still_works(self):
        client = TestClient(app)
        response = client.post("/v1/planning/corridor", json={
            "corridor_id": "MVP-HTTP",
            "intersection_ids": ["a", "b"],
            "constraints": {"design_speed_kmh": 50, "default_link_spacing_m": 300},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["plan"]["coordination"]["cycle_s"] is not None
