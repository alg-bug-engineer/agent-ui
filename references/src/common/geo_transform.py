"""WGS-84 ↔ GCJ-02（国测局/火星坐标，高德、腾讯地图底图）转换.

算法与常见开源实现一致；中国境外不做偏移。
"""

from __future__ import annotations

import math

_a = 6378245.0
_ee = 0.00669342162296594


def out_of_china(lng: float, lat: float) -> bool:
    """境外或明显不在中国大陆矩形范围内的点不做偏移."""
    if lng < 72.004 or lng > 137.8347:
        return True
    if lat < 0.8293 or lat > 55.8271:
        return True
    return False


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """WGS-84 → GCJ-02."""
    if out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_a * (1 - _ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (_a / sqrtmagic * math.cos(radlat) * math.pi)
    return round(lng + dlng, 7), round(lat + dlat, 7)


def gcj02_to_wgs84(lng: float, lat: float) -> tuple[float, float]:
    """GCJ-02 → WGS-84（迭代逼近）."""
    if out_of_china(lng, lat):
        return lng, lat
    th = 1e-7
    w_lng, w_lat = lng, lat
    for _ in range(28):
        m_lng, m_lat = wgs84_to_gcj02(w_lng, w_lat)
        w_lng += lng - m_lng
        w_lat += lat - m_lat
        if abs(lng - m_lng) < th and abs(lat - m_lat) < th:
            break
    return round(w_lng, 7), round(w_lat, 7)


def gcj02_bbox_to_wgs84_bounds(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> tuple[float, float, float, float]:
    """将高德地图视野矩形（GCJ-02）转为覆盖该矩形所需的 WGS-84 轴对齐外包矩形，用于查库."""
    corners = (
        (min_lon, min_lat),
        (min_lon, max_lat),
        (max_lon, min_lat),
        (max_lon, max_lat),
    )
    wgs = [gcj02_to_wgs84(ln, lt) for ln, lt in corners]
    lons = [p[0] for p in wgs]
    lats = [p[1] for p in wgs]
    return min(lons), max(lons), min(lats), max(lats)
