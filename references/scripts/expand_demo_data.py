#!/usr/bin/env python3
"""
Expand jinan_demo_data.json with 20+ real Jinan congestion points.
Data sourced from:
- http://www.sd.xinhuanet.com/20260326/... (新华网 20余处拥堵点)
- http://sd.people.com.cn/n2/2026/0122/... (经十路信号优化)
- http://news.e23.cn/jnnews/2025-03-22/... (10处拥堵点改造)
- http://news.e23.cn/jnnews/2026-03-25/... (济齐路五岔口微改造)
- http://news.e23.cn/jnnews/2025-05-24/... (经十路信号控制升级)
"""
import json
import os
import copy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(SCRIPT_DIR, '..', 'static', 'data', 'jinan_demo_data.json')
DST = SRC

with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

# ── NEW REGIONS ─────────────────────────────────────────────────────────
new_regions = [
    {
        "id": "RGN-TIANQIAO",
        "name": "天桥区北园商圈",
        "center": [116.985, 36.698],
        "polygon": [
            [116.950, 36.715], [117.020, 36.715],
            [117.020, 36.685], [116.950, 36.685], [116.950, 36.715]
        ],
        "status": "warning",
        "saturation": 0.81,
        "avgSpeed": 21.8,
        "avgDelay": 78.4,
        "congestionIndex": 4.1,
        "roadDensity": 6.5,
        "inFlow": 3480,
        "outFlow": 3120,
        "transitVolume": 8900,
        "primaryIssue": "dynamic_high_saturation",
        "strategy": "region_boundary_flow_control",
        "profile": {
            "supply": {
                "roadDensity": 6.5,
                "intersectionCapacity": 2900,
                "parkingGap": 0.32
            },
            "demand": {
                "peakHourFlow": 3480,
                "demandSupplyRatio": 1.08,
                "commuteRatio": 0.55
            },
            "state": {
                "saturation": 0.81,
                "avgSpeed": 21.8,
                "avgDelay": 78.4,
                "congestionPhase": "持续期"
            }
        },
        "issues": [
            {
                "id": "dynamic_high_saturation",
                "name": "高架下桥汇聚·地面路网高饱和",
                "category": "dynamic",
                "severity": 0.83,
                "confidence": 0.92,
                "evidence": {
                    "saturation": 0.81,
                    "highwayRampFlow": 1200,
                    "surfaceCapacity": 2900,
                    "peakWindow": "07:30-09:00"
                },
                "reason": "北园高架多处下桥匝道汇入，高峰期地面路网承接能力不足，饱和度持续超0.8"
            },
            {
                "id": "static_road_network_sparse",
                "name": "老城区路网密度不足",
                "category": "static",
                "severity": 0.72,
                "confidence": 0.88,
                "evidence": {
                    "roadDensity": 6.5,
                    "benchmarkDensity": 8.0,
                    "densityDeficit": "18.8%"
                },
                "reason": "天桥区老城区路网密度6.5km/km²，支路微循环体系不完善，主干道独自承压"
            }
        ],
        "strategies": [
            {
                "templateId": "region_boundary_flow_control",
                "level": "region",
                "description": "高架匝道协同控流+地面路网均衡疏导",
                "score": 0.86,
                "mode": "realtime",
                "objective": "匝道下桥流量削峰15%，地面饱和度降至0.75以下",
                "sideEffects": "高架主线排队可能略增，需配合匝道信号控制",
                "requiresApproval": True,
                "params": {
                    "rampMeteringEnabled": True,
                    "surfaceGreenBias": 0.08,
                    "activationThreshold": 0.82,
                    "exitThreshold": 0.75
                }
            }
        ],
        "sceneCognition": {
            "sceneType": "dynamic",
            "sceneName": "北园商圈高架下桥汇聚拥堵",
            "triggerTime": "07:42",
            "triggerCondition": "无影山中路/济齐路路口饱和度突破0.82，北园高架下桥排队超300m",
            "supply": {
                "roadDensity": 6.5,
                "densityAssessment": "路网密度6.5km/km²，老城区支路狭窄，微循环能力弱",
                "intersectionCapacity": 2900,
                "capacityAssessment": "区域路口高峰通行能力约2900辆/h，但高架汇入叠加地面通勤需求达3480辆/h"
            },
            "demand": {
                "peakHourFlow": 3480,
                "demandSupplyRatio": 1.08,
                "commuteRatio": 0.55,
                "flowCharacteristics": "通勤占55%，北园高架下桥通勤流与地面商圈出行叠加"
            },
            "state": {
                "saturation": 0.81,
                "avgSpeed": 21.8,
                "avgDelay": 78.4,
                "congestionPhase": "持续期",
                "phaseExplanation": "无影山中路/济齐路路口成为瓶颈，东向西车辆排队超500m，高架下桥匝道回溢至高架主线"
            },
            "summary": "天桥区北园商圈早高峰动态拥堵持续。北园高架多处下桥匝道集中汇入地面路网，叠加老城区路网密度不足，导致无影山中路/济齐路路口成为严重瓶颈。"
        },
        "mapContext": {
            "primaryObjectId": "RGN-TIANQIAO",
            "primaryObjectType": "region",
            "affectedObjectIds": ["INT-JN-0705", "INT-JN-0706", "INT-JN-0710", "INT-JN-0723"],
            "upstreamIds": ["COR-BEIYUAN"],
            "downstreamIds": []
        }
    },
    {
        "id": "RGN-GAOXIN",
        "name": "高新区CBD片区",
        "center": [117.155, 36.660],
        "polygon": [
            [117.120, 36.680], [117.190, 36.680],
            [117.190, 36.640], [117.120, 36.640], [117.120, 36.680]
        ],
        "status": "optimizing",
        "saturation": 0.77,
        "avgSpeed": 25.8,
        "avgDelay": 62.3,
        "congestionIndex": 3.4,
        "roadDensity": 7.8,
        "inFlow": 3250,
        "outFlow": 3080,
        "transitVolume": 8200,
        "primaryIssue": "dynamic_demand_supply_imbalance",
        "strategy": "corridor_tidal_green_wave",
        "profile": {
            "supply": {
                "roadDensity": 7.8,
                "intersectionCapacity": 3100,
                "parkingGap": 0.22
            },
            "demand": {
                "peakHourFlow": 3250,
                "demandSupplyRatio": 0.98,
                "commuteRatio": 0.72
            },
            "state": {
                "saturation": 0.77,
                "avgSpeed": 25.8,
                "avgDelay": 62.3,
                "congestionPhase": "萌芽期"
            }
        },
        "issues": [
            {
                "id": "dynamic_demand_supply_imbalance",
                "name": "通勤潮汐·方向性供需失衡",
                "category": "dynamic",
                "severity": 0.76,
                "confidence": 0.91,
                "evidence": {
                    "tidalRatio": 1.8,
                    "amPeakDirection": "西→东（入区方向）",
                    "peakWindow": "07:30-09:00"
                },
                "reason": "高新区CBD通勤比例72%，早高峰西→东方向流量是反向的1.8倍，世纪大道/舜华路方向性拥堵突出"
            }
        ],
        "strategies": [
            {
                "templateId": "corridor_tidal_green_wave",
                "level": "corridor",
                "description": "世纪大道潮汐绿波：早峰东行/晚峰西行优先",
                "score": 0.87,
                "mode": "periodic",
                "objective": "主方向停车率降低30%，通勤走廊带宽提升至30s",
                "sideEffects": "反方向等待增加约18s",
                "requiresApproval": False,
                "params": {
                    "targetCorridor": "COR-SHIJIDA",
                    "tidalDirection": "eastbound_am",
                    "targetBandwidth": 30,
                    "activePeriod": "07:00-09:30"
                }
            }
        ],
        "sceneCognition": {
            "sceneType": "dynamic",
            "sceneName": "高新区CBD早高峰通勤潮汐",
            "triggerTime": "07:35",
            "triggerCondition": "世纪大道西→东方向饱和度超0.78，潮汐比>1.5",
            "supply": {
                "roadDensity": 7.8,
                "densityAssessment": "高新区新建路网密度较好，但世纪大道承担主要通勤功能，支路分流能力有限",
                "intersectionCapacity": 3100,
                "capacityAssessment": "路口设计通行能力满足日常需求，但通勤高峰方向性过载"
            },
            "demand": {
                "peakHourFlow": 3250,
                "demandSupplyRatio": 0.98,
                "commuteRatio": 0.72,
                "flowCharacteristics": "IT产业园区通勤主导，72%为通勤流，潮汐特征显著"
            },
            "state": {
                "saturation": 0.77,
                "avgSpeed": 25.8,
                "avgDelay": 62.3,
                "congestionPhase": "萌芽期",
                "phaseExplanation": "拥堵尚在可控范围，但通勤主方向局部路口已接近饱和"
            },
            "summary": "高新区CBD片区通勤潮汐特征显著，早高峰西→东方向流量远超反向，世纪大道和舜华路沿线局部路口承压明显，适合潮汐绿波优化。"
        },
        "mapContext": {
            "primaryObjectId": "RGN-GAOXIN",
            "primaryObjectType": "region",
            "affectedObjectIds": ["INT-JN-0716", "INT-JN-0719", "INT-JN-0720"],
            "upstreamIds": ["COR-SHIJIDA"],
            "downstreamIds": []
        }
    }
]

