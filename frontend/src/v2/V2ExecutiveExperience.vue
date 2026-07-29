<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dataRepository } from '../services/dataRepository'
import type {
  ActId,
  DailySummary,
  DevicePoint,
  EffectTrendScene,
  ExpertDiagnosis,
  FlowTraceScene,
  KnowledgeBaseStats,
  MetricItem,
  SimilarCase,
  TargetIntersection,
  TimingPlanScene,
} from '../types'

type PresentationView = 'home' | 'flow'
type KnowledgeTab = 'experience' | 'case'
type ExperienceTab = 'cognition' | 'governance' | 'plan'

interface ExperienceData {
  summary: Array<{ label: string; value: number; unit: string }>
  pipeline: Array<{ name: string; count: number; status: string }>
  featured: Array<{
    title: string
    scene: string
    result: string
    tags: string[]
  }>
}

interface KnowledgeAsset {
  id: string
  label: string
  value: string
  unit: string
  detail: string
  progress: number
}

const props = defineProps<{
  view: PresentationView
  activeStage: ActId
}>()

const emit = defineEmits<{
  start: []
  home: []
  stage: [value: ActId]
}>()

const target = ref<TargetIntersection | null>(null)
const devices = ref<DevicePoint[]>([])
const metrics = ref<MetricItem[]>([])
const trace = ref<FlowTraceScene | null>(null)
const diagnosis = ref<ExpertDiagnosis | null>(null)
const knowledgeBase = ref<KnowledgeBaseStats | null>(null)
const cases = ref<SimilarCase[]>([])
const plan = ref<TimingPlanScene | null>(null)
const effect = ref<EffectTrendScene | null>(null)
const daily = ref<DailySummary | null>(null)
const experiences = ref<ExperienceData | null>(null)
const prompt = ref('')
const submitting = ref(false)
const knowledgeTab = ref<KnowledgeTab>('experience')
const experienceTab = ref<ExperienceTab>('cognition')
const selectedAssetId = ref('timing')

const stages: Array<{
  id: ActId
  label: string
  en: string
  statement: string
  cue: string
  next: string
}> = [
  {
    id: 1,
    label: '多源感知',
    en: 'MULTI-SOURCE PERCEPTION',
    statement: '把路口、方向、设备与实时指标放在同一张空间底图上',
    cue: '对应讲稿：实时采集流量、排队、延误等 10 余项指标；以解放东路—奥体西路交叉口为例。',
    next: '下一页：智能研判如何确认问题',
  },
  {
    id: 2,
    label: '智能研判',
    en: 'INTELLIGENT DIAGNOSIS',
    statement: '上游连续来车叠加有效放行不足，形成北进口溢流风险',
    cue: '对应讲稿：自动识别溢流积压和相位空放，结合实时车流与周边道路承载情况精准判断配时短板。',
    next: '下一页：调用案例与规则生成方案',
  },
  {
    id: 3,
    label: '方案生成',
    en: 'PLAN GENERATION',
    statement: '案例、专家规则与信控模型共同生成三套候选方案',
    cue: '对应讲稿：匹配相似案例及专家规则，联动信控专业模型测算周期、绿信比和相位差。',
    next: '下一页：方案评估并落地执行',
  },
  {
    id: 4,
    label: '落地执行',
    en: 'DEPLOYMENT',
    statement: '组合方案通过安全边界校核，绑定护栏后下发信号机',
    cue: '对应讲稿：仅用十几秒即可生成多套优选方案，并完成评估、下发与自动回退保护。',
    next: '下一页：查看执行前后效果',
  },
  {
    id: 5,
    label: '效果优化',
    en: 'EFFECT OPTIMIZATION',
    statement: '排队由 129 米下降至 78 米，晚高峰持续低于原有基线',
    cue: '对应讲稿：效果评估与持续优化——高峰排队长度明显下降，路口溢出问题得到缓解。',
    next: '下一页：复盘沉淀为长期经验',
  },
  {
    id: 6,
    label: '持续优化',
    en: 'CONTINUOUS LEARNING',
    statement: '每次处置形成可追溯记录，有效策略持续回流知识库',
    cue: '讲解收口：从单路口治理回到全市常态扫描，形成“发现—处置—验证—学习”的持续进化闭环。',
    next: '演示完成 · 可返回首页继续扫描',
  },
]

