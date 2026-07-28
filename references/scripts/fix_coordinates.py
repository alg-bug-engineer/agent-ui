#!/usr/bin/env python3
"""Fix all coordinates in jinan_demo_data.json:
1. Swap lat/lng fields (they were incorrectly named)
2. Use real geocoded coordinates from Nominatim + manual corrections
3. Update region polygons and corridor paths accordingly
"""
import json, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'data', 'jinan_demo_data.json')
with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Real coordinates from Nominatim + manual corrections for Jinan intersections
# Format: id -> (lng, lat) -- AMap uses [lng, lat]
REAL_COORDS = {
    "INT-JN-0281": (117.021, 36.648),
    "INT-JN-0271": (117.033, 36.648),
    "INT-JN-0278": (117.042, 36.648),
    "INT-JN-0289": (116.998, 36.649),
    "INT-JN-0295": (117.088, 36.648),
    "INT-JN-0104": (117.014, 36.655),
    "INT-JN-0102": (117.010, 36.660),
    "INT-JN-0108": (117.010, 36.668),
    "INT-JN-0112": (117.010, 36.672),
    "INT-JN-0451": (117.062, 36.671),
    "INT-JN-0155": (117.008, 36.662),
    "INT-JN-0620": (117.109, 36.678),
    "INT-JN-0701": (117.098, 36.653),
    "INT-JN-0702": (117.018, 36.660),
    "INT-JN-0703": (117.050, 36.648),
    "INT-JN-0704": (116.974, 36.593),
    "INT-JN-0705": (116.960, 36.685),
    "INT-JN-0706": (116.949, 36.681),
    "INT-JN-0707": (117.195, 36.675),
    "INT-JN-0708": (117.130, 36.658),
    "INT-JN-0709": (117.060, 36.638),
    "INT-JN-0710": (117.008, 36.684),
    "INT-JN-0711": (117.078, 36.700),
    "INT-JN-0712": (116.994, 36.705),
    "INT-JN-0713": (117.022, 36.660),
    "INT-JN-0714": (116.982, 36.649),
    "INT-JN-0715": (117.105, 36.664),
    "INT-JN-0716": (117.168, 36.688),
    "INT-JN-0717": (117.099, 36.672),
    "INT-JN-0718": (117.078, 36.638),
    "INT-JN-0719": (117.150, 36.680),
    "INT-JN-0720": (117.187, 36.673),
    "INT-JN-0721": (116.920, 36.595),
    "INT-JN-0722": (117.122, 36.654),
    "INT-JN-0723": (117.045, 36.692),
    "INT-JN-0322": (117.042, 36.638),
    "INT-JN-0328": (117.042, 36.650),
    "INT-JN-0334": (117.042, 36.660),
    "INT-JN-0340": (117.042, 36.668),
    "INT-JN-0346": (117.042, 36.684),
}

# Fix intersection coordinates
for inter in data['intersections']:
    iid = inter['id']
    if iid in REAL_COORDS:
        lng, lat = REAL_COORDS[iid]
        inter['lng'] = lng
        inter['lat'] = lat
    else:
        old_lat = inter.get('lat', 0)
        old_lng = inter.get('lng', 0)
        if old_lat > 100:
            inter['lng'] = old_lat
            inter['lat'] = old_lng

# Fix region centers, polygons
REGION_DATA = {
    "RGN-LIXIA": {
        "center": [117.030, 36.660],
        "polygon": [[116.998, 36.678], [117.070, 36.678], [117.070, 36.640], [116.998, 36.640], [116.998, 36.678]]
    },
    "RGN-SHIZHONG": {
        "center": [116.980, 36.640],
        "polygon": [[116.950, 36.660], [117.010, 36.660], [117.010, 36.620], [116.950, 36.620], [116.950, 36.660]]
    },
    "RGN-LICHENG": {
        "center": [117.100, 36.672],
        "polygon": [[117.060, 36.695], [117.140, 36.695], [117.140, 36.650], [117.060, 36.650], [117.060, 36.695]]
    },
    "RGN-TIANQIAO": {
        "center": [116.985, 36.695],
        "polygon": [[116.940, 36.710], [117.030, 36.710], [117.030, 36.678], [116.940, 36.678], [116.940, 36.710]]
    },
    "RGN-GAOXIN": {
        "center": [117.160, 36.678],
        "polygon": [[117.120, 36.698], [117.200, 36.698], [117.200, 36.658], [117.120, 36.658], [117.120, 36.698]]
    }
}