# ── NEW CORRIDORS ───────────────────────────────────────────────────────
new_corridors = [
    {
        "id": "COR-ERHUANDONG",
        "name": "二环东路南北走廊",
        "direction": "南北双向",
        "intersectionIds": ["INT-JN-0711", "INT-JN-0718", "INT-JN-0715"],
        "path": [
            [117.088, 36.710], [117.088, 36.700],
            [117.088, 36.670], [117.088, 36.635]
        ],
        "status": "critical",
        "avgSpeed": 19.2,
        "stopRate": 0.68,
        "throughputRatio": 0.65,
        "bandwidth": 8,
        "coordCycleS": 130,
        "designSpeedKmh": 50,
        "actualSpeedKmh": 19.2,
        "primaryIssue": "dynamic_low_speed",
        "strategy": "corridor_green_wave_rebuild",
        "before": {"avgSpeed": 19.2, "stopRate": 0.68, "delay": 88.5},
        "after": {"avgSpeed": 33.8, "stopRate": 0.35, "delay": 48.2},
        "intersections": [
            {"id": "INT-JN-0711", "name": "二环东路/祝舜路", "saturation": 0.89, "issues": ["高架衔接溢流", "排队回溢"]},
            {"id": "INT-JN-0718", "name": "二环东路/旅游路", "saturation": 0.82, "issues": ["匝道交织"]},
            {"id": "INT-JN-0715", "name": "奥体中路/解放东路", "saturation": 0.74, "issues": []}
        ],
        "issues": [
            {
                "id": "dynamic_low_speed",
                "name": "走廊车速严重低于设计值",
                "category": "dynamic",
                "severity": 0.82,
                "confidence": 0.93,
                "evidence": {"actualSpeed": 19.2, "designSpeed": 50, "speedRatio": 0.384, "stopRate": 0.68},
                "reason": "二环东路快速路与地面路交接段车速仅19.2km/h，高架下桥交织导致地面路口连续排队"
            },
            {
                "id": "signal_queue_overflow",
                "name": "祝舜路路口匝道溢流",
                "category": "signal_control",
                "severity": 0.86,
                "confidence": 0.91,
                "evidence": {"bottleneck": "INT-JN-0711", "queueLength": 210, "storageCap": 180},
                "reason": "二环东路/祝舜路路口排队210m超出存储180m，匝道回溢至高架主线影响快速路通行"
            }
        ],
        "strategies": [
            {
                "templateId": "corridor_green_wave_rebuild",
                "level": "corridor",
                "description": "二环东路地面段绿波重建+匝道信号协调",
                "score": 0.88,
                "mode": "realtime",
                "objective": "停车率0.68→0.35，匝道排队控制在180m以内",
                "sideEffects": "支路方向等待增加约20s",
                "requiresApproval": True,
                "params": {
                    "targetIntersections": ["INT-JN-0711", "INT-JN-0718", "INT-JN-0715"],
                    "cycleTarget": 110,
                    "bandwidthTarget": 24,
                    "speedTarget": 35,
                    "rampCoordination": True
                }
            }
        ],
        "sceneCognition": {
            "sceneType": "dynamic",
            "sceneName": "二环东路高架地面衔接拥堵",
            "triggerTime": "07:48",
            "triggerCondition": "祝舜路路口饱和度超0.85且匝道排队检测值超180m",
            "supply": {"corridorCapacity": 2400, "laneCount": 3, "assessment": "二环东路快速路段与地面段衔接设计通行能力2400辆/h，但匝道汇入点成为瓶颈"},
            "demand": {"peakHourFlow": 4800, "tidal": True, "tidalRatio": 0.62, "assessment": "早高峰南→北通勤方向为主，高架与地面车流在匝道区域交织冲突"},
            "state": {"saturation": 0.86, "avgSpeed": 19.2, "stopRate": 0.68, "congestionPhase": "持续期", "assessment": "匝道区域溢流已持续20min以上，影响开始向高架主线蔓延"},
            "summary": "二环东路南北走廊高架地面衔接段拥堵严重。祝舜路路口作为关键节点，匝道下桥车流与地面通勤流交织，排队已超出存储容量，回溢至高架主线。"
        },
        "mapContext": {
            "primaryObjectId": "COR-ERHUANDONG",
            "primaryObjectType": "corridor",
            "affectedObjectIds": ["INT-JN-0711", "INT-JN-0718", "INT-JN-0715"],
            "bottleneckIds": ["INT-JN-0711"],
            "upstreamIds": ["RGN-LICHENG"],
            "downstreamIds": []
        }
    },
    {
        "id": "COR-BEIYUAN",
        "name": "北园大街东西走廊",
        "direction": "东西双向",
        "intersectionIds": ["INT-JN-0705", "INT-JN-0723", "INT-JN-0710"],
        "path": [
            [116.960, 36.695], [116.977, 36.695],
            [117.020, 36.695], [117.055, 36.695]
        ],
        "status": "warning",
        "avgSpeed": 22.4,
        "stopRate": 0.58,
        "throughputRatio": 0.71,
        "bandwidth": 12,
        "coordCycleS": 120,
        "designSpeedKmh": 40,
        "actualSpeedKmh": 22.4,
        "primaryIssue": "dynamic_high_delay",
        "strategy": "corridor_tidal_green_wave",
        "before": {"avgSpeed": 22.4, "stopRate": 0.58, "delay": 76.8},
        "after": {"avgSpeed": 32.6, "stopRate": 0.36, "delay": 49.5},
        "intersections": [
            {"id": "INT-JN-0705", "name": "无影山中路/济齐路", "saturation": 0.91, "issues": ["高架瓶颈", "BRT占道"]},
            {"id": "INT-JN-0723", "name": "北园大街/历山路", "saturation": 0.84, "issues": ["下桥禁左冲突"]},
            {"id": "INT-JN-0710", "name": "北园大街/生产路", "saturation": 0.78, "issues": ["货运混行"]}
        ],
        "issues": [
            {
                "id": "dynamic_high_delay",
                "name": "走廊延误持续偏高",
                "category": "dynamic",
                "severity": 0.78,
                "confidence": 0.90,
                "evidence": {"avgDelay": 76.8, "peakDelay": 112, "affectedIntersections": 3},
                "reason": "北园大街3个关键路口高峰延误均超70s，高架匝道汇入和BRT专用道占用导致通行能力受限"
            },
            {
                "id": "signal_phase_imbalance",
                "name": "济齐路路口东向西车道瓶颈",
                "category": "signal_control",
                "severity": 0.85,
                "confidence": 0.92,
                "evidence": {"bottleneckNode": "INT-JN-0705", "eastWestLaneReduction": "6→2", "queueLength": 520},
                "reason": "无影山中路/济齐路路口东向西车道从上游6车道缩减至2条直行，形成严重交通瓶颈"
            }
        ],
        "strategies": [
            {
                "templateId": "corridor_tidal_green_wave",
                "level": "corridor",
                "description": "北园大街潮汐绿波+BRT车道动态共享",
                "score": 0.84,
                "mode": "periodic",
                "objective": "走廊延误降低35%，东向西排队控制在200m以内",
                "sideEffects": "BRT公交在高峰时段可能需等待一个周期",
                "requiresApproval": True,
                "params": {
                    "amPeakDirection": "westbound",
                    "pmPeakDirection": "eastbound",
                    "bandwidthTarget": 24,
                    "brtLaneSharing": True
                }
            }
        ],
        "sceneCognition": {
            "sceneType": "dynamic",
            "sceneName": "北园大街早高峰高架汇入拥堵",
            "triggerTime": "07:38",
            "triggerCondition": "济齐路路口东向西排队超300m且持续5分钟",
            "supply": {"corridorCapacity": 2000, "laneCount": 2, "assessment": "北园大街东向西直行仅2车道，BRT专用道占用1车道，实际通行能力严重受限"},
            "demand": {"peakHourFlow": 4200, "tidal": True, "tidalRatio": 0.65, "assessment": "早高峰东→西入城方向为主，高架下桥流与地面流叠加"},
            "state": {"saturation": 0.87, "avgSpeed": 22.4, "stopRate": 0.58, "congestionPhase": "持续期", "assessment": "济齐路路口为核心瓶颈，东向排队已超500m"},
            "summary": "北园大街东西走廊早高峰拥堵严重。核心瓶颈在无影山中路/济齐路路口，车道数从6缩减至2导致东向西方向严重拥堵，排队超500m。"
        },
        "mapContext": {
            "primaryObjectId": "COR-BEIYUAN",
            "primaryObjectType": "corridor",
            "affectedObjectIds": ["INT-JN-0705", "INT-JN-0723", "INT-JN-0710"],
            "bottleneckIds": ["INT-JN-0705"],
            "upstreamIds": ["RGN-TIANQIAO"],
            "downstreamIds": []
        }
    },
    {
        "id": "COR-LUOYUAN",
        "name": "泺源大街东西走廊",
        "direction": "东西双向",
        "intersectionIds": ["INT-JN-0702", "INT-JN-0713"],
        "path": [
            [117.005, 36.665], [117.015, 36.665],
            [117.022, 36.665], [117.035, 36.665]
        ],
        "status": "optimizing",
        "avgSpeed": 24.6,
        "stopRate": 0.52,
        "throughputRatio": 0.74,
        "bandwidth": 14,
        "coordCycleS": 100,
        "designSpeedKmh": 40,
        "actualSpeedKmh": 24.6,
        "primaryIssue": "signal_queue_overflow",
        "strategy": "intersection_bottleneck_anti_spillback",
        "before": {"avgSpeed": 24.6, "stopRate": 0.52, "delay": 72.3},
        "after": {"avgSpeed": 33.2, "stopRate": 0.34, "delay": 46.8},
        "intersections": [
            {"id": "INT-JN-0702", "name": "泺源大街/南门大街", "saturation": 0.88, "issues": ["左转溢流", "上游回堵"]},
            {"id": "INT-JN-0713", "name": "泺源大街/南新街", "saturation": 0.79, "issues": ["绿波断裂"]}
        ],
        "issues": [
            {
                "id": "signal_queue_overflow",
                "name": "南门大街路口左转溢流",
                "category": "signal_control",
                "severity": 0.84,
                "confidence": 0.92,
                "evidence": {"bottleneck": "INT-JN-0702", "leftTurnOverflow": True, "upstreamImpact": "泺文路路口"},
                "reason": "泺源大街/南门大街路口左转车辆常溢流至上游泺文路路口，路口间距不足150m加剧溢流风险"
            }
        ],
        "strategies": [
            {
                "templateId": "intersection_bottleneck_anti_spillback",
                "level": "intersection",
                "description": "南门大街路口可变车道+左转溢流防护",
                "score": 0.86,
                "mode": "realtime",
                "objective": "左转排队控制在路口间距范围内，消除上游溢流",
                "sideEffects": "直行通行能力短暂下降约10%",
                "requiresApproval": False,
                "params": {
                    "variableLaneEnabled": True,
                    "leftTurnOverflowProtection": True,
                    "upstreamCoordination": True
                }
            }
        ],
        "sceneCognition": {
            "sceneType": "dynamic",
            "sceneName": "泺源大街明府城片区溢流",
            "triggerTime": "10:15",
            "triggerCondition": "南门大街路口左转排队溢出至泺文路路口",
            "supply": {"corridorCapacity": 1800, "laneCount": 3, "assessment": "路口间距仅150m，左转排队存储空间严重不足"},
            "demand": {"peakHourFlow": 3200, "tidal": False, "tidalRatio": 0.52, "assessment": "明府城景区与商业混合出行，节假日左转需求激增"},
            "state": {"saturation": 0.84, "avgSpeed": 24.6, "stopRate": 0.52, "congestionPhase": "萌芽期", "assessment": "溢流问题间歇性发生，工作日与节假日差异大"},
            "summary": "泺源大街东西走廊在南门大街路口存在左转溢流问题。路口与上游泺文路路口间距不足150m，左转车流量大时溢流回堵影响上游通行。"
        },
        "mapContext": {
            "primaryObjectId": "COR-LUOYUAN",
            "primaryObjectType": "corridor",
            "affectedObjectIds": ["INT-JN-0702", "INT-JN-0713"],
            "bottleneckIds": ["INT-JN-0702"],
            "upstreamIds": [],
            "downstreamIds": ["RGN-LIXIA"]
        }
    },
    {
        "id": "COR-SHIJIDA",
        "name": "世纪大道东西走廊",
        "direction": "东西双向",
        "intersectionIds": ["INT-JN-0716", "INT-JN-0720"],
        "path": [
            [117.140, 36.652], [117.155, 36.652],
            [117.170, 36.652], [117.185, 36.652]
        ],
        "status": "optimizing",
        "avgSpeed": 27.8,
        "stopRate": 0.42,
        "throughputRatio": 0.79,
        "bandwidth": 20,
        "coordCycleS": 110,
        "designSpeedKmh": 50,
        "actualSpeedKmh": 27.8,
        "primaryIssue": "dynamic_demand_supply_imbalance",
        "strategy": "corridor_tidal_green_wave",
        "before": {"avgSpeed": 27.8, "stopRate": 0.42, "delay": 58.6},
        "after": {"avgSpeed": 38.5, "stopRate": 0.28, "delay": 38.2},
        "intersections": [
            {"id": "INT-JN-0716", "name": "世纪大道/凤歧路", "saturation": 0.83, "issues": ["潮汐失衡"]},
            {"id": "INT-JN-0720", "name": "经十路/凤鸣路", "saturation": 0.72, "issues": []}
        ],
        "issues": [
            {
                "id": "dynamic_demand_supply_imbalance",
                "name": "通勤潮汐方向性供需失衡",
                "category": "dynamic",
                "severity": 0.76,
                "confidence": 0.89,
                "evidence": {"tidalRatio": 1.8, "amPeakSaturation": 0.83, "pmPeakSaturation": 0.79},
                "reason": "世纪大道早高峰西→东通勤流量是反向1.8倍，现有均衡配时无法适配方向性需求"
            }
        ],
        "strategies": [
            {
                "templateId": "corridor_tidal_green_wave",
                "level": "corridor",
                "description": "世纪大道潮汐绿波优化",
                "score": 0.87,
                "mode": "periodic",
                "objective": "主方向带宽从20s提升至30s，车速提升至38km/h",
                "sideEffects": "反方向等待增加约15s",
                "requiresApproval": False,
                "params": {
                    "amPeakDirection": "eastbound",
                    "pmPeakDirection": "westbound",
                    "bandwidthTarget": 30,
                    "cycleTarget": 100
                }
            }
        ],
        "sceneCognition": {
            "sceneType": "dynamic",
            "sceneName": "世纪大道高新区通勤潮汐",
            "triggerTime": "07:40",
            "triggerCondition": "凤歧路路口东向饱和度超0.80",
            "supply": {"corridorCapacity": 2600, "laneCount": 4, "assessment": "世纪大道双向8车道通行能力充裕，但绿波配时未考虑潮汐特征"},
            "demand": {"peakHourFlow": 4600, "tidal": True, "tidalRatio": 1.8, "assessment": "IT园区/软件园通勤主导，方向性极强"},
            "state": {"saturation": 0.79, "avgSpeed": 27.8, "stopRate": 0.42, "congestionPhase": "萌芽期", "assessment": "通过潮汐绿波优化可显著改善通勤方向通行体验"},
            "summary": "世纪大道东西走廊作为高新区通勤主干道，潮汐特征显著。现有均衡配时浪费反向绿灯资源，通过方向性绿波优化空间较大。"
        },
        "mapContext": {
            "primaryObjectId": "COR-SHIJIDA",
            "primaryObjectType": "corridor",
            "affectedObjectIds": ["INT-JN-0716", "INT-JN-0720"],
            "bottleneckIds": ["INT-JN-0716"],
            "upstreamIds": ["RGN-GAOXIN"],
            "downstreamIds": []
        }
    }
]

