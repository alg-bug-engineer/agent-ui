#!/usr/bin/env python3
"""
配时方案转阶段工具：按 cycle_list 的 Ring-Barrier 结构解析「阶段」，
结合 greenTime/yellowTime/redTime（单相位放行时间=绿+黄+红）做多环同步时间线仿真。

支持两种输入输出方式：
  - CSV -> CSV
  - MySQL 源表 -> MySQL 新表（默认）

阶段：在同一屏障段内各环并行；任一环当前相位结束时进入下一子区间；
屏障段依次衔接构成完整周期。

输出（JSON 字符串列）：
  - 阶段方向描述：[[ "东直", "西左", "北行人" ], …] — 无环别；仅含可解析流向；
    同阶段内机动车（东直、西左等）在前，行人（…行人、入行、出行）在后。
  - 阶段时间：[秒数, …]（与上一数组逐元素对应）
  - 相位与方向的对应关系：{"1":"东直","2":"西左",…}，键为相位号字符串，值为该相位全部流向
    拼接（机动车在前、行人在后）；无解析结果的相位不出现在对象中。

相位中文标识：channelDim 解析同 ring_timing_visualizer。
无有效 channelDim 时解析 direction 文本；若 cycle_list 仅含一个 Cycle 且 channelDim 全为 0，
则 direction 按易华录 oad_direction（1–8 进口方位）+ flow_direction（含 20 行人）解析。
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor, SSDictCursor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.config import get_settings

DEFAULT_SOURCE_TABLE = "signal_timing_d"
DEFAULT_TARGET_TABLE = "signal_timing_stage_d"
TARGET_STAGE_DIRECTION_COLUMN = "stage_direction_desc"
TARGET_STAGE_TIME_COLUMN = "stage_time"
TARGET_PHASE_DIRECTION_MAP_COLUMN = "phase_direction_map"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DIRECTION_NAME = {
    0: "北",
    2: "东",
    4: "南",
    6: "西",
    1: "东北",
    3: "东南",
    5: "西南",
    7: "西北",
}

TURN_NAME = {
    -1: "未知",
    11: "直行",
    12: "左转",
    13: "右转",
    14: "直左调头",
    15: "右调头",
    16: "左右调头",
    17: "直右调头",
    18: "左直右调头",
    21: "直左混行",
    22: "直右混行",
    23: "左右混行",
    24: "直左右混行",
    31: "掉头",
    41: "直行掉头",
    42: "左转掉头",
    98: "其他",
    99: "其他",
    100: "出入口行人",
    101: "入口行人",
    102: "出口行人",
}

direction_map = {0: 0, 1: 2, 2: 4, 3: 6, 4: 1, 5: 3, 6: 5, 7: 7}
# channelDim 5bit 段解码用（与 ring_timing_visualizer 一致）
turn_map = {
    1: 12,
    2: 11,
    3: 13,
    4: 31,
    5: 42,
    6: 21,
    7: 23,
    8: 22,
    9: 24,
    10: 41,
    11: 101,
    12: 102,
    13: 100,
    14: 14,
    15: 15,
    16: 16,
    17: 17,
    18: 18,
}
# phase_list「direction」里「方向_转向」文本的第二段与 channelDim 的 5bit 索引（turn_map 1–18）
# 不是同一套枚举；未映射的整数会原样作为“转向码”，若无中文则显示为「码{n}」。
# 若掌握厂商/地方对照表，可在此增加：TEXT_FORMAT_TURN_MAP = {20: 11, ...} 再于 parse_direction_text 中引用。
TEXT_FORMAT_TURN_MAP: dict[int, int] = {}

TURN_SHORT: dict[int, str] = {
    11: "直",
    12: "左",
    13: "右",
    14: "直左掉",
    15: "右掉",
    16: "左右掉",
    17: "直右掉",
    18: "左直右掉",
    21: "直左",
    22: "直右",
    23: "左右",
    24: "直左右",
    31: "掉",
    41: "直掉",
    42: "左掉",
    98: "其他",
    99: "其他",
    100: "行人",
    101: "入行",
    102: "出行",
}

_PAIR_RE = re.compile(r"(\d+)_(\d+)")
_CYCLE_KEY_RE = re.compile(r"^Cycle(\d+)$", re.I)

# ---------------------------------------------------------------------------
# 易华录：单环 + channelDim 全 0 时，direction「方位_流向」文本（方位 1–8，流向见下表）
# ---------------------------------------------------------------------------
EHUALU_OAD_DIRECTION_CN: dict[int, str] = {
    1: "北",
    2: "东北",
    3: "东",
    4: "东南",
    5: "南",
    6: "西南",
    7: "西",
    8: "西北",
}
# flow_code -> (是否行人, 机动车时接在方位后的简称；行人由解析逻辑拼成「{方位}行人」)
EHUALU_FLOW_TO_CN: dict[int, tuple[bool, str]] = {
    1: (False, "左"),
    2: (False, "直"),
    3: (False, "右"),
    4: (False, "掉"),
    5: (False, "直左"),
    6: (False, "直右"),
    7: (False, "直左右"),
    8: (False, "左右"),
    9: (False, "左掉"),
    10: (False, "直掉"),
    11: (False, "右掉"),
    12: (False, "直左掉"),
    13: (False, "直右掉"),
    14: (False, "直左右掉"),
    15: (False, "左右掉"),
}

# 行人相关转向码（与 TURN_NAME 中出入口/入出口行人一致）
PEDESTRIAN_TURNS = frozenset({100, 101, 102})


def _is_pedestrian_turn(turn: int) -> bool:
    return turn in PEDESTRIAN_TURNS


def channelDim_analysis(channel_list: list) -> list:
    result = []
    for num in channel_list:
        if num == 0:
            result.append([])
        else:
            binary_num = bin(num)[2:]
            zero_count = (8 - len(binary_num) % 8) % 8
            binary_num = "0" * zero_count + binary_num
            binary_groups = [binary_num[i : i + 8] for i in range(0, len(binary_num), 8)]
            group_list = []
            for group in binary_groups:
                first_three = int(group[:3], 2)
                last_five = int(group[3:], 2)
                if last_five in turn_map:
                    direction = direction_map.get(first_three, first_three)
                    turn = turn_map[last_five]
                    group_list.append((direction, turn))
            result.append(group_list)
    return result


def _turn_to_short(turn_code: int) -> str:
    if turn_code in TURN_SHORT:
        return TURN_SHORT[turn_code]
    name = TURN_NAME.get(turn_code, "")
    if name:
        return name
    # 非 channelDim 标准内部码（如 direction 文本遗留的原始数）
    return f"码{turn_code}"


def _channels_to_atoms(channels: list[tuple[int, int]]) -> list[tuple[bool, str]]:
    """单相位内每条流向 -> (是否行人, 东直 / 北行人 等原子串)。"""
    atoms: list[tuple[bool, str]] = []
    for d, t in channels:
        dname = DIRECTION_NAME.get(d, f"D{d}")
        atoms.append((_is_pedestrian_turn(t), f"{dname}{_turn_to_short(t)}"))
    return atoms


def all_channel_dim_zero(phase_data: dict) -> bool:
    raw = phase_data.get("channelDim") or ""
    parts = str(raw).split()
    if not parts:
        return True
    try:
        return all(int(x) == 0 for x in parts)
    except ValueError:
        return False


def use_ehualu_direction_text(cycle_list_cell: str, phase_data: dict) -> bool:
    """单 Cycle 且 channelDim 全 0 时启用易华录 direction 解析。"""
    if not all_channel_dim_zero(phase_data):
        return False
    try:
        rings = parse_cycle_list_ordered(
            cycle_list_cell if cycle_list_cell and str(cycle_list_cell).strip() not in ("", "nan") else ""
        )
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        return False
    return len(rings) == 1


def parse_direction_text_ehualu(direction_str: str) -> list[tuple[bool, str]]:
    """
    易华录「方位_流向」：方位 1–8（oad_direction），流向 1–15 与 20（20 为行人）。
    返回与 _channels_to_atoms 相同结构的 (是否行人, 方位+流向简称)。
    """
    atoms: list[tuple[bool, str]] = []
    if not direction_str or not str(direction_str).strip():
        return atoms
    s = str(direction_str).strip()
    if s in ("0", "00"):
        return atoms
    if "_" not in s and "，" not in s:
        return atoms
    for m in _PAIR_RE.finditer(s.replace("，", ",")):
        oad = int(m.group(1))
        flow = int(m.group(2))
        if oad not in EHUALU_OAD_DIRECTION_CN:
            continue
        dcn = EHUALU_OAD_DIRECTION_CN[oad]
        if flow == 20:
            atoms.append((True, f"{dcn}行人"))
            continue
        if flow in EHUALU_FLOW_TO_CN:
            is_ped, suf = EHUALU_FLOW_TO_CN[flow]
            atoms.append((is_ped, f"{dcn}{suf}"))
        else:
            atoms.append((False, f"{dcn}码{flow}"))
    return atoms


def parse_direction_text(direction_str: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    if not direction_str or not str(direction_str).strip():
        return out
    s = str(direction_str).strip()
    if s in ("0", "00"):
        return out
    if "_" not in s and "，" not in s:
        return out
    for m in _PAIR_RE.finditer(s.replace("，", ",")):
        d_idx = int(m.group(1))
        raw_turn = int(m.group(2))
        if d_idx not in range(8):
            continue
        direction = d_idx
        if raw_turn in turn_map:
            turn = turn_map[raw_turn]
        elif raw_turn in TEXT_FORMAT_TURN_MAP:
            turn = TEXT_FORMAT_TURN_MAP[raw_turn]
        else:
            turn = raw_turn
        out.append((direction, turn))
    return out


def _normalize_json_cell(s: str) -> str:
    if not isinstance(s, str):
        return json.dumps(s, ensure_ascii=False)
    t = s.strip()
    t = t.replace("“", '"').replace("”", '"').replace('""', '"')
    t = t.replace("，", ",")
    return t


def parse_one_ring_string(ring_str: str) -> tuple[list[int], list[int]]:
    phases: list[int] = []
    barriers: list[int] = []
    parts = ring_str.replace("_", " _ ").split()
    phase_idx = 0
    for part in parts:
        if part == "_":
            if phases:
                barriers.append(phase_idx - 1)
        elif part.strip():
            phases.append(int(part.strip()))
            phase_idx += 1
    return phases, barriers


def parse_cycle_list_ordered(cycle_list_str: str) -> list[dict[str, list]]:
    if not cycle_list_str or str(cycle_list_str).strip() in ("", "nan"):
        return []
    s = _normalize_json_cell(str(cycle_list_str))
    cycle_dict = json.loads(s)
    keys = [k for k in cycle_dict if _CYCLE_KEY_RE.match(k)]
    keys.sort(key=lambda k: int(_CYCLE_KEY_RE.match(k).group(1)))
    rings = []
    for k in keys:
        p, b = parse_one_ring_string(str(cycle_dict[k]))
        rings.append({"phases": p, "barriers": b})
    return rings


def phases_to_barrier_segments(phases: list[int], barriers: list[int]) -> list[list[int]]:
    if not phases:
        return []
    barriers_sorted = sorted(set(int(x) for x in barriers))
    segments: list[list[int]] = []
    start = 0
    for b in barriers_sorted:
        segments.append(phases[start : b + 1])
        start = b + 1
    if start < len(phases):
        segments.append(phases[start:])
    return segments


def _pad_gyr(phase_data: dict) -> tuple[list[int], list[int], list[int]]:
    def split_ints(key: str) -> list[int]:
        raw = phase_data.get(key) or ""
        try:
            xs = [int(x) for x in str(raw).split()]
        except ValueError:
            xs = []
        while len(xs) < 16:
            xs.append(0)
        return xs[:16]

    return split_ints("greenTime"), split_ints("yellowTime"), split_ints("redTime")


def phase_total_duration(phase_no: int, g: list[int], y: list[int], r: list[int]) -> int:
    i = phase_no - 1
    if i < 0 or i >= 16:
        return 0
    return g[i] + y[i] + r[i]


def load_phase_data(phase_list_cell: str) -> dict | None:
    """从 CSV 的 phase_list 单元格解析出首条 phase 字典；失败返回 None。"""
    try:
        phase_list = json.loads(_normalize_json_cell(phase_list_cell))
    except (json.JSONDecodeError, TypeError):
        return None
    if not phase_list or not isinstance(phase_list, list):
        return None
    phase_data = phase_list[0]
    if not isinstance(phase_data, dict):
        return None
    return phase_data


def _phase_atoms_to_label(atoms: list[tuple[bool, str]]) -> str:
    """单相位：机动车在前、行人在后，再拼接为一条描述。"""
    if not atoms:
        return ""
    triples = [(1 if ped else 0, atom) for ped, atom in atoms]
    triples.sort(key=lambda x: (x[0], x[1]))
    return "".join(t[1] for t in triples)


def build_phase_direction_map_json(phase_data: dict, cycle_list_cell: str = "") -> str:
    """
    相位号（字符串 \"1\"..\"16\"） -> 该相位方向中文描述。
    与阶段描述使用同一套 channelDim / direction 解析及机动车/行人排序。
    """
    movements = build_phase_movements(phase_data, cycle_list_cell)
    out: dict[str, str] = {}
    for i in range(16):
        label = _phase_atoms_to_label(movements[i])
        if label:
            out[str(i + 1)] = label
    return json.dumps(out, ensure_ascii=False)


def build_phase_movements(phase_data: dict, cycle_list_cell: str = "") -> list[list[tuple[bool, str]]]:
    """
    返回 16 个相位各自的流向原子列表。
    无 channelDim / direction 可解析时为空列表（该相位不参与阶段描述）。
    """
    channel_str = phase_data.get("channelDim") or ""
    direction_strs = (phase_data.get("direction") or "").split()
    try:
        channel_dims = [int(x) for x in str(channel_str).split()]
    except ValueError:
        channel_dims = []
    while len(channel_dims) < 16:
        channel_dims.append(0)
    channel_dims = channel_dims[:16]
    channel_info = channelDim_analysis(channel_dims)
    ehualu = use_ehualu_direction_text(cycle_list_cell, phase_data)
    out: list[list[tuple[bool, str]]] = [[] for _ in range(16)]
    for i in range(16):
        ch = channel_info[i] if i < len(channel_info) else []
        if ch:
            out[i] = _channels_to_atoms(ch)
        elif i < len(direction_strs):
            text = direction_strs[i]
            if ehualu:
                atoms = parse_direction_text_ehualu(text)
                if atoms:
                    out[i] = atoms
            else:
                parsed = parse_direction_text(text)
                if parsed:
                    out[i] = _channels_to_atoms(parsed)
    return out


def _compose_stage_ordered_description(
    active_ring_indices: list[int],
    phase_no_per_ring: list[int],
    phase_movements: list[list[tuple[bool, str]]],
) -> list[str]:
    """
    合并多环当前相位上的所有原子流向：机动车在前、行人在后；
    同组内按环号再按字符串稳定排序。
    """
    triples: list[tuple[int, int, str]] = []  # (sort_group, ring_idx, atom)
    for r in active_ring_indices:
        ph = phase_no_per_ring[r]
        if not (1 <= ph <= 16):
            continue
        for is_ped, atom in phase_movements[ph - 1]:
            # 1=行人组在后，0=机动车组在前
            triples.append((1 if is_ped else 0, r, atom))
    triples.sort(key=lambda x: (x[0], x[1], x[2]))
    return [t[2] for t in triples]


def simulate_barrier_segment(
    segment_phases_per_ring: list[list[int]],
    duration_fn: Callable[[int], int],
    phase_movements: list[list[tuple[bool, str]]],
) -> tuple[list[list[str]], list[int]]:
    """单屏障窗内多环同步子阶段；方向为每阶段一条有序流向字符串数组。"""
    n = len(segment_phases_per_ring)
    ptr = [0] * n
    remain = [0] * n

    def load_remain(r: int) -> None:
        if ptr[r] < len(segment_phases_per_ring[r]):
            ph = segment_phases_per_ring[r][ptr[r]]
            remain[r] = duration_fn(ph)
        else:
            remain[r] = 0

    for r in range(n):
        load_remain(r)

    dir_stages: list[list[str]] = []
    time_stages: list[int] = []

    while any(ptr[r] < len(segment_phases_per_ring[r]) for r in range(n)):
        active = [r for r in range(n) if ptr[r] < len(segment_phases_per_ring[r])]
        if not active:
            break
        pos_rem = [remain[r] for r in active if remain[r] > 0]
        if not pos_rem:
            for r in active:
                if remain[r] <= 0:
                    ptr[r] += 1
                    load_remain(r)
            continue

        dt = min(pos_rem)
        if dt <= 0:
            for r in active:
                if remain[r] <= 0:
                    ptr[r] += 1
                    load_remain(r)
            continue

        phase_nos = [0] * n
        for r in active:
            if remain[r] > 0:
                phase_nos[r] = segment_phases_per_ring[r][ptr[r]]
        desc = _compose_stage_ordered_description(
            [r for r in active if remain[r] > 0],
            phase_nos,
            phase_movements,
        )
        dir_stages.append(desc)
        time_stages.append(int(dt))

        for r in active:
            if remain[r] > 0:
                remain[r] -= dt
                if remain[r] <= 0:
                    ptr[r] += 1
                    load_remain(r)

    return dir_stages, time_stages


def build_stage_json_for_row(cycle_list_cell: str, phase_list_cell: str) -> tuple[str, str]:
    empty = "[]", "[]"
    phase_data = load_phase_data(phase_list_cell)
    if not phase_data:
        return empty

    g, y, r = _pad_gyr(phase_data)

    def dur(p: int) -> int:
        return phase_total_duration(p, g, y, r)

    cl_norm = cycle_list_cell if not _is_missing(cycle_list_cell) else ""
    phase_movements = build_phase_movements(phase_data, str(cl_norm))

    try:
        rings = parse_cycle_list_ordered(str(cl_norm))
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        return empty

    if not rings:
        return empty

    segments_per_ring = [
        phases_to_barrier_segments(ring["phases"], ring["barriers"]) for ring in rings
    ]
    n_seg = min(len(s) for s in segments_per_ring) if segments_per_ring else 0

    all_dirs: list[list[str]] = []
    all_times: list[int] = []

    for si in range(n_seg):
        seg_rings = [segments_per_ring[ri][si] for ri in range(len(rings))]
        d_part, t_part = simulate_barrier_segment(seg_rings, dur, phase_movements)
        all_dirs.extend(d_part)
        all_times.extend(t_part)

    return json.dumps(all_dirs, ensure_ascii=False), json.dumps(all_times, ensure_ascii=False)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    return False


def _normalize_cell_value(value: object) -> str:
    if _is_missing(value):
        return ""
    return str(value)


def convert_csv(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if "phase_list" not in fieldnames:
        raise ValueError("CSV 缺少 phase_list 列")
    if "cycle_list" not in fieldnames:
        raise ValueError("CSV 缺少 cycle_list 列")

    output_fieldnames = fieldnames + [
        name
        for name in ("相位与方向的对应关系", "阶段方向描述", "阶段时间")
        if name not in fieldnames
    ]

    for row in rows:
        pl = _normalize_cell_value(row.get("phase_list", ""))
        cl = _normalize_cell_value(row.get("cycle_list", ""))
        pd_obj = load_phase_data(pl)
        row["相位与方向的对应关系"] = (
            build_phase_direction_map_json(pd_obj, cl) if pd_obj else "{}"
        )
        dj, tj = build_stage_json_for_row(cl, pl)
        row["阶段方向描述"] = dj
        row["阶段时间"] = tj

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _quote_identifier(name: str) -> str:
    if not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"非法标识符: {name}")
    return f"`{name}`"


def _parse_mysql_url(mysql_url: str) -> dict[str, object]:
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
        "database": database,
        "charset": query.get("charset", ["utf8mb4"])[0],
    }


def _get_mysql_connection(*, streaming: bool = False) -> pymysql.connections.Connection:
    mysql_url = get_settings().mysql_url
    if not mysql_url:
        raise ValueError("未配置 MYSQL_URL")
    conn_args = _parse_mysql_url(mysql_url)
    conn_args["cursorclass"] = SSDictCursor if streaming else DictCursor
    conn_args["autocommit"] = False
    return pymysql.connect(**conn_args)


def _column_exists(conn: pymysql.connections.Connection, table_name: str, column_name: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM {_quote_identifier(table_name)} LIKE %s", (column_name,))
        return cursor.fetchone() is not None


def ensure_target_table(
    conn: pymysql.connections.Connection,
    source_table: str,
    target_table: str,
    *,
    replace_target: bool = False,
) -> None:
    if source_table == target_table:
        raise ValueError("目标表必须与源表不同")
    with conn.cursor() as cursor:
        if replace_target:
            cursor.execute(f"DROP TABLE IF EXISTS {_quote_identifier(target_table)}")
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {_quote_identifier(target_table)} "
            f"LIKE {_quote_identifier(source_table)}"
        )
    conn.commit()

    extra_columns = {
        TARGET_PHASE_DIRECTION_MAP_COLUMN: "LONGTEXT NULL COMMENT '相位号与方向描述映射(JSON)'",
        TARGET_STAGE_DIRECTION_COLUMN: "LONGTEXT NULL COMMENT '阶段方向描述(JSON数组)'",
        TARGET_STAGE_TIME_COLUMN: "LONGTEXT NULL COMMENT '阶段时间(JSON数组)'",
    }
    for column_name, definition in extra_columns.items():
        if _column_exists(conn, target_table, column_name):
            continue
        with conn.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {_quote_identifier(target_table)} "
                f"ADD COLUMN {_quote_identifier(column_name)} {definition}"
            )
        conn.commit()


def _transform_row(row: dict[str, object]) -> dict[str, object]:
    result = dict(row)
    phase_list_cell = _normalize_cell_value(result.get("phase_list", ""))
    cycle_list_cell = _normalize_cell_value(result.get("cycle_list", ""))
    phase_data = load_phase_data(phase_list_cell)
    result[TARGET_PHASE_DIRECTION_MAP_COLUMN] = (
        build_phase_direction_map_json(phase_data, cycle_list_cell) if phase_data else "{}"
    )
    stage_direction_json, stage_time_json = build_stage_json_for_row(cycle_list_cell, phase_list_cell)
    result[TARGET_STAGE_DIRECTION_COLUMN] = stage_direction_json
    result[TARGET_STAGE_TIME_COLUMN] = stage_time_json
    return result


def _build_upsert_sql(table_name: str, columns: list[str]) -> str:
    quoted_columns = ", ".join(_quote_identifier(col) for col in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    update_columns = [col for col in columns if col != "id"]
    if not update_columns:
        raise ValueError("写入列不能为空")
    update_clause = ", ".join(
        f"{_quote_identifier(col)}=VALUES({_quote_identifier(col)})" for col in update_columns
    )
    return (
        f"INSERT INTO {_quote_identifier(table_name)} ({quoted_columns}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )


def _upsert_rows(
    conn: pymysql.connections.Connection,
    table_name: str,
    rows: list[dict[str, object]],
) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    values = [tuple(row.get(col) for col in columns) for row in rows]
    sql = _build_upsert_sql(table_name, columns)
    with conn.cursor() as cursor:
        cursor.executemany(sql, values)
    conn.commit()


def convert_mysql_table(
    source_table: str = DEFAULT_SOURCE_TABLE,
    target_table: str = DEFAULT_TARGET_TABLE,
    *,
    batch_size: int = 500,
    replace_target: bool = False,
) -> int:
    source_ident = _quote_identifier(source_table)
    processed = 0
    read_conn = _get_mysql_connection(streaming=True)
    write_conn = _get_mysql_connection(streaming=False)
    try:
        ensure_target_table(
            write_conn,
            source_table=source_table,
            target_table=target_table,
            replace_target=replace_target,
        )
        with read_conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {source_ident} ORDER BY id")
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                transformed_rows = [_transform_row(row) for row in rows]
                _upsert_rows(write_conn, target_table, transformed_rows)
                processed += len(transformed_rows)
                print(f"已处理 {processed} 条")
    finally:
        read_conn.close()
        write_conn.close()
    return processed


def main() -> None:
    p = argparse.ArgumentParser(description="配时表转阶段结果，支持 CSV 与 MySQL 落表")
    p.add_argument("-i", "--input", type=Path, help="CSV 输入文件；传入后启用 CSV 模式")
    p.add_argument("-o", "--output", type=Path, help="CSV 输出文件；CSV 模式下默认自动推导")
    p.add_argument("--source-table", default=DEFAULT_SOURCE_TABLE, help="MySQL 源表名")
    p.add_argument("--target-table", default=DEFAULT_TARGET_TABLE, help="MySQL 目标表名")
    p.add_argument("--batch-size", type=int, default=500, help="MySQL 批量写入大小")
    p.add_argument(
        "--replace-target",
        action="store_true",
        help="重建目标表（先删后建），适合全量重跑",
    )
    args = p.parse_args()
    if args.input:
        output_path = args.output or args.input.with_name(f"{args.input.stem}_阶段表{args.input.suffix}")
        convert_csv(args.input, output_path)
        print(f"已写入 CSV: {output_path}")
        return

    processed = convert_mysql_table(
        source_table=args.source_table,
        target_table=args.target_table,
        batch_size=args.batch_size,
        replace_target=args.replace_target,
    )
    print(f"已写入数据表: {args.target_table}，共 {processed} 条")


if __name__ == "__main__":
    main()