for region in data['regions']:
    rid = region['id']
    if rid in REGION_DATA:
        region['center'] = REGION_DATA[rid]['center']
        region['polygon'] = REGION_DATA[rid]['polygon']
        if region.get('sceneCognition') and region['sceneCognition'].get('state'):
            pass
        if region.get('boundaryFlows'):
            for bf in region['boundaryFlows']:
                iid_bf = bf.get('intersectionId')
                if iid_bf in REAL_COORDS:
                    lng, lat = REAL_COORDS[iid_bf]
                    bf['position'] = [lng, lat]
        if region.get('mapContext') and region['mapContext'].get('influencePolygon'):
            rd = REGION_DATA[rid]
            poly = rd['polygon']
            expansion = 0.005
            region['mapContext']['influencePolygon'] = [
                [poly[0][0] - expansion, poly[0][1] + expansion],
                [poly[1][0] + expansion, poly[1][1] + expansion],
                [poly[2][0] + expansion, poly[2][1] - expansion],
                [poly[3][0] - expansion, poly[3][1] - expansion],
                [poly[0][0] - expansion, poly[0][1] + expansion]
            ]

# Fix corridor paths
CORRIDOR_PATHS = {
    "COR-JINGSHI": [
        [116.982, 36.649], [116.998, 36.649], [117.021, 36.648],
        [117.033, 36.648], [117.042, 36.648], [117.050, 36.648],
        [117.088, 36.648], [117.098, 36.653]
    ],
    "COR-JIEFANG": [
        [117.010, 36.648], [117.010, 36.655],
        [117.010, 36.660], [117.010, 36.668], [117.010, 36.672]
    ],
    "COR-HUAYUAN": [
        [117.042, 36.638], [117.042, 36.648],
        [117.042, 36.660], [117.042, 36.668], [117.042, 36.684]
    ],
    "COR-ERHUANDONG": [
        [117.078, 36.710], [117.078, 36.700],
        [117.078, 36.670], [117.078, 36.638]
    ],
    "COR-BEIYUAN": [
        [116.949, 36.685], [116.960, 36.685],
        [117.008, 36.684], [117.045, 36.692]
    ],
    "COR-LUOYUAN": [
        [117.008, 36.662], [117.018, 36.660],
        [117.022, 36.660], [117.032, 36.660]
    ],
    "COR-SHIJIDA": [
        [117.130, 36.680], [117.150, 36.680],
        [117.168, 36.688], [117.187, 36.680]
    ]
}

for corridor in data['corridors']:
    cid = corridor['id']
    if cid in CORRIDOR_PATHS:
        corridor['path'] = CORRIDOR_PATHS[cid]

# Fix corridor inline intersection references (update saturation refs)
# Update sceneCognition bottleneck positions
for region in data['regions']:
    sc = region.get('sceneCognition', {})
    if sc.get('bottlenecks'):
        for bn in sc['bottlenecks']:
            iid = bn.get('intersectionId')
            if iid in REAL_COORDS:
                bn['position'] = list(REAL_COORDS[iid])

with open(SRC, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Coordinates fixed!")
count = 0
for inter in data['intersections']:
    lng = inter.get('lng', 0)
    lat = inter.get('lat', 0)
    in_jinan = 116.8 < lng < 117.3 and 36.5 < lat < 36.8
    status = "OK" if in_jinan else "WARN"
    print(f"  {status} {inter['id']:16} {inter['name']:18} lng={lng:.3f} lat={lat:.3f}")
    if in_jinan:
        count += 1
print(f"\n{count}/{len(data['intersections'])} intersections within Jinan bounds")