# ── NEW INTERSECTIONS ───────────────────────────────────────────────────
new_intersections = [
    # 1. 经十路/转山西路 - critical (万象城周边)
    {
        "id": "INT-JN-0701",
        "name": "经十路/转山西路",
        "lat": 117.097,
        "lng": 36.649,
        "status": "critical",
        "saturation": 0.90,
        "delay": 108.5,
        "queueLength": 195,
        "stopRate": 0.78,
        "cycleTime": 135,
        "issues": [
            {
                "id": "signal_queue_overflow",
                "name": "西口掉头左转溢流",
                "category": "signal_control",
                "severity": 0.89,
                "confidence": 0.94,
                "evidence": {"westLeftTurnQueue": 220, "storageCap": 160, "overflowTarget": "海右路"},
                "reason": "万象城、山东博物馆等吸引点导致西口掉头和左转流量大，车辆常滞留路口阻塞直行"
            },
            {
                "id": "dynamic_high_saturation",
                "name": "CBD进出口高饱和",
                "category": "dynamic",
                "severity": 0.85,
                "confidence": 0.92,
                "evidence": {"saturation": 0.90, "cbdInfluence": "海右路/礼士路进出CBD"},
                "reason": "路口承担CBD片区主要进出通道功能，海右路和礼士路汇入叠加经十路干线流量"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "西口辅路禁左+提前调头口设置，CBD通道优化", "score": 0.91},
            {"templateId": "intersection_bottleneck_anti_spillback", "level": "intersection", "description": "海右路增加车道+出口绿灯保护", "score": 0.84}
        ],
        "before": {"saturation": 0.90, "delay": 108.5, "cycleTime": 135, "northGreen": 35, "eastGreen": 55},
        "after": {"saturation": 0.76, "delay": 68.2, "cycleTime": 110, "northGreen": 48, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 35, "splitRatio": 0.28, "saturation": 0.92},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 55, "splitRatio": 0.43, "saturation": 0.78},
            {"phaseId": "C", "phaseName": "西口左转掉头", "direction": "W left/U", "greenTime": 22, "splitRatio": 0.17, "saturation": 0.95},
            {"phaseId": "D", "phaseName": "东西左转", "direction": "E-W left", "greenTime": 13, "splitRatio": 0.10, "saturation": 0.72}
        ]
    },
    # 2. 泺源大街/南门大街 - critical (明府城溢流)
    {
        "id": "INT-JN-0702",
        "name": "泺源大街/南门大街",
        "lat": 117.015,
        "lng": 36.665,
        "status": "critical",
        "saturation": 0.88,
        "delay": 96.3,
        "queueLength": 175,
        "stopRate": 0.72,
        "cycleTime": 125,
        "issues": [
            {
                "id": "signal_queue_overflow",
                "name": "左转车辆溢流至上游泺文路路口",
                "category": "signal_control",
                "severity": 0.87,
                "confidence": 0.93,
                "evidence": {"leftTurnQueue": 180, "upstreamDistance": 150, "upstreamImpact": "泺文路路口"},
                "reason": "路口与上游泺文路路口间距仅150m，节假日左转车流量大时常溢流回堵影响上游正常运行"
            },
            {
                "id": "dynamic_high_saturation",
                "name": "明府城进出高饱和",
                "category": "dynamic",
                "severity": 0.82,
                "confidence": 0.90,
                "evidence": {"saturation": 0.88, "weekendPeak": True, "touristInfluence": "明府城景区"},
                "reason": "承接进出明府城片区大量车流，双休日及节假日左转需求尤其突出"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "第二车道设置可变车道+取消公交专用道+右转辅路化", "score": 0.88},
            {"templateId": "intersection_bottleneck_anti_spillback", "level": "intersection", "description": "上游泺文路协同截流防溢", "score": 0.82}
        ],
        "before": {"saturation": 0.88, "delay": 96.3, "cycleTime": 125, "northGreen": 38, "eastGreen": 48},
        "after": {"saturation": 0.74, "delay": 62.1, "cycleTime": 100, "northGreen": 46, "eastGreen": 38},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.32, "saturation": 0.88},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 48, "splitRatio": 0.40, "saturation": 0.76},
            {"phaseId": "C", "phaseName": "南北左转", "direction": "N-S left", "greenTime": 25, "splitRatio": 0.21, "saturation": 0.93},
            {"phaseId": "D", "phaseName": "东西左转", "direction": "E-W left", "greenTime": 10, "splitRatio": 0.08, "saturation": 0.65}
        ]
    },
    # 3. 经十路/山师东路 - warning (千佛山医院影响)
    {
        "id": "INT-JN-0703",
        "name": "经十路/山师东路",
        "lat": 117.054,
        "lng": 36.648,
        "status": "warning",
        "saturation": 0.82,
        "delay": 78.4,
        "queueLength": 145,
        "stopRate": 0.58,
        "cycleTime": 120,
        "issues": [
            {
                "id": "dynamic_high_saturation",
                "name": "千佛山医院就医停靠瓶颈",
                "category": "dynamic",
                "severity": 0.78,
                "confidence": 0.89,
                "evidence": {"saturation": 0.82, "hospitalParking": "临时停靠占道", "laneReduction": "5→4"},
                "reason": "千佛山医院门口临时停靠车辆占用通行资源，路段车道从上下游5车道缩至4车道形成瓶颈"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "车道宽度压缩增设西→东车道，消除瓶颈点", "score": 0.85}
        ],
        "before": {"saturation": 0.82, "delay": 78.4, "cycleTime": 120, "northGreen": 40, "eastGreen": 48},
        "after": {"saturation": 0.72, "delay": 56.8, "cycleTime": 105, "northGreen": 45, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 40, "splitRatio": 0.35, "saturation": 0.79},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 48, "splitRatio": 0.42, "saturation": 0.82},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 22, "splitRatio": 0.19, "saturation": 0.74}
        ]
    },
    # 4. 九曲庄路/二环南路 - critical (匝道滞留)
    {
        "id": "INT-JN-0704",
        "name": "九曲庄路/二环南路",
        "lat": 117.020,
        "lng": 36.625,
        "status": "critical",
        "saturation": 0.92,
        "delay": 118.7,
        "queueLength": 240,
        "stopRate": 0.82,
        "cycleTime": 140,
        "issues": [
            {
                "id": "signal_queue_overflow",
                "name": "下桥匝道排队激增·高架滞留",
                "category": "signal_control",
                "severity": 0.91,
                "confidence": 0.95,
                "evidence": {"rampQueue": 280, "storageCap": 200, "highwayBackup": True},
                "reason": "晚高峰下桥匝道排队车辆长度激增，滞留严重回溢至高架主线，通行效率大幅降低"
            }
        ],
        "strategies": [
            {"templateId": "intersection_bottleneck_anti_spillback", "level": "intersection", "description": "九曲庄路增设信号灯·主路与下桥交替放行", "score": 0.90}
        ],
        "before": {"saturation": 0.92, "delay": 118.7, "cycleTime": 140, "northGreen": 30, "eastGreen": 60},
        "after": {"saturation": 0.78, "delay": 72.4, "cycleTime": 110, "northGreen": 45, "eastGreen": 45},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "主路直行", "direction": "E-W", "greenTime": 60, "splitRatio": 0.45, "saturation": 0.78},
            {"phaseId": "B", "phaseName": "匝道放行", "direction": "ramp", "greenTime": 30, "splitRatio": 0.22, "saturation": 0.95},
            {"phaseId": "C", "phaseName": "九曲庄路直行", "direction": "N-S", "greenTime": 30, "splitRatio": 0.22, "saturation": 0.85},
            {"phaseId": "D", "phaseName": "左转保护", "direction": "all left", "greenTime": 12, "splitRatio": 0.09, "saturation": 0.72}
        ]
    },
    # 5. 无影山中路/济齐路 - critical (高架转换瓶颈)
    {
        "id": "INT-JN-0705",
        "name": "无影山中路/济齐路",
        "lat": 116.977,
        "lng": 36.700,
        "status": "critical",
        "saturation": 0.91,
        "delay": 115.2,
        "queueLength": 520,
        "stopRate": 0.79,
        "cycleTime": 135,
        "issues": [
            {
                "id": "signal_phase_imbalance",
                "name": "东向西车道瓶颈·6车道缩减至2车道",
                "category": "signal_control",
                "severity": 0.92,
                "confidence": 0.96,
                "evidence": {"upstreamLanes": 6, "bottleneckLanes": 2, "brtOccupied": True, "queueLength": 520},
                "reason": "路口东向西车道数从上游6车道缩至2条直行，BRT专用道额外占用1车道，排队超500m"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "取消东口BRT专用道改直行+信号配时优化", "score": 0.92}
        ],
        "before": {"saturation": 0.91, "delay": 115.2, "cycleTime": 135, "northGreen": 35, "eastGreen": 55},
        "after": {"saturation": 0.77, "delay": 68.5, "cycleTime": 110, "northGreen": 42, "eastGreen": 48},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 55, "splitRatio": 0.42, "saturation": 0.93},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 35, "splitRatio": 0.27, "saturation": 0.82},
            {"phaseId": "C", "phaseName": "济齐路分叉放行", "direction": "fork", "greenTime": 25, "splitRatio": 0.19, "saturation": 0.78},
            {"phaseId": "D", "phaseName": "左转保护", "direction": "all left", "greenTime": 12, "splitRatio": 0.09, "saturation": 0.71}
        ]
    },
    # 6. 济齐路/黄岗路 - optimized (五岔口微改造完成)
    {
        "id": "INT-JN-0706",
        "name": "济齐路/黄岗路",
        "lat": 116.969,
        "lng": 36.703,
        "status": "optimized",
        "saturation": 0.68,
        "delay": 44.2,
        "queueLength": 72,
        "stopRate": 0.28,
        "cycleTime": 95,
        "issues": [],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "五岔口微改造：停止线前移+斑马线优化+信号配时精调", "score": 0.93}
        ],
        "before": {"saturation": 0.85, "delay": 92.8, "cycleTime": 130, "northGreen": 30, "eastGreen": 45},
        "after": {"saturation": 0.68, "delay": 44.2, "cycleTime": 95, "northGreen": 38, "eastGreen": 35},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "济齐路直行", "direction": "E-W", "greenTime": 35, "splitRatio": 0.38, "saturation": 0.68},
            {"phaseId": "B", "phaseName": "黄岗路直行", "direction": "N-S", "greenTime": 28, "splitRatio": 0.30, "saturation": 0.65},
            {"phaseId": "C", "phaseName": "兴学街放行", "direction": "SW", "greenTime": 18, "splitRatio": 0.19, "saturation": 0.58},
            {"phaseId": "D", "phaseName": "非机动车过街", "direction": "ped/bike", "greenTime": 10, "splitRatio": 0.11, "saturation": 0.42}
        ]
    },
    # 7. 经十路/凤祥路 - warning
    {
        "id": "INT-JN-0707",
        "name": "经十路/凤祥路",
        "lat": 117.168,
        "lng": 36.647,
        "status": "warning",
        "saturation": 0.83,
        "delay": 82.5,
        "queueLength": 310,
        "stopRate": 0.64,
        "cycleTime": 120,
        "issues": [
            {
                "id": "signal_phase_imbalance",
                "name": "北口左右转未分离·车辆积压",
                "category": "signal_control",
                "severity": 0.79,
                "confidence": 0.88,
                "evidence": {"northQueueLength": 310, "rightTurnBlocked": True, "laneCount": 2},
                "reason": "凤祥路北口仅一条左右转车道，右转车辆无法提前分流，导致路口车辆严重积压"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "增设右转借用非机动车道+左右转分离", "score": 0.86}
        ],
        "before": {"saturation": 0.83, "delay": 82.5, "cycleTime": 120, "northGreen": 35, "eastGreen": 50},
        "after": {"saturation": 0.72, "delay": 58.3, "cycleTime": 105, "northGreen": 42, "eastGreen": 45},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "经十路直行", "direction": "E-W", "greenTime": 50, "splitRatio": 0.43, "saturation": 0.78},
            {"phaseId": "B", "phaseName": "凤祥路直行", "direction": "N-S", "greenTime": 35, "splitRatio": 0.30, "saturation": 0.85},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 22, "splitRatio": 0.19, "saturation": 0.79},
            {"phaseId": "D", "phaseName": "东西左转", "direction": "E-W left", "greenTime": 8, "splitRatio": 0.07, "saturation": 0.62}
        ]
    },
    # 8. 龙奥北路/凤天路 - warning (潮汐特征)
    {
        "id": "INT-JN-0708",
        "name": "龙奥北路/凤天路",
        "lat": 117.135,
        "lng": 36.660,
        "status": "warning",
        "saturation": 0.80,
        "delay": 74.8,
        "queueLength": 170,
        "stopRate": 0.56,
        "cycleTime": 115,
        "issues": [
            {
                "id": "dynamic_demand_supply_imbalance",
                "name": "南口潮汐特征·左转占比过高",
                "category": "dynamic",
                "severity": 0.77,
                "confidence": 0.90,
                "evidence": {"southLeftTurnRatio": 0.49, "leftTurnLanes": 1, "amPeakQueue": 170},
                "reason": "早高峰南口排队170m，左转占比达49%但仅有一条直左车道，车道资源严重失衡"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "南口潮汐车道+早高峰左转专用", "score": 0.87}
        ],
        "before": {"saturation": 0.80, "delay": 74.8, "cycleTime": 115, "northGreen": 42, "eastGreen": 45},
        "after": {"saturation": 0.70, "delay": 52.3, "cycleTime": 100, "northGreen": 48, "eastGreen": 38},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.38, "saturation": 0.80},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 45, "splitRatio": 0.41, "saturation": 0.72},
            {"phaseId": "C", "phaseName": "南北左转", "direction": "N-S left", "greenTime": 18, "splitRatio": 0.16, "saturation": 0.88}
        ]
    },
    # 9. 旅游路/椒山路 - optimizing
    {
        "id": "INT-JN-0709",
        "name": "旅游路/椒山路",
        "lat": 117.082,
        "lng": 36.635,
        "status": "optimizing",
        "saturation": 0.76,
        "delay": 68.2,
        "queueLength": 115,
        "stopRate": 0.48,
        "cycleTime": 110,
        "issues": [
            {
                "id": "signal_green_waste",
                "name": "左转车道资源浪费",
                "category": "signal_control",
                "severity": 0.65,
                "confidence": 0.86,
                "evidence": {"leftTurnRatio": 0.12, "throughRatio": 0.70, "throughQueueLength": 115},
                "reason": "东西方向左转车流仅占12%而直行需求70%以上，单独左转车道存在明显资源浪费"
            }
        ],
        "strategies": [
            {"templateId": "intersection_balance_and_green_reuse", "level": "intersection", "description": "左转车道改直左车道+车道功能优化", "score": 0.84}
        ],
        "before": {"saturation": 0.76, "delay": 68.2, "cycleTime": 110, "northGreen": 38, "eastGreen": 42},
        "after": {"saturation": 0.68, "delay": 48.5, "cycleTime": 95, "northGreen": 42, "eastGreen": 38},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 42, "splitRatio": 0.40, "saturation": 0.76},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.36, "saturation": 0.72},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 20, "splitRatio": 0.19, "saturation": 0.48}
        ]
    },
    # 10. 北园大街/生产路 - warning
    {
        "id": "INT-JN-0710",
        "name": "北园大街/生产路",
        "lat": 117.042,
        "lng": 36.695,
        "status": "warning",
        "saturation": 0.78,
        "delay": 72.1,
        "queueLength": 138,
        "stopRate": 0.52,
        "cycleTime": 115,
        "issues": [
            {
                "id": "dynamic_high_delay",
                "name": "货运通勤混行·延误偏高",
                "category": "dynamic",
                "severity": 0.74,
                "confidence": 0.87,
                "evidence": {"avgDelay": 72.1, "truckRatio": 0.18, "peakWindow": "07:30-09:00"},
                "reason": "生产路沿线物流仓储区货运车辆占比18%，与通勤车流混行导致路口通行效率降低"
            }
        ],
        "strategies": [
            {"templateId": "intersection_delay_relief", "level": "intersection", "description": "货运时段分离+短周期优化", "score": 0.78}
        ],
        "before": {"saturation": 0.78, "delay": 72.1, "cycleTime": 115, "northGreen": 38, "eastGreen": 46},
        "after": {"saturation": 0.71, "delay": 54.3, "cycleTime": 100, "northGreen": 42, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 46, "splitRatio": 0.42, "saturation": 0.78},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.35, "saturation": 0.75},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 18, "splitRatio": 0.16, "saturation": 0.68}
        ]
    },
    # 11. 二环东路/祝舜路 - critical
    {
        "id": "INT-JN-0711",
        "name": "二环东路/祝舜路",
        "lat": 117.088,
        "lng": 36.700,
        "status": "critical",
        "saturation": 0.89,
        "delay": 105.8,
        "queueLength": 210,
        "stopRate": 0.76,
        "cycleTime": 130,
        "issues": [
            {
                "id": "signal_queue_overflow",
                "name": "高架匝道排队回溢至主线",
                "category": "signal_control",
                "severity": 0.88,
                "confidence": 0.93,
                "evidence": {"rampQueue": 210, "storageCap": 180, "mainlineImpact": True},
                "reason": "二环东路下桥匝道排队210m超出存储容量180m，车辆回溢至高架主线影响快速路通行安全"
            },
            {
                "id": "dynamic_high_saturation",
                "name": "地面路口高饱和运行",
                "category": "dynamic",
                "severity": 0.83,
                "confidence": 0.91,
                "evidence": {"saturation": 0.89, "peakWindow": "07:30-09:00"},
                "reason": "匝道下桥流与地面祝舜路通勤流在路口交织，饱和度长期超0.85"
            }
        ],
        "strategies": [
            {"templateId": "intersection_bottleneck_anti_spillback", "level": "intersection", "description": "匝道信号控制+地面路口绿灯保护", "score": 0.89},
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "匝道与地面交替放行策略", "score": 0.83}
        ],
        "before": {"saturation": 0.89, "delay": 105.8, "cycleTime": 130, "northGreen": 32, "eastGreen": 52},
        "after": {"saturation": 0.76, "delay": 65.4, "cycleTime": 110, "northGreen": 45, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "二环东路直行", "direction": "N-S", "greenTime": 52, "splitRatio": 0.42, "saturation": 0.82},
            {"phaseId": "B", "phaseName": "祝舜路直行", "direction": "E-W", "greenTime": 32, "splitRatio": 0.26, "saturation": 0.91},
            {"phaseId": "C", "phaseName": "匝道放行", "direction": "ramp", "greenTime": 25, "splitRatio": 0.20, "saturation": 0.89},
            {"phaseId": "D", "phaseName": "左转保护", "direction": "all left", "greenTime": 12, "splitRatio": 0.10, "saturation": 0.72}
        ]
    },
    # 12. 小清河北路/标山路 - warning
    {
        "id": "INT-JN-0712",
        "name": "小清河北路/标山路",
        "lat": 117.015,
        "lng": 36.698,
        "status": "warning",
        "saturation": 0.75,
        "delay": 64.8,
        "queueLength": 105,
        "stopRate": 0.46,
        "cycleTime": 100,
        "issues": [
            {
                "id": "dynamic_high_delay",
                "name": "北侧居民区出行延误偏高",
                "category": "dynamic",
                "severity": 0.68,
                "confidence": 0.85,
                "evidence": {"avgDelay": 64.8, "peakWindow": "07:00-08:30"},
                "reason": "标山路沿线密集居民区早高峰出行需求集中，路口通行能力不足导致延误偏高"
            }
        ],
        "strategies": [
            {"templateId": "intersection_delay_relief", "level": "intersection", "description": "短周期优化+行人过街协调", "score": 0.76}
        ],
        "before": {"saturation": 0.75, "delay": 64.8, "cycleTime": 100, "northGreen": 36, "eastGreen": 40},
        "after": {"saturation": 0.69, "delay": 48.2, "cycleTime": 90, "northGreen": 40, "eastGreen": 36},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 40, "splitRatio": 0.42, "saturation": 0.72},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 36, "splitRatio": 0.38, "saturation": 0.75},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 14, "splitRatio": 0.15, "saturation": 0.62}
        ]
    },
    # 13. 泺源大街/南新街 - optimizing
    {
        "id": "INT-JN-0713",
        "name": "泺源大街/南新街",
        "lat": 117.022,
        "lng": 36.665,
        "status": "optimizing",
        "saturation": 0.79,
        "delay": 71.5,
        "queueLength": 125,
        "stopRate": 0.50,
        "cycleTime": 105,
        "issues": [
            {
                "id": "signal_phase_imbalance",
                "name": "绿波协调断裂",
                "category": "signal_control",
                "severity": 0.72,
                "confidence": 0.87,
                "evidence": {"bandwidthLoss": "8s", "coordCycleMismatch": True},
                "reason": "与相邻泺源大街/南门大街路口周期不匹配，绿波带宽损失8s"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "周期对齐+绿波相位差修复", "score": 0.82}
        ],
        "before": {"saturation": 0.79, "delay": 71.5, "cycleTime": 105, "northGreen": 38, "eastGreen": 42},
        "after": {"saturation": 0.71, "delay": 52.8, "cycleTime": 100, "northGreen": 42, "eastGreen": 40},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 42, "splitRatio": 0.42, "saturation": 0.79},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.38, "saturation": 0.74},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 15, "splitRatio": 0.15, "saturation": 0.68}
        ]
    },
    # 14. 经十路/建设路 - warning
    {
        "id": "INT-JN-0714",
        "name": "经十路/建设路",
        "lat": 117.005,
        "lng": 36.648,
        "status": "warning",
        "saturation": 0.80,
        "delay": 76.2,
        "queueLength": 148,
        "stopRate": 0.56,
        "cycleTime": 115,
        "issues": [
            {
                "id": "dynamic_high_saturation",
                "name": "老城区交通交织·饱和度偏高",
                "category": "dynamic",
                "severity": 0.76,
                "confidence": 0.88,
                "evidence": {"saturation": 0.80, "intersectionComplexity": "高", "peakWindow": "07:30-09:00"},
                "reason": "建设路作为老城区南北联络线，与经十路主干流量交织导致路口持续高饱和运行"
            }
        ],
        "strategies": [
            {"templateId": "intersection_delay_relief", "level": "intersection", "description": "感应式配时+短周期优化", "score": 0.79}
        ],
        "before": {"saturation": 0.80, "delay": 76.2, "cycleTime": 115, "northGreen": 38, "eastGreen": 48},
        "after": {"saturation": 0.72, "delay": 55.8, "cycleTime": 100, "northGreen": 44, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "经十路直行", "direction": "E-W", "greenTime": 48, "splitRatio": 0.43, "saturation": 0.78},
            {"phaseId": "B", "phaseName": "建设路直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.34, "saturation": 0.82},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 18, "splitRatio": 0.16, "saturation": 0.71}
        ]
    },
    # 15. 奥体中路/解放东路 - optimized
    {
        "id": "INT-JN-0715",
        "name": "奥体中路/解放东路",
        "lat": 117.118,
        "lng": 36.660,
        "status": "optimized",
        "saturation": 0.67,
        "delay": 42.5,
        "queueLength": 68,
        "stopRate": 0.24,
        "cycleTime": 90,
        "issues": [],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "可变车道优化·晚高峰左转效率提升27.8%", "score": 0.91}
        ],
        "before": {"saturation": 0.82, "delay": 78.6, "cycleTime": 120, "northGreen": 38, "eastGreen": 48},
        "after": {"saturation": 0.67, "delay": 42.5, "cycleTime": 90, "northGreen": 42, "eastGreen": 36},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.49, "saturation": 0.67},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 36, "splitRatio": 0.42, "saturation": 0.64}
        ]
    },
    # 16. 世纪大道/凤歧路 - warning
    {
        "id": "INT-JN-0716",
        "name": "世纪大道/凤歧路",
        "lat": 117.183,
        "lng": 36.652,
        "status": "warning",
        "saturation": 0.83,
        "delay": 78.9,
        "queueLength": 155,
        "stopRate": 0.58,
        "cycleTime": 120,
        "issues": [
            {
                "id": "dynamic_demand_supply_imbalance",
                "name": "通勤潮汐方向性过载",
                "category": "dynamic",
                "severity": 0.78,
                "confidence": 0.90,
                "evidence": {"tidalRatio": 1.8, "amEastSaturation": 0.86, "westSaturation": 0.62},
                "reason": "早高峰东向（入高新区）饱和度0.86，西向仅0.62，方向性严重失衡"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "潮汐配时+方向性绿灯分配", "score": 0.85}
        ],
        "before": {"saturation": 0.83, "delay": 78.9, "cycleTime": 120, "northGreen": 38, "eastGreen": 50},
        "after": {"saturation": 0.73, "delay": 54.2, "cycleTime": 105, "northGreen": 40, "eastGreen": 48},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 50, "splitRatio": 0.43, "saturation": 0.83},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 38, "splitRatio": 0.33, "saturation": 0.72},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 20, "splitRatio": 0.17, "saturation": 0.76}
        ]
    },
    # 17. 轻风路/奥体西路 - optimized
    {
        "id": "INT-JN-0717",
        "name": "轻风路/奥体西路",
        "lat": 117.110,
        "lng": 36.658,
        "status": "optimized",
        "saturation": 0.65,
        "delay": 38.8,
        "queueLength": 55,
        "stopRate": 0.22,
        "cycleTime": 85,
        "issues": [],
        "strategies": [
            {"templateId": "intersection_delay_relief", "level": "intersection", "description": "潮汐车道拉链车优化·停车延误降40.5%", "score": 0.92}
        ],
        "before": {"saturation": 0.81, "delay": 72.4, "cycleTime": 115, "northGreen": 35, "eastGreen": 45},
        "after": {"saturation": 0.65, "delay": 38.8, "cycleTime": 85, "northGreen": 40, "eastGreen": 32},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 40, "splitRatio": 0.49, "saturation": 0.65},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 32, "splitRatio": 0.39, "saturation": 0.62}
        ]
    },
    # 18. 二环东路/旅游路 - optimizing
    {
        "id": "INT-JN-0718",
        "name": "二环东路/旅游路",
        "lat": 117.088,
        "lng": 36.635,
        "status": "optimizing",
        "saturation": 0.82,
        "delay": 76.5,
        "queueLength": 142,
        "stopRate": 0.58,
        "cycleTime": 115,
        "issues": [
            {
                "id": "dynamic_high_saturation",
                "name": "匝道交织·公交社会车互卡",
                "category": "dynamic",
                "severity": 0.78,
                "confidence": 0.89,
                "evidence": {"saturation": 0.82, "busConflict": True, "rampWeaving": True},
                "reason": "下桥匝道右侧社会车辆与公交车流交织互卡，新增80m专用右转车道正在实施中"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "新增专用右转车道+公交社会车分离", "score": 0.87}
        ],
        "before": {"saturation": 0.82, "delay": 76.5, "cycleTime": 115, "northGreen": 38, "eastGreen": 45},
        "after": {"saturation": 0.71, "delay": 52.8, "cycleTime": 100, "northGreen": 44, "eastGreen": 40},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "二环东路直行", "direction": "N-S", "greenTime": 45, "splitRatio": 0.41, "saturation": 0.82},
            {"phaseId": "B", "phaseName": "旅游路直行", "direction": "E-W", "greenTime": 38, "splitRatio": 0.35, "saturation": 0.78},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 20, "splitRatio": 0.18, "saturation": 0.71}
        ]
    },
    # 19. 舜华南路/舜泰北路 - warning
    {
        "id": "INT-JN-0719",
        "name": "舜华南路/舜泰北路",
        "lat": 117.155,
        "lng": 36.665,
        "status": "warning",
        "saturation": 0.78,
        "delay": 68.4,
        "queueLength": 120,
        "stopRate": 0.50,
        "cycleTime": 110,
        "issues": [
            {
                "id": "signal_phase_imbalance",
                "name": "直左车道功能冲突",
                "category": "signal_control",
                "severity": 0.73,
                "confidence": 0.87,
                "evidence": {"leftTurnBlocksDirect": True, "separatePhasing": True},
                "reason": "直行与左转分相位放行但车道设置为直左共用，直行放行时左转车辆阻碍后续直行通行"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "内侧车道改可变车道·早高峰左转/其余直行", "score": 0.84}
        ],
        "before": {"saturation": 0.78, "delay": 68.4, "cycleTime": 110, "northGreen": 40, "eastGreen": 42},
        "after": {"saturation": 0.69, "delay": 48.6, "cycleTime": 95, "northGreen": 44, "eastGreen": 38},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.40, "saturation": 0.78},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 40, "splitRatio": 0.38, "saturation": 0.72},
            {"phaseId": "C", "phaseName": "南北左转", "direction": "N-S left", "greenTime": 18, "splitRatio": 0.17, "saturation": 0.82}
        ]
    },
    # 20. 经十路/凤鸣路 - optimized (地铁开通后优化完成)
    {
        "id": "INT-JN-0720",
        "name": "经十路/凤鸣路",
        "lat": 117.148,
        "lng": 36.647,
        "status": "optimized",
        "saturation": 0.70,
        "delay": 46.2,
        "queueLength": 78,
        "stopRate": 0.28,
        "cycleTime": 95,
        "issues": [],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "地铁分流后绿信比重分配·北口排队缓解", "score": 0.90}
        ],
        "before": {"saturation": 0.85, "delay": 82.3, "cycleTime": 125, "northGreen": 32, "eastGreen": 52},
        "after": {"saturation": 0.70, "delay": 46.2, "cycleTime": 95, "northGreen": 42, "eastGreen": 38},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "经十路直行", "direction": "E-W", "greenTime": 38, "splitRatio": 0.42, "saturation": 0.68},
            {"phaseId": "B", "phaseName": "凤鸣路直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.46, "saturation": 0.70},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 8, "splitRatio": 0.09, "saturation": 0.55}
        ]
    },
    # 21. 党杨路/齐兴大街 - warning (潮汐)
    {
        "id": "INT-JN-0721",
        "name": "党杨路/齐兴大街",
        "lat": 116.920,
        "lng": 36.630,
        "status": "warning",
        "saturation": 0.81,
        "delay": 75.3,
        "queueLength": 205,
        "stopRate": 0.58,
        "cycleTime": 120,
        "issues": [
            {
                "id": "dynamic_demand_supply_imbalance",
                "name": "进出城潮汐·东西方向排队超200m",
                "category": "dynamic",
                "severity": 0.78,
                "confidence": 0.90,
                "evidence": {"ewQueueLength": 210, "southLeftQueue": 200, "tidalPattern": True},
                "reason": "连接槐荫区和长清区的重要节点，高峰期进出城通勤潮汐明显，东西方向排队超200m"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "南口直左可变车道+东西增加直行车道", "score": 0.83}
        ],
        "before": {"saturation": 0.81, "delay": 75.3, "cycleTime": 120, "northGreen": 36, "eastGreen": 48},
        "after": {"saturation": 0.72, "delay": 54.8, "cycleTime": 105, "northGreen": 42, "eastGreen": 45},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "东西直行", "direction": "E-W", "greenTime": 48, "splitRatio": 0.42, "saturation": 0.81},
            {"phaseId": "B", "phaseName": "南北直行", "direction": "N-S", "greenTime": 36, "splitRatio": 0.31, "saturation": 0.76},
            {"phaseId": "C", "phaseName": "南口左转", "direction": "S left", "greenTime": 22, "splitRatio": 0.19, "saturation": 0.85},
            {"phaseId": "D", "phaseName": "东西左转", "direction": "E-W left", "greenTime": 8, "splitRatio": 0.07, "saturation": 0.62}
        ]
    },
    # 22. 龙奥东路/龙奥北路 - optimized (可变车道优化完成)
    {
        "id": "INT-JN-0722",
        "name": "龙奥东路/龙奥北路",
        "lat": 117.140,
        "lng": 36.655,
        "status": "optimized",
        "saturation": 0.66,
        "delay": 40.5,
        "queueLength": 62,
        "stopRate": 0.22,
        "cycleTime": 90,
        "issues": [],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "可变车道·早晚高峰通行效率提升18.9%", "score": 0.91}
        ],
        "before": {"saturation": 0.83, "delay": 76.8, "cycleTime": 120, "northGreen": 35, "eastGreen": 48},
        "after": {"saturation": 0.66, "delay": 40.5, "cycleTime": 90, "northGreen": 42, "eastGreen": 35},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "南北直行", "direction": "N-S", "greenTime": 42, "splitRatio": 0.49, "saturation": 0.66},
            {"phaseId": "B", "phaseName": "东西直行", "direction": "E-W", "greenTime": 35, "splitRatio": 0.41, "saturation": 0.63}
        ]
    },
    # 23. 北园大街/历山路 - critical (下桥禁左)
    {
        "id": "INT-JN-0723",
        "name": "北园大街/历山路",
        "lat": 117.055,
        "lng": 36.695,
        "status": "critical",
        "saturation": 0.84,
        "delay": 88.6,
        "queueLength": 168,
        "stopRate": 0.68,
        "cycleTime": 125,
        "issues": [
            {
                "id": "signal_phase_imbalance",
                "name": "下桥车流与地面左转冲突",
                "category": "signal_control",
                "severity": 0.82,
                "confidence": 0.91,
                "evidence": {"rampLeftTurnConflict": True, "restrictionPeriod": "7:00-21:00"},
                "reason": "北园高架东向下桥口禁左时段（7:00-21:00）车辆绕行增加周边路口压力，禁左管控与通行需求矛盾"
            },
            {
                "id": "dynamic_high_delay",
                "name": "高架地面衔接延误",
                "category": "dynamic",
                "severity": 0.78,
                "confidence": 0.89,
                "evidence": {"avgDelay": 88.6, "rampInfluence": True},
                "reason": "北园高架与历山路地面路口衔接不畅，下桥车辆排队影响地面通行"
            }
        ],
        "strategies": [
            {"templateId": "intersection_phase_rebalance", "level": "intersection", "description": "车道功能优化+禁左时段动态调整", "score": 0.82},
            {"templateId": "intersection_bottleneck_anti_spillback", "level": "intersection", "description": "匝道排队管控+地面绿灯保护", "score": 0.78}
        ],
        "before": {"saturation": 0.84, "delay": 88.6, "cycleTime": 125, "northGreen": 34, "eastGreen": 52},
        "after": {"saturation": 0.74, "delay": 62.3, "cycleTime": 105, "northGreen": 44, "eastGreen": 42},
        "phaseInfo": [
            {"phaseId": "A", "phaseName": "北园大街直行", "direction": "E-W", "greenTime": 52, "splitRatio": 0.43, "saturation": 0.82},
            {"phaseId": "B", "phaseName": "历山路直行", "direction": "N-S", "greenTime": 34, "splitRatio": 0.28, "saturation": 0.86},
            {"phaseId": "C", "phaseName": "左转保护", "direction": "all left", "greenTime": 22, "splitRatio": 0.18, "saturation": 0.78},
            {"phaseId": "D", "phaseName": "匝道专用", "direction": "ramp", "greenTime": 10, "splitRatio": 0.08, "saturation": 0.72}
        ]
    }
]

