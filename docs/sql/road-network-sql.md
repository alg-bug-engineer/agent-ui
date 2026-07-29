# RoadNetworkMap SQL 文档

> 对应 Controller：`RoadNetworkMapController`
> 对应 Service：`RoadNetworkMapServiceImpl`
> 对应 Mapper：`RoadNetworkMapMapper` / `RoadNetworkMapSql`
>
> 默认参数：`version_id = '20260501'`，`constraints` / `tfcunitId` 不参与过滤

---

## 1. inters — 路口列表（含车道设备覆盖率 & 转向覆盖率）

**接口**：`GET /api/road-network/inters`

**业务逻辑**：查询路口基础信息，并计算每个路口的两项覆盖率指标：
- **车道设备覆盖率** = 有设备绑定的进口道数 / 进口道总数
- **转向覆盖率** = 有设备覆盖的转向类型数 / 3（左转、直行、右转）

```sql
-- 归一化设备类型码（01:卡口, 02:电警, 03:雷视一体机, 04:信号机,
--                  05:视频检测器电警, 06:视频检测器匝道, 07:边缘盒子, 08:地磁）
-- 传 NULL 表示不过滤设备类型；传 '01,02' 等逗号分隔值按类型过滤

WITH params AS (
    -- 查询参数（在此修改设备类型，NULL 表示不过滤）
    SELECT '01'::text AS device_type_nos  -- ← 在这里修改设备类型
),

-- ① 取所有路口的进口道车道（link_role='entrance' 表示进口方向）
entrance_lanes AS (
    SELECT inter_id,        -- 路口 ID
           lane_id,         -- 车道 ID
           lane_func_code,  -- 车道功能码（如 'ABC'，每个字符代表一种转向功能）
           version_id       -- 数据版本
    FROM road9.dwd_tfc_rltn_wide_inter_ft_lane  -- 路口-车道关系宽表
    WHERE link_role = 'entrance'                -- 仅取进口道
      AND version_id = '20260501'
),

-- ② 取当前有效的、且符合设备类型筛选的车道集合
device_lanes AS (
    SELECT DISTINCT dl.lane_id  -- 去重：一条车道可能绑了多个设备
    FROM road9.dwd_tfc_rltn_devc_lane dl        -- 设备-车道关系表
    WHERE dl.valid_end_time > now()              -- 设备绑定仍在有效期内
      AND (
          -- 如果未指定设备类型则不过滤
          (SELECT device_type_nos FROM params) IS NULL
          OR EXISTS (
              -- 校验该车道上绑定的设备是否属于指定的设备类型
              SELECT 1
              FROM road9.dim_device_info d       -- 设备维表
              WHERE d.device_id = dl.device_id
                AND d.version_id = '20260501'
                -- 设备类型编号补齐为两位（如 '1' → '01'），与逗号分隔的筛选值做匹配
                AND lpad(trim(both FROM COALESCE(d.device_type_no, '')), 2, '0')
                    = ANY(string_to_array((SELECT device_type_nos FROM params), ','))
          )
      )
),

-- ③ 进口道 LEFT JOIN 设备车道，标记每条进口道是否有设备覆盖
entrance_with_device AS (
    SELECT el.inter_id,
           el.lane_id,
           el.lane_func_code,
           el.version_id,
           CASE WHEN dl.lane_id IS NOT NULL THEN 1 ELSE 0 END AS has_device  -- 1=有设备, 0=无设备
    FROM entrance_lanes el
    LEFT JOIN device_lanes dl ON el.lane_id = dl.lane_id
),

-- ④ 按路口聚合，计算车道设备覆盖率
lane_coverage AS (
    SELECT inter_id,
           version_id,
           COUNT(lane_id)                                                  AS total_lane_cnt,   -- 进口道总数
           SUM(has_device)                                                 AS device_lane_cnt,   -- 有设备的进口道数
           ROUND(SUM(has_device)::numeric / NULLIF(COUNT(lane_id), 0), 4) AS lane_device_coverage_rate  -- 覆盖率 = 有设备数/总数
    FROM entrance_with_device
    GROUP BY inter_id, version_id
),

-- ⑤ 将车道功能码拆成单个字符（如 'ABC' → 'A','B','C'），每个字符代表一种转向功能
lane_func_explode AS (
    SELECT inter_id, lane_id, version_id, has_device,
           func_char  -- 单个功能码字符
    FROM entrance_with_device
    CROSS JOIN LATERAL regexp_split_to_table(lane_func_code, '') AS func_char
    WHERE lane_func_code IS NOT NULL
),

-- ⑥ 将功能码字符映射为转向类型
--    A/B = 左转(left), C = 直行(straight), D/E = 右转(right)
lane_turn_map AS (
    SELECT inter_id, lane_id, version_id, has_device,
           CASE
               WHEN func_char IN ('A', 'B') THEN 'left'      -- A:左转, B:左转弯待转
               WHEN func_char = 'C'          THEN 'straight'  -- C:直行
               WHEN func_char IN ('D', 'E')  THEN 'right'     -- D:右转, E:右转弯待转
               ELSE NULL
           END AS turn_type
    FROM lane_func_explode
),

-- ⑦ 按路口+转向类型聚合：只要该转向下有任意一条车道覆盖了设备，就算该转向被覆盖
inter_turn_coverage AS (
    SELECT inter_id,
           version_id,
           turn_type,
           MAX(has_device) AS is_covered  -- 1=该转向已覆盖, 0=未覆盖
    FROM lane_turn_map
    WHERE turn_type IS NOT NULL
    GROUP BY inter_id, version_id, turn_type
),

-- ⑧ 按路口聚合转向覆盖率（满分 3 = 左转+直行+右转全部覆盖）
turn_coverage AS (
    SELECT inter_id,
           version_id,
           SUM(is_covered)                                   AS covered_turn_cnt,   -- 已覆盖的转向类型数
           ROUND(SUM(is_covered)::numeric / 3, 4)           AS turn_coverage_rate   -- 转向覆盖率 = 已覆盖数/3
    FROM inter_turn_coverage
    GROUP BY inter_id, version_id
)

-- ⑨ 最终输出：路口基础信息 + 车道覆盖率 + 转向覆盖率
SELECT i.inter_id,                -- 路口 ID
       i.inter_name,              -- 路口名称
       i.inter_alias1,            -- 路口别名
       i.inter_type,              -- 路口类型
       i.inter_proto,             -- 路口协议类型
       i.is_signalized,           -- 是否信号灯控制（1=是, 0=否）
       i.entr_cnt,                -- 进口道数量
       i.geom_center,             -- 路口中心点几何坐标
       i.version_id,              -- 数据版本
       COALESCE(lc.total_lane_cnt, 0)                AS total_lane_cnt,             -- 进口道总数（无车道时为 0）
       COALESCE(lc.device_lane_cnt, 0)               AS device_lane_cnt,            -- 有设备覆盖的进口道数
       COALESCE(lc.lane_device_coverage_rate, 0)     AS lane_device_coverage_rate,  -- 车道设备覆盖率
       COALESCE(tc.covered_turn_cnt, 0)              AS covered_turn_cnt,           -- 已覆盖的转向类型数
       COALESCE(tc.turn_coverage_rate, 0)            AS turn_coverage_rate          -- 转向覆盖率
FROM road9.dim_inter_info i      -- 路口维表（路口基础信息主表）
LEFT JOIN lane_coverage lc
       ON i.inter_id = lc.inter_id AND i.version_id = lc.version_id
LEFT JOIN turn_coverage tc
       ON i.inter_id = tc.inter_id AND i.version_id = tc.version_id
WHERE i.version_id = '20260501'
ORDER BY i.inter_id;
```