const knowledgeAssets: KnowledgeAsset[] = [
  {
    id: 'experts',
    label: '资深专家',
    value: '20',
    unit: '名',
    detail: '覆盖信号配时、交通组织与走廊协调等专业方向',
    progress: 88,
  },
  {
    id: 'timing',
    label: '配时方案',
    value: '1,000+',
    unit: '套',
    detail: '可按周期、绿信比、相位差与适用场景检索复用',
    progress: 82,
  },
  {
    id: 'cases',
    label: '处置案例',
    value: '1,400',
    unit: '个',
    detail: '来自一线民警的真实问题认知与治理过程',
    progress: 93,
  },
  {
    id: 'primary-tags',
    label: '一级标签',
    value: '10',
    unit: '类',
    detail: '覆盖时段、问题、道路、交通组成等关键维度',
    progress: 100,
  },
  {
    id: 'detail-tags',
    label: '细分标签',
    value: '50',
    unit: '个',
    detail: '用于准确描述场景结构、问题类型与处置动作',
    progress: 78,
  },
  {
    id: 'semantics',
    label: '场景语义',
    value: '9,000',
    unit: '条',
    detail: '把“晚高峰潮汐失稳”等一线认知转为机器可理解特征',
    progress: 90,
  },
  {
    id: 'rules',
    label: '专家规则',
    value: '200',
    unit: '类',
    detail: '支撑问题判因、方案约束、安全边界与效果判断',
    progress: 86,
  },
]

const activeStageMeta = computed(() => stages[props.activeStage - 1])
const selectedAsset = computed(
  () => knowledgeAssets.find((item) => item.id === selectedAssetId.value) ?? knowledgeAssets[0],
)
const onlineDeviceCount = computed(() => devices.value.filter((item) => item.status === 'online').length)
const recommendedPlan = computed(() => plan.value?.options.find((item) => item.recommended))
const recommendedImpact = computed(() =>
  plan.value?.impacts.find((item) => item.optionId === recommendedPlan.value?.id),
)
const selectedExperience = computed(() => {
  const content: Record<ExperienceTab, { title: string; description: string; sample: string }> = {
    cognition: {
      title: '认知经验',
      description: '一线交警对路口长期运行规律和特殊时段问题的现场认知。',
      sample: '解放东路—奥体西路工作日晚高峰北进口易出现连续到达波。',
    },
    governance: {
      title: '治理经验',
      description: '针对学校、商场、医院等交通吸引源形成的定性判因经验。',
      sample: '临近大型活动场馆，散场时段需优先关注北侧走廊集中到达。',
    },
    plan: {
      title: '方案经验',
      description: '经效果验证后沉淀的定性策略、配时参数和安全护栏。',
      sample: '适度加放目标方向，同时上游削峰并保留下游承接保护。',
    },
  }
  return content[experienceTab.value]
})
const effectPeakRows = computed(() => effect.value?.hourlyComparison ?? [])
const maxQueue = computed(() =>
  Math.max(1, ...effectPeakRows.value.flatMap((item) => [item.before, item.after])),
)

function submitPrompt() {
  if (!prompt.value.trim() || submitting.value) return
  submitting.value = true
  window.setTimeout(() => {
    submitting.value = false
    emit('start')
  }, 650)
}

function goPrevious() {
  if (props.activeStage === 1) {
    emit('home')
    return
  }
  emit('stage', (props.activeStage - 1) as ActId)
}

function goNext() {
  if (props.activeStage === 6) {
    emit('home')
    return
  }
  emit('stage', (props.activeStage + 1) as ActId)
}

onMounted(async () => {
  const [
    targetData,
    deviceData,
    metricData,
    traceData,
    diagnosisData,
    knowledgeData,
    caseData,
    planData,
    effectData,
    dailyData,
    experienceData,
  ] = await Promise.all([
    dataRepository.targetIntersection(),
    dataRepository.devices(),
    dataRepository.metrics(),
    dataRepository.flowTrace(),
    dataRepository.expertDiagnosis(),
    dataRepository.knowledgeBase(),
    dataRepository.similarCases(),
    dataRepository.timingPlan(),
    dataRepository.effectTrend(),
    dataRepository.dailySummary(),
    dataRepository.experiences(),
  ])

  target.value = targetData
  devices.value = deviceData
  metrics.value = metricData
  trace.value = traceData
  diagnosis.value = diagnosisData
  knowledgeBase.value = knowledgeData
  cases.value = caseData
  plan.value = planData
  effect.value = effectData
  daily.value = dailyData
  experiences.value = experienceData as unknown as ExperienceData
})
</script>