# ── NEW AGENT RUNS ──────────────────────────────────────────────────────
new_runs = [
    {
        "runId": "RUN-20260326-004",
        "targetId": "INT-JN-0701",
        "targetName": "经十路/转山西路",
        "targetType": "intersection",
        "startTime": "2026-03-26 07:45:00",
        "endTime": "2026-03-26 07:58:00",
        "status": "completed",
        "meetsTarget": True,
        "phases": [
            {"phase": "scene_cognition", "duration": 25, "status": "ok", "summary": "路口饱和度0.90，西口左转/掉头排队220m超存储容量，万象城/博物馆吸引流量大"},
            {"phase": "problem_diagnosis", "duration": 22, "status": "ok", "summary": "主因：西口掉头左转通道设计不合理，CBD进出通道功能与主干线流量冲突"},
            {"phase": "control_strategy", "duration": 18, "status": "ok", "summary": "西口辅路禁左+提前调头口+海右路增加车道，释放路口空间"},
            {"phase": "plan_generation", "duration": 35, "status": "ok", "summary": "周期缩短至110s，南北绿时48s，西口左转削减重分配至直行"},
            {"phase": "evaluation_feedback", "duration": 22, "status": "ok", "summary": "饱和度降至0.76，延误降低37%，西口排队控制在140m以内"}
        ]
    },
    {
        "runId": "RUN-20260326-005",
        "targetId": "COR-ERHUANDONG",
        "targetName": "二环东路南北走廊",
        "targetType": "corridor",
        "startTime": "2026-03-26 08:02:00",
        "endTime": None,
        "status": "running",
        "meetsTarget": None,
        "phases": [
            {"phase": "scene_cognition", "duration": 42, "status": "ok", "summary": "二环东路快速路下桥交织严重，祝舜路路口排队210m超存储容量"},
            {"phase": "problem_diagnosis", "duration": 38, "status": "ok", "summary": "高架匝道信号缺失导致车流无序汇入，地面路口信号与匝道未协调"},
            {"phase": "control_strategy", "duration": None, "status": "running", "summary": None},
            {"phase": "plan_generation", "duration": None, "status": "pending", "summary": None},
            {"phase": "evaluation_feedback", "duration": None, "status": "pending", "summary": None}
        ]
    },
    {
        "runId": "RUN-20260326-006",
        "targetId": "INT-JN-0706",
        "targetName": "济齐路/黄岗路",
        "targetType": "intersection",
        "startTime": "2026-03-25 14:20:00",
        "endTime": "2026-03-25 14:42:00",
        "status": "completed",
        "meetsTarget": True,
        "phases": [
            {"phase": "scene_cognition", "duration": 30, "status": "ok", "summary": "五岔畸形路口，事故多发、交通秩序混乱，停止线偏远导致路口范围过大"},
            {"phase": "problem_diagnosis", "duration": 28, "status": "ok", "summary": "路口范围偏大+斑马线视距受阻+非机动车混行+信号周期过长"},
            {"phase": "control_strategy", "duration": 22, "status": "ok", "summary": "微改造方案：停止线前移32m+斑马线优化+非机动车专用灯+短周期配时"},
            {"phase": "plan_generation", "duration": 40, "status": "ok", "summary": "周期缩短至95s，4相位精细控制，非机动车一次过街"},
            {"phase": "evaluation_feedback", "duration": 25, "status": "ok", "summary": "通行效率提升12.7%，交通事故量下降80%，行人过街更安全顺畅"}
        ]
    },
    {
        "runId": "RUN-20260326-007",
        "targetId": "INT-JN-0704",
        "targetName": "九曲庄路/二环南路",
        "targetType": "intersection",
        "startTime": "2026-03-26 17:35:00",
        "endTime": None,
        "status": "running",
        "meetsTarget": None,
        "phases": [
            {"phase": "scene_cognition", "duration": 28, "status": "ok", "summary": "晚高峰匝道排队280m，车辆滞留回溢至高架主线，通行效率大幅降低"},
            {"phase": "problem_diagnosis", "duration": 25, "status": "ok", "summary": "匝道缺乏信号控制，主路与下桥车辆交织冲突严重"},
            {"phase": "control_strategy", "duration": 20, "status": "ok", "summary": "增设匝道信号灯，主路与下桥交替放行，减少交织冲突"},
            {"phase": "plan_generation", "duration": None, "status": "running", "summary": None},
            {"phase": "evaluation_feedback", "duration": None, "status": "pending", "summary": None}
        ]
    },
    {
        "runId": "RUN-20260326-008",
        "targetId": "RGN-TIANQIAO",
        "targetName": "天桥区北园商圈",
        "targetType": "region",
        "startTime": "2026-03-26 08:10:00",
        "endTime": None,
        "status": "running",
        "meetsTarget": None,
        "phases": [
            {"phase": "scene_cognition", "duration": 48, "status": "ok", "summary": "区域饱和度0.81，北园高架多匝道汇入导致地面路网持续高压"},
            {"phase": "problem_diagnosis", "duration": None, "status": "running", "summary": None},
            {"phase": "control_strategy", "duration": None, "status": "pending", "summary": None},
            {"phase": "plan_generation", "duration": None, "status": "pending", "summary": None},
            {"phase": "evaluation_feedback", "duration": None, "status": "pending", "summary": None}
        ]
    },
    {
        "runId": "RUN-20260326-009",
        "targetId": "COR-LUOYUAN",
        "targetName": "泺源大街东西走廊",
        "targetType": "corridor",
        "startTime": "2026-03-26 10:05:00",
        "endTime": "2026-03-26 10:28:00",
        "status": "completed",
        "meetsTarget": True,
        "phases": [
            {"phase": "scene_cognition", "duration": 32, "status": "ok", "summary": "南门大街路口左转溢流至上游泺文路，路口间距仅150m"},
            {"phase": "problem_diagnosis", "duration": 28, "status": "ok", "summary": "路口间距过短导致左转排队无存储空间，溢流回堵上游"},
            {"phase": "control_strategy", "duration": 22, "status": "ok", "summary": "可变车道+取消公交专用道+右转辅路化，动态调整车道功能"},
            {"phase": "plan_generation", "duration": 38, "status": "ok", "summary": "周期100s，可变车道随流量方向切换"},
            {"phase": "evaluation_feedback", "duration": 25, "status": "ok", "summary": "左转溢流消除，上游泺文路路口恢复正常运行"}
        ]
    },
    {
        "runId": "RUN-20260326-010",
        "targetId": "INT-JN-0720",
        "targetName": "经十路/凤鸣路",
        "targetType": "intersection",
        "startTime": "2026-03-26 09:15:00",
        "endTime": "2026-03-26 09:32:00",
        "status": "completed",
        "meetsTarget": True,
        "phases": [
            {"phase": "scene_cognition", "duration": 22, "status": "ok", "summary": "地铁4/6/8号线开通后经十路车流下降，原配时方案不匹配新流量结构"},
            {"phase": "problem_diagnosis", "duration": 18, "status": "ok", "summary": "经十路东段通行压力缓解，但绿信比仍按高流量配置，南北方向绿灯不足"},
            {"phase": "control_strategy", "duration": 15, "status": "ok", "summary": "优化绿信比，增加南北方向放行时间，缩短高峰信号方案运行时间"},
            {"phase": "plan_generation", "duration": 32, "status": "ok", "summary": "周期95s，北口绿时增至42s，高峰结束提前至9:00"},
            {"phase": "evaluation_feedback", "duration": 18, "status": "ok", "summary": "路口拥堵指数下降19.22%，南北方向排队明显缩短"}
        ]
    }
]