---

## 2. devices — 设备列表

**接口**：`GET /api/road-network/devices`

> **注意**：`screenshot_urls`（截图地址列表）不是来自 SQL，而是由 Service 层通过 `DeviceScreenshotService` 按 `original_device_id` 查询后填充。

```sql
SELECT t1.device_id,             -- 设备 ID
       t1.device_name,           -- 设备名称
       t1.device_type_no,        -- 设备类型编号（01~08，见上方类型码说明）
       t1.vendor_code,           -- 厂商编码
       t1.ip_addr,               -- IP 地址
       t1.mac_addr,              -- MAC 地址
       t1.geom_install,          -- 设备安装位置几何坐标
       t1.screenshot_url,        -- 截图基础 URL（完整列表由 Service 层补充）
       t1.asset_status,          -- 资产状态
       t1.source_refs,           -- 数据来源引用
       t1.version_id,            -- 数据版本
       t1.lanes,                 -- 关联车道信息
       t1.original_device_id,    -- 原始设备 ID（用于关联截图文件）
       -- 绑定状态：1=已绑定（设备已关联到车道），其他=未绑定
       CASE WHEN t1.is_bind = 1 THEN '已绑定' ELSE '未绑定' END AS is_bind,
       t1.reason,                -- 未绑定/异常原因描述
       -- 原因标记：根据 reason 文本前缀自动分类
       CASE
           WHEN t1.reason LIKE '车道数不足%'   THEN 1  -- 车道数不足，无法完成绑定
           WHEN t1.reason LIKE '周边%'         THEN 2  -- 周边无匹配路口
           WHEN t1.reason LIKE '方向不匹配%'   THEN 3  -- 设备方向与路口进口方向不一致
           ELSE 0                                      -- 其他/无异常
       END AS reason_flag
FROM road9.dim_device_info t1   -- 设备维表（设备基础信息主表）
WHERE t1.version_id = '20260501'
ORDER BY t1.device_id;
```

---

## 涉及的表清单

| 表名 | 用途 |
|---|---|
| `road9.dim_inter_info` | 路口维表，路口基础信息 |
| `road9.dim_device_info` | 设备维表，设备基础信息 |
| `road9.dwd_tfc_rltn_wide_inter_ft_lane` | 路口-车道关系宽表（`link_role='entrance'` 取进口道） |
| `road9.dwd_tfc_rltn_devc_lane` | 设备-车道关系表（`valid_end_time > now()` 取有效设备） |
