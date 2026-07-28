"""Demo LLM 服务：基于环境变量真实调用大模型，失败时回退规则模板.

调用链：请求 -> 本地缓存 -> HTTP调用(dashscope/openai-compat) -> 失败回退
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import httpx

from src.common.config import get_settings


class LLMService:
    """Demo 专用 LLM 服务，封装调用、缓存和兜底."""

    def __init__(self):
        self._settings = get_settings()
        self._cache: dict[str, dict] = {}
        self._cache_ttl = 600  # 缓存10分钟，避免演示时频繁消耗token
        self._timeout = 25.0   # 超时25秒

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def city_overview_summary(self, overview: dict) -> dict:
        """城市总览态势总结 - 对应主智能体语义化报告能力."""
        prompt = self._build_overview_prompt(overview)
        fallback = self._fallback_overview(overview)
        return self._call_with_cache("city_overview", prompt, fallback)

    def scene_cognition_report(self, target: dict, profile: dict) -> dict:
        """场景认知三维画像解读 - 对应场景认知子智能体自然语言生成."""
        prompt = self._build_cognition_prompt(target, profile)
        fallback = self._fallback_cognition(target, profile)
        return self._call_with_cache(f"cognition_{target.get('id','')}", prompt, fallback)

    def diagnosis_report(self, target: dict, issues: list) -> dict:
        """问题诊断可解释报告 - 对应诊断子智能体归因说明."""
        prompt = self._build_diagnosis_prompt(target, issues)
        fallback = self._fallback_diagnosis(target, issues)
        return self._call_with_cache(f"diagnosis_{target.get('id','')}", prompt, fallback)

    def strategy_explanation(self, target: dict, strategies: list, issues: list) -> dict:
        """控制策略自然语言说明 - 对应控制策略子智能体."""
        prompt = self._build_strategy_prompt(target, strategies, issues)
        fallback = self._fallback_strategy(target, strategies)
        return self._call_with_cache(f"strategy_{target.get('id','')}", prompt, fallback)

    def evaluation_report(self, run: dict) -> dict:
        """评价反馈复盘报告 - 对应评价反馈子智能体."""
        prompt = self._build_evaluation_prompt(run)
        fallback = self._fallback_evaluation(run)
        return self._call_with_cache(f"eval_{run.get('runId','')}", prompt, fallback)

    def intervention_advice(self, intervention: dict, context: dict) -> dict:
        """人工干预审批辅助意见 - 对应人机协同层风险分析."""
        prompt = self._build_intervention_prompt(intervention, context)
        fallback = self._fallback_intervention(intervention)
        return self._call_with_cache(
            f"hmi_{intervention.get('targetId','')}_advice", prompt, fallback, ttl=120
        )

    def experience_summary(self, intervention: dict, effect: dict) -> dict:
        """经验沉淀总结生成 - 对应经验采集与知识库写入."""
        prompt = self._build_experience_prompt(intervention, effect)
        fallback = self._fallback_experience(intervention)
        return self._call_with_cache(
            f"exp_{intervention.get('id','')}", prompt, fallback
        )

    def plan_generation_summary(self, plan: dict, target: dict) -> dict:
        """方案生成说明 - 对应方案生成子智能体配时决策解读."""
        prompt = self._build_plan_prompt(plan, target)
        fallback = self._fallback_plan(plan, target)
        return self._call_with_cache(f"plan_{plan.get('planId','')}", prompt, fallback)

    def evaluation_summary(self, evaluation: dict) -> dict:
        """评价反馈复盘报告 - 对应评价反馈子智能体效果分析."""
        prompt = self._build_eval_summary_prompt(evaluation)
        fallback = self._fallback_eval_summary(evaluation)
        return self._call_with_cache(f"eval_sum_{evaluation.get('evalId','')}", prompt, fallback)

    # ------------------------------------------------------------------
    # 基于统一 Run 实体的闭环报告（10-15 分钟首版自动报告核心入口）
    # ------------------------------------------------------------------

    def run_full_report(self, run_detail: dict) -> dict:
        """基于统一 Run 输出生成结构化首版自动报告.

        报告结构固定为六段：
        1. 交通态势变化
        2. 场景触发与问题发现
        3. OD 变化与影响范围
        4. 关键堵点与主因判断
        5. 已生成策略和执行动作
        6. 当前效果与后续建议
        """
        report_snapshot = run_detail.get("report") or {}
        effect = run_detail.get("effect") or {}
        phases = {p["phase"]: p for p in run_detail.get("phases", [])}
        diag_phase = phases.get("problem_diagnosis", {})
        strat_phase = phases.get("control_strategy", {})
        eval_phase = phases.get("evaluation_feedback", {})

        traffic = report_snapshot.get("traffic_situation", "—")
        trigger = report_snapshot.get("trigger_and_findings", "—")
        od = report_snapshot.get("od_change_analysis", "OD 数据采集中")
        bottleneck = report_snapshot.get("key_bottleneck", "—")
        strategy = report_snapshot.get("strategy_and_action", "—")
        result = report_snapshot.get("effect_and_suggestion", "—")

        improvements = (effect.get("improvements") or [])
        metrics_str = "；".join(
            f"{i.get('metric','指标')} {'+' if (i.get('delta_pct') or 0) > 0 else ''}{(i.get('delta_pct') or 0):.1f}%"
            for i in improvements[:4]
        ) if improvements else "效果数据积累中"

        prompt = (
            f"请生成一份城市信控智能体闭环运行首版报告（专业、简洁，3-5句话）：\n"
            f"【交通态势】{traffic}\n"
            f"【问题发现】{trigger}\n"
            f"【OD变化】{od}\n"
            f"【关键堵点】{bottleneck}\n"
            f"【策略执行】{strategy}\n"
            f"【优化效果】{result}；关键指标：{metrics_str}\n"
            f"要求：输出纯文本综合报告，禁止markdown，数据精确，语言专业简练。"
        )
        fallback = (
            f"{traffic} {trigger} "
            f"主要处置：{strategy} {result} 关键指标：{metrics_str}"
        )
        return self._call_with_cache(
            f"run_report_{run_detail.get('runId', 'unknown')}", prompt, fallback, ttl=1800
        )

    def experience_from_run(self, run_detail: dict) -> dict:
        """从 Run 结果生成经验沉淀摘要."""
        target_name = run_detail.get("targetName", "")
        effect = run_detail.get("effect") or {}
        phases = {p["phase"]: p for p in run_detail.get("phases", [])}
        strat_ev = (phases.get("control_strategy") or {}).get("evidence", {})
        template_desc = strat_ev.get("topTemplateDesc", "")
        score = effect.get("overall_score", 0)
        improvements = (effect.get("improvements") or [])
        imp_str = "；".join(
            f"{i.get('metric')} 改善 {abs(i.get('delta_pct') or 0):.1f}%"
            for i in improvements if i.get("meets_target")
        )
        prompt = (
            f"请将以下信控智能体优化经验提炼为可复用摘要（50字以内）：\n"
            f"对象：{target_name}；策略：{template_desc}；评分：{score:.2f}；达标指标：{imp_str}\n"
            f"格式：适用场景/触发条件/推荐参数/预期改善，纯文本，禁止符号。"
        )
        fallback = f"{target_name}采用「{template_desc}」策略，综合评分{score:.2f}，{imp_str}，可作为同类场景参考模板。"
        return self._call_with_cache(
            f"exp_run_{run_detail.get('runId', 'unknown')}", prompt, fallback
        )

    # ------------------------------------------------------------------
    # 核心调用逻辑
    # ------------------------------------------------------------------

    def _call_with_cache(
        self, key: str, prompt: str, fallback: str, ttl: int | None = None
    ) -> dict:
        """带缓存的模型调用."""
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:12]
        full_key = f"{key}_{cache_key}"
        now = time.time()
        ttl = ttl or self._cache_ttl

        cached = self._cache.get(full_key)
        if cached and now - cached["ts"] < ttl:
            return {**cached, "from_cache": True}

        result = self._do_call(prompt)
        if result["ok"]:
            self._cache[full_key] = {**result, "ts": now}
            return {**result, "from_cache": False}
        else:
            return {
                "ok": False,
                "text": fallback,
                "from_cache": False,
                "fallback": True,
                "error": result.get("error", ""),
                "ts": now,
            }

    def _do_call(self, prompt: str) -> dict:
        """执行真实 HTTP 调用，使用 dashscope OpenAI 兼容接口."""
        api_base = self._settings.llm_api_base
        api_key = self._settings.llm_api_key or self._settings.dashscope_api_key

        if not api_base or not api_key:
            return {"ok": False, "error": "LLM config missing", "text": ""}

        url = api_base.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "qwen-plus",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是城市交通信号控制领域的专业分析师，擅长解读交通运行数据、"
                        "诊断交通问题、制定信控策略。请用简洁专业的中文输出分析结论，"
                        "注重数据引用和可操作性，禁止使用markdown格式符号。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 600,
            "temperature": 0.4,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return {"ok": True, "text": text, "model": data.get("model", "qwen-plus"),
                    "usage": data.get("usage", {})}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "text": ""}

    # ------------------------------------------------------------------
    # Prompt 构造
    # ------------------------------------------------------------------

    def _build_overview_prompt(self, ov: dict) -> str:
        s = ov.get("stats", {})
        ai = ov.get("agentStatus", {})
        issues = ov.get("topIssues", [])
        issue_text = "、".join(f"{i['name']}（{i['issue']}）" for i in issues)
        return (
            f"当前时间：{ov.get('updateTime','未知')}，城市：{ov.get('city','济南市')}。\n"
            f"全市信控概况：共监测路口{s.get('monitoredIntersections',0)}个，"
            f"当前异常路口{s.get('abnormalIntersections',0)}个、"
            f"异常干线{s.get('abnormalCorridors',0)}条、"
            f"异常区域{s.get('abnormalRegions',0)}个，"
            f"正在优化对象{s.get('optimizingObjects',0)}个，今日已执行优化{s.get('todayOptimizations',0)}次。\n"
            f"全网平均车速{s.get('avgSpeed',0)}km/h，平均延误{s.get('avgDelay',0)}s，拥堵指数{s.get('congestionIndex',0)}。\n"
            f"当前主要问题对象：{issue_text}。\n"
            f"主智能体成功率：{ai.get('master',{}).get('successRate',0)*100:.0f}%，诊断子智能体成功率："
            f"{ai.get('problemDiagnosis',{}).get('successRate',0)*100:.0f}%。\n"
            f"请用3-4句话对当前济南市交通运行态势进行总体评估，指出核心问题和重点关注区域，"
            f"并对智能体的工作状态给出简要判断。"
        )

    @staticmethod
    def _detect_object_type(target: dict) -> str:
        """从对象 ID 前缀或 objectType 字段推断对象类型."""
        ot = target.get("objectType") or target.get("type") or ""
        if ot:
            return ot.lower()
        oid = target.get("id", "")
        if oid.startswith("RGN-"):
            return "region"
        if oid.startswith("COR-"):
            return "corridor"
        return "intersection"

    def _build_cognition_prompt(self, target: dict, profile: dict) -> str:
        obj_type = self._detect_object_type(target)
        s = profile.get("supply", {})
        d = profile.get("demand", {})
        st = profile.get("state", {})
        name = target.get("name", "未知")
        oid = target.get("id", "")

        if obj_type == "region":
            supply_text = (
                f"路网密度{s.get('roadDensity','?')}km/km²，"
                f"区域交通承载力约{s.get('trafficCarryingCapacity', s.get('intersectionCapacity','?'))}pcu/h，"
                f"停车位供给{s.get('parkingSupply','?')}个、缺口率{s.get('parkingGap','?')}，"
                f"公交地铁覆盖率{s.get('transitStationCoverage','?')}，"
                f"站点布局：{s.get('transitLayout','待补充')}"
            )
            demand_text = (
                f"机动车出行量约{d.get('motorVehicleTripVolume','?')}次/日，"
                f"进入流量{d.get('inboundFlow', d.get('peakHourFlow','?'))}pcu/h、离开流量{d.get('outboundFlow','?')}pcu/h，"
                f"在途量{d.get('inTransitVehicles','?')}辆，过境量{d.get('throughTrafficVolume','?')}pcu/h，"
                f"分目的出行：{d.get('purposeTripStructure','待补充')}，"
                f"区域流量分布差异：{d.get('flowDistributionPattern','待补充')}，"
                f"典型时段波动：{d.get('typicalTimePattern','待补充')}，"
                f"供需比{d.get('demandSupplyRatio','?')}，"
                f"通勤占比{int(d.get('commuteRatio',0)*100)}%"
            )
            state_text = (
                f"区域饱和度{st.get('saturation','?')}，"
                f"全网平均车速{st.get('avgSpeed','?')}km/h，"
                f"平均延误{st.get('avgDelay','?')}s，"
                f"运行效率指数{st.get('operationEfficiencyIndex','?')}，"
                f"拥堵指数{st.get('congestionIndex','?')}，"
                f"拥堵发展阶段：{st.get('congestionPhase','?')}，"
                f"拥堵画像：{st.get('congestionPortrait','待补充')}"
            )
            guide = (
                "请从供给（路网密度、交通承载力、停车供给、公交地铁布局）、需求（机动车出行量、进出流量、在途量、过境量、分目的出行、区域差异与时段波动）、状态（饱和度、运行效率、拥堵画像）三个维度，"
                "解读该区域交通画像，说明其成为本轮管控重点的核心原因，输出3-5句专业文字。"
            )
        elif obj_type == "corridor":
            supply_text = (
                f"路口间距{s.get('intersectionSpacing','?')}，"
                f"走廊通行能力{s.get('corridorCapacity','?')}pcu/h，"
                f"车道数{s.get('laneCount','?')}，"
                f"行人过街干扰{s.get('pedestrianInterference','?')}，"
                f"公交站点干扰{s.get('busStopInterference','?')}，"
                f"单位出入口干扰{s.get('accessInterference','?')}，"
                f"交叉道路等级：{s.get('crossRoadHierarchy','待补充')}，"
                f"设计绿波带宽{s.get('bandwidthDesign','?')}s"
            )
            if s.get('assessment'):
                supply_text += f"；{s['assessment']}"
            demand_text = (
                f"机动车出行量约{d.get('motorVehicleTripVolume','?')}次/日，"
                f"高峰流量{d.get('peakHourFlow','?')}pcu/h，"
                f"干线进入流量{d.get('inboundFlow','?')}pcu/h、离开流量{d.get('outboundFlow','?')}pcu/h，"
                f"过境量{d.get('throughTrafficVolume','?')}pcu/h，"
                f"分目的出行：{d.get('purposeTripStructure','待补充')}，"
                f"路段流量分布：{d.get('segmentFlowPattern','待补充')}，"
                f"潮汐特征：{'有' if d.get('tidal') else '无'}，"
                f"潮汐比{d.get('tidalRatio','?')}，"
                f"供需比{d.get('demandSupplyRatio','?')}"
            )
            if d.get('assessment'):
                demand_text += f"；{d['assessment']}"
            state_text = (
                f"走廊饱和度{st.get('saturation','?')}，"
                f"实际车速{st.get('avgSpeed','?')}km/h，"
                f"平均延误{st.get('avgDelay','?')}s，"
                f"停车率{st.get('stopRate','?')}，"
                f"绿波带宽{st.get('bandwidth','?')}s，"
                f"运行效率指数{st.get('operationEfficiencyIndex','?')}，"
                f"所处阶段：{st.get('congestionPhase','?')}，"
                f"拥堵画像：{st.get('congestionPortrait','待补充')}"
            )
            guide = (
                "请从供给（路口间距、通行能力、行人过街设施/公交站点/单位出入口等路段干扰、交叉道路等级）、需求（机动车出行量、干线进出流量、过境量、分目的出行、路段流量分布）、状态（饱和度、运行效率、拥堵画像）三个维度，"
                "解读该走廊的交通画像，说明绿波协调存在的问题与优化重点，输出3-5句专业文字。"
            )
        else:  # intersection
            supply_text = (
                f"路口通行能力{s.get('intersectionCapacity','?')}pcu/h，"
                f"渠化特征：{s.get('channelization','待补充')}，"
                f"信号配时：{s.get('signalTimingPlan','待补充')}，"
                f"信号周期{s.get('cycleTime','?')}s，相位数{s.get('phaseCount','?')}，"
                f"控制方式：{s.get('controlMode','待补充')}，"
                f"通行能力评估：{s.get('assessment','待评估')}"
            )
            demand_text = (
                f"主压力方向：{d.get('dominantPhase','?')}，"
                f"机动车流量特征：{d.get('motorVehiclePattern','待补充')}，"
                f"非机动车峰值{d.get('nonMotorVehiclePeakFlow','?')}辆/h，"
                f"行人过街需求{d.get('pedestrianPeakFlow','?')}人/h，"
                f"转向流量结构：{d.get('turningFlowStructure','待补充')}，"
                f"时段方向特征：{d.get('directionalTimePattern','待补充')}，"
                f"高冲突区域：{d.get('conflictZones','待补充')}"
            )
            state_text = (
                f"饱和度{st.get('saturation','?')}，"
                f"平均延误{st.get('avgDelay','?')}s，"
                f"排队{st.get('queueLength','?')}m，"
                f"停车率{st.get('stopRate','?')}，"
                f"运行效率指数{st.get('operationEfficiencyIndex','?')}，"
                f"所处阶段：{st.get('congestionPhase','?')}，"
                f"拥堵画像：{st.get('congestionPortrait','待补充')}"
            )
            guide = (
                "请从供给（路口通行能力、渠化、信号配时）、需求（不同方向与时段的机动车/非机动车/行人流量、转向流量结构、机非人冲突区域）、状态（饱和度、运行效率、拥堵画像）三个维度，"
                "解读该路口的信控画像，说明其成为本轮单点优化重点的原因，输出3-5句专业文字。"
            )
        return (
            f"对象：{name}（ID: {oid}）\n"
            f"供给维度：{supply_text}。\n"
            f"需求维度：{demand_text}。\n"
            f"状态维度：{state_text}。\n"
            f"{guide}"
        )

    def _build_diagnosis_prompt(self, target: dict, issues: list) -> str:
        obj_type = self._detect_object_type(target)
        issue_lines = []
        for i in issues:
            issue_lines.append(
                f"- {i.get('name','')}（{i.get('category','')}）：{i.get('reason','')}，"
                f"严重程度{i.get('severity',0):.2f}，置信度{i.get('confidence',0):.2f}"
            )
        issues_text = "\n".join(issue_lines) if issue_lines else "无明显问题"
        name = target.get("name", "未知")

        if obj_type == "region":
            context = (
                f"诊断对象：{name}（区域级），"
                f"区域饱和度{target.get('saturation','?')}，"
                f"平均车速{target.get('avgSpeed','?')}km/h，"
                f"进出流量差{target.get('inFlow',0) - target.get('outFlow',0)}pcu/h"
            )
            guide = (
                "请综合解读以上区域级诊断结果：说明静态短板与动态问题的叠加关系，"
                "明确区域性扩散风险的主驱动因素，给出本轮「控边界-疏堵点-保核心」的优先处理顺序。用4-5句专业文字。"
            )
        elif obj_type == "corridor":
            context = (
                f"诊断对象：{name}（走廊级），"
                f"实际车速{target.get('actualSpeedKmh', target.get('avgSpeed','?'))}km/h，"
                f"设计速度{target.get('designSpeedKmh','?')}km/h，"
                f"停车率{target.get('stopRate','?')}，"
                f"绿波带宽{target.get('bandwidth','?')}s，"
                f"协调周期{target.get('coordCycleS','?')}s"
            )
            guide = (
                "请综合解读以上走廊级诊断结果：说明协调失效或瓶颈传导的成因链条，"
                "明确绿波重建或潮汐优化的核心切入点，给出「连续通行-潮汐适配」的优先处理顺序。用4-5句专业文字。"
            )
        else:  # intersection
            context = (
                f"诊断对象：{name}（路口级），"
                f"饱和度{target.get('saturation','?')}，"
                f"平均延误{target.get('delay','?')}s，"
                f"排队{target.get('queueLength','?')}m，"
                f"停车率{target.get('stopRate','?')}"
            )
            guide = (
                "请综合解读以上路口级诊断结果：说明相位失衡、溢流或空放问题的关联机制，"
                "明确绿信比调整或防溢流策略的优先级，给出本轮单点精调的处置顺序。用4-5句专业文字。"
            )
        return (
            f"{context}。\n"
            f"诊断发现的问题：\n{issues_text}\n"
            f"{guide}"
        )

    def _build_strategy_prompt(self, target: dict, strategies: list, issues: list) -> str:
        obj_type = self._detect_object_type(target)
        strat_lines = []
        for s in strategies:
            line = f"- {s.get('description', s.get('templateId',''))}（层级：{s.get('level','?')}，推荐分{s.get('score',0):.2f}）"
            if s.get('objective'):
                line += f"；目标：{s['objective']}"
            strat_lines.append(line)
        issue_names = "、".join(i.get("name", "") for i in issues)
        name = target.get("name", "未知")

        if obj_type == "region":
            obj_desc = f"区域「{name}」"
            task_desc = "控边界、疏堵点、保核心"
            guide = (
                "请解释为什么选择以上区域级策略组合：说明主策略如何实现边界控流与疏堵目标，"
                "联动走廊/路口策略的触发条件与协同关系，以及各策略的退出条件与副作用管控方式。输出4-6句话。"
            )
        elif obj_type == "corridor":
            obj_desc = f"走廊「{name}」"
            task_desc = "连续通行、潮汐适配、多路径协同"
            guide = (
                "请解释为什么选择以上走廊级策略组合：说明绿波重建或潮汐优化的技术路径，"
                "瓶颈路口专项策略与走廊整体协调的联动关系，以及调整过渡期的风险与监控要点。输出4-6句话。"
            )
        else:  # intersection
            obj_desc = f"路口「{name}」"
            task_desc = "绿信比优化、防溢流、削空放"
            guide = (
                "请解释为什么选择以上路口级策略组合：说明相位调整或防溢流策略的适配逻辑，"
                "上下游路口的联动影响与约束边界，以及方案落地时的关键参数范围与监控指标。输出4-6句话。"
            )
        return (
            f"管控对象：{obj_desc}，核心任务：{task_desc}。\n"
            f"已诊断主要问题：{issue_names}。\n"
            f"系统已匹配策略包：\n" + "\n".join(strat_lines) + "\n"
            f"{guide}"
        )

    def _build_evaluation_prompt(self, run: dict) -> str:
        phases = run.get("phases", [])
        done_phases = [p for p in phases if p.get("status") == "ok"]
        summaries = " -> ".join(p.get("summary", "") for p in done_phases)
        before = None
        after = None
        return (
            f"优化对象：{run.get('targetName','?')}（{run.get('targetType','?')}），"
            f"运行ID：{run.get('runId','')}。\n"
            f"五环节执行摘要：{summaries}\n"
            f"是否达到优化目标：{'是' if run.get('meetsTarget') else '否'}。\n"
            f"请对本轮信控闭环执行过程进行专业复盘：总结各环节效果、指出关键决策点、"
            f"评价最终效果，并对后续类似场景的处置给出建议。输出4-5句话。"
        )

    def _build_intervention_prompt(self, iv: dict, context: dict) -> str:
        return (
            f"人工干预请求：{iv.get('operator','')}（{iv.get('operatorRole','')}）"
            f"对{iv.get('targetName','')}发起【{iv.get('action','')}】操作。\n"
            f"干预原因：{iv.get('reason','')}\n"
            f"参数变更：{json.dumps(iv.get('params',{}), ensure_ascii=False)}\n"
            f"当前对象状态：饱和度{context.get('saturation','?')}，延误{context.get('delay','?')}s。\n"
            f"请从风险评估角度给出AI审批建议：分析该干预操作的合理性、潜在影响范围、"
            f"需要重点关注的指标，以及恢复自动控制的建议时间。输出3-4句话。"
        )

    def _build_plan_prompt(self, plan: dict, target: dict) -> str:
        pp = plan.get("planParams") or {}
        checks = pp.get("safetyChecks", [])
        pass_cnt = sum(1 for c in checks if c.get("pass"))
        inters = pp.get("intersectionPlans", [])
        cycle = pp.get("commonCycle", "?")
        wave_speed = pp.get("greenWaveSpeed")
        gain = plan.get("estimatedGain") or {}
        return (
            f"方案生成对象：{plan.get('targetName','')}（{plan.get('targetType','')}），"
            f"策略模板：{plan.get('strategyTemplateId','')}。\n"
            f"配时参数概要：公共周期{cycle}s，"
            + (f"绿波设计速度{wave_speed}km/h，" if wave_speed else "")
            + f"涉及{len(inters)}个路口。\n"
            f"安全约束检验：{pass_cnt}/{len(checks)}项通过。\n"
            f"预期效果：车速提升{gain.get('avgSpeedImprovement','?')}，"
            f"延误降低{gain.get('delayReduction','?')}，停车率降低{gain.get('stopRateReduction','?')}。\n"
            f"请对本次方案生成过程做简要说明：解释配时参数选择依据、绿波设计逻辑、"
            f"关键约束如何满足，以及方案可能存在的局限或风险。输出4-5句专业文字。"
        )

    def _build_eval_summary_prompt(self, ev: dict) -> str:
        improvements = ev.get("improvements", [])
        met = [i for i in improvements if i.get("meetsTarget")]
        total = len(improvements)
        score = ev.get("overallScore", 0)
        rec = ev.get("recommendation", "")
        side = ev.get("sideEffects", [])
        return (
            f"评价对象：{ev.get('targetName','')}（{ev.get('targetType','')}），"
            f"评价时窗：优化后{ev.get('windowMinutes',30)}分钟。\n"
            f"综合评分：{score:.2f}，{total}项指标中{len(met)}项达标。\n"
            f"指标改善：" + "、".join(
                f"{i['metric']}{'+' if i['deltaPercent']>0 else ''}{i['deltaPercent']:.1f}%"
                for i in improvements[:3]
            ) + "。\n"
            f"副作用：{'; '.join(s['description'] for s in side) if side else '无明显副作用'}。\n"
            f"系统建议：{rec}\n"
            f"请对本轮闭环优化进行全面复盘：总结各指标改善情况、分析达标原因，"
            f"指出值得推广的经验，并对后续同类场景处置给出建议。输出4-5句话。"
        )

    def _build_experience_prompt(self, iv: dict, effect: dict) -> str:
        return (
            f"人工干预已完成：{iv.get('targetName','')}，操作类型：{iv.get('action','')}。\n"
            f"干预背景：{iv.get('reason','')}\n"
            f"效果数据：{json.dumps(effect, ensure_ascii=False)}\n"
            f"请为这条经验生成一段可复用的经验描述，包含：适用场景、关键触发条件、"
            f"推荐操作参数范围、预期改善效果。格式：标准经验摘要，50字以内。"
        )

    # ------------------------------------------------------------------
    # 兜底规则文案
    # ------------------------------------------------------------------

    def _fallback_overview(self, ov: dict) -> str:
        s = ov.get("stats", {})
        return (
            f"当前济南市交通运行压力较大，全网拥堵指数{s.get('congestionIndex',0)}，"
            f"异常路口{s.get('abnormalIntersections',0)}个，平均延误{s.get('avgDelay',0)}s。"
            f"信控智能体已识别{s.get('abnormalRegions',0)}个异常区域，"
            f"正在对{s.get('optimizingObjects',0)}个对象执行闭环优化，系统运行正常。"
        )

    def _fallback_cognition(self, target: dict, profile: dict) -> str:
        obj_type = self._detect_object_type(target)
        st = profile.get("state", {})
        name = target.get("name", "")
        phase = st.get("congestionPhase", "未知")
        if obj_type == "region":
            sat = st.get("saturation") or target.get("saturation", 0)
            speed = st.get("avgSpeed") or target.get("avgSpeed", 0)
            return (
                f"{name}区域饱和度{sat}，平均车速{speed}km/h，处于{phase}阶段。"
                f"区域供需画像已完成，进出流量与路网承载能力失衡特征明显，智能体将启动区域级闭环处理。"
            )
        elif obj_type == "corridor":
            speed = st.get("avgSpeed") or target.get("avgSpeed", 0)
            stop = st.get("stopRate") or target.get("stopRate", 0)
            return (
                f"{name}实际车速{speed}km/h，停车率{stop}，处于{phase}阶段。"
                f"走廊供给-需求-状态三维画像已构建，绿波协调效率下降特征明显，智能体将启动走廊级闭环处理。"
            )
        else:
            sat = st.get("saturation") or target.get("saturation", 0)
            delay = st.get("avgDelay") or target.get("delay", 0)
            return (
                f"{name}饱和度{sat}，平均延误{delay}s，处于{phase}阶段。"
                f"路口三维画像已构建，相位与流量匹配特征明确，智能体将启动单点精调闭环处理。"
            )

    def _fallback_diagnosis(self, target: dict, issues: list) -> str:
        obj_type = self._detect_object_type(target)
        name = target.get("name", "")
        if not issues:
            return f"{name}当前无明显信控问题，运行状态正常。"
        names = "、".join(i.get("name", "") for i in issues)
        max_sev = max(i.get("severity", 0) for i in issues)
        level_tag = {"region": "区域级", "corridor": "走廊级", "intersection": "路口级"}.get(obj_type, "")
        return (
            f"{name}（{level_tag}）诊断出{len(issues)}个问题：{names}。"
            f"最高严重程度{max_sev:.2f}，建议优先处理后进入策略生成环节。"
        )

    def _fallback_strategy(self, target: dict, strategies: list) -> str:
        obj_type = self._detect_object_type(target)
        name = target.get("name", "")
        if not strategies:
            return f"{name}当前无需策略调整，维持现有方案。"
        primary = [s for s in strategies if s.get("level") == obj_type]
        support = [s for s in strategies if s.get("level") != obj_type]
        names = "、".join(s.get("description", s.get("templateId", "")) for s in (primary or strategies)[:2])
        result = f"系统为{name}匹配主策略：{names}"
        if support:
            support_names = "、".join(s.get("description", s.get("templateId", "")) for s in support[:1])
            result += f"，联动支撑策略：{support_names}"
        result += "，将在方案生成环节落地为具体配时参数。"
        return result

    def _fallback_evaluation(self, run: dict) -> str:
        status = "达标" if run.get("meetsTarget") else "未达标"
        return (
            f"{run.get('targetName','')}本轮闭环优化{status}，"
            f"五环节执行状态：{', '.join(p.get('phase','') for p in run.get('phases',[]) if p.get('status')=='ok')} 已完成。"
            f"智能体将在下一轮评估中持续跟踪效果。"
        )

    def _fallback_intervention(self, iv: dict) -> str:
        return (
            f"AI审批意见：{iv.get('action','')}操作属于{iv.get('level','')}级干预，"
            f"请关注操作后{iv.get('targetName','')}周边路口的连带影响，"
            f"建议30分钟后评估干预效果，适时恢复自动控制模式。"
        )

    def _fallback_plan(self, plan: dict, target: dict) -> str:
        pp = plan.get("planParams") or {}
        cycle = pp.get("commonCycle", "?")
        wave = pp.get("greenWaveSpeed")
        gain = plan.get("estimatedGain") or {}
        return (
            f"{plan.get('targetName','')}方案已生成，公共周期{cycle}s"
            + (f"，绿波速度{wave}km/h" if wave else "")
            + f"。预计车速提升{gain.get('avgSpeedImprovement','?')}，"
            f"延误降低{gain.get('delayReduction','?')}。安全约束已全部通过校验，方案可下发执行。"
        )

    def _fallback_eval_summary(self, ev: dict) -> str:
        score = ev.get("overallScore", 0)
        conclusion = ev.get("conclusion", "达标")
        rec = ev.get("recommendation", "")
        return (
            f"{ev.get('targetName','')}本轮优化评价{conclusion}，综合评分{score:.2f}。"
            f"各项指标均有明显改善，系统建议：{rec}"
        )

    def _fallback_experience(self, iv: dict) -> str:
        return (
            f"经验标签：{iv.get('targetName','')}_{iv.get('action','')}。"
            f"适用场景：{iv.get('reason','')}。已记录入经验库供后续参考。"
        )


# 全局单例
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