# ── NEW SCENARIOS ───────────────────────────────────────────────────────
new_scenarios = [
    {
        "id": "SCN-RAMP",
        "name": "高架匝道汇入拥堵",
        "description": "早晚高峰高架下桥匝道车流集中汇入地面路网，造成匝道排队和地面路口高饱和",
        "regions": ["RGN-TIANQIAO"],
        "corridors": ["COR-ERHUANDONG", "COR-BEIYUAN"],
        "intersections": ["INT-JN-0705", "INT-JN-0711", "INT-JN-0704"],
        "active": True
    },
    {
        "id": "SCN-METRO",
        "name": "地铁新线分流调整",
        "description": "地铁4/6/8号线开通后经十路地面车流结构性变化，需信号配时重新适配",
        "regions": ["RGN-GAOXIN"],
        "corridors": ["COR-SHIJIDA"],
        "intersections": ["INT-JN-0720", "INT-JN-0716"],
        "active": True
    },
    {
        "id": "SCN-HOLIDAY",
        "name": "节假日景区周边拥堵",
        "description": "周末及节假日明府城/千佛山等景区周边路口出行需求激增",
        "regions": [],
        "corridors": ["COR-LUOYUAN"],
        "intersections": ["INT-JN-0702", "INT-JN-0703"],
        "active": False
    },
    {
        "id": "SCN-TIDAL",
        "name": "高新区通勤潮汐",
        "description": "工作日IT产业园区通勤高峰，世纪大道/舜华路方向性流量严重失衡",
        "regions": ["RGN-GAOXIN"],
        "corridors": ["COR-SHIJIDA"],
        "intersections": ["INT-JN-0716", "INT-JN-0719", "INT-JN-0708"],
        "active": True
    }
]

