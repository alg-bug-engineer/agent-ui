<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { dataRepository } from '../services/dataRepository'
import type {
  ActId,
  ChannelizationScene,
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
type TaskBoardTab = 'anomaly' | 'optimizing' | 'completed'
type Severity = 'critical' | 'major' | 'warning' | 'watch'

const Act6Report = defineAsyncComponent(() => import('../../act6/Act6Report.vue'))

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

interface AnomalyTask {
  id: string
  intersection: string
  problem: string
  evidence: string
  severity: Severity
  severityLabel: string
  detectedAt: string
  score: number
}

interface OptimizingTask {
  id: string
  intersection: string
  stage: string
  action: string
  progress: number
  eta: string
  tone: 'analysis' | 'action' | 'verification'
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
const channelization = ref<ChannelizationScene | null>(null)
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
const taskBoardTab = ref<TaskBoardTab>('anomaly')
const selectedPlanId = ref('')
const selectedCaseId = ref('')

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
    cue: '运行要点：实时采集流量、排队、延误等 10 余项指标，完成路口认知与异常核验。',
    next: '下一页：智能研判如何确认问题',
  },
  {
    id: 2,
    label: '智能研判',
    en: 'INTELLIGENT DIAGNOSIS',
    statement: '上游连续来车叠加有效放行不足，形成北进口溢流风险',
    cue: '运行要点：融合拓扑、流量来源与问题验证，确认溢流积压和相位空放的直接成因。',
    next: '下一页：调用案例与规则生成方案',
  },
  {
    id: 3,
    label: '方案生成',
    en: 'PLAN GENERATION',
    statement: '案例、专家规则与信控模型共同生成三套候选方案',
    cue: '运行要点：检索相似案例与专家规则，联动专业模型生成并对比周期、绿信比和相位差。',
    next: '下一页：方案评估并落地执行',
  },
  {
    id: 4,
    label: '落地执行',
    en: 'DEPLOYMENT',
    statement: '组合方案通过安全边界校核，绑定护栏后下发信号机',
    cue: '运行要点：完成方案影响评估、安全校核、信号下发和自动回退保护。',
    next: '下一页：查看执行前后效果',
  },
  {
    id: 5,
    label: '效果优化',
    en: 'EFFECT OPTIMIZATION',
    statement: '排队由 129 米下降至 78 米，晚高峰持续低于原有基线',
    cue: '运行要点：持续核验高峰排队、延误和绿灯利用率，确认改善稳定且未发生压力转移。',
    next: '下一页：复盘沉淀为长期经验',
  },
  {
    id: 6,
    label: '持续优化',
    en: 'CONTINUOUS LEARNING',
    statement: '每次处置形成可追溯记录，有效策略持续回流知识库',
    cue: '运行要点：有效处置过程沉淀为长期经验，形成“发现—处置—验证—学习”的持续进化闭环。',
    next: '闭环完成 · 可返回首页继续扫描',
  },
]

const stageDimensions: Partial<Record<ActId, Array<{ name: string; detail: string }>>> = {
  1: [
    { name: '路口认知', detail: '路网 · 方向 · 设备' },
    { name: '异常核验', detail: '指标 · 阈值 · 周期' },
  ],
  2: [
    { name: '拓扑结构', detail: '目标 · 冲突 · 上下游' },
    { name: '流量溯源', detail: '六跳来源 · 贡献占比' },
    { name: '问题验证', detail: '假设核验 · 病因排除' },
  ],
  3: [
    { name: '案例检索', detail: '标签 · 语义 · 效果' },
    { name: '参数生成', detail: '周期 · 绿信比 · 相位差' },
    { name: '方案对比', detail: '目标改善 · 网络副作用' },
  ],
  4: [
    { name: '方案评估', detail: '影响预估 · 安全校核' },
    { name: '落地执行', detail: '信号下发 · 回退护栏' },
  ],
  5: [
    { name: '前后对比', detail: '排队 · 延误 · 效率' },
    { name: '晚高峰验证', detail: '逐周期 · 无反弹' },
  ],
}

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

