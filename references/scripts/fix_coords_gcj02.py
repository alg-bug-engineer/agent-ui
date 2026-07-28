#!/usr/bin/env python3
"""Fix intersection coordinates:
1. Apply WGS84 → GCJ-02 transform (AMap uses GCJ-02)
2. Correct obviously wrong Nominatim results with accurate positions
"""
import json, os, math

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'data', 'jinan_demo_data.json')

# ---- WGS84 → GCJ-02 conversion ----
_a = 6378245.0
_ee = 0.00669342162296594

def _transform_lat(x, y):
    ret = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
    ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
    ret += (20.0*math.sin(y*math.pi) + 40.0*math.sin(y/3.0*math.pi)) * 2.0/3.0
    ret += (160.0*math.sin(y/12.0*math.pi) + 320.0*math.sin(y*math.pi/30.0)) * 2.0/3.0
    return ret

def _transform_lng(x, y):
    ret = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
    ret += (20.0*math.sin(6.0*x*math.pi) + 20.0*math.sin(2.0*x*math.pi)) * 2.0/3.0
    ret += (20.0*math.sin(x*math.pi) + 40.0*math.sin(x/3.0*math.pi)) * 2.0/3.0
    ret += (150.0*math.sin(x/12.0*math.pi) + 300.0*math.sin(x/30.0*math.pi)) * 2.0/3.0
    return ret

