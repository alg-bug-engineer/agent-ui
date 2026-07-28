"""问题诊断标准问题码表（供 MCP 与问题诊断 agent 对齐输出契约）."""

# 说明：
# - category: static | dynamic | signal_control
# - default_scope: 问题最典型/最细粒度的诊断对象层级（region | corridor | intersection）
# - allowed_scopes: 该问题在方法论框架内可以合法出现的对象层级列表
#   * static_road_network_sparse / static_parking_supply_gap 属于区域静态短板，仅在区域层有意义
#   * dynamic_high_saturation 在方法论中分别有区域饱和度、路段饱和度、路口饱和度三层评估，三级均合法
#   * dynamic_low_speed 主要描述走廊通行效率，路口也有局部速度概念
#   * dynamic_high_delay 方法论在走廊（停车次数/延误）和路口（单点延误）两层均有定义
#   * dynamic_demand_supply_imbalance 区域层（进出流量失衡）和走廊层（潮汐方向性失衡）均合法
#   * signal_queue_overflow 路口是根源，走廊内多个路口溢流传导可在走廊层描述
#   * signal_phase_imbalance 路口是根源，走廊协调失配可在走廊层描述
# - tags: 用于下游策略匹配与统计聚合

ISSUE_CODEBOOK: dict[str, dict] = {
    # ---------- static ----------
    "static_road_network_sparse": {
        "name": "路网密度不足",
        "category": "static",
        "default_scope": "region",
        "allowed_scopes": ["region"],
        "tags": ["road_network", "capacity"],
    },
    "static_channelization_mismatch": {
        "name": "渠化设计与需求不匹配",
        "category": "static",
        "default_scope": "intersection",
        "allowed_scopes": ["intersection"],
        "tags": ["channelization", "lane_function"],
    },
    "static_parking_supply_gap": {
        "name": "停车供给缺口",
        "category": "static",
        "default_scope": "region",
        "allowed_scopes": ["region"],
        "tags": ["parking", "induced_traffic"],
    },
    # ---------- dynamic ----------
    "dynamic_high_saturation": {
        "name": "高饱和运行",
        "category": "dynamic",
        # 方法论在区域/走廊/路口三层均有饱和度评估，default 取最细粒度的路口层
        "default_scope": "intersection",
        "allowed_scopes": ["region", "corridor", "intersection"],
        "tags": ["saturation", "congestion"],
    },
    "dynamic_low_speed": {
        "name": "平均车速偏低",
        "category": "dynamic",
        "default_scope": "corridor",
        "allowed_scopes": ["corridor", "intersection"],
        "tags": ["speed", "efficiency"],
    },
    "dynamic_high_delay": {
        "name": "延误时间过高",
        "category": "dynamic",
        "default_scope": "intersection",
        # 方法论对区域/走廊/路口均有平均延误指标，三层均合法
        "allowed_scopes": ["region", "corridor", "intersection"],
        "tags": ["delay", "efficiency"],
    },
    "dynamic_demand_supply_imbalance": {
        "name": "供需失衡",
        "category": "dynamic",
        "default_scope": "region",
        # 走廊层的潮汐方向性供需失衡同样合法（方法论潮汐走廊协调场景）
        "allowed_scopes": ["region", "corridor"],
        "tags": ["demand", "supply", "imbalance"],
    },
    # ---------- signal_control ----------
    "signal_queue_overflow": {
        "name": "排队溢流",
        "category": "signal_control",
        "default_scope": "intersection",
        # 走廊内瓶颈路口溢流传导形成走廊级问题，走廊层合法
        "allowed_scopes": ["corridor", "intersection"],
        "tags": ["queue", "spillback", "risk_lock"],
    },
    "signal_green_waste": {
        "name": "绿灯空放/利用率低",
        "category": "signal_control",
        "default_scope": "intersection",
        "allowed_scopes": ["intersection"],
        "tags": ["green_utilization", "timing"],
    },
    "signal_phase_imbalance": {
        "name": "相位失衡",
        "category": "signal_control",
        "default_scope": "intersection",
        # 走廊协调方向与主流方向不匹配的配时失配可在走廊层描述
        "allowed_scopes": ["corridor", "intersection"],
        "tags": ["phase", "green_split"],
    },
}