const anomalyTasks: AnomalyTask[] = [
  {
    id: 'anomaly-jiefang-aoti',
    intersection: '解放东路 × 奥体西路',
    problem: '北进口排队连续增长',
    evidence: '排队 129m / 动态阈值 114.8m · 连续 3 周期',
    severity: 'critical',
    severityLabel: '严重',
    detectedAt: '18:06',
    score: 98,
  },
  {
    id: 'anomaly-aoti-gongye',
    intersection: '奥体西路 × 工业南路',
    problem: '晚高峰相位空放',
    evidence: '绿灯利用率 51.6% · 南北向需求持续增长',
    severity: 'major',
    severityLabel: '较重',
    detectedAt: '18:04',
    score: 86,
  },
  {
    id: 'anomaly-qichuan-jiefang',
    intersection: '齐川路 × 解放东路',
    problem: '东进口排队增长',
    evidence: '当前排队 103m · 较同期上升 21.4%',
    severity: 'warning',
    severityLabel: '一般',
    detectedAt: '18:02',
    score: 73,
  },
  {
    id: 'anomaly-aotizhong-qingfeng',
    intersection: '奥体中路 × 轻风路',
    problem: '进口道饱和度偏高',
    evidence: '饱和度 0.81 · 尚未突破动态阈值',
    severity: 'watch',
    severityLabel: '关注',
    detectedAt: '17:58',
    score: 61,
  },
]

const optimizingTasks: OptimizingTask[] = [
  {
    id: 'optimizing-aotizhong-jiefang',
    intersection: '奥体中路 × 解放东路',
    stage: '落地执行',
    action: '绿波协调参数已下发，正在验证连续 3 个周期',
    progress: 78,
    eta: '预计 42 秒',
    tone: 'verification',
  },
  {
    id: 'optimizing-gongye-aoti',
    intersection: '工业南路 × 奥体西路',
    stage: '方案生成',
    action: '正在对比单点加绿、上游削峰与协同组合',
    progress: 52,
    eta: '预计 8 秒',
    tone: 'action',
  },
  {
    id: 'optimizing-tianchen-shunhua',
    intersection: '天辰路 × 舜华路',
    stage: '智能研判',
    action: '正在核验下游承接空间与上游流量贡献',
    progress: 31,
    eta: '预计 15 秒',
    tone: 'analysis',
  },
]

const sortedAnomalyTasks = computed(() =>
  [...anomalyTasks].sort((left, right) => right.score - left.score),
)

const activeStageMeta = computed(() => stages[props.activeStage - 1])
const selectedAsset = computed(
  () => knowledgeAssets.find((item) => item.id === selectedAssetId.value) ?? knowledgeAssets[0],
)
const activeDimensions = computed(() => stageDimensions[props.activeStage] ?? [])
const onlineDeviceCount = computed(() => devices.value.filter((item) => item.status === 'online').length)
const entranceLaneCount = computed(() =>
  channelization.value?.links
    .filter((item) => item.role === 'entrance')
    .reduce((sum, item) => sum + item.laneCount, 0) ?? 16,
)
const recommendedPlan = computed(() => plan.value?.options.find((item) => item.recommended))
const selectedPlan = computed(() =>
  plan.value?.options.find((item) => item.id === selectedPlanId.value)
  ?? recommendedPlan.value
  ?? plan.value?.options[0],
)
const recommendedImpact = computed(() =>
  plan.value?.impacts.find((item) => item.optionId === recommendedPlan.value?.id),
)
const selectedPlanImpact = computed(() =>
  plan.value?.impacts.find((item) => item.optionId === selectedPlan.value?.id)
  ?? recommendedImpact.value,
)
const selectedCase = computed(() =>
  cases.value.find((item) => item.id === selectedCaseId.value) ?? cases.value[0],
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

watch(
  () => props.view,
  (view) => {
    if (view === 'home') taskBoardTab.value = 'anomaly'
  },
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
    channelizationData,
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
    dataRepository.channelization(),
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
  channelization.value = channelizationData
  devices.value = deviceData
  metrics.value = metricData
  trace.value = traceData
  diagnosis.value = diagnosisData
  knowledgeBase.value = knowledgeData
  cases.value = caseData
  selectedCaseId.value = caseData[0]?.id ?? ''
  plan.value = planData
  selectedPlanId.value = planData.options.find((item) => item.recommended)?.id
    ?? planData.options[0]?.id
    ?? ''
  effect.value = effectData
  daily.value = dailyData
  experiences.value = experienceData as unknown as ExperienceData
})
</script>