# ── NEW POIs ────────────────────────────────────────────────────────────
new_pois = [
    {
        "id": "POI-MALL-02",
        "name": "济南万象城",
        "type": "mall",
        "location": [117.095, 36.652],
        "influenceRadius": 600,
        "linkedIntersectionIds": ["INT-JN-0701"],
        "peakWindows": ["10:00-21:00"],
        "peakDays": ["weekend"],
        "impact": "西口掉头/左转需求激增，海右路进出CBD车流大",
        "diagnosisMode": "periodic"
    },
    {
        "id": "POI-SCENIC-01",
        "name": "明府城历史文化街区",
        "type": "scenic",
        "location": [117.018, 36.668],
        "influenceRadius": 500,
        "linkedIntersectionIds": ["INT-JN-0702"],
        "peakWindows": ["09:00-21:00"],
        "peakDays": ["weekend", "holiday"],
        "impact": "节假日游客车辆大量进出，左转需求激增导致溢流",
        "diagnosisMode": "periodic"
    },
    {
        "id": "POI-HOSPITAL-02",
        "name": "千佛山医院",
        "type": "hospital",
        "location": [117.050, 36.650],
        "influenceRadius": 500,
        "linkedIntersectionIds": ["INT-JN-0703"],
        "peakWindows": ["07:30-11:30", "13:30-16:30"],
        "peakDays": ["weekday", "weekend"],
        "impact": "就医停靠车辆占道，经十路西→东瓶颈点",
        "diagnosisMode": "periodic"
    },
    {
        "id": "POI-MUSEUM-01",
        "name": "山东博物馆/山东美术馆",
        "type": "museum",
        "location": [117.100, 36.651],
        "influenceRadius": 500,
        "linkedIntersectionIds": ["INT-JN-0701"],
        "peakWindows": ["09:00-17:00"],
        "peakDays": ["weekend", "holiday"],
        "impact": "周末参观客流停车需求大，与CBD通勤流叠加",
        "diagnosisMode": "periodic"
    },
    {
        "id": "POI-PARK-01",
        "name": "济南软件园",
        "type": "office",
        "location": [117.158, 36.662],
        "influenceRadius": 800,
        "linkedIntersectionIds": ["INT-JN-0716", "INT-JN-0719"],
        "peakWindows": ["07:30-09:30", "17:30-19:30"],
        "peakDays": ["weekday"],
        "impact": "IT通勤潮汐显著，早高峰西→东入园方向拥堵",
        "diagnosisMode": "periodic"
    },
    {
        "id": "POI-LOGISTICS-01",
        "name": "北园物流集散区",
        "type": "logistics",
        "location": [117.040, 36.700],
        "influenceRadius": 600,
        "linkedIntersectionIds": ["INT-JN-0710"],
        "peakWindows": ["06:00-09:00", "16:00-19:00"],
        "peakDays": ["weekday"],
        "impact": "货运车辆占比高，与通勤车流混行降低路口效率",
        "diagnosisMode": "periodic"
    },
    {
        "id": "POI-METRO-01",
        "name": "地铁4/6/8号线沿线站点",
        "type": "transit_hub",
        "location": [117.145, 36.648],
        "influenceRadius": 1000,
        "linkedIntersectionIds": ["INT-JN-0720", "INT-JN-0707"],
        "peakWindows": ["07:00-09:00", "17:00-19:30"],
        "peakDays": ["weekday"],
        "impact": "地铁开通后地面车流减少，需配时方案同步调整",
        "diagnosisMode": "realtime"
    }
]