def wgs84_to_gcj02(lng, lat):
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_a * (1 - _ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (_a / sqrtmagic * math.cos(radlat) * math.pi)
    return round(lng + dlng, 6), round(lat + dlat, 6)

# ---- Accurate GCJ-02 coordinates for Jinan intersections ----
# These are directly in GCJ-02 (AMap coordinate system)
ACCURATE_GCJ02 = {
    "INT-JN-0281": (117.027, 36.659),   # 经十路/舜耕路
    "INT-JN-0271": (117.064, 36.658),   # 经十路/历山路 (历山路在经十路以东)
    "INT-JN-0278": (117.051, 36.658),   # 经十路/花园路
    "INT-JN-0289": (117.013, 36.659),   # 经十路/解放路
    "INT-JN-0295": (117.098, 36.661),   # 经十路/工业南路(实际工业南路在东)
    "INT-JN-0104": (117.009, 36.656),   # 解放路/趵突泉路
    "INT-JN-0102": (117.013, 36.668),   # 解放路/泺源大街
    "INT-JN-0108": (117.013, 36.675),   # 解放路/经一路
    "INT-JN-0112": (117.013, 36.680),   # 解放路/泺文路
    "INT-JN-0451": (117.065, 36.680),   # 历山路/工业南路
    "INT-JN-0155": (117.009, 36.668),   # 泺源大街/趵突泉北路
    "INT-JN-0620": (117.115, 36.665),   # 奥体中路/英雄山路→奥体中路/经十路
    "INT-JN-0701": (117.090, 36.658),   # 经十路/转山西路
    "INT-JN-0702": (117.018, 36.668),   # 泺源大街/南门大街
    "INT-JN-0703": (117.056, 36.658),   # 经十路/山师东路
    "INT-JN-0704": (116.981, 36.600),   # 九曲庄路/二环南路
    "INT-JN-0705": (116.966, 36.692),   # 无影山中路/济齐路
    "INT-JN-0706": (116.955, 36.688),   # 济齐路/黄岗路
    "INT-JN-0707": (117.200, 36.672),   # 经十路/凤祥路(高新区东)
    "INT-JN-0708": (117.130, 36.652),   # 龙奥北路/凤天路(奥体南)
    "INT-JN-0709": (117.065, 36.640),   # 旅游路/椒山路(千佛山东)
    "INT-JN-0710": (117.015, 36.691),   # 北园大街/生产路
    "INT-JN-0711": (117.082, 36.705),   # 二环东路/祝舜路(二环北段)
    "INT-JN-0712": (117.000, 36.710),   # 小清河北路/标山路
    "INT-JN-0713": (117.024, 36.668),   # 泺源大街/南新街
    "INT-JN-0714": (116.988, 36.659),   # 经十路/建设路(西段)
    "INT-JN-0715": (117.108, 36.668),   # 奥体中路/解放东路
    "INT-JN-0716": (117.175, 36.692),   # 世纪大道/凤歧路
    "INT-JN-0717": (117.105, 36.678),   # 轻风路/奥体西路
    "INT-JN-0718": (117.082, 36.640),   # 二环东路/旅游路
    "INT-JN-0719": (117.155, 36.680),   # 舜华南路/舜泰北路
    "INT-JN-0720": (117.192, 36.670),   # 经十路/凤鸣路
    "INT-JN-0721": (116.926, 36.600),   # 党杨路/齐兴大街(西部)
    "INT-JN-0722": (117.128, 36.648),   # 龙奥东路/龙奥北路
    "INT-JN-0723": (117.051, 36.695),   # 北园大街/历山路
    "INT-JN-0322": (117.049, 36.648),   # 花园路/经十路
    "INT-JN-0328": (117.049, 36.660),   # 花园路/历山路→花园路/文化路附近
    "INT-JN-0334": (117.049, 36.670),   # 花园路/文化东路
    "INT-JN-0340": (117.049, 36.675),   # 花园路/解放路(花园路北段)
    "INT-JN-0346": (117.049, 36.692),   # 花园路/北园大街
}

with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fix intersections
for inter in data['intersections']:
    iid = inter['id']
    if iid in ACCURATE_GCJ02:
        lng, lat = ACCURATE_GCJ02[iid]
        inter['lng'] = lng
        inter['lat'] = lat
    else:
        old_lng = inter.get('lng', 117.0)
        old_lat = inter.get('lat', 36.66)
        new_lng, new_lat = wgs84_to_gcj02(old_lng, old_lat)
        inter['lng'] = new_lng
        inter['lat'] = new_lat

# Fix region centers and polygons (apply GCJ-02 transform)
for region in data['regions']:
    c = region.get('center', [])
    if len(c) == 2:
        region['center'] = list(wgs84_to_gcj02(c[0], c[1]))
    poly = region.get('polygon', [])
    region['polygon'] = [list(wgs84_to_gcj02(p[0], p[1])) for p in poly]

# Fix corridor paths
CORRIDOR_PATHS_GCJ02 = {
    "COR-JINGSHI": [
        [116.988, 36.659], [117.013, 36.659], [117.027, 36.659],
        [117.051, 36.658], [117.056, 36.658], [117.064, 36.658],
        [117.090, 36.658], [117.098, 36.661]
    ],
    "COR-JIEFANG": [
        [117.013, 36.656], [117.013, 36.659],
        [117.013, 36.668], [117.013, 36.675], [117.013, 36.680]
    ],
    "COR-HUAYUAN": [
        [117.049, 36.648], [117.049, 36.658],
        [117.049, 36.670], [117.049, 36.675], [117.049, 36.692]
    ],
    "COR-ERHUANDONG": [
        [117.082, 36.715], [117.082, 36.705],
        [117.082, 36.678], [117.082, 36.640]
    ],
    "COR-BEIYUAN": [
        [116.955, 36.692], [116.966, 36.692],
        [117.015, 36.691], [117.051, 36.695]
    ],
    "COR-LUOYUAN": [
        [117.009, 36.668], [117.018, 36.668],
        [117.024, 36.668], [117.038, 36.668]
    ],
    "COR-SHIJIDA": [
        [117.135, 36.680], [117.155, 36.680],
        [117.175, 36.692], [117.192, 36.680]
    ]
}

for corridor in data['corridors']:
    cid = corridor['id']
    if cid in CORRIDOR_PATHS_GCJ02:
        corridor['path'] = CORRIDOR_PATHS_GCJ02[cid]

with open(SRC, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("=== GCJ-02 坐标修正完成 ===")
for inter in data['intersections']:
    lng = inter.get('lng',0)
    lat = inter.get('lat',0)
    ok = 116.8 < lng < 117.3 and 36.5 < lat < 36.8
    print(f"  {'OK' if ok else 'WARN'} {inter['id']:16} {inter['name']:22} lng={lng:.4f} lat={lat:.4f}")
