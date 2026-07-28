# 干线绿波协调：模型与契约

## 决策变量

| 符号 | 名称 | 约束 |
|------|------|------|
| C | 公共周期（秒） | C_min ≤ C ≤ C_max |
| g_i | 路口 i 协调相位有效绿（秒） | g_min,i ≤ g_i ≤ g_max,i 且 g_i ≤ C − L_i |
| θ_i | 路口 i 主协调相位偏移（秒） | θ_0 = 0（首路口为参考）；0 ≤ θ_i < C |

## 已知量

| 符号 | 来源 |
|------|------|
| τ_f,i | 路段 i→i+1 正向行程时间 = distance_m / (forward_speed_kmh / 3.6) |
| τ_b,i | 路段 i→i+1 反向行程时间 = distance_m / (reverse_speed_kmh / 3.6) |
| L_i | 路口 i 每周期损失时间（黄灯+全红+启动损失） |

## 带宽定义

### 严格带宽（MAXBAND 型）

对正向，带宽 b⁺ 定义为：在给定 C、g、θ 下，所有路口协调绿灯窗口沿正向行程时间链
的**交集宽度**（模 C 意义），即车队以设计速度行驶时能从第一个路口绿灯起始一路不停地
通过最后一个路口的**最大连续时间段**：

    b⁺ = max { w ≥ 0 : 对每对 (i, i+1)，存在整数 k_i 使得
              [θ_i + τ_f,i + k_i·C, θ_i + τ_f,i + k_i·C + w] ⊂ [θ_{i+1}, θ_{i+1} + g_{i+1}] }

反向 b⁻ 类似，用 τ_b 并反转路口序。

### 代理带宽（MVP）

当前 MVP 实现（`solve_arterial_two_way_max_bandwidth`）中 `bandwidth_s = min_i(g_i)`，
是严格带宽的**上界代理**，不等价于上述定义。响应中 `bandwidth_s` 需在 `meta` 标注
`bandwidth_definition: "proxy_min_green"` 或 `"maxband_lp"`。

## 协调策略

| 策略 ID | 含义 |
|---------|------|
| `oneway_forward` | 单向绿波，正向优先（反向次优） |
| `oneway_reverse` | 单向绿波，反向优先 |
| `bidirectional` | 双向绿波，正反向同时 |
| `bidirectional_no_double_stop` | 双向绿波 + 抑制相邻连续停车 |

## 输出契约（每路口）

- cycle_s：该路口周期
- phase_stage_timing_list：各相位阶段绿时与绿信比
- main_coordination_offset_s：主协调相位偏移
- main_coordination_phase_id：主协调相位 ID
- webster_delay_s：Webster 延误（后算 KPI）
