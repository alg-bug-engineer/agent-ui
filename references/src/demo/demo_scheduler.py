"""Demo 级自动调度器.

职责：
- 周期扫描（默认 60 秒）检测当前 demo 数据中的异常对象
- 识别规律性场景（通勤高峰/学校/医院等）并触发对应 Run
- 识别实时动态异常并触发实时 Run
- 避免对同一对象重复触发（冷却期机制）
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.demo.run_model import SceneType, TriggerSource
from src.demo.run_orchestrator import RunOrchestrator, get_orchestrator
from src.demo.run_store import RunStore, get_run_store

_DEMO_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "data" / "jinan_demo_data.json"

# 实时触发的饱和度阈值
REALTIME_SAT_THRESHOLD = 0.88

# 同一对象的触发冷却期（秒）
TRIGGER_COOLDOWN_SECONDS = 300

# 规律性场景的触发 ID -> 是否已激活
PERIODIC_SCENE_IDS = {
    "SCN-COMMUTE": "通勤走廊早高峰",
    "SCN-SCHOOL": "学校周边接送高峰",
}


class DemoScheduler:
    """Demo 自动调度器，驱动智能体持续自动运行."""

    def __init__(
        self,
        orchestrator: RunOrchestrator | None = None,
        store: RunStore | None = None,
        scan_interval_seconds: int = 60,
    ) -> None:
        self._orchestrator = orchestrator or get_orchestrator()
        self._store = store or get_run_store()
        self._scan_interval = scan_interval_seconds
        self._running = False
        self._thread: threading.Thread | None = None
        # object_id -> last_trigger_time (timestamp)
        self._cooldown_map: dict[str, float] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # 主扫描循环
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        # 首次启动后 5 秒开始扫描（给 API 服务时间就绪）
        time.sleep(5)
        while self._running:
            try:
                self._scan()
            except Exception:
                pass
            time.sleep(self._scan_interval)

    def _scan(self) -> None:
        data = self._load_demo_data()
        if not data:
            return
        self._scan_realtime_anomalies(data)
        self._scan_periodic_scenes(data)

    # ------------------------------------------------------------------
    # 实时异常扫描
    # ------------------------------------------------------------------

    def _scan_realtime_anomalies(self, data: dict) -> None:
        """扫描饱和度超阈值的对象，触发实时 Run。"""
        candidates = []

        for region in data.get("regions", []):
            sat = region.get("saturation", 0)
            if region.get("status") in ("critical", "warning") and sat >= REALTIME_SAT_THRESHOLD:
                candidates.append({
                    "id": region["id"],
                    "name": region["name"],
                    "type": "region",
                    "saturation": sat,
                    "confidence": min(1.0, sat / 0.95),
                    "reason": f"区域饱和度 {sat:.2f}，超过阈值 {REALTIME_SAT_THRESHOLD}",
                    "data": region,
                })

        for corridor in data.get("corridors", []):
            if corridor.get("status") in ("critical", "warning"):
                sat = corridor.get("stopRate", 0)
                confidence = min(1.0, sat + 0.1)
                candidates.append({
                    "id": corridor["id"],
                    "name": corridor["name"],
                    "type": "corridor",
                    "saturation": sat,
                    "confidence": confidence,
                    "reason": f"干线停车率 {sat:.2f}，运行异常",
                    "data": corridor,
                })

        for inter in data.get("intersections", []):
            sat = inter.get("saturation", 0)
            if inter.get("status") in ("critical", "warning") and sat >= REALTIME_SAT_THRESHOLD:
                candidates.append({
                    "id": inter["id"],
                    "name": inter["name"],
                    "type": "intersection",
                    "saturation": sat,
                    "confidence": min(1.0, sat / 0.95),
                    "reason": f"路口饱和度 {sat:.2f}，超阈值",
                    "data": inter,
                })

        # 按严重程度排序，每次最多触发 3 个（避免 demo 过载）
        candidates.sort(key=lambda x: x["saturation"], reverse=True)
        for c in candidates[:3]:
            if self._in_cooldown(c["id"]):
                continue
            if self._already_running(c["id"]):
                continue
            self._orchestrator.trigger(
                target_id=c["id"],
                target_name=c["name"],
                target_type=c["type"],
                trigger_source=TriggerSource.REALTIME,
                scene_type=SceneType.DYNAMIC,
                trigger_reason=c["reason"],
                trigger_confidence=c["confidence"],
                demo_target_data=c["data"],
            )
            self._mark_cooldown(c["id"])

    # ------------------------------------------------------------------
    # 规律性场景扫描
    # ------------------------------------------------------------------

    def _scan_periodic_scenes(self, data: dict) -> None:
        """扫描 demo 数据中激活的规律性场景，触发周期 Run。"""
        now = datetime.now()
        hour = now.hour

        for scene in data.get("scenarios", []):
            if not scene.get("active"):
                continue
            scene_id = scene["id"]

            # 简单时间规则：通勤 7-9 点，学校 7-9 点和 15-17 点
            is_time = False
            if scene_id == "SCN-COMMUTE" and 7 <= hour < 9:
                is_time = True
            elif scene_id == "SCN-SCHOOL" and ((7 <= hour < 9) or (15 <= hour < 17)):
                is_time = True

            if not is_time:
                continue

            # 触发该场景内的首个有问题对象
            target_ids = scene.get("intersections", []) + scene.get("corridors", []) + scene.get("regions", [])
            for tid in target_ids:
                if self._in_cooldown(f"periodic_{tid}"):
                    continue
                if self._already_running(tid):
                    continue
                target_obj = self._find_obj(data, tid)
                if not target_obj:
                    continue
                obj_type = self._detect_type(data, tid)
                self._orchestrator.trigger(
                    target_id=tid,
                    target_name=target_obj.get("name", tid),
                    target_type=obj_type,
                    trigger_source=TriggerSource.PERIODIC,
                    scene_type=SceneType.PERIODIC,
                    scene_id=scene_id,
                    scene_name=scene.get("name", ""),
                    trigger_reason=f"规律性场景触发：{scene.get('name', scene_id)}",
                    trigger_confidence=0.92,
                    demo_target_data=target_obj,
                )
                self._mark_cooldown(f"periodic_{tid}")
                break  # 每个场景每轮只触发一个对象

    # ------------------------------------------------------------------
    # 手动单次触发（供 API 路由调用）
    # ------------------------------------------------------------------

    def trigger_manual(
        self,
        target_id: str,
        target_name: str,
        target_type: str,
        reason: str = "手动触发",
        demo_target_data: dict | None = None,
    ) -> str:
        return self._orchestrator.trigger(
            target_id=target_id,
            target_name=target_name,
            target_type=target_type,
            trigger_source=TriggerSource.MANUAL,
            scene_type=SceneType.DYNAMIC,
            trigger_reason=reason,
            trigger_confidence=1.0,
            demo_target_data=demo_target_data,
        )

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _in_cooldown(self, obj_id: str) -> bool:
        with self._lock:
            last = self._cooldown_map.get(obj_id)
            if last is None:
                return False
            return (time.time() - last) < TRIGGER_COOLDOWN_SECONDS

    def _mark_cooldown(self, obj_id: str) -> None:
        with self._lock:
            self._cooldown_map[obj_id] = time.time()

    def _already_running(self, target_id: str) -> bool:
        """检查该对象是否已有活跃 Run。"""
        for run in self._store.list_active():
            if run.target_id == target_id and not run.is_complete():
                return True
        return False

    @staticmethod
    def _load_demo_data() -> dict | None:
        try:
            return json.loads(_DEMO_DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _find_obj(data: dict, obj_id: str) -> dict | None:
        for key in ("regions", "corridors", "intersections"):
            for item in data.get(key, []):
                if item.get("id") == obj_id:
                    return item
        return None

    @staticmethod
    def _detect_type(data: dict, obj_id: str) -> str:
        type_map = {
            "regions": "region",
            "corridors": "corridor",
            "intersections": "intersection",
        }
        for key, t in type_map.items():
            if any(item.get("id") == obj_id for item in data.get(key, [])):
                return t
        return "intersection"


# 全局单例
_scheduler: DemoScheduler | None = None


def get_scheduler() -> DemoScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = DemoScheduler()
    return _scheduler