<template>
  <section v-if="view === 'home'" class="v2-home-experience">
    <aside class="v2-panel v2-task-rail">
      <div class="v2-panel-cap">
        <span><i></i> AGENT TASK CENTER</span>
        <b>智能体任务中心</b>
        <small>LIVE</small>
      </div>

      <div class="v2-task-summary">
        <div>
          <small>全市常态运行</small>
          <strong>持续扫描中</strong>
        </div>
        <span class="v2-orbit"><i></i><b>986</b></span>
      </div>

      <div class="v2-section-title">
        <span>正在执行</span>
        <b>01</b>
      </div>
      <article class="v2-running-task">
        <header>
          <span><i></i> 多源态势扫描</span>
          <small>已持续 06:42:18</small>
        </header>
        <strong>济南市重点监测路网</strong>
        <p>视频、电警、地磁、互联网路况与信号机数据正在持续融合。</p>
        <div class="v2-scan-progress"><span></span></div>
        <footer><span>已覆盖 986 个路口</span><b>实时刷新</b></footer>
      </article>

      <div class="v2-section-title completed">
        <span>已完成</span>
        <b>180</b>
      </div>
      <button class="v2-completed-task" @click="emit('start')">
        <span class="v2-task-status">闭环完成</span>
        <small>18:21 · 晚高峰溢流治理</small>
        <strong>解放东路 × 奥体西路</strong>
        <p>自主完成感知、研判、方案生成、执行与效果评估。</p>
        <div class="v2-task-result">
          <span><small>北进口排队</small><b>129m</b></span>
          <i>→</i>
          <strong>78m</strong>
        </div>
        <footer><span>点击按顺序回放完整处置过程</span><b>进入演示 →</b></footer>
      </button>

      <div class="v2-rail-foot">
        <span><i></i> 45 项异常已发现</span>
        <span><i></i> 96.8% 闭环完成率</span>
      </div>
    </aside>

    <section class="v2-scan-hero">
      <div class="v2-scan-radar" aria-hidden="true">
        <span></span><i></i><b></b>
      </div>
      <div>
        <small>AUTONOMOUS CITY SENSING</small>
        <strong>智能体正在持续理解城市交通运行状态</strong>
        <p>流量 · 排队 · 延误 · 饱和度 · 绿灯利用率 · 路网承载</p>
      </div>
    </section>

    <aside class="v2-panel v2-knowledge-panel">
      <div class="v2-panel-cap">
        <span><i></i> TRAFFIC KNOWLEDGE BASE</span>
        <b>交管知识库</b>
        <small>已连接</small>
      </div>

      <div class="v2-knowledge-intro">
        <div>
          <small>知识资产总览</small>
          <strong>专家知识 × 一线经验 × 实战案例</strong>
        </div>
        <span>持续学习</span>
      </div>

      <div class="v2-knowledge-assets">
        <button
          v-for="asset in knowledgeAssets"
          :key="asset.id"
          :class="{ active: selectedAssetId === asset.id }"
          @click="selectedAssetId = asset.id"
        >
          <strong>{{ asset.value }}<small>{{ asset.unit }}</small></strong>
          <span>{{ asset.label }}</span>
        </button>
      </div>

      <div class="v2-asset-detail">
        <div
          class="v2-ring"
          :style="{ '--asset-progress': `${selectedAsset.progress * 3.6}deg` }"
        >
          <span>{{ selectedAsset.progress }}%</span>
        </div>
        <div>
          <small>当前查看 · {{ selectedAsset.label }}</small>
          <strong>{{ selectedAsset.value }} {{ selectedAsset.unit }}</strong>
          <p>{{ selectedAsset.detail }}</p>
        </div>
      </div>

      <nav class="v2-knowledge-tabs">
        <button :class="{ active: knowledgeTab === 'experience' }" @click="knowledgeTab = 'experience'">
          经验库
        </button>
        <button :class="{ active: knowledgeTab === 'case' }" @click="knowledgeTab = 'case'">
          案例库
        </button>
      </nav>

      <div v-if="knowledgeTab === 'experience'" class="v2-knowledge-library">
        <div class="v2-library-subtabs">
          <button :class="{ active: experienceTab === 'cognition' }" @click="experienceTab = 'cognition'">认知经验</button>
          <button :class="{ active: experienceTab === 'governance' }" @click="experienceTab = 'governance'">治理经验</button>
          <button :class="{ active: experienceTab === 'plan' }" @click="experienceTab = 'plan'">方案经验</button>
        </div>
        <article>
          <small>{{ selectedExperience.title }}</small>
          <strong>{{ selectedExperience.description }}</strong>
          <p>“{{ selectedExperience.sample }}”</p>
          <span>来自一线民警经验 · 已结构化入库</span>
        </article>
      </div>

      <div v-else class="v2-knowledge-library v2-case-library">
        <div class="v2-library-subtabs">
          <button class="active">行业案例</button>
          <button>路口治理案例</button>
        </div>
        <article v-for="item in cases.slice(0, 2)" :key="item.id">
          <span>{{ item.matchScore }}%</span>
          <div>
            <small>{{ item.location }}</small>
            <strong>{{ item.title }}</strong>
          </div>
        </article>
      </div>
    </aside>

    <div class="v2-command-center">
      <div v-if="submitting" class="v2-submit-state"><i></i> 正在理解任务并定位目标路口…</div>
      <div class="v2-command-input">
        <span class="v2-agent-spark">AI</span>
        <input
          v-model="prompt"
          :disabled="submitting"
          placeholder="也可主动输入：分析解放东路与奥体西路晚高峰排队问题"
          @keyup.enter="submitPrompt"
        />
        <button :disabled="!prompt.trim() || submitting" @click="submitPrompt">发起研判</button>
      </div>
      <div class="v2-command-guide">
        <span>演示建议：讲完知识库数据后，点击左侧“已完成”任务进入全流程回放</span>
        <b>支持键盘输入主动任务</b>
      </div>
    </div>
  </section>

  <section v-else class="v2-flow-experience">
    <div class="v2-stage-context">
      <span>{{ activeStageMeta.en }}</span>
      <strong>{{ activeStageMeta.label }}</strong>
      <p>{{ activeStageMeta.statement }}</p>
    </div>

    <aside class="v2-panel v2-stage-left">
      <div class="v2-panel-cap">
        <span><i></i> EVIDENCE CHAIN</span>
        <b>{{ activeStageMeta.label }} · 核心证据</b>
        <small>{{ String(activeStage).padStart(2, '0') }}/06</small>
      </div>

      <template v-if="activeStage === 1">
        <div class="v2-target-card">
          <small>本次演示对象</small>
          <strong>{{ target?.name ?? '解放东路与奥体西路交叉口' }}</strong>
          <p>晚高峰 · 北进口向南直行 · 溢流风险</p>
        </div>
        <div class="v2-evidence-grid">
          <article>
            <span>感知数据源</span><strong>4<small>类</small></strong><p>视频 / 地磁 / 路况 / 信号</p>
          </article>
          <article>
            <span>在线设备</span><strong>{{ onlineDeviceCount }}<small>台</small></strong><p>覆盖率 91.7%</p>
          </article>
        </div>
        <div class="v2-metric-stack">
          <article v-for="metric in metrics" :key="metric.id" :class="metric.status">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}<small>{{ metric.unit }}</small></strong>
            <p>{{ metric.trend }}</p>
          </article>
        </div>
      </template>

      <template v-else-if="activeStage === 2">
        <ol class="v2-analysis-chain">
          <li>
            <span>01</span><div><strong>拓扑关系</strong><p>目标、冲突、上游与下游同屏分析</p></div><b>完成</b>
          </li>
          <li>
            <span>02</span><div><strong>流量溯源</strong><p>六跳主走廊累计解释 {{ trace?.summary.coveredSharePct.toFixed(1) ?? '92.0' }}%</p></div><b>完成</b>
          </li>
          <li>
            <span>03</span><div><strong>问题验证</strong><p>逐项核验放行不足、到达波与下游承接</p></div><b>完成</b>
          </li>
        </ol>
        <div class="v2-direction-facts">
          <article v-for="item in diagnosis?.directions" :key="item.id" :class="item.tone">
            <small>{{ item.role }}</small><strong>{{ item.primaryMetric }}</strong><p>{{ item.label }}</p>
          </article>
        </div>
      </template>

      <template v-else-if="activeStage === 3">
        <div class="v2-recall-summary">
          <span>知识检索完成</span>
          <strong>{{ knowledgeBase?.matchLatencySeconds ?? 1.8 }}<small>秒</small></strong>
          <p>命中 {{ knowledgeBase?.matchedCaseCount ?? 37 }} 个高相似案例与适用专家规则</p>
        </div>
        <div class="v2-case-stack">
          <article v-for="item in cases" :key="item.id">
            <span>{{ item.matchScore }}%</span>
            <div><small>{{ item.location }}</small><strong>{{ item.title }}</strong></div>
          </article>
        </div>
        <div class="v2-model-badges">
          <span>周期测算</span><span>绿信比优化</span><span>相位差协调</span>
        </div>
      </template>

      <template v-else-if="activeStage === 4">
        <div class="v2-recommended-plan">
          <small>评估通过 · 推荐执行</small>
          <strong>{{ recommendedPlan?.name ?? '方案 C · 协同组合' }}</strong>
          <p>{{ recommendedPlan?.summary }}</p>
        </div>
        <div class="v2-impact-list">
          <article>
            <span>北进口排队</span><b>{{ recommendedImpact?.target.before }}</b><i>→</i><strong>{{ recommendedImpact?.target.after }}</strong>
          </article>
          <article>
            <span>东西向排队</span><b>{{ recommendedImpact?.conflict.before }}</b><i>→</i><strong>{{ recommendedImpact?.conflict.after }}</strong>
          </article>
          <article>
            <span>下游占有率</span><b>{{ recommendedImpact?.downstream.before }}</b><i>→</i><strong>{{ recommendedImpact?.downstream.after }}</strong>
          </article>
        </div>
        <div class="v2-safety-badge"><i>✓</i><span><b>安全边界全部通过</b>未把压力转移给相邻方向</span></div>
      </template>

      <template v-else-if="activeStage === 5">
        <div class="v2-outcome-hero">
          <small>北进口高峰排队</small>
          <div><b>129<small>m</small></b><i>→</i><strong>78<small>m</small></strong></div>
          <span>下降 39.5%</span>
        </div>
        <div class="v2-outcome-metrics">
          <article v-for="item in effect?.metrics" :key="item.id">
            <span>{{ item.label }}</span>
            <div><b>{{ item.before }}</b><i>→</i><strong>{{ item.after }}{{ item.unit }}</strong></div>
            <em>{{ item.direction === 'down' ? '↓' : '↑' }} {{ item.improvementPct }}%</em>
          </article>
        </div>
      </template>

      <template v-else>
        <div class="v2-daily-verdict">
          <small>今日运行评价</small>
          <strong>稳定 · 有效 · 可控</strong>
          <p>{{ daily?.headline }}</p>
        </div>
        <div class="v2-daily-kpis">
          <article v-for="item in daily?.kpis.slice(0, 4)" :key="item.label">
            <span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.delta }}</small>
          </article>
        </div>
      </template>
    </aside>

    <aside class="v2-panel v2-stage-right">
      <div class="v2-panel-cap">
        <span><i></i> EXECUTIVE CONCLUSION</span>
        <b>本页结论</b>
        <small>LEADER VIEW</small>
      </div>

      <template v-if="activeStage === 1">
        <div class="v2-conclusion-block critical">
          <small>异常已核验</small>
          <strong>排队越过动态阈值，并连续 3 个周期增长</strong>
          <p>不是瞬时波动，目标方向与现场证据已经完成空间绑定。</p>
        </div>
        <div class="v2-threshold-visual">
          <div><span>动态阈值</span><b>114.8m</b></div>
          <div><span>当前排队</span><strong>129m</strong></div>
          <i><span></span></i>
          <p>超出阈值 12.4%</p>
        </div>
        <div class="v2-source-list">
          <span><i></i>电警视频</span><span><i></i>地磁检测</span>
          <span><i></i>互联网路况</span><span><i></i>信号控制</span>
        </div>
      </template>

      <template v-else-if="activeStage === 2">
        <div class="v2-causal-chain">
          <article><span>上游连续到达</span><strong>前两跳贡献 57.9%</strong></article>
          <i>＋</i>
          <article><span>目标有效放行不足</span><strong>绿灯利用率 54.2%</strong></article>
          <i>＝</i>
          <article class="critical"><span>北进口排队增长</span><strong>129m · 溢流风险</strong></article>
        </div>
        <div class="v2-exclusion">
          <span>已排除</span>
          <div><strong>下游不是病因</strong><p>占有率 42%，仍有约 168m 储车空间</p></div>
        </div>
        <div class="v2-conclusion-block warning">
          <small>研判结论</small>
          <strong>先补足目标方向放行，再用上游削峰降低到达强度</strong>
        </div>
      </template>

      <template v-else-if="activeStage === 3">
        <div class="v2-generation-time">
          <div><span>人工调参</span><b>{{ plan?.manualBaselineMinutes ?? 20 }}<small>分钟</small></b></div>
          <i>VS</i>
          <div><span>智能体测算</span><strong>{{ plan?.generationSeconds ?? 12.4 }}<small>秒</small></strong></div>
        </div>
        <div class="v2-plan-options">
          <article v-for="item in plan?.options" :key="item.id" :class="{ recommended: item.recommended }">
            <header><span>{{ item.name }}</span><b>{{ item.recommended ? '推荐' : '对照' }}</b></header>
            <p>{{ item.summary }}</p>
            <footer><span>目标 +{{ item.targetGreenDeltaSeconds }}s</span><span>上游削峰 {{ item.upstreamMeteringPct }}%</span></footer>
          </article>
        </div>
        <div class="v2-conclusion-block action">
          <small>生成结论</small>
          <strong>适度加放 + 上游削峰 + 下游协调</strong>
          <p>三套方案同屏对比，组合方案进入落地评估。</p>
        </div>
      </template>

      <template v-else-if="activeStage === 4">
        <div class="v2-deployment-card">
          <span class="v2-deploy-state"><i></i> 已下发并生效</span>
          <strong>解放东路 × 奥体西路信号机</strong>
          <p>{{ plan?.deployment.effectiveAt }}</p>
          <div>
            <span><small>北进口直行</small><b>+4s</b></span>
            <span><small>上游削峰</small><b>12%</b></span>
            <span><small>下游协调</small><b>8s</b></span>
          </div>
        </div>
        <div class="v2-guardrails">
          <strong>自动回退护栏</strong>
          <span v-for="item in plan?.deployment.rollbackConditions" :key="item"><i>!</i>{{ item }}</span>
        </div>
        <div class="v2-execution-timeline">
          <span class="done"><i>✓</i><b>方案评估</b><small>12.4s</small></span>
          <span class="done"><i>✓</i><b>安全校核</b><small>通过</small></span>
          <span class="active"><i></i><b>效果跟踪</b><small>3 周期</small></span>
        </div>
      </template>

      <template v-else-if="activeStage === 5">
        <div class="v2-peak-chart">
          <header><strong>晚高峰逐周期验证</strong><span><i></i>执行前 <i></i>执行后</span></header>
          <div class="v2-chart-body">
            <article v-for="item in effectPeakRows" :key="item.hour">
              <div>
                <span class="before" :style="{ height: `${item.before / maxQueue * 100}%` }"></span>
                <span class="after" :style="{ height: `${item.after / maxQueue * 100}%` }"></span>
              </div>
              <small>{{ item.hour.slice(0, 2) }}</small>
            </article>
          </div>
        </div>
        <div class="v2-safe-results">
          <span><small>东西向</small><strong>71m</strong><b>&lt; 92m</b></span>
          <span><small>下游占有率</small><strong>55%</strong><b>&lt; 65%</b></span>
          <span><small>验证周期</small><strong>3</strong><b>持续稳定</b></span>
        </div>
        <div class="v2-conclusion-block success">
          <small>效果结论</small>
          <strong>改善持续成立，未产生压力转移和后期反弹</strong>
        </div>
      </template>

      <template v-else>
        <div class="v2-learning-loop">
          <article v-for="(item, index) in experiences?.pipeline" :key="item.name">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div><strong>{{ item.name }}</strong><small>{{ item.status }}</small></div>
            <b>{{ item.count }}</b>
            <i v-if="index < (experiences?.pipeline.length ?? 0) - 1">↓</i>
          </article>
        </div>
        <div v-if="experiences?.featured[0]" class="v2-featured-experience">
          <small>本次新增代表经验</small>
          <strong>{{ experiences.featured[0].title }}</strong>
          <p>{{ experiences.featured[0].result }}</p>
          <div><span v-for="tag in experiences.featured[0].tags" :key="tag">{{ tag }}</span></div>
        </div>
        <div class="v2-conclusion-block success">
          <small>闭环结论</small>
          <strong>有效过程回流知识库，下一次研判更快、更准</strong>
        </div>
      </template>
    </aside>

    <footer class="v2-presentation-control">
      <button class="previous" @click="goPrevious">← {{ activeStage === 1 ? '返回扫描首页' : '上一阶段' }}</button>
      <div>
        <span>讲解提示</span>
        <strong>{{ activeStageMeta.cue }}</strong>
        <small>{{ activeStageMeta.next }}</small>
      </div>
      <button class="next" @click="goNext">{{ activeStage === 6 ? '完成并返回首页' : '下一阶段' }} →</button>
    </footer>
  </section>
</template>
