#!/usr/bin/env python3
"""Add standalone intersection entries for IDs that only exist inline in corridors."""
import json, os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'data', 'jinan_demo_data.json')
with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

existing_ids = {i['id'] for i in data['intersections']}

inline_intersections = [
    {
        "id": "INT-JN-0271", "name": "经十路/历山路", "lat": 117.072, "lng": 36.648,
        "status": "critical", "saturation": 0.91, "delay": 102.3, "queueLength": 178,
        "stopRate": 0.76, "cycleTime": 125,
        "issues": [
            {"id": "signal_phase_imbalance", "name": "南北直行压制·相位失衡", "category": "signal_control",
             "severity": 0.88, "confidence": 0.93,
             "evidence": {"northSaturation": 0.91, "eastSaturation": 0.74, "imbalanceIndex": 0.23},
             "reason": "经十路东西向绿灯时间过长，历山路南北向高峰期饱和度0.91，排队持续溢出"}
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "南北绿灯增加+东西压缩·恢复方向均衡", "score": 0.90}
        ],
        "before": {"saturation": 0.91, "delay": 102.3, "cycleTime": 125, "northGreen": 30, "eastGreen": 55},
        "after": {"saturation": 0.78, "delay": 68.5, "cycleTime": 110, "northGreen": 45, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 30, "splitRatio": 0.26, "saturation": 0.91},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 55, "splitRatio": 0.46, "saturation": 0.74},
            {"phaseId": "C", "phaseName": "南北左转", "direction": "N-S left", "greenTime": 22, "splitRatio": 0.18, "saturation": 0.82},
            {"phaseId": "D", "phaseName": "东西左转", "direction": "E-W left", "greenTime": 10, "splitRatio": 0.08, "saturation": 0.65}
        ]
    },
    {
        "id": "INT-JN-0278", "name": "经十路/花园路", "lat": 117.047, "lng": 36.648,
        "status": "warning", "saturation": 0.84, "delay": 78.5, "queueLength": 142,
        "stopRate": 0.62, "cycleTime": 120,
        "issues": [
            {"id": "signal_phase_imbalance", "name": "绿波断裂·相位差偏移", "category": "signal_control",
             "severity": 0.72, "confidence": 0.88,
             "evidence": {"bandwidthLoss": "12s", "offsetError": True},
             "reason": "与经十路走廊公共周期存在相位差偏移，导致绿波在此断裂"}
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "相位差修正·绿波对齐", "score": 0.84}
        ],
        "before": {"saturation": 0.84, "delay": 78.5, "cycleTime": 120, "northGreen": 36, "eastGreen": 50},
        "after": {"saturation": 0.75, "delay": 55.2, "cycleTime": 100, "northGreen": 42, "eastGreen": 40},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 36, "splitRatio": 0.32, "saturation": 0.84},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 50, "splitRatio": 0.44, "saturation": 0.76},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 22, "splitRatio": 0.19, "saturation": 0.72}
        ]
    },
    {
        "id": "INT-JN-0289", "name": "经十路/解放路", "lat": 117.020, "lng": 36.648,
        "status": "warning", "saturation": 0.79, "delay": 68.4, "queueLength": 118,
        "stopRate": 0.52, "cycleTime": 110,
        "issues": [
            {"id": "signal_green_waste", "name": "次要方向空放", "category": "signal_control",
             "severity": 0.58, "confidence": 0.82,
             "evidence": {"minorDirectionUtil": 0.42},
             "reason": "解放路方向绿灯利用率仅42%，平峰期空放较多"}
        ],
        "strategies": [
            {"templateId": "intersection_balance_and_green_reuse", "level": "intersection", "description": "空放削减·绿信比重分配", "score": 0.78}
        ],
        "before": {"saturation": 0.79, "delay": 68.4, "cycleTime": 110, "northGreen": 35, "eastGreen": 48},
        "after": {"saturation": 0.72, "delay": 52.1, "cycleTime": 100, "northGreen": 40, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 48, "splitRatio": 0.46, "saturation": 0.76},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 35, "splitRatio": 0.33, "saturation": 0.79},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 18, "splitRatio": 0.17, "saturation": 0.65}
        ]
    },
    {
        "id": "INT-JN-0295", "name": "经十路/工业南路", "lat": 117.098, "lng": 36.648,
        "status": "normal", "saturation": 0.75, "delay": 52.8, "queueLength": 88,
        "stopRate": 0.38, "cycleTime": 100,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 44, "splitRatio": 0.46, "saturation": 0.72},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.40, "saturation": 0.68}
        ]
    },
    {
        "id": "INT-JN-0102", "name": "解放路/泺源大街", "lat": 116.993, "lng": 36.658,
        "status": "optimized", "saturation": 0.71, "delay": 48.5, "queueLength": 75,
        "stopRate": 0.26, "cycleTime": 90,
        "issues": [],
        "strategies": [
            {"templateId": "corridor_flexible_coordination", "level": "corridor", "description": "解放路绿波协调节点", "score": 0.88}
        ],
        "before": {"saturation": 0.82, "delay": 72.3, "cycleTime": 120, "northGreen": 36, "eastGreen": 48},
        "after": {"saturation": 0.71, "delay": 48.5, "cycleTime": 90, "northGreen": 42, "eastGreen": 36},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.49, "saturation": 0.71},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 36, "splitRatio": 0.42, "saturation": 0.68}
        ]
    },
    {
        "id": "INT-JN-0108", "name": "解放路/经一路", "lat": 116.993, "lng": 36.665,
        "status": "normal", "saturation": 0.74, "delay": 55.2, "queueLength": 92,
        "stopRate": 0.34, "cycleTime": 90,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 40, "splitRatio": 0.47, "saturation": 0.74},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 38, "splitRatio": 0.44, "saturation": 0.70}
        ]
    },
    {
        "id": "INT-JN-0112", "name": "解放路/泺文路", "lat": 116.993, "lng": 36.672,
        "status": "normal", "saturation": 0.69, "delay": 45.8, "queueLength": 68,
        "stopRate": 0.24, "cycleTime": 90,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.49, "saturation": 0.69},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 36, "splitRatio": 0.42, "saturation": 0.65}
        ]
    },
    {
        "id": "INT-JN-0322", "name": "花园路/经十路", "lat": 117.047, "lng": 36.636,
        "status": "optimizing", "saturation": 0.82, "delay": 74.8, "queueLength": 128,
        "stopRate": 0.54, "cycleTime": 100,
        "issues": [
            {"id": "signal_phase_imbalance", "name": "花园路走廊协调瓶颈", "category": "signal_control",
             "severity": 0.68, "confidence": 0.85,
             "evidence": {"bandwidthLoss": "10s", "saturation": 0.82},
             "reason": "花园路/经十路路口配时与花园路走廊周期存在偏差，限制了走廊绿波带宽"}
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "花园路走廊协调对齐", "score": 0.82}
        ],
        "before": {"saturation": 0.82, "delay": 74.8, "cycleTime": 100, "northGreen": 35, "eastGreen": 42},
        "after": {"saturation": 0.74, "delay": 55.3, "cycleTime": 100, "northGreen": 42, "eastGreen": 38},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 35, "splitRatio": 0.37, "saturation": 0.82},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 42, "splitRatio": 0.44, "saturation": 0.76},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 15, "splitRatio": 0.16, "saturation": 0.68}
        ]
    },
    {
        "id": "INT-JN-0328", "name": "花园路/历山路", "lat": 117.047, "lng": 36.651,
        "status": "normal", "saturation": 0.78, "delay": 62.4, "queueLength": 98,
        "stopRate": 0.42, "cycleTime": 100,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.44, "saturation": 0.78},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 40, "splitRatio": 0.42, "saturation": 0.72}
        ]
    },
    {
        "id": "INT-JN-0334", "name": "花园路/文化东路", "lat": 117.047, "lng": 36.660,
        "status": "normal", "saturation": 0.75, "delay": 56.8, "queueLength": 85,
        "stopRate": 0.38, "cycleTime": 100,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 44, "splitRatio": 0.46, "saturation": 0.75},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 38, "splitRatio": 0.40, "saturation": 0.70}
        ]
    },
    {
        "id": "INT-JN-0340", "name": "花园路/解放路", "lat": 117.047, "lng": 36.668,
        "status": "normal", "saturation": 0.71, "delay": 48.5, "queueLength": 72,
        "stopRate": 0.32, "cycleTime": 100,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 44, "splitRatio": 0.46, "saturation": 0.71},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 38, "splitRatio": 0.40, "saturation": 0.68}
        ]
    },
    {
        "id": "INT-JN-0346", "name": "花园路/北园大街", "lat": 117.047, "lng": 36.682,
        "status": "normal", "saturation": 0.68, "delay": 42.3, "queueLength": 62,
        "stopRate": 0.26, "cycleTime": 100,
        "issues": [],
        "strategies": [],
        "before": None, "after": None,
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 46, "splitRatio": 0.48, "saturation": 0.68},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 36, "splitRatio": 0.38, "saturation": 0.64}
        ]
    }
]

