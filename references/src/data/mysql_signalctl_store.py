"""signalctl MySQL 只读查询：路口、渠化、配时阶段表、流量、排队.

表名与字段以现网库为准；`signal_timing_stage_d` 与 `queue_length_all` 通过路口名称
与 `路口信息表` 关联，`traffic_flow_d` / `路口渠化信息表` 通过 cross_id = 路口 id 关联。
路口渠化信息表的 lane_num 列表示该进口方向上的车道条数（非车道序号）；地图 overlay 会展开为逐车道条目。
车道转向等缺失字段保持为空（JSON null），不填默认值。
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from src.common.config import get_settings
from src.common.geo_transform import gcj02_bbox_to_wgs84_bounds, wgs84_to_gcj02


def _pymysql():
    """延迟导入，避免未安装 PyMySQL 时整个包无法加载；并给出可操作的安装提示."""
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as e:
        raise RuntimeError(
            "当前 Python 环境未安装 PyMySQL。请在**运行 uvicorn 的同一环境**中执行: pip install pymysql "
            "或使用项目虚拟环境启动: source .venv/bin/activate && uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
        ) from e
    return pymysql, DictCursor

# 固定表名（含中文表），勿拼接用户输入
T_INTERSECTION = "`路口信息表`"
T_CHANNEL = "`路口渠化信息表`"
T_TIMING_STAGE = "`signal_timing_stage_d`"
T_TRAFFIC = "`traffic_flow_d`"
T_QUEUE = "`queue_length_all`"

# SHOW COLUMNS 解析到的小时维度 SQL 片段缓存（库名固定于连接）
_lane_hour_expr_cache: dict[str, tuple[str, str] | None] = {}


def _parse_mysql_url(mysql_url: str) -> dict[str, Any]:
    parsed = urlparse(mysql_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError("MYSQL_URL 仅支持 mysql:// 或 mysql+pymysql://")
    database = parsed.path.lstrip("/")
    if not database:
        raise ValueError("MYSQL_URL 缺少数据库名")
    query = parse_qs(parsed.query)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": database.split("?")[0],
        "charset": query.get("charset", ["utf8mb4"])[0],
    }


def mysql_signalctl_connection() -> Any:
    pymysql, dict_cursor = _pymysql()
    mysql_url = get_settings().mysql_url
    if not mysql_url:
        raise RuntimeError("未配置 MYSQL_URL")
    args = _parse_mysql_url(mysql_url)
    args["cursorclass"] = dict_cursor
    args["autocommit"] = True
    return pymysql.connect(**args)


def _jsonable(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def _row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _jsonable(v) for k, v in row.items()}


def _intersection_coord_profile() -> str:
    v = (get_settings().mysql_intersection_lonlat_srs or "wgs84").strip().lower()
    return v if v in ("wgs84", "gcj02") else "wgs84"


def _expose_intersection_lonlat(d: dict[str, Any]) -> dict[str, Any]:
    """将路口 lon/lat 转为高德所用 GCJ-02；库内为 WGS-84 时写入 lon_wgs84/lat_wgs84 元数据."""
    out = dict(d)
    ln, lt = out.get("lon"), out.get("lat")
    if ln is None or lt is None:
        return out
    if _intersection_coord_profile() == "gcj02":
        out["coord_srs_db"] = "GCJ-02"
        out["coord_srs_map"] = "GCJ-02"
        return out
    fln, flat = float(ln), float(lt)
    gcj_ln, gcj_lt = wgs84_to_gcj02(fln, flat)
    out["lon"] = gcj_ln
    out["lat"] = gcj_lt
    out["lon_wgs84"] = fln
    out["lat_wgs84"] = flat
    out["coord_srs_db"] = "WGS-84"
    out["coord_srs_map"] = "GCJ-02"
    return out


def list_intersections(
    *,
    min_lon: float | None = None,
    min_lat: float | None = None,
    max_lon: float | None = None,
    max_lat: float | None = None,
) -> list[dict[str, Any]]:
    """列出带坐标的路口（可选矩形范围）.

    当 ``MYSQL_INTERSECTION_LONLAT_SRS=wgs84``（默认）时，库内为 WGS-84；``min_lon`` 等
    筛选参数应按 **GCJ-02（与高德 getBounds 一致）** 传入，服务端会换算为 WGS-84 再查库。
    """
    where = ["lon IS NOT NULL", "lat IS NOT NULL"]
    params: list[Any] = []
    if min_lon is not None and max_lon is not None and min_lat is not None and max_lat is not None:
        where.append("lon BETWEEN %s AND %s AND lat BETWEEN %s AND %s")
        if _intersection_coord_profile() == "gcj02":
            params.extend([min_lon, max_lon, min_lat, max_lat])
        else:
            w_min_lon, w_max_lon, w_min_lat, w_max_lat = gcj02_bbox_to_wgs84_bounds(
                min_lon, min_lat, max_lon, max_lat
            )
            params.extend([w_min_lon, w_max_lon, w_min_lat, w_max_lat])
    sql = (
        f"SELECT id, name, lon, lat, control_vendor, control_crossroad_id, "
        f"amap_crossroad_id, platform_id, road_type, adcode "
        f"FROM {T_INTERSECTION} WHERE " + " AND ".join(where) + " ORDER BY name"
    )
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_expose_intersection_lonlat(_row(r)) for r in cur.fetchall()]


def get_intersection_by_id(intersection_id: str) -> dict[str, Any] | None:
    sql = f"SELECT * FROM {T_INTERSECTION} WHERE id = %s LIMIT 1"
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (intersection_id,))
            r = cur.fetchone()
            return _expose_intersection_lonlat(_row(r)) if r else None


def get_latest_timing_by_name(name: str) -> dict[str, Any] | None:
    sql = (
        f"SELECT id, cross_id, name, pattern, cycle_len, ring_count, offset, "
        f"data_date, request_time, sink_time, "
        f"stage_direction_desc, stage_time, phase_direction_map, "
        f"cycle_list, phase_list "
        f"FROM {T_TIMING_STAGE} WHERE name = %s "
        f"ORDER BY data_date DESC, id DESC LIMIT 1"
    )
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name,))
            r = cur.fetchone()
            return _row(r) if r else None


def aggregate_traffic(cross_id: str, data_date: date | None) -> dict[str, Any]:
    """按路口汇总流量；未指定日期则用该路口最新 data_date。"""
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            if data_date is None:
                cur.execute(
                    f"SELECT MAX(data_date) AS d FROM {T_TRAFFIC} WHERE cross_id = %s",
                    (cross_id,),
                )
                dr = cur.fetchone()
                data_date = dr["d"] if dr and dr["d"] else None
            if data_date is None:
                return {"data_date": None, "total_flow": 0, "row_count": 0, "by_lane": []}
            cur.execute(
                f"SELECT lane_num, entry, entry_type, SUM(traffic_flow_count) AS flow "
                f"FROM {T_TRAFFIC} WHERE cross_id = %s AND data_date = %s "
                f"GROUP BY lane_num, entry, entry_type ORDER BY flow DESC",
                (cross_id, data_date),
            )
            by_lane = [_row(x) for x in cur.fetchall()]
            cur.execute(
                f"SELECT SUM(traffic_flow_count) AS t, COUNT(*) AS c FROM {T_TRAFFIC} "
                f"WHERE cross_id = %s AND data_date = %s",
                (cross_id, data_date),
            )
            agg = cur.fetchone() or {}
            return {
                "data_date": _jsonable(data_date),
                "total_flow": int(agg.get("t") or 0),
                "row_count": int(agg.get("c") or 0),
                "by_lane": by_lane,
            }


def aggregate_queue(name: str, data_date: date | None) -> dict[str, Any]:
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            if data_date is None:
                cur.execute(
                    f"SELECT MAX(data_date) AS d FROM {T_QUEUE} WHERE name = %s",
                    (name,),
                )
                dr = cur.fetchone()
                data_date = dr["d"] if dr and dr["d"] else None
            if data_date is None:
                return {"data_date": None, "avg_queue": None, "max_queue": None, "sample_count": 0}
            cur.execute(
                f"SELECT AVG(queueLength) AS a, MAX(queueLength) AS m, COUNT(*) AS c "
                f"FROM {T_QUEUE} WHERE name = %s AND data_date = %s",
                (name, data_date),
            )
            r = cur.fetchone() or {}
            return {
                "data_date": _jsonable(data_date),
                "avg_queue": float(r["a"]) if r.get("a") is not None else None,
                "max_queue": float(r["m"]) if r.get("m") is not None else None,
                "sample_count": int(r.get("c") or 0),
            }


def queue_stats_by_lane(name: str, data_date: date | None) -> list[dict[str, Any]]:
    """排队按进口方位 + 车道号聚合，供渠化叠加与图例."""
    if not name:
        return []
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            if data_date is None:
                cur.execute(
                    f"SELECT MAX(data_date) AS d FROM {T_QUEUE} WHERE name = %s",
                    (name,),
                )
                dr = cur.fetchone()
                data_date = dr["d"] if dr and dr["d"] else None
            if data_date is None:
                return []
            cur.execute(
                f"SELECT face_direction, `laneNum` AS lane_num, "
                f"MAX(queueLength) AS queue_max, AVG(queueLength) AS queue_avg, COUNT(*) AS n "
                f"FROM {T_QUEUE} WHERE name = %s AND data_date = %s "
                f"GROUP BY face_direction, `laneNum` "
                f"ORDER BY face_direction, lane_num",
                (name, data_date),
            )
            return [_row(x) for x in cur.fetchall()]


def _table_column_names(cur: Any, table_ref: str) -> list[str]:
    cur.execute(f"SHOW COLUMNS FROM {table_ref}")
    return [str(r["Field"]) for r in cur.fetchall()]


def _pick_hour_sql_expression(columns: list[str]) -> tuple[str, str] | None:
    """返回 (SELECT/GROUP BY 用 SQL 片段, 人类可读说明)；无可用列时 None."""
    lower_map = {c.lower(): c for c in columns}
    int_candidates = (
        "hour",
        "data_hour",
        "stat_hour",
        "time_hour",
        "bh",
        "统计小时",
        "小时",
        "time_slice",
    )
    for name in int_candidates:
        lk = name.lower()
        if lk in lower_map:
            c = lower_map[lk]
            return f"`{c}`", c
    dt_candidates = (
        "record_time",
        "data_time",
        "create_time",
        "sink_time",
        "request_time",
        "data_datetime",
        "ts",
        "统计时间",
        "采集时间",
        "event_time",
    )
    for name in dt_candidates:
        lk = name.lower()
        if lk in lower_map:
            c = lower_map[lk]
            expr = f"HOUR(`{c}`)"
            return expr, f"HOUR({c})"
    return None


def _cached_hour_expr(cur: Any, table_ref: str) -> tuple[str, str] | None:
    key = table_ref.strip("`")
    if key in _lane_hour_expr_cache:
        return _lane_hour_expr_cache[key]
    try:
        cols = _table_column_names(cur, table_ref)
    except Exception:
        _lane_hour_expr_cache[key] = None
        return None
    picked = _pick_hour_sql_expression(cols)
    _lane_hour_expr_cache[key] = picked
    return picked


def lane_hour_metrics(
    cross_id: str,
    intersection_name: str,
    *,
    data_date: date | None,
) -> dict[str, Any]:
    """按车道 + 小时：流量为 traffic_flow_count 时段内求和；排队为 queueLength 按样本平均（先按小时聚再供前端做时段加权）。"""
    traffic_rows: list[dict[str, Any]] = []
    queue_rows: list[dict[str, Any]] = []
    traffic_dd: date | None = data_date
    queue_dd: date | None = data_date
    traffic_dim: str | None = None
    queue_dim: str | None = None

    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            if traffic_dd is None:
                cur.execute(
                    f"SELECT MAX(data_date) AS d FROM {T_TRAFFIC} WHERE cross_id = %s",
                    (cross_id,),
                )
                dr = cur.fetchone()
                traffic_dd = dr["d"] if dr and dr.get("d") else None
            if queue_dd is None and intersection_name:
                cur.execute(
                    f"SELECT MAX(data_date) AS d FROM {T_QUEUE} WHERE name = %s",
                    (intersection_name,),
                )
                drq = cur.fetchone()
                queue_dd = drq["d"] if drq and drq.get("d") else None

            he_t = _cached_hour_expr(cur, T_TRAFFIC) if traffic_dd else None
            if he_t and traffic_dd:
                he_sql, traffic_dim = he_t
                cur.execute(
                    f"SELECT {he_sql} AS hr, lane_num, `entry`, `entry_type`, "
                    f"SUM(traffic_flow_count) AS flow "
                    f"FROM {T_TRAFFIC} WHERE cross_id = %s AND data_date = %s "
                    f"GROUP BY {he_sql}, lane_num, `entry`, `entry_type` "
                    f"ORDER BY hr, `entry`, lane_num, `entry_type`",
                    (cross_id, traffic_dd),
                )
                traffic_rows = [_row(x) for x in cur.fetchall()]

            he_q = _cached_hour_expr(cur, T_QUEUE) if intersection_name and queue_dd else None
            if he_q and queue_dd and intersection_name:
                he_sql_q, queue_dim = he_q
                cur.execute(
                    f"SELECT {he_sql_q} AS hr, face_direction, `laneNum` AS lane_num, "
                    f"AVG(queueLength) AS queue_avg, COUNT(*) AS n "
                    f"FROM {T_QUEUE} WHERE name = %s AND data_date = %s "
                    f"GROUP BY {he_sql_q}, face_direction, `laneNum` "
                    f"ORDER BY hr, face_direction, lane_num",
                    (intersection_name, queue_dd),
                )
                queue_rows = [_row(x) for x in cur.fetchall()]

    return {
        "traffic": {
            "data_date": _jsonable(traffic_dd) if traffic_dd else None,
            "hour_dimension": traffic_dim,
            "rows": traffic_rows,
        },
        "queue": {
            "data_date": _jsonable(queue_dd) if queue_dd else None,
            "hour_dimension": queue_dim,
            "rows": queue_rows,
        },
    }


# 渠化 dir 与 traffic_flow_d.entry、queue_length_all.face_direction 中文对齐（八方位）
_DIR_TO_APPROACH: dict[int, str] = {
    0: "北",
    1: "东北",
    2: "东",
    3: "东南",
    4: "南",
    5: "西南",
    6: "西",
    7: "西北",
}
_APPROACH_NAMES: frozenset[str] = frozenset(_DIR_TO_APPROACH.values())
_APPROACH_TO_DIR: dict[str, int] = {v: k for k, v in _DIR_TO_APPROACH.items()}

# 渠化表常见列名差异（现网库可能为中文列名或与 traffic 表一致的 face_direction）
_CHANNEL_LINK_COLUMNS: tuple[str, ...] = (
    "cross_id",
    "路口id",
    "路口ID",
    "intersection_id",
)


def _first_key_value(row: dict[str, Any], *candidates: str) -> Any:
    if not row:
        return None
    lower_index = {str(k).lower(): k for k in row}
    for c in candidates:
        if c in row:
            return row[c]
        lk = str(c).lower()
        if lk in lower_index:
            return row[lower_index[lk]]
    return None


def _coerce_channel_dir(val: Any) -> int:
    if val is None or val == "":
        return -1
    if isinstance(val, bool):
        return -1
    if isinstance(val, (int, float)):
        i = int(val)
        return i if 0 <= i <= 7 else -1
    s = str(val).strip()
    if not s:
        return -1
    try:
        i = int(float(s))
        return i if 0 <= i <= 7 else -1
    except (TypeError, ValueError):
        pass
    return _APPROACH_TO_DIR.get(s, -1)


def _coerce_channel_lane_num(val: Any) -> int:
    if val is None or val == "":
        return 0
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def _optional_int_field(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _row_approach_lane_count(r: dict[str, Any]) -> int:
    """渠化行：进口车道条数（表字段 lane_num 的语义）."""
    c = int(r.get("lane_count") or 0)
    if c > 0:
        return c
    return _coerce_channel_lane_num(r.get("lane_num"))


def _legacy_one_row_per_lane(rows: list[dict[str, Any]]) -> bool:
    """兼容旧库：同一进口多行、每行 lane_num 为车道序号 1..N（且未写 lane_count）。"""
    if len(rows) <= 1:
        return False
    if not all(_row_approach_lane_count(r) <= 1 for r in rows):
        return False
    idxs = sorted({_coerce_channel_lane_num(r.get("lane_num")) for r in rows})
    if not idxs or idxs[0] < 1:
        return False
    return idxs == list(range(1, len(idxs) + 1)) and len(idxs) == len(rows)


def _normalize_channel_record(raw: dict[str, Any]) -> dict[str, Any]:
    """将 SELECT * 的渠化行映射为 overlay 使用的标准字段（保留原列便于排查）."""
    out = dict(raw)
    d_raw = _first_key_value(
        raw,
        "dir",
        "direction",
        "进口方向",
        "方位",
        "face_direction",
        "FaceDir",
        "faceDirection",
    )
    ln_raw = _first_key_value(
        raw,
        "lane_num",
        "laneNum",
        "lane_no",
        "laneNo",
        "进口车道数",
        "车道数量",
        "车道数",
        "车道条数",
    )
    len_raw = _first_key_value(
        raw,
        "lane_len",
        "laneLen",
        "lane_length",
        "车道长度",
        "渠化长度",
        "长度",
    )
    et_raw = _first_key_value(raw, "entry_type", "entryType", "入口类型")
    dd_raw = _first_key_value(raw, "drive_dir", "driveDir", "行驶方向", "流向", "车道转向", "转向")

    out["dir"] = _coerce_channel_dir(d_raw)
    # 表列 lane_num：该进口方向车道条数（非车道序号）
    out["lane_count"] = max(0, _coerce_channel_lane_num(ln_raw))
    if len_raw is not None:
        try:
            out["lane_len"] = int(float(len_raw))
        except (TypeError, ValueError):
            out["lane_len"] = 0
    et = _optional_int_field(et_raw)
    if et is not None:
        out["entry_type"] = et
    else:
        out["entry_type"] = None
    if dd_raw is not None and str(dd_raw).strip():
        out["drive_dir"] = str(dd_raw).strip()
    else:
        out["drive_dir"] = None
    return out


def _channel_link_column_sql(name: str) -> str:
    if name == "cross_id":
        return "cross_id"
    return f"`{name}`"


def list_channelization_for_intersection(
    intersection: dict[str, Any], *, limit: int = 500
) -> list[dict[str, Any]]:
    """查询路口渠化信息表：多关联键、多外键列尝试，并规整列名与方位编码."""
    _pymysql()
    from pymysql.err import OperationalError

    bind_vals: list[str] = []
    rid = intersection.get("id")
    if rid is not None and str(rid).strip():
        bind_vals.append(str(rid).strip())
    for key in ("platform_id", "control_crossroad_id", "amap_crossroad_id"):
        v = intersection.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s and s not in bind_vals:
            bind_vals.append(s)
    if not bind_vals:
        return []

    rows_raw: list[dict[str, Any]] = []
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            for bv in bind_vals:
                for link in _CHANNEL_LINK_COLUMNS:
                    sql = f"SELECT * FROM {T_CHANNEL} WHERE {_channel_link_column_sql(link)} = %s LIMIT %s"
                    try:
                        cur.execute(sql, (bv, limit))
                    except OperationalError as e:
                        if e.args and e.args[0] == 1054:
                            continue
                        raise
                    batch = cur.fetchall()
                    if batch:
                        rows_raw = list(batch)
                        break
                if rows_raw:
                    break

    normed = [_normalize_channel_record(_row(r)) for r in rows_raw]
    normed.sort(key=lambda x: (int(x.get("dir") or -1), int(x.get("lane_count") or 0)))
    return normed


def list_channelization(cross_id: str, limit: int = 500) -> list[dict[str, Any]]:
    """仅按路口信息表 id 查 cross_id（无多键回退）；兼容旧调用."""
    return list_channelization_for_intersection({"id": cross_id}, limit=limit)


def build_channel_overlay_spec(
    channel_rows: list[dict[str, Any]],
    traffic_by_lane: list[dict[str, Any]],
    queue_by_lane: list[dict[str, Any]],
) -> dict[str, Any]:
    """合并渠化、分车道流量、分车道排队，供前端在路口中心绘制示意条带."""
    flow_sum: dict[tuple[str, int], int] = {}
    for r in traffic_by_lane or []:
        ap = str(r.get("entry") or "").strip() or "未知"
        try:
            ln = int(r.get("lane_num") or 0)
        except (TypeError, ValueError):
            continue
        key = (ap, ln)
        flow_sum[key] = flow_sum.get(key, 0) + int(r.get("flow") or 0)

    queue_map: dict[tuple[str, int], dict[str, float | int]] = {}
    for r in queue_by_lane or []:
        ap = str(r.get("face_direction") or "").strip() or "未知"
        try:
            ln = int(r.get("lane_num") or 0)
        except (TypeError, ValueError):
            continue
        queue_map[(ap, ln)] = {
            "queue_max": float(r["queue_max"] or 0),
            "queue_avg": float(r["queue_avg"] or 0),
            "samples": int(r.get("n") or 0),
        }

    # 同一进口方向多行时取最大车道条数；几何/类型字段取自「条数最大」的代表行
    by_dir: dict[int, list[dict[str, Any]]] = {}
    for r in channel_rows or []:
        d = _coerce_channel_dir(r.get("dir"))
        if not (0 <= d <= 7):
            continue
        by_dir.setdefault(d, []).append(r)

    lanes_acc: dict[tuple[int, int], dict[str, Any]] = {}
    for d, rows in by_dir.items():
        if _legacy_one_row_per_lane(rows):
            lane_count = len(rows)
            rep = max(rows, key=lambda x: int(x.get("lane_len") or 0))
        else:
            lane_count = max((_row_approach_lane_count(x) for x in rows), default=0)
            if lane_count <= 0:
                continue
            rep = max(
                rows,
                key=lambda x: (_row_approach_lane_count(x), int(x.get("lane_len") or 0)),
            )
        if lane_count <= 0:
            continue
        approach = _DIR_TO_APPROACH[d]
        lane_len_m = int(rep.get("lane_len") or 0)
        entry_type = rep.get("entry_type")
        if entry_type is not None and not isinstance(entry_type, bool):
            try:
                entry_type = int(float(entry_type))
            except (TypeError, ValueError):
                entry_type = None
        drive_dir = rep.get("drive_dir")
        if drive_dir is not None:
            drive_dir = str(drive_dir).strip() or None

        for idx in range(1, lane_count + 1):
            key = (d, idx)
            lanes_acc[key] = {
                "dir": d,
                "approach": approach,
                "lane_num": idx,
                "lane_len_m": lane_len_m,
                "entry_type": entry_type,
                "drive_dir": drive_dir,
            }

    lanes: list[dict[str, Any]] = []
    for (_d, _ln), meta in sorted(lanes_acc.items(), key=lambda x: (x[0][0], x[0][1])):
        ap = str(meta["approach"])
        ln = int(meta["lane_num"])
        fk = (ap, ln) if ap in _APPROACH_NAMES else None
        flow = flow_sum.get(fk, 0) if fk else 0
        qinfo = queue_map.get(fk) if fk else None
        lanes.append(
            {
                **meta,
                "traffic_flow": flow,
                "queue_max_m": (qinfo or {}).get("queue_max"),
                "queue_avg_m": (qinfo or {}).get("queue_avg"),
                "queue_samples": (qinfo or {}).get("samples"),
            }
        )

    return {
        "dir_scheme": (
            "渠化表 lane_num：该进口方向车道条数（非序号）；overlay.lanes 按车道 1..N 展开。"
            "dir：0北 1东北 2东 3东南 4南 5西南 6西 7西北；"
            "与 traffic_flow_d.entry、queue_length_all.face_direction 中文一致方可匹配流量/排队"
        ),
        "lanes": lanes,
        "legend": {
            "flow": "车道条带填充色：流量相对越高越偏红（绿→黄→红）",
            "queue": "车道条带描边：排队越大红色描边越粗",
        },
    }


def global_latest_dates() -> dict[str, Any]:
    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT MAX(data_date) AS d FROM {T_TRAFFIC}")
            t = cur.fetchone()
            cur.execute(f"SELECT MAX(data_date) AS d FROM {T_QUEUE}")
            q = cur.fetchone()
            cur.execute(f"SELECT MAX(data_date) AS d FROM {T_TIMING_STAGE}")
            s = cur.fetchone()
        return {
            "traffic_latest": _jsonable(t["d"]) if t and t.get("d") else None,
            "queue_latest": _jsonable(q["d"]) if q and q.get("d") else None,
            "timing_latest": _jsonable(s["d"]) if s and s.get("d") else None,
        }


def batch_metrics(
    intersection_ids: list[str],
    *,
    data_date: date | None = None,
) -> dict[str, Any]:
    """批量指标：流量（按 id）、排队与配时（按路口名称，需先查 name）."""
    if not intersection_ids:
        return {"data_date": _jsonable(data_date) if data_date else None, "by_id": {}}
    id_list = list(dict.fromkeys(intersection_ids))  # 保序去重
    placeholders = ",".join(["%s"] * len(id_list))

    with mysql_signalctl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, name FROM {T_INTERSECTION} WHERE id IN ({placeholders})",
                id_list,
            )
            id_to_name = {r["id"]: r["name"] for r in cur.fetchall()}
            names = [id_to_name[i] for i in id_list if i in id_to_name]

            if data_date is None:
                cur.execute(f"SELECT MAX(data_date) AS d FROM {T_TRAFFIC}")
                dr = cur.fetchone()
                data_date = dr["d"] if dr and dr["d"] else None

            flow_by_id: dict[str, int] = {i: 0 for i in id_list}
            if data_date is not None:
                cur.execute(
                    f"SELECT cross_id, SUM(traffic_flow_count) AS t FROM {T_TRAFFIC} "
                    f"WHERE cross_id IN ({placeholders}) AND data_date = %s GROUP BY cross_id",
                    [*id_list, data_date],
                )
                for r in cur.fetchall():
                    flow_by_id[str(r["cross_id"])] = int(r["t"] or 0)

            queue_by_name: dict[str, dict[str, Any]] = {}
            if names:
                phn = ",".join(["%s"] * len(names))
                qdate = data_date
                if qdate is None:
                    cur.execute(f"SELECT MAX(data_date) AS d FROM {T_QUEUE}")
                    qd = cur.fetchone()
                    qdate = qd["d"] if qd and qd["d"] else None
                if qdate is not None:
                    cur.execute(
                        f"SELECT name, AVG(queueLength) AS a, MAX(queueLength) AS m, COUNT(*) AS c "
                        f"FROM {T_QUEUE} WHERE name IN ({phn}) AND data_date = %s GROUP BY name",
                        [*names, qdate],
                    )
                    for r in cur.fetchall():
                        queue_by_name[r["name"]] = {
                            "avg_queue": float(r["a"]) if r.get("a") is not None else None,
                            "max_queue": float(r["m"]) if r.get("m") is not None else None,
                            "sample_count": int(r.get("c") or 0),
                            "data_date": _jsonable(qdate),
                        }

            timing_by_name: dict[str, dict[str, Any]] = {}
            if names:
                for nm in names:
                    cur.execute(
                        f"SELECT cycle_len, pattern, data_date, cross_id FROM {T_TIMING_STAGE} "
                        f"WHERE name = %s ORDER BY data_date DESC, id DESC LIMIT 1",
                        (nm,),
                    )
                    tr = cur.fetchone()
                    if tr:
                        timing_by_name[nm] = {
                            "cycle_len": tr.get("cycle_len"),
                            "pattern": tr.get("pattern"),
                            "data_date": _jsonable(tr.get("data_date")),
                            "vendor_cross_id": tr.get("cross_id"),
                        }

            ch_count: dict[str, int] = {i: 0 for i in id_list}
            cur.execute(
                f"SELECT cross_id, COUNT(*) AS c FROM {T_CHANNEL} "
                f"WHERE cross_id IN ({placeholders}) GROUP BY cross_id",
                id_list,
            )
            for r in cur.fetchall():
                ch_count[str(r["cross_id"])] = int(r["c"] or 0)

    by_id: dict[str, Any] = {}
    for i in id_list:
        nm = id_to_name.get(i)
        by_id[i] = {
            "name": nm,
            "total_flow": flow_by_id.get(i, 0),
            "channel_rows": ch_count.get(i, 0),
            "timing": timing_by_name.get(nm) if nm else None,
            "queue": queue_by_name.get(nm) if nm else None,
        }

    return {
        "traffic_data_date": _jsonable(data_date) if data_date else None,
        "by_id": by_id,
    }
