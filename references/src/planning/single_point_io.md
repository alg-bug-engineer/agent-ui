# `single_point.py` 输入输出规范

本文档描述单路口优化算法的输入输出结构。

当前文档与以下实现保持一致：

- `src/planning/single_point.py`
- `src/api/main.py`
- `src/support/mcp_tools.py`
- `static/timing-optimizer.html`

依赖要求：运行环境需可导入 `scipy`，求解器使用 `scipy.optimize.minimize(method="SLSQP")`。

---

## 1. 设计原则

单路口优化输入按以下原则规范化：

1. 参数命名优先参照外部平台结构，核心字段采用 `phasePlanOfTimeList`、`phaseStageInfoList`、`phaseDirInfoDTOList`、`dir8No`、`turnDirNo`。
2. 流量挂载在“转向流量”层级。
3. 转向流量支持两种表达形式：
  - 转向总流量 `turnFlowTotal` + 车道数 `laneCount`
  - 转向关键车道流量 `criticalLaneFlow`
4. 求解前统一折算为车道级流量；如果同时提供两种表达，优先使用 `criticalLaneFlow`。
5. 输出结果统一采用规范化结果字段，不再保留旧版相位输出结构。

---

## 2. 方向与转向编码

### 2.1 `dir8No`

`dir8No` 按 8 个方向顺时针编号：


| 编号  | 方向  |
| --- | --- |
| `1` | 北   |
| `2` | 东北  |
| `3` | 东   |
| `4` | 东南  |
| `5` | 南   |
| `6` | 西南  |
| `7` | 西   |
| `8` | 西北  |


### 2.2 `turnDirNo`

`turnDirNo` 表示车流转向：


| 编号  | 转向  |
| --- | --- |
| `0` | 掉头  |
| `1` | 左转  |
| `2` | 直行  |
| `3` | 右转  |


---

## 3. 推荐请求结构

### 3.1 顶层字段


| 字段                     | 类型             | 说明                                       |
| ---------------------- | -------------- | ---------------------------------------- |
| `interId`              | `str`          | 路口 ID。                                   |
| `obj_intensity`        | `number`       | 目标供需强度，内部映射到 `target_saturation`。        |
| `parameter_json_str`   | `str` / `dict` | 规范化参数主入口，内容推荐包含 `phasePlanOfTimeList`。   |
| `phasePlanOfTimeList`  | `list[dict]`   | 也支持直接透传为对象，不必先序列化成字符串。                   |
| `constraints`          | `dict`         | 工程约束，如最大周期、最小绿、黄灯、全红等。                   |
| `strategy_instruction` | `dict`         | 策略覆盖项，优先级高于 `constraints`。               |
| `profile`              | `dict`         | 画像侧扩展信息。当前单路口优化主输入不再从 `profile` 中提取相位数据。 |


### 3.2 `parameter_json_str` 内容

推荐结构如下：

```json
{
  "phasePlanOfTimeList": [
    {
      "interId": "INT-001",
      "phasePlanId": "PLAN-001",
      "phasePlanName": "默认相位方案",
      "startTime": "00:00",
      "endTime": "24:00",
      "controlPlanId": null,
      "cycleTime": null,
      "phaseStageInfoList": [
        {
          "phaseStageId": "A",
          "phaseStageName": "A",
          "phaseDirInfoDTOList": [
            {
              "dir8No": 1,
              "turnDirNo": 2,
              "turnFlowTotal": 600,
              "laneCount": 2
            },
            {
              "dir8No": 5,
              "turnDirNo": 2,
              "criticalLaneFlow": 280,
              "laneCount": 1
            }
          ]
        },
        {
          "phaseStageId": "B",
          "phaseStageName": "B",
          "phaseDirInfoDTOList": [
            {
              "dir8No": 3,
              "turnDirNo": 2,
              "turnFlowTotal": 420,
              "laneCount": 2
            },
            {
              "dir8No": 7,
              "turnDirNo": 2,
              "criticalLaneFlow": 210,
              "laneCount": 1
            }
          ]
        }
      ]
    }
  ]
}
```

### 3.3 `phaseDirInfoDTOList[]` 字段说明


| 字段                 | 类型       | 必填  | 说明                   |
| ------------------ | -------- | --- | -------------------- |
| `dir8No`           | `int`    | 是   | 进口道方向编号。             |
| `turnDirNo`        | `int`    | 是   | 转向编号。                |
| `turnFlowTotal`    | `number` | 否   | 转向总流量。               |
| `laneCount`        | `int`    | 否   | 转向对应车道数；未传时按 `1` 处理。 |
| `criticalLaneFlow` | `number` | 否   | 转向关键车道流量。            |
| `fridList`         | `any`    | 否   | 保留扩展字段，算法当前原样透传。     |
| `phaseId`          | `str`    | 否   | 保留扩展字段，算法当前原样透传。     |


折算规则：

- 若有 `criticalLaneFlow`，求解直接使用它作为车道级流量。
- 若没有 `criticalLaneFlow`，但有 `turnFlowTotal` 和 `laneCount`，则使用 `turnFlowTotal / laneCount`。
- 若两者都未提供，则按 `0` 流量处理。