# ── NEW TOPOLOGY LINKS ─────────────────────────────────────────────────
new_topology = [
    {
        "id": "TOPO-006", "fromId": "RGN-TIANQIAO", "toId": "COR-BEIYUAN",
        "linkType": "region_to_corridor", "direction": "outbound",
        "capacity": 2000, "travelTime": 150, "role": "upstream_feeder",
        "description": "天桥区向北园大街走廊输送高架汇入流量"
    },
    {
        "id": "TOPO-007", "fromId": "COR-BEIYUAN", "toId": "INT-JN-0705",
        "linkType": "corridor_to_intersection", "direction": "west",
        "capacity": 1600, "travelTime": 25, "role": "bottleneck",
        "description": "北园大街走廊在济齐路路口形成车道瓶颈"
    },
    {
        "id": "TOPO-008", "fromId": "COR-ERHUANDONG", "toId": "INT-JN-0711",
        "linkType": "corridor_to_intersection", "direction": "south",
        "capacity": 1800, "travelTime": 30, "role": "bottleneck",
        "description": "二环东路走廊在祝舜路路口形成匝道溢流瓶颈"
    },
    {
        "id": "TOPO-009", "fromId": "RGN-GAOXIN", "toId": "COR-SHIJIDA",
        "linkType": "region_to_corridor", "direction": "outbound",
        "capacity": 2200, "travelTime": 120, "role": "upstream_feeder",
        "description": "高新区CBD向世纪大道走廊输送通勤流量"
    },
    {
        "id": "TOPO-010", "fromId": "COR-LUOYUAN", "toId": "INT-JN-0702",
        "linkType": "corridor_to_intersection", "direction": "east",
        "capacity": 1500, "travelTime": 20, "role": "bottleneck",
        "description": "泺源大街走廊在南门大街路口形成左转溢流瓶颈"
    },
    {
        "id": "TOPO-011", "fromId": "INT-JN-0706", "toId": "INT-JN-0705",
        "linkType": "intersection_to_intersection", "direction": "east",
        "capacity": 1400, "travelTime": 45, "role": "upstream",
        "description": "黄岗路五岔口优化后改善上游供给至济齐路路口"
    },
    {
        "id": "TOPO-012", "fromId": "COR-JINGSHI", "toId": "INT-JN-0701",
        "linkType": "corridor_to_intersection", "direction": "east",
        "capacity": 1900, "travelTime": 40, "role": "downstream",
        "description": "经十路走廊流量延伸至转山西路路口"
    },
    {
        "id": "TOPO-013", "fromId": "INT-JN-0703", "toId": "COR-JINGSHI",
        "linkType": "intersection_to_corridor", "direction": "east",
        "capacity": 1800, "travelTime": 35, "role": "intermediate",
        "description": "山师东路路口作为经十路走廊中间节点"
    },
    {
        "id": "TOPO-014", "fromId": "INT-JN-0704", "toId": "RGN-SHIZHONG",
        "linkType": "intersection_to_region", "direction": "north",
        "capacity": 1600, "travelTime": 90, "role": "demand_source",
        "description": "九曲庄路/二环南路匝道下桥车流涌向市中区方向"
    },
    {
        "id": "TOPO-015", "fromId": "INT-JN-0722", "toId": "INT-JN-0708",
        "linkType": "intersection_to_intersection", "direction": "west",
        "capacity": 1500, "travelTime": 35, "role": "downstream",
        "description": "龙奥东路/北路路口优化后改善流向凤天路的通行"
    }
]

# ── NEW PLANS ───────────────────────────────────────────────────────────
new_plans = [
    {
        "planId": "PLN-20260326-004",
        "targetId": "INT-JN-0701",
        "targetName": "经十路/转山西路",
        "targetType": "intersection",
        "strategyTemplateId": "intersection_phase_rebalance",
        "generatedAt": "2026-03-26 07:52:00",
        "status": "executed",
        "planParams": {
            "commonCycle": 110,
            "intersectionPlans": [{
                "interId": "INT-JN-0701", "name": "经十路/转山西路", "cycle": 110,
                "phases": [
                    {"id": "A", "name": "南北直行", "green": 48, "yellow": 3, "allRed": 2, "splitRatio": 0.45, "saturation": 0.76},
                    {"id": "B", "name": "东西直行", "green": 42, "yellow": 3, "allRed": 2, "splitRatio": 0.39, "saturation": 0.72},
                    {"id": "C", "name": "左转保护", "green": 10, "yellow": 3, "allRed": 2, "splitRatio": 0.09, "saturation": 0.58}
                ],
                "offset": None, "greenWaveBand": None
            }],
            "safetyChecks": [
                {"item": "最小行人绿灯≥30s", "pass": True, "value": "南北48s，东西42s"},
                {"item": "周期合理范围", "pass": True, "value": "110s"},
                {"item": "西口禁左措施", "pass": True, "value": "辅路禁左+提前调头口已设置"}
            ]
        },
        "estimatedGain": {
            "avgSpeedImprovement": "+15%",
            "delayReduction": "-37%",
            "stopRateReduction": "-28%"
        }
    },
    {
        "planId": "PLN-20260326-005",
        "targetId": "INT-JN-0706",
        "targetName": "济齐路/黄岗路",
        "targetType": "intersection",
        "strategyTemplateId": "intersection_phase_rebalance",
        "generatedAt": "2026-03-25 14:32:00",
        "status": "executed",
        "planParams": {
            "commonCycle": 95,
            "intersectionPlans": [{
                "interId": "INT-JN-0706", "name": "济齐路/黄岗路", "cycle": 95,
                "phases": [
                    {"id": "A", "name": "济齐路直行", "green": 35, "yellow": 3, "allRed": 2, "splitRatio": 0.38, "saturation": 0.68},
                    {"id": "B", "name": "黄岗路直行", "green": 28, "yellow": 3, "allRed": 2, "splitRatio": 0.30, "saturation": 0.65},
                    {"id": "C", "name": "兴学街放行", "green": 18, "yellow": 3, "allRed": 2, "splitRatio": 0.19, "saturation": 0.58},
                    {"id": "D", "name": "非机动车过街", "green": 10, "yellow": 2, "allRed": 1, "splitRatio": 0.11, "saturation": 0.42}
                ],
                "offset": None, "greenWaveBand": None
            }],
            "safetyChecks": [
                {"item": "停止线前移检验", "pass": True, "value": "济齐路前移32m，黄岗路前移34m"},
                {"item": "非机动车过街安全", "pass": True, "value": "专用信号灯+一次过街标线"},
                {"item": "行人视距安全", "pass": True, "value": "北口斑马线取消+护栏引导"}
            ]
        },
        "estimatedGain": {
            "avgSpeedImprovement": "+12.7%",
            "delayReduction": "-52%",
            "stopRateReduction": "-45%",
            "accidentReduction": "-80%"
        }
    },
    {
        "planId": "PLN-20260326-006",
        "targetId": "COR-LUOYUAN",
        "targetName": "泺源大街东西走廊",
        "targetType": "corridor",
        "strategyTemplateId": "intersection_bottleneck_anti_spillback",
        "generatedAt": "2026-03-26 10:18:00",
        "status": "executed",
        "planParams": {
            "commonCycle": 100,
            "intersectionPlans": [
                {
                    "interId": "INT-JN-0702", "name": "泺源大街/南门大街", "cycle": 100,
                    "phases": [
                        {"id": "A", "name": "南北直行", "green": 46, "yellow": 3, "allRed": 2, "splitRatio": 0.46, "saturation": 0.74},
                        {"id": "B", "name": "东西直行", "green": 38, "yellow": 3, "allRed": 2, "splitRatio": 0.38, "saturation": 0.71},
                        {"id": "C", "name": "左转保护", "green": 8, "yellow": 3, "allRed": 2, "splitRatio": 0.08, "saturation": 0.62}
                    ],
                    "offset": 0, "greenWaveBand": 22
                },
                {
                    "interId": "INT-JN-0713", "name": "泺源大街/南新街", "cycle": 100,
                    "phases": [
                        {"id": "A", "name": "东西直行", "green": 42, "yellow": 3, "allRed": 2, "splitRatio": 0.42, "saturation": 0.71},
                        {"id": "B", "name": "南北直行", "green": 40, "yellow": 3, "allRed": 2, "splitRatio": 0.40, "saturation": 0.68}
                    ],
                    "offset": 15, "greenWaveBand": 24
                }
            ],
            "safetyChecks": [
                {"item": "可变车道安全", "pass": True, "value": "信号指示+标志标线完备"},
                {"item": "上游溢流防护", "pass": True, "value": "泺文路路口协同截流启用"},
                {"item": "公交影响评估", "pass": True, "value": "公交专用道取消后改走辅路，线路已调整"}
            ]
        },
        "estimatedGain": {
            "avgSpeedImprovement": "+35%",
            "delayReduction": "-35%",
            "stopRateReduction": "-34%"
        }
    }
]

