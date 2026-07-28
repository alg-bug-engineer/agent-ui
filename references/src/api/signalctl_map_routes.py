"""MySQL 信控数据 + 高德底图可视化 API."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/signalctl-map", tags=["信控数据库地图"])


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        y, m, d = (int(x) for x in s.split("-", 2))
        return date(y, m, d)
    except Exception:
        raise HTTPException(status_code=400, detail=f"非法日期: {s}") from None


@router.get("/status")
def map_data_status():
    """是否已配置数据库及路口数量."""
    from src.common.config import get_settings
    from src.data.mysql_signalctl_store import list_intersections, mysql_signalctl_connection

    has_url = bool(get_settings().mysql_url)
    try:
        with mysql_signalctl_connection():
            pass
    except RuntimeError as e:
        # 未配置 URL → configured=false；已配 URL 但缺 PyMySQL 等 → configured=true 便于区分
        return {"ok": False, "configured": has_url, "message": str(e)}
    except Exception as e:
        return {"ok": False, "configured": has_url, "message": str(e)}

    try:
        xs = list_intersections()
    except Exception as e:
        return {"ok": False, "configured": True, "message": str(e)}
    return {"ok": True, "configured": True, "intersection_count": len(xs)}


@router.get("/reference")
def schema_reference():
    """当前工程对接的表与关联方式说明（只读文档）."""
    return {
        "intersections_table": "路口信息表",
        "keys": {
            "intersection_id": "路口信息表.id（UUID）",
            "lon_lat": "默认库内为 WGS-84；API 输出 lon/lat 为 GCJ-02（高德），并带 lon_wgs84/lat_wgs84。"
            "若 MYSQL_INTERSECTION_LONLAT_SRS=gcj02 则库与输出均为 GCJ-02。",
        },
        "bbox_query": "当库为 WGS-84 时，GET /intersections 的 min_lon 等筛选须传 GCJ-02（与 map.getBounds() 一致），服务端会换算后查库。",
        "channelization": {
            "table": "路口渠化信息表",
            "join": "优先 路口渠化信息表.cross_id = 路口信息表.id；若无行则依次用路口的 platform_id、control_crossroad_id、amap_crossroad_id 与渠化表 cross_id 匹配；"
            "仍无则尝试渠化表外键列 路口id / 路口ID / intersection_id（列不存在则自动跳过）。",
            "dir": "0北 1东北 2东 3东南 4南 5西南 6西 7西北；可为整数或中文方位；与 traffic_flow_d.entry、queue_length_all.face_direction 中文一致时匹配流量/排队",
            "lane_num_semantics": "路口渠化信息表.lane_num 表示该进口车道条数；API 的 channelization[].lane_count 与之对应；channel_overlay.lanes 按车道 1..N 展开。",
            "lane_column_aliases": "进口车道数、车道数量 等见 mysql_signalctl_store._normalize_channel_record",
        },
        "timing": {
            "table": "signal_timing_stage_d",
            "join": "按路口名称 signal_timing_stage_d.name = 路口信息表.name（cross_id 与平台 id 口径不一致）",
        },
        "traffic": {
            "table": "traffic_flow_d",
            "join": "traffic_flow_d.cross_id = 路口信息表.id",
        },
        "queue": {
            "table": "queue_length_all",
            "join": "queue_length_all.name = 路口信息表.name",
        },
        "optional_tables": [
            "signal_timing_d（原始相位 JSON）",
            "greenroad_speed_all / greenroad_link_speed_all（绿波速度，与路口 id 映射未固化，本界面未接）",
        ],
        "map_overlay": "GET /intersections/{id}/detail 返回 channel_overlay（合并渠化+分车道流量+排队）与 queue_by_lane，供高德地图绘制示意条带。",
        "lane_hour_metrics": "detail 中 lane_hour_metrics：流量按车道+小时 SUM(traffic_flow_count)；排队按车道+小时 AVG(queueLength)。"
        "小时列通过 SHOW COLUMNS 自动匹配 hour / data_hour / HOUR(record_time) 等。",
    }


@router.get(
    "/intersections",
    summary="路口列表（坐标已转高德 GCJ-02）",
    description="默认库为 WGS-84 时，返回 lon/lat 为 GCJ-02；矩形筛选参数亦为 GCJ-02。",
)
def intersections(
    min_lon: float | None = None,
    min_lat: float | None = None,
    max_lon: float | None = None,
    max_lat: float | None = None,
):
    from src.data.mysql_signalctl_store import list_intersections

    if sum(x is not None for x in (min_lon, min_lat, max_lon, max_lat)) not in (0, 4):
        raise HTTPException(status_code=400, detail="范围筛选需同时提供 min_lon, min_lat, max_lon, max_lat")
    try:
        items = list_intersections(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"count": len(items), "intersections": items}


@router.get("/default-dates")
def default_dates():
    from src.data.mysql_signalctl_store import global_latest_dates

    try:
        return global_latest_dates()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/intersections/{intersection_id}/detail")
def intersection_detail(intersection_id: str, data_date: str | None = None):
    from src.data.mysql_signalctl_store import (
        aggregate_queue,
        aggregate_traffic,
        build_channel_overlay_spec,
        get_intersection_by_id,
        get_latest_timing_by_name,
        lane_hour_metrics,
        list_channelization_for_intersection,
        queue_stats_by_lane,
    )

    d = _parse_date(data_date)
    base = get_intersection_by_id(intersection_id)
    if not base:
        raise HTTPException(status_code=404, detail="路口不存在")
    name = base.get("name") or ""
    try:
        ch = list_channelization_for_intersection(base)
        timing = get_latest_timing_by_name(name) if name else None
        traffic = aggregate_traffic(intersection_id, d)
        queue = aggregate_queue(name, d) if name else {"data_date": None}
        q_lane = queue_stats_by_lane(name, d) if name else []
        overlay = build_channel_overlay_spec(ch, traffic.get("by_lane") or [], q_lane)
        lh = lane_hour_metrics(intersection_id, name, data_date=d)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {
        "intersection": base,
        "channelization": ch,
        "timing_latest": timing,
        "traffic": traffic,
        "queue": queue,
        "queue_by_lane": q_lane,
        "channel_overlay": overlay,
        "lane_hour_metrics": lh,
    }


class BatchMetricsRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, description="路口信息表.id 列表")
    data_date: str | None = Field(default=None, description="YYYY-MM-DD；缺省取流量表最新日期")


@router.post("/metrics/batch")
def metrics_batch(body: BatchMetricsRequest):
    from src.data.mysql_signalctl_store import batch_metrics

    if len(body.ids) > 200:
        raise HTTPException(status_code=400, detail="单次最多 200 个路口")
    try:
        return batch_metrics(body.ids, data_date=_parse_date(body.data_date))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