added = 0
for inter in inline_intersections:
    if inter['id'] not in existing_ids:
        data['intersections'].append(inter)
        existing_ids.add(inter['id'])
        added += 1

with open(SRC, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Added {added} standalone intersection entries")
print(f"Total intersections: {len(data['intersections'])}")

# Re-validate
all_ids = set()
for r in data['regions']: all_ids.add(r['id'])
for c in data['corridors']: all_ids.add(c['id'])
for i in data['intersections']: all_ids.add(i['id'])

corridor_int_ids = set()
for c in data['corridors']:
    for iid in c.get('intersectionIds', []):
        corridor_int_ids.add(iid)

missing = corridor_int_ids - set(i['id'] for i in data['intersections'])
if missing:
    print(f"Still missing: {missing}")
else:
    print("All corridor intersection references resolved!")

for t in data['topologyLinks']:
    if t['fromId'] not in all_ids:
        print(f"WARNING: topology {t['id']} fromId {t['fromId']} not found")
    if t['toId'] not in all_ids:
        print(f"WARNING: topology {t['id']} toId {t['toId']} not found")

for p in data['pois']:
    for lid in p.get('linkedIntersectionIds', []):
        if lid not in all_ids:
            print(f"WARNING: POI {p['id']} linked {lid} not found")

# Final status distribution
statuses = {}
for inter in data['intersections']:
    s = inter['status']
    statuses[s] = statuses.get(s, 0) + 1
print(f"\nFinal intersection status distribution: {statuses}")