---

## 4. `constraints` 默认值

与 `single_point.py` 中 `DEFAULT_SINGLE_POINT_CONFIG` 一致：


| 字段                             | 默认值      |
| ------------------------------ | -------- |
| `default_cycle_s`              | `120`    |
| `target_saturation`            | `0.8`    |
| `target_saturation_min`        | `0.5`    |
| `target_saturation_max`        | `0.98`   |
| `max_cycle_s`                  | `190`    |
| `min_green_s`                  | `20`     |
| `green_loss_s`                 | `5`      |
| `saturation_flow_vph`          | `1400.0` |
| `yellow_s`                     | `3`      |
| `all_red_s`                    | `2`      |
| `intensity_std_penalty_weight` | `5.0`    |
| `over_target_penalty_weight`   | `10.0`   |
| `solver_multi_start_count`     | `20`     |
| `solver_random_seed`           | `42`     |
| `solver_max_iterations`        | `600`    |
| `solver_ftol`                  | `1e-9`   |
| `debug_objective_terms`        | `false`  |


说明：

- `strategy_instruction` 中同名字段会覆盖 `constraints`。
- `obj_intensity` 会映射到 `target_saturation`，便于与外部平台命名对齐。

---

## 5. 推荐调用示例

### 5.1 Python

```python
import json

from src.planning.single_point import generate_single_point_plan

request = {
    "interId": "INT-001",
    "obj_intensity": 0.8,
    "parameter_json_str": json.dumps(
        {
            "phasePlanOfTimeList": [
                {
                    "interId": "INT-001",
                    "phasePlanId": "PLAN-001",
                    "phasePlanName": "默认相位方案",
                    "startTime": "00:00",
                    "endTime": "24:00",
                    "phaseStageInfoList": [
                        {
                            "phaseStageId": "A",
                            "phaseStageName": "A",
                            "phaseDirInfoDTOList": [
                                {"dir8No": 1, "turnDirNo": 2, "turnFlowTotal": 600, "laneCount": 2},
                                {"dir8No": 5, "turnDirNo": 2, "criticalLaneFlow": 280, "laneCount": 1},
                            ],
                        },
                        {
                            "phaseStageId": "B",
                            "phaseStageName": "B",
                            "phaseDirInfoDTOList": [
                                {"dir8No": 3, "turnDirNo": 2, "turnFlowTotal": 420, "laneCount": 2},
                                {"dir8No": 7, "turnDirNo": 2, "criticalLaneFlow": 210, "laneCount": 1},
                            ],
                        },
                    ],
                }
            ]
        }
    ),
    "constraints": {
        "max_cycle_s": 190,
        "min_green_s": 20,
        "green_loss_s": 5,
        "yellow_s": 3,
        "all_red_s": 2,
    },
}

plan = generate_single_point_plan(request)
print(plan["phaseStageTimingList"])
```

### 5.2 HTTP

```bash
curl -X POST "http://127.0.0.1:8000/v1/planning/single-point" \
  -H "Content-Type: application/json" \
  -d '{
    "interId": "INT-001",
    "obj_intensity": 0.8,
    "phasePlanOfTimeList": [
      {
        "interId": "INT-001",
        "phasePlanId": "PLAN-001",
        "phasePlanName": "默认相位方案",
        "startTime": "00:00",
        "endTime": "24:00",
        "phaseStageInfoList": [
          {
            "phaseStageId": "A",
            "phaseStageName": "A",
            "phaseDirInfoDTOList": [
              { "dir8No": 1, "turnDirNo": 2, "turnFlowTotal": 600, "laneCount": 2 },
              { "dir8No": 5, "turnDirNo": 2, "criticalLaneFlow": 280, "laneCount": 1 }
            ]
          },
          {
            "phaseStageId": "B",
            "phaseStageName": "B",
            "phaseDirInfoDTOList": [
              { "dir8No": 3, "turnDirNo": 2, "turnFlowTotal": 420, "laneCount": 2 },
              { "dir8No": 7, "turnDirNo": 2, "criticalLaneFlow": 210, "laneCount": 1 }
            ]
          }
        ]
      }
    ],
    "constraints": {
      "max_cycle_s": 190,
      "min_green_s": 20,
      "green_loss_s": 5
    }
  }'
```

### 5.3 本地可视化测试调用方式

如果需要在本地通过页面联调和观察结果，可直接使用项目自带的可视化调试页。

1. 在项目根目录启动服务：

```bash
.venv/bin/python -m uvicorn src.api.main:app --reload
```

2. 浏览器打开以下地址：

- 调试页面入口：`http://127.0.0.1:8000/v1/planning/single-point/ui`
- 页面实际地址：`http://127.0.0.1:8000/debug/timing-optimizer.html`

3. 在页面中按以下步骤操作：