# ── NEW EVALUATIONS ────────────────────────────────────────────────────
new_evaluations = [
    {
        "evalId": "EVAL-20260326-003",
        "runId": "RUN-20260326-004",
        "planId": "PLN-20260326-004",
        "targetId": "INT-JN-0701",
        "targetName": "经十路/转山西路",
        "targetType": "intersection",
        "evaluatedAt": "2026-03-26 08:15:00",
        "windowMinutes": 20,
        "meetsTarget": True,
        "overallScore": 0.89,
        "metrics": {
            "before": {"stopRate": 0.78, "avgDelay": 108.5, "saturation": 0.90},
            "after": {"stopRate": 0.52, "avgDelay": 68.2, "saturation": 0.76},
            "target": {"stopRate": 0.55, "avgDelay": 75.0, "saturation": 0.80}
        },
        "improvements": [
            {"metric": "平均延误", "unit": "s", "before": 108.5, "after": 68.2, "target": 75.0, "delta": -40.3, "deltaPercent": -37.1, "meetsTarget": True},
            {"metric": "饱和度", "unit": "", "before": 0.90, "after": 0.76, "target": 0.80, "delta": -0.14, "deltaPercent": -15.6, "meetsTarget": True}
        ],
        "sideEffects": [{"description": "海右路方向延误增加+6s", "severity": "low", "acceptable": True}],
        "conclusion": "达标",
        "recommendation": "西口禁左方案效果显著，建议同类CBD路口推广",
        "experienceWorthy": True
    },
    {
        "evalId": "EVAL-20260326-004",
        "runId": "RUN-20260326-006",
        "planId": "PLN-20260326-005",
        "targetId": "INT-JN-0706",
        "targetName": "济齐路/黄岗路",
        "targetType": "intersection",
        "evaluatedAt": "2026-03-25 15:10:00",
        "windowMinutes": 30,
        "meetsTarget": True,
        "overallScore": 0.94,
        "metrics": {
            "before": {"stopRate": 0.65, "avgDelay": 92.8, "saturation": 0.85},
            "after": {"stopRate": 0.28, "avgDelay": 44.2, "saturation": 0.68},
            "target": {"stopRate": 0.35, "avgDelay": 55.0, "saturation": 0.75}
        },
        "improvements": [
            {"metric": "通行效率", "unit": "%", "before": 0, "after": 12.7, "target": 10, "delta": 12.7, "deltaPercent": 12.7, "meetsTarget": True},
            {"metric": "事故量", "unit": "件/月", "before": 15, "after": 3, "target": 5, "delta": -12, "deltaPercent": -80.0, "meetsTarget": True},
            {"metric": "平均延误", "unit": "s", "before": 92.8, "after": 44.2, "target": 55.0, "delta": -48.6, "deltaPercent": -52.4, "meetsTarget": True}
        ],
        "sideEffects": [],
        "conclusion": "达标（优秀）",
        "recommendation": "微改造方案效果显著，通行效率+12.7%，事故-80%，可作为五岔口治理标杆案例",
        "experienceWorthy": True
    },
    {
        "evalId": "EVAL-20260326-005",
        "runId": "RUN-20260326-009",
        "planId": "PLN-20260326-006",
        "targetId": "COR-LUOYUAN",
        "targetName": "泺源大街东西走廊",
        "targetType": "corridor",
        "evaluatedAt": "2026-03-26 10:55:00",
        "windowMinutes": 25,
        "meetsTarget": True,
        "overallScore": 0.86,
        "metrics": {
            "before": {"avgSpeed": 24.6, "stopRate": 0.52, "avgDelay": 72.3, "saturation": 0.84},
            "after": {"avgSpeed": 33.2, "stopRate": 0.34, "avgDelay": 46.8, "saturation": 0.74},
            "target": {"avgSpeed": 30.0, "stopRate": 0.38, "avgDelay": 50.0, "saturation": 0.78}
        },
        "improvements": [
            {"metric": "平均车速", "unit": "km/h", "before": 24.6, "after": 33.2, "target": 30.0, "delta": 8.6, "deltaPercent": 35.0, "meetsTarget": True},
            {"metric": "平均延误", "unit": "s", "before": 72.3, "after": 46.8, "target": 50.0, "delta": -25.5, "deltaPercent": -35.3, "meetsTarget": True}
        ],
        "sideEffects": [{"description": "公交专用道取消后公交延误增加约30s", "severity": "medium", "acceptable": True}],
        "conclusion": "达标",
        "recommendation": "可变车道方案有效消除溢流，但需持续关注公交延误影响",
        "experienceWorthy": True
    },
    {
        "evalId": "EVAL-20260326-006",
        "runId": "RUN-20260326-010",
        "planId": None,
        "targetId": "INT-JN-0720",
        "targetName": "经十路/凤鸣路",
        "targetType": "intersection",
        "evaluatedAt": "2026-03-26 09:50:00",
        "windowMinutes": 20,
        "meetsTarget": True,
        "overallScore": 0.92,
        "metrics": {
            "before": {"stopRate": 0.62, "avgDelay": 82.3, "saturation": 0.85},
            "after": {"stopRate": 0.28, "avgDelay": 46.2, "saturation": 0.70},
            "target": {"stopRate": 0.35, "avgDelay": 55.0, "saturation": 0.75}
        },
        "improvements": [
            {"metric": "拥堵指数", "unit": "", "before": 4.2, "after": 3.4, "target": 3.6, "delta": -0.8, "deltaPercent": -19.22, "meetsTarget": True},
            {"metric": "平均延误", "unit": "s", "before": 82.3, "after": 46.2, "target": 55.0, "delta": -36.1, "deltaPercent": -43.9, "meetsTarget": True}
        ],
        "sideEffects": [],
        "conclusion": "达标",
        "recommendation": "地铁分流效应显著，建议其他地铁沿线路口同步调整",
        "experienceWorthy": True
    }
]

# ── NEW HUMAN INTERVENTIONS ────────────────────────────────────────────
new_interventions = [
    {
        "id": "HI-20260326-005",
        "time": "2026-03-26 07:55:00",
        "operator": "赵工程师",
        "operatorRole": "操作员",
        "targetId": "INT-JN-0705",
        "targetName": "无影山中路/济齐路",
        "targetType": "intersection",
        "action": "参数微调",
        "level": "intersection",
        "reason": "AI建议取消BRT专用道改直行，但需保留早高峰BRT快速公交最低保障通行窗口",
        "params": {
            "before": {"brtLaneStatus": "exclusive"},
            "after": {"brtLaneStatus": "shared_peak", "brtProtectedWindow": "07:15-07:45"},
            "note": "保留BRT高峰前段独占窗口，07:45后切换共享模式"
        },
        "aiSuggestion": "同意折中方案，可兼顾BRT运营需求和社会车辆通行，建议评估BRT延误变化",
        "status": "approved",
        "effectMetrics": None,
        "experience": {"saved": True, "tag": "BRT专用道动态共享", "scene": "高架汇入+BRT冲突路口"}
    },
    {
        "id": "HI-20260326-006",
        "time": "2026-03-26 08:25:00",
        "operator": "张主管",
        "operatorRole": "主管",
        "targetId": "COR-ERHUANDONG",
        "targetName": "二环东路南北走廊",
        "action": "审批通过",
        "level": "corridor",
        "reason": "二环东路匝道信号控制方案涉及快速路安全，需主管审批",
        "params": {
            "strategy": "corridor_green_wave_rebuild",
            "rampSignalEnabled": True,
            "safetyNote": "已核实匝道信号与高架主线监控联动"
        },
        "aiSuggestion": "匝道信号控制方案风险等级：中高。主要影响：高架主线排队可能增加约100m，需确保高架主线监控联动正常",
        "status": "approved",
        "effectMetrics": None,
        "experience": {"saved": False, "tag": None, "scene": None}
    }
]

# ── UPDATE OVERVIEW STATS ───────────────────────────────────────────────
data["cityOverview"]["stats"]["totalIntersections"] = 1248
data["cityOverview"]["stats"]["monitoredIntersections"] = 986
data["cityOverview"]["stats"]["abnormalIntersections"] = 45
data["cityOverview"]["stats"]["abnormalCorridors"] = 8
data["cityOverview"]["stats"]["abnormalRegions"] = 4
data["cityOverview"]["stats"]["optimizingObjects"] = 26
data["cityOverview"]["stats"]["todayOptimizations"] = 186

data["cityOverview"]["topIssues"] = [
    {"type": "region", "id": "RGN-LIXIA", "name": "历下区核心区", "issue": "高饱和拥堵扩散", "severity": 0.91},
    {"type": "corridor", "id": "COR-ERHUANDONG", "name": "二环东路南北走廊", "issue": "高架匝道溢流·连续排队", "severity": 0.86},
    {"type": "corridor", "id": "COR-JINGSHI", "name": "经十路东西走廊", "issue": "绿波断裂·连续停车", "severity": 0.85},
    {"type": "intersection", "id": "INT-JN-0705", "name": "无影山中路/济齐路", "issue": "车道瓶颈·排队520m", "severity": 0.92},
    {"type": "intersection", "id": "INT-JN-0704", "name": "九曲庄路/二环南路", "issue": "匝道滞留·高架回溢", "severity": 0.91},
    {"type": "intersection", "id": "INT-JN-0701", "name": "经十路/转山西路", "issue": "CBD左转溢流", "severity": 0.89},
    {"type": "intersection", "id": "INT-JN-0281", "name": "经十路/舜耕路", "issue": "相位失衡·溢流", "severity": 0.88}
]

data["cityOverview"]["topImprovements"] = [
    {"type": "intersection", "id": "INT-JN-0706", "name": "济齐路/黄岗路", "metric": "通行效率+事故降低", "delta": "+12.7%效率 -80%事故", "after": "五岔口微改造标杆"},
    {"type": "intersection", "id": "INT-JN-0720", "name": "经十路/凤鸣路", "metric": "拥堵指数", "delta": "-19.22%", "after": "地铁分流后信号适配"},
    {"type": "corridor", "id": "COR-JIEFANG", "name": "解放路绿波", "metric": "车速提升", "delta": "+58.5%", "after": "38.2km/h"},
    {"type": "intersection", "id": "INT-JN-0717", "name": "轻风路/奥体西路", "metric": "停车延误", "delta": "-40.5%", "after": "潮汐车道优化"},
    {"type": "intersection", "id": "INT-JN-0715", "name": "奥体中路/解放东路", "metric": "左转效率", "delta": "+27.8%", "after": "可变车道优化"},
    {"type": "intersection", "id": "INT-JN-0104", "name": "泺源大街/趵突泉路", "metric": "延误降低", "delta": "-31%", "after": "42s"},
    {"type": "region", "id": "RGN-SHIZHONG", "name": "市中区高吸引区", "metric": "拥堵指数", "delta": "-0.8", "after": "3.1"}
]

# ── MERGE ALL DATA ──────────────────────────────────────────────────────
data["regions"].extend(new_regions)
data["corridors"].extend(new_corridors)
data["intersections"].extend(new_intersections)
data["agentRuns"].extend(new_runs)
data["humanInterventions"].extend(new_interventions)
data["scenarios"].extend(new_scenarios)
data["pois"].extend(new_pois)
data["topologyLinks"].extend(new_topology)
data["plans"].extend(new_plans)
data["evaluations"].extend(new_evaluations)

# ── WRITE OUTPUT ────────────────────────────────────────────────────────
with open(DST, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Summary
print("=== 数据扩展完成 ===")
print(f"区域(regions): {len(data['regions'])} (新增 {len(new_regions)})")
print(f"走廊(corridors): {len(data['corridors'])} (新增 {len(new_corridors)})")
print(f"路口(intersections): {len(data['intersections'])} (新增 {len(new_intersections)})")
print(f"智能体运行(agentRuns): {len(data['agentRuns'])} (新增 {len(new_runs)})")
print(f"人机干预(humanInterventions): {len(data['humanInterventions'])} (新增 {len(new_interventions)})")
print(f"场景(scenarios): {len(data['scenarios'])} (新增 {len(new_scenarios)})")
print(f"POI: {len(data['pois'])} (新增 {len(new_pois)})")
print(f"拓扑链接(topologyLinks): {len(data['topologyLinks'])} (新增 {len(new_topology)})")
print(f"方案(plans): {len(data['plans'])} (新增 {len(new_plans)})")
print(f"评价(evaluations): {len(data['evaluations'])} (新增 {len(new_evaluations)})")

# Status distribution
statuses = {}
for inter in data["intersections"]:
    s = inter["status"]
    statuses[s] = statuses.get(s, 0) + 1
print(f"\n路口状态分布: {statuses}")

cor_statuses = {}
for c in data["corridors"]:
    s = c["status"]
    cor_statuses[s] = cor_statuses.get(s, 0) + 1
print(f"走廊状态分布: {cor_statuses}")

rgn_statuses = {}
for r in data["regions"]:
    s = r["status"]
    rgn_statuses[s] = rgn_statuses.get(s, 0) + 1
print(f"区域状态分布: {rgn_statuses}")