<template>
  <section v-if="view === 'home'" class="v2-home-experience">
    <aside class="v2-panel v2-task-rail">
      <div class="v2-panel-cap">
        <span><i></i> AGENT MONITORING BOARD</span>
        <b>智能体监控覆盖</b>
        <small>LIVE</small>
      </div>

      <section class="v2-monitoring-overview">
        <header>
          <div>
            <small>奥体片区 · 常态运行</small>
            <strong>持续扫描中</strong>
          </div>
          <span><i></i> 2.4s 刷新</span>
        </header>
        <div class="v2-coverage-metrics">
          <article>
            <strong>1</strong>
            <span>监控区域</span>
            <small>重点片区</small>
          </article>
          <article>
            <strong>4</strong>
            <span>感知链路</span>
            <small>4 / 4 在线</small>
          </article>
          <article>
            <strong>12</strong>
            <span>扫描路口</span>
            <small>优化中 3</small>
          </article>
        </div>
      </section>

      <div class="v2-network-kpis">
        <span><small>均速</small><strong>24.6</strong><b>km/h</b></span>
        <span><small>延误</small><strong>68</strong><b>s</b></span>
        <span><small>拥堵指数</small><strong>3.8</strong></span>
        <span><small>闭环率</small><strong>96.8</strong><b>%</b></span>
      </div>

      <nav class="v2-task-tabs" aria-label="智能体任务状态">
        <button
          :class="{ active: taskBoardTab === 'anomaly' }"
          @click="taskBoardTab = 'anomaly'"
        >
          <span>⚡</span>动态异常<b>{{ anomalyTasks.length }}</b>
        </button>
        <button
          :class="{ active: taskBoardTab === 'optimizing' }"
          @click="taskBoardTab = 'optimizing'"
        >
          <span>↻</span>优化中<b>{{ optimizingTasks.length }}</b>
        </button>
        <button
          :class="{ active: taskBoardTab === 'completed' }"
          @click="taskBoardTab = 'completed'"
        >
          <span>✓</span>已完成<b>180</b>
        </button>
      </nav>

      <div class="v2-task-list">
        <template v-if="taskBoardTab === 'anomaly'">
          <div class="v2-task-list-heading">
            <span>扫描区域异常路口</span>
            <small>按问题严重程度排序</small>
          </div>
          <article
            v-for="(item, index) in sortedAnomalyTasks"
            :key="item.id"
            :class="['v2-anomaly-item', item.severity]"
          >
            <i></i>
            <div>
              <header>
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <strong>{{ item.intersection }}</strong>
                <b>{{ item.severityLabel }}</b>
              </header>
              <p>{{ item.problem }}</p>
              <small>{{ item.evidence }}</small>
            </div>
            <time>{{ item.detectedAt }}</time>
          </article>
        </template>

        <template v-else-if="taskBoardTab === 'optimizing'">
          <div class="v2-task-list-heading">
            <span>智能体正在处置</span>
            <small>按当前闭环阶段展示</small>
          </div>
          <article
            v-for="item in optimizingTasks"
            :key="item.id"
            :class="['v2-optimizing-item', item.tone]"
          >
            <header>
              <span>{{ item.stage }}</span>
              <strong>{{ item.intersection }}</strong>
              <b>{{ item.progress }}%</b>
            </header>
            <p>{{ item.action }}</p>
            <div><i :style="{ width: `${item.progress}%` }"></i></div>
            <footer><span>AI 自主优化</span><small>{{ item.eta }}</small></footer>
          </article>
        </template>

        <template v-else>
          <div class="v2-task-list-heading">
            <span>已完成闭环任务</span>
            <small>点击代表任务查看完整闭环</small>
          </div>
          <button class="v2-completed-task v2-completed-entry" @click="emit('start')">
            <span class="v2-task-status">重点闭环任务</span>
            <small>18:21 · 晚高峰溢流治理</small>
            <strong>解放东路 × 奥体西路</strong>
            <p>自主完成感知、研判、方案生成、执行与效果评估。</p>
            <div class="v2-task-result">
              <span><small>北进口排队</small><b>129m</b></span>
              <i>→</i>
              <strong>78m</strong>
            </div>
            <footer><span>已验证 3 个周期 · 未触发回退</span><b>查看处置详情 →</b></footer>
          </button>
        </template>
      </div>

      <footer class="v2-task-board-foot">
        <span><i></i> 45 项异常已发现</span>
        <span><i></i> 24 小时持续监测</span>
      </footer>
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
        <span>操作提示：切换左侧“已完成”，点击重点任务查看全流程处置记录</span>
        <b>支持键盘输入主动任务</b>
      </div>
    </div>
  </section>

  <section v-else-if="activeStage === 6" class="v2-review-experience">
    <Act6Report />
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
        <div class="v2-dimension-banner">
          <small>指标分析维度</small>
          <div>
            <span v-for="item in activeDimensions" :key="item.name">
              <strong>{{ item.name }}</strong><b>{{ item.detail }}</b>
            </span>
          </div>
        </div>
        <div class="v2-target-card">
          <small>当前治理对象</small>
          <strong>{{ target?.name ?? '解放东路与奥体西路交叉口' }}</strong>
          <p>晚高峰 · 北进口向南直行 · 溢流风险</p>
        </div>
        <div class="v2-cognition-grid">
          <article>
            <span>进口车道</span><strong>{{ entranceLaneCount }}<small>条</small></strong><p>十字路口 · 4 相位</p>
          </article>
          <article>
            <span>感知设备</span><strong>{{ onlineDeviceCount }}<small>台在线</small></strong><p>覆盖率 91.7%</p>
          </article>
          <article>
            <span>目标方向</span><strong>北进口</strong><p>向南直行</p>
          </article>
          <article>
            <span>融合数据</span><strong>4<small>类</small></strong><p>视频 / 地磁 / 路况 / 信号</p>
          </article>
        </div>
        <div class="v2-section-title"><span>实时异常指标</span><b>4 项同步核验</b></div>
        <div class="v2-metric-stack">
          <article v-for="metric in metrics" :key="metric.id" :class="metric.status">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}<small>{{ metric.unit }}</small></strong>
            <p>{{ metric.trend }}</p>
          </article>
        </div>
      </template>

      <template v-else-if="activeStage === 2">
        <div class="v2-dimension-banner three">
          <small>指标分析维度</small>
          <div>
            <span v-for="item in activeDimensions" :key="item.name">
              <strong>{{ item.name }}</strong><b>{{ item.detail }}</b>
            </span>
          </div>
        </div>
        <div class="v2-section-title v2-topology-title"><span>专家空间拓扑</span><b>四类角色同屏研判</b></div>
        <div class="v2-direction-facts">
          <article v-for="item in diagnosis?.directions" :key="item.id" :class="item.tone">
            <header><small>{{ item.role }}</small><b>{{ item.tone === 'critical' ? '重点' : item.tone === 'warning' ? '关注' : '正常' }}</b></header>
            <strong>{{ item.label }}</strong>
            <div>{{ item.primaryMetric }}</div>
            <p>{{ item.secondaryMetric }}</p>
            <footer>{{ item.assessment }}</footer>
          </article>
        </div>
        <div class="v2-topology-path">
          <span><small>上游来源</small><strong>57.9%</strong></span>
          <i>→</i>
          <span class="target"><small>目标路口</small><strong>129m</strong></span>
          <i>→</i>
          <span><small>下游承接</small><strong>42%</strong></span>
          <b><small>垂直冲突</small>63m / 警戒 92m</b>
        </div>
        <ol class="v2-analysis-chain">
          <li>
            <span>01</span><div><strong>拓扑关系</strong><p>目标、冲突、上游与下游建立空间关联</p></div><b>已建立</b>
          </li>
          <li>
            <span>02</span><div><strong>流量溯源</strong><p>六跳主走廊累计解释 {{ trace?.summary.coveredSharePct.toFixed(1) ?? '92.0' }}%</p></div><b>已完成</b>
          </li>
          <li>
            <span>03</span><div><strong>问题验证</strong><p>逐项核验放行不足、到达波与下游承接</p></div><b>已确认</b>
          </li>
        </ol>
      </template>

      <template v-else-if="activeStage === 3">
        <div class="v2-dimension-banner three">
          <small>指标分析维度</small>
          <div>
            <span v-for="item in activeDimensions" :key="item.name">
              <strong>{{ item.name }}</strong><b>{{ item.detail }}</b>
            </span>
          </div>
        </div>
        <div class="v2-recall-summary">
          <span>案例检索完成</span>
          <strong>{{ knowledgeBase?.matchLatencySeconds ?? 1.8 }}<small>秒</small></strong>
          <p>命中 {{ knowledgeBase?.matchedCaseCount ?? 37 }} 个高相似案例与适用专家规则</p>
        </div>
        <div class="v2-case-selector">
          <button
            v-for="item in cases"
            :key="item.id"
            :class="{ active: item.id === selectedCase?.id }"
            @click="selectedCaseId = item.id"
          >
            <span>{{ item.matchScore }}<small>%</small></span>
            <div><small>{{ item.location }}</small><strong>{{ item.title }}</strong></div>
          </button>
        </div>
        <article v-if="selectedCase" class="v2-case-dossier">
          <header>
            <div><small>案例 {{ selectedCase.caseId }} · 完整处置链</small><strong>{{ selectedCase.title }}</strong></div>
            <span>{{ selectedCase.matchScore }}%<small>综合匹配</small></span>
          </header>
          <div class="v2-case-match-groups">
            <section>
              <b>标签命中</b>
              <div><span v-for="item in selectedCase.hitTags.slice(0, 4)" :key="`${item.dimension}-${item.value}`">{{ item.value }}</span></div>
            </section>
            <section>
              <b>语义命中</b>
              <div><span v-for="item in selectedCase.hitSemantics.slice(0, 3)" :key="`${item.dimension}-${item.value}`">{{ item.value }}</span></div>
            </section>
          </div>
          <dl>
            <div><dt>场景</dt><dd>{{ selectedCase.scenario }}</dd></div>
            <div><dt>诊断</dt><dd>{{ selectedCase.diagnosis }}</dd></div>
            <div><dt>治理</dt><dd>{{ selectedCase.treatment }}</dd></div>
            <div class="result"><dt>效果</dt><dd>{{ selectedCase.effect }}</dd></div>
          </dl>
          <footer><span>来源：{{ selectedCase.source.account }}</span><b>已通过知识质量校验</b></footer>
        </article>
      </template>

      <template v-else-if="activeStage === 4">
        <div class="v2-dimension-banner">
          <small>指标分析维度</small>
          <div>
            <span v-for="item in activeDimensions" :key="item.name">
              <strong>{{ item.name }}</strong><b>{{ item.detail }}</b>
            </span>
          </div>
        </div>
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
        <div class="v2-readiness-grid">
          <article><span>参数完整性</span><strong>100%</strong><small>周期 / 绿信比 / 相位差</small></article>
          <article><span>影响校核</span><strong>4 / 4</strong><small>目标、冲突、上游、下游</small></article>
          <article><span>控制器链路</span><strong>在线</strong><small>SC-011WWE28FMC00001</small></article>
          <article><span>回退策略</span><strong>3 条</strong><small>阈值触发 · 自动恢复</small></article>
        </div>
      </template>

      <template v-else-if="activeStage === 5">
        <div class="v2-dimension-banner">
          <small>指标分析维度</small>
          <div>
            <span v-for="item in activeDimensions" :key="item.name">
              <strong>{{ item.name }}</strong><b>{{ item.detail }}</b>
            </span>
          </div>
        </div>
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
        <div class="v2-verification-window">
          <header><strong>连续周期效果确认</strong><span>未触发回退</span></header>
          <div>
            <span><small>周期 01</small><b>86m</b><em>稳定</em></span>
            <span><small>周期 02</small><b>81m</b><em>稳定</em></span>
            <span><small>周期 03</small><b>78m</b><em>稳定</em></span>
          </div>
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
        <small>DECISION VIEW</small>
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
        <div class="v2-cycle-verification">
          <header><strong>连续周期核验</strong><span>动态阈值 114.8m</span></header>
          <div>
            <article><i style="height: 74%"></i><span>T-2</span><b>118m</b></article>
            <article><i style="height: 86%"></i><span>T-1</span><b>124m</b></article>
            <article class="critical"><i style="height: 100%"></i><span>当前</span><b>129m</b></article>
          </div>
          <p>视频队尾、地磁流量与信号相位数据一致，异常置信度 <strong>96.4%</strong></p>
        </div>
        <div class="v2-source-list">
          <span><i></i><b>电警视频</b>队尾定位</span><span><i></i><b>地磁检测</b>流量校验</span>
          <span><i></i><b>互联网路况</b>速度验证</span><span><i></i><b>信号控制</b>相位对齐</span>
        </div>
      </template>

      <template v-else-if="activeStage === 2">
        <div class="v2-trace-summary">
          <header>
            <div><small>上游流量溯源</small><strong>{{ trace?.summary.dominantSource ?? '奥体西路北侧连续来车波' }}</strong></div>
            <span>{{ trace?.summary.coveredSharePct.toFixed(1) ?? '92.0' }}<small>%</small></span>
          </header>
          <div>
            <span v-for="item in trace?.mainCorridorChain.slice(0, 3)" :key="item.nodeId">
              <b>第 {{ item.hop }} 跳</b><strong>{{ item.sharePct }}%</strong>
            </span>
          </div>
          <p>轻风路、工业南路等支路汇入主走廊，形成连续到达波。</p>
        </div>
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
        <div class="v2-hypothesis-grid">
          <article
            v-for="item in diagnosis?.hypotheses"
            :key="item.id"
            :class="{ supported: item.supported }"
          >
            <span>{{ item.supported ? '成立' : '排除' }}</span>
            <div><strong>{{ item.question }}</strong><p>{{ item.evidence }}</p></div>
          </article>
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
        <div class="v2-timing-parameters">
          <header><strong>配时参数生成</strong><span>12.4 秒完成测算</span></header>
          <div class="v2-parameter-head">
            <span>相位</span><span>当前</span><span>建议</span><span>变化</span>
          </div>
          <div v-for="phase in plan?.recommended.phases" :key="phase.name" class="v2-parameter-row">
            <strong>{{ phase.name }}</strong>
            <span>{{ phase.currentGreen }}s</span>
            <b>{{ phase.proposedGreen }}s</b>
            <em :class="{ changed: phase.currentGreen !== phase.proposedGreen }">
              {{ phase.proposedGreen === phase.currentGreen ? '保持' : `${phase.proposedGreen - phase.currentGreen > 0 ? '+' : ''}${phase.proposedGreen - phase.currentGreen}s` }}
            </em>
          </div>
          <footer><span>周期 <b>{{ plan?.recommended.cycleSeconds }}s</b></span><span>相位差 <b>+{{ plan?.recommended.phaseDiffSeconds }}s</b></span></footer>
        </div>
        <div class="v2-plan-options">
          <article
            v-for="item in plan?.options"
            :key="item.id"
            :class="{ recommended: item.recommended, active: item.id === selectedPlan?.id }"
            @click="selectedPlanId = item.id"
          >
            <header><span>{{ item.name }}</span><b>{{ item.recommended ? '推荐' : '对照' }}</b></header>
            <p>{{ item.summary }}</p>
            <footer><span>目标 +{{ item.targetGreenDeltaSeconds }}s</span><span>上游削峰 {{ item.upstreamMeteringPct }}%</span></footer>
          </article>
        </div>
        <div v-if="selectedPlanImpact" class="v2-plan-impact-preview">
          <header><strong>{{ selectedPlan?.name }} · 影响对比</strong><span>点击上方方案切换</span></header>
          <div>
            <span><small>北进口</small><b>{{ selectedPlanImpact.target.before }}</b><i>→</i><strong>{{ selectedPlanImpact.target.after }}</strong></span>
            <span><small>东西向</small><b>{{ selectedPlanImpact.conflict.before }}</b><i>→</i><strong>{{ selectedPlanImpact.conflict.after }}</strong></span>
            <span><small>下游</small><b>{{ selectedPlanImpact.downstream.before }}</b><i>→</i><strong>{{ selectedPlanImpact.downstream.after }}</strong></span>
          </div>
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
        <div class="v2-command-receipt">
          <header><span><i></i> 控制指令回执</span><strong>签名校验通过</strong></header>
          <div><span>策略版本<b>V2026.07.29-03</b></span><span>任务编号<b>OPT-3701-0186</b></span></div>
          <footer><span>生效窗口</span><strong>17:00—19:10</strong><b>状态同步正常</b></footer>
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
        <span>运行摘要</span>
        <strong>{{ activeStageMeta.cue }}</strong>
        <small>{{ activeStageMeta.next }}</small>
      </div>
      <button class="next" @click="goNext">下一阶段 →</button>
    </footer>
  </section>
</template>