- 左侧配置路口 ID、进口道车道数、阶段放行关系、周期约束和饱和流率。
- 右侧按转向填写 `turnFlowTotal` 或 `criticalLaneFlow`。
- 点击“开始优化”，页面会自动组装 `phasePlanOfTimeList` 请求并调用 `POST /v1/planning/single-point`。
- 结果区可直接查看 `cycleTime`、各阶段 `greenTime/yellowTime/redTime`、阶段饱和度，以及 `direction_intensity_list` 对应的各转向供需强度。

4. 页面联调时的请求特点：

- 页面会直接提交 `interId`、`obj_intensity`、`phasePlanOfTimeList`。
- 同时会附带 `parameter_json_str`，其内容与页面组装出的 `phasePlanOfTimeList` 一致，便于对照查看。
- 当前页面不再拼接旧版 `phases` 输入。

5. 适用场景：

- 校验 `dir8No` / `turnDirNo` 编码是否正确。
- 快速验证不同转向流量、关键车道流量和周期约束对结果的影响。
- 让非开发人员通过浏览器直接联调单路口优化接口。

---

## 6. 输出结构

### 6.1 规范化结果字段

算法返回的 `plan` 中新增以下主字段：


| 字段                     | 说明                      |
| ---------------------- | ----------------------- |
| `isError`              | 是否出错。当前成功结果固定为 `false`。 |
| `data`                 | 规范化阶段输出列表。              |
| `error`                | 错误对象；成功时为 `null`。       |
| `planType`             | 固定为 `"single_point"`。   |
| `intersectionId`       | 规范化路口 ID。               |
| `cycleTime`            | 周期时长。                   |
| `phasePlanId`          | 相位方案 ID。                |
| `phasePlanName`        | 相位方案名称。                 |
| `phaseStageTimingList` | 与 `data` 同结构的阶段配时结果。    |


### 6.2 `data[]` / `phaseStageTimingList[]`

返回结构参考如下：

```json
{
  "isError": false,
  "data": [
    {
      "phaseStageId": "A",
      "phaseStageName": "A",
      "splitTime": 70,
      "greenTime": 35,
      "yellowTime": 5,
      "redTime": 30,
      "allRedTime": 2,
      "splitRatio": 0.5,
      "phaseSaturation": 0.82,
      "phaseDirInfoDTOList": [
        {
          "movementKey": "d1_t2",
          "dir8No": 1,
          "turnDirNo": 2,
          "turnFlowTotal": 600,
          "laneCount": 2,
          "criticalLaneFlow": 300,
          "laneLevelFlow": 300,
          "label": "北-直行"
        }
      ]
    }
  ],
  "error": null
}
```

字段说明：


| 字段                    | 说明              |
| --------------------- | --------------- |
| `phaseStageId`        | 阶段 ID。          |
| `phaseStageName`      | 阶段名称。           |
| `splitTime`           | 当前按周期口径返回。      |
| `greenTime`           | 绿灯时长。           |
| `yellowTime`          | 黄灯时长。           |
| `redTime`             | 红灯时长。           |
| `allRedTime`          | 全红时长。           |
| `splitRatio`          | 绿灯占周期比。         |
| `phaseSaturation`     | 阶段代表饱和度。        |
| `phaseDirInfoDTOList` | 原始转向输入的规范化透传结果。 |


### 6.3 `meta` 字段

`meta` 用于承载求解器与诊断信息，例如：

- `algorithm`
- `version`
- `solver`
- `solver_family`
- `target_saturation`
- `lost_time_total_s`
- `effective_green_total_s`
- `max_phase_saturation`
- `direction_intensity_list`
- `notes`

---

## 7. HTTP / MCP 外层信封

HTTP 与 MCP 工具仍返回统一信封：

```json
{
  "ok": true,
  "isError": false,
  "data": [
    {
      "phaseStageId": "A",
      "splitTime": 70
    }
  ],
  "error": null,
  "tool": "single_point_plan_tool",
  "plan": {
    "planType": "single_point",
    "cycleTime": 70
  }
}
```

说明：

- 顶层 `data/error/isError` 便于直接对接外部平台返回格式。
- `plan` 中保留完整结果，供前端页面与内部工作流继续使用。

---

## 8. 输入优先级

当前实现支持以下输入优先级：

1. `request.phasePlanOfTimeList`
2. `request.parameter_json_str` 中的 `phasePlanOfTimeList`

除此之外不会再尝试旧版字段。

---

## 9. 常见问题

### 9.1 为什么不再推荐“相位流量”

因为优化模型本质上使用的是转向车流供需强度。把流量挂在 `phaseDirInfoDTOList` 层级，更符合工程数据来源，也能直接表达车道数和关键车道流量。

### 9.2 什么时候会自动折算车道级流量

只要提供以下任一形式就会折算：

- `criticalLaneFlow`
- `turnFlowTotal + laneCount`

### 9.3 没有任何正流量会怎样

若归一化后所有转向均为零流量，求解器无法获得有效解；此时会返回错误并提示检查输入。

---

## 10. 相关入口

- 算法入口：`src/planning/single_point.py`
- HTTP 接口：`POST /v1/planning/single-point`
- MCP 工具：`single_point_plan_tool`
- 调试页面：`GET /v1/planning/single-point/ui`

