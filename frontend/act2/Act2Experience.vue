<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type {
  ChannelizationScene,
  DevicePoint,
  ExpertDiagnosis,
  FlowTraceScene,
  MetricItem,
  TargetIntersection,
} from '../src/types'

const props = defineProps<{ paused: boolean }>()
const emit = defineEmits<{
  beat: [value: string]
  openReport: []
}>()

const beats = [
  {
    id: 'cognition',
    title: '路口认知',
    subtitle: '先看清路、方向与感知条件',
    duration: 5.8,
  },
  {
    id: 'direction',
    title: '方向拆解',
    subtitle: '主方向、垂直、下游、上游',
    duration: 6.2,
  },
  {
    id: 'evidence',
    title: '异常核验',
    subtitle: '指标、阈值与现场交叉验证',
    duration: 6.5,
  },
  {
    id: 'cause',
    title: '溢流判因',
    subtitle: '逐项验证，不凭直觉下结论',
    duration: 6.8,
  },
  {
    id: 'constraints',
    title: '约束检查',
    subtitle: '先划安全边界，再谈怎么调',
    duration: 6.4,
  },
  {
    id: 'options',
    title: '方案生成',
    subtitle: '目标缓解与网络副作用并列',
    duration: 7,
  },
  {
    id: 'simulation',
    title: '反事实推演',
    subtitle: '比较“不调、只加绿、组合调控”',
    duration: 8,
  },
  {
    id: 'decision',
    title: '专家决策',
    subtitle: '动作、依据、护栏同时交付',
    duration: 7.2,
  },
  {
    id: 'trace',
    title: '源头治理',
    subtitle: '把方案落到具体上游节点',
    duration: 9,
  },
] as const

const currentIndex = ref(0)
const elapsed = ref(0)
const target = ref<TargetIntersection | null>(null)
const devices = ref<DevicePoint[]>([])
const metrics = ref<MetricItem[]>([])
const flowTrace = ref<FlowTraceScene | null>(null)
const channelization = ref<ChannelizationScene | null>(null)
const diagnosis = ref<ExpertDiagnosis | null>(null)
const expandedEvidence = ref(false)
let timer = 0

const current = computed(() => beats[currentIndex.value])
const completed = computed(() =>
  currentIndex.value === beats.length - 1 && elapsed.value >= current.value.duration,
)
const overallProgress = computed(() => {
  const done = beats.slice(0, currentIndex.value).reduce((sum, beat) => sum + beat.duration, 0)
  const total = beats.reduce((sum, beat) => sum + beat.duration, 0)
  return Math.min(100, ((done + elapsed.value) / total) * 100)
})

const channelStats = computed(() => {
  const entrances = channelization.value?.links.filter((link) => link.role === 'entrance') ?? []
  const exits = channelization.value?.links.filter((link) => link.role === 'exit') ?? []
  return {
    entrances: entrances.length,
    entranceLanes: entrances.reduce((sum, link) => sum + link.laneCount, 0),
    exitLanes: exits.reduce((sum, link) => sum + link.laneCount, 0),
    northLaneInfo: entrances.find((link) => link.direction === '北进口')?.laneInfo.join(' · ') ?? '—',
  }
})

const onlineDeviceCount = computed(() =>
  devices.value.filter((item) => item.status === 'online').length,
)
function selectBeat(index: number) {
  currentIndex.value = index
  elapsed.value = 0
  emit('beat', beats[index].id)
}

onMounted(async () => {
  const [targetData, deviceData, metricData, traceData, channelData, diagnosisData] =
    await Promise.all([
      dataRepository.targetIntersection(),
      dataRepository.devices(),
      dataRepository.metrics(),
      dataRepository.flowTrace(),
      dataRepository.channelization(),
      dataRepository.expertDiagnosis(),
    ])
  target.value = targetData
  devices.value = deviceData
  metrics.value = metricData
  flowTrace.value = traceData
  channelization.value = channelData
  diagnosis.value = diagnosisData
  emit('beat', current.value.id)
  timer = window.setInterval(() => {
    if (props.paused || completed.value) return
    elapsed.value += 0.1
    if (elapsed.value >= current.value.duration && currentIndex.value < beats.length - 1) {
      currentIndex.value += 1
      elapsed.value = 0
      emit('beat', current.value.id)
    }
  }, 100)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="act-experience act2-experience">
    <aside class="glass-panel agent-dock reasoning-panel">
      <div class="dock-cap">
        <span class="dock-live"><i></i> EXPERT REASONING</span>
        <b>专家研判链</b>
        <small>{{ String(currentIndex + 1).padStart(2, '0') }} / {{ String(beats.length).padStart(2, '0') }}</small>
      </div>

      <div class="diagnosis-title">
        <div class="agent-emblem"><span></span><span></span><span></span></div>
        <div>
          <h2>溢流风险诊断</h2>
          <p>{{ target?.name ?? '正在加载目标路口' }}</p>
        </div>
      </div>

      <div class="reasoning-progress">
        <span :style="{ width: `${overallProgress}%` }"></span>
      </div>

      <ol class="reasoning-steps">
        <li
          v-for="(item, index) in beats"
          :key="item.id"
          :class="{ active: index === currentIndex, done: index < currentIndex }"
          @click="selectBeat(index)"
        >
          <span class="step-index">{{ index < currentIndex ? '✓' : String(index + 1).padStart(2, '0') }}</span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.subtitle }}</small>
          </div>
          <i v-if="index === currentIndex"></i>
        </li>
      </ol>

      <div class="reasoning-footer">
        <span class="live-dot"></span>
        {{ completed ? '诊断完成 · 已形成策略与安全护栏' : `研判进行中 · ${current.title}` }}
      </div>
    </aside>

    <aside class="glass-panel agent-dock evidence-panel">
      <div class="dock-cap evidence-cap">
        <span class="dock-live"><i></i> ANALYSIS WORKBENCH</span>
        <b>{{ current.title }}</b>
        <small>LIVE</small>
      </div>

      <template v-if="current.id === 'cognition'">
        <div class="evidence-heading"><span>先认知，再诊断</span><b>01</b></div>
        <div class="target-card">
          <small>诊断对象 · 真实路网快照</small>
          <h2>{{ target?.name }}</h2>
          <p>{{ target?.problemApproach }} · {{ target?.problemMovement }}</p>
        </div>
        <div class="cognition-axis">
          <div class="axis-primary">
            <span>分析方向</span>
            <strong>北进口 → 向南直行</strong>
            <small>{{ channelStats.northLaneInfo }} · 4 条进口车道</small>
          </div>
          <div>
            <span>垂直方向</span>
            <strong>解放东路东西向</strong>
            <small>加绿时必须同步评估</small>
          </div>
          <div>
            <span>下游</span>
            <strong>南侧坤顺路方向</strong>
            <small>检查承接与回溢风险</small>
          </div>
          <div>
            <span>上游</span>
            <strong>轻风路—工业南路</strong>
            <small>检查来车与截流条件</small>
          </div>
        </div>
        <div class="cognition-proof">
          <span><b>{{ channelStats.entranceLanes }}</b> 进口车道</span>
          <span><b>{{ channelStats.exitLanes }}</b> 出口车道</span>
          <span><b>{{ onlineDeviceCount }}</b> 在线设备</span>
          <span><b>91.7%</b> 感知覆盖</span>
        </div>
        <div class="plain-conclusion">
          <b>认知结论</b>
          后续所有判断都围绕四个空间角色展开，不把“北进口排队”孤立看待。
        </div>
      </template>

      <template v-else-if="current.id === 'direction'">
        <div class="evidence-heading"><span>四向运行拆解</span><b>02</b></div>
        <div class="direction-list">
          <article
            v-for="item in diagnosis?.directions"
            :key="item.id"
            :class="['direction-card', item.tone]"
          >
            <div><span>{{ item.role }}</span><strong>{{ item.label }}</strong></div>
            <b>{{ item.primaryMetric }}</b>
            <small>{{ item.secondaryMetric }}</small>
            <p>{{ item.assessment }}</p>
          </article>
        </div>
        <div class="plain-conclusion warning">
          <b>初步判断</b>
          问题集中在北进口，垂直方向和下游尚未失稳；上游连续来车可能在放大排队。
        </div>
      </template>

      <template v-else-if="current.id === 'evidence'">
        <div class="evidence-heading"><span>异常成立性核验</span><b>03</b></div>
        <div class="metric-list compact">
          <div
            v-for="metric in metrics"
            :key="metric.id"
            class="metric-item"
            :class="[metric.status, { emphasis: metric.emphasis }]"
          >
            <div>
              <span>{{ metric.label }}</span>
              <small>{{ metric.trend }}</small>
            </div>
            <strong>{{ metric.value }}<small>{{ metric.unit }}</small></strong>
            <div v-if="metric.threshold" class="threshold">
              动态阈值 {{ metric.threshold }}{{ metric.unit }}
            </div>
          </div>
        </div>
        <button class="video-evidence compact-video" @click="expandedEvidence = true">
          <span class="video-road horizontal"></span>
          <span class="video-road vertical"></span>
          <span class="video-cars"></span>
          <i class="rec-dot"></i>
          <strong>现场画面：排队接近上游开口</strong>
          <small>18:06:32 · 连续 3 周期超阈值</small>
          <b>查看证据</b>
        </button>
        <div class="plain-conclusion critical">
          <b>证据结论</b>
          指标、趋势和现场影像相互印证：这不是单周期波动，排队异常成立。
        </div>
      </template>

      <template v-else-if="current.id === 'cause'">
        <div class="evidence-heading"><span>三类成因逐项验证</span><b>04</b></div>
        <div class="hypothesis-list">
          <article v-for="item in diagnosis?.hypotheses" :key="item.id" :class="{ supported: item.supported }">
            <header>
              <span>{{ item.supported ? '✓ 成立' : '× 排除' }}</span>
              <strong>{{ item.question }}</strong>
            </header>
            <p>{{ item.evidence }}</p>
            <b>{{ item.verdict }}</b>
          </article>
        </div>
        <div class="causal-chain">
          <span>上游连续到达波</span><i>放大</i>
          <span>当前有效放行不足</span><i>导致</i>
          <strong>北进口排队增长</strong>
        </div>
        <div class="plain-conclusion">
          <b>因果结论</b>
          先改善目标方向放行，再用上游削峰压低到达强度；无需把下游当作病因处理。
        </div>
      </template>

      <template v-else-if="current.id === 'constraints'">
        <div class="evidence-heading"><span>调控前先画安全边界</span><b>05</b></div>
        <div class="constraint-grid">
          <article
            v-for="item in diagnosis?.constraints"
            :key="item.label"
            :class="item.tone"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.boundary }}</small>
            <p>{{ item.conclusion }}</p>
          </article>
        </div>
        <div class="boundary-answer">
          <span>目标方向增配</span><strong>具备条件，首轮增加 4 秒</strong>
          <span>垂直方向约束</span><strong>等待将增加，排队控制在 92m 内</strong>
          <span>下游承接约束</span><strong>当前可承接，占有率达到 65% 即停止</strong>
          <span>上游削峰条件</span><strong>具备条件，截流比例控制在 12%</strong>
        </div>
      </template>

      <template v-else-if="current.id === 'options'">
        <div class="evidence-heading"><span>三种策略，不只看目标口</span><b>06</b></div>
        <div class="strategy-list">
          <article
            v-for="item in diagnosis?.options"
            :key="item.id"
            :class="{ recommended: item.recommended }"
          >
            <header>
              <strong>{{ item.name }}</strong>
              <span>{{ item.recommended ? '推荐进入推演' : '对照方案' }}</span>
            </header>
            <h3>{{ item.action }}</h3>
            <div>
              <p><span>目标方向</span>{{ item.targetEffect }}</p>
              <p><span>垂直方向</span>{{ item.conflictEffect }}</p>
              <p><span>下游</span>{{ item.downstreamEffect }}</p>
            </div>
            <footer>{{ item.verdict }}</footer>
          </article>
        </div>
      </template>

      <template v-else-if="current.id === 'simulation'">
        <div class="evidence-heading"><span>执行前反事实推演</span><b>07</b></div>
        <div class="scenario-table">
          <div class="scenario-head">
            <span>方案</span><span>北进口</span><span>东西向</span><span>下游</span><span>风险</span>
          </div>
          <div
            v-for="item in diagnosis?.scenarios"
            :key="item.id"
            :class="['scenario-row', { selected: item.id === 'combined' }]"
          >
            <strong>{{ item.name }}</strong>
            <span>{{ item.targetQueueM }}m</span>
            <span>{{ item.conflictQueueM }}m</span>
            <span>{{ item.downstreamOccupancyPct }}%</span>
            <b :class="`risk-${item.risk}`">{{ item.risk }}</b>
            <p>{{ item.conclusion }}</p>
          </div>
        </div>
        <div class="counterfactual-callout">
          <span>单点加绿风险</span>
          <strong>北进口 +8s 虽降至 88m，却让东西向升至 101m，超过 92m 警戒线。</strong>
        </div>
        <div class="plain-conclusion">
          <b>推演结论</b>
          组合方案不是效果最激进的方案，却是三个方向同时不过界的方案。
        </div>
      </template>

      <template v-else-if="current.id === 'decision'">
        <div class="evidence-heading"><span>专家决策与安全护栏</span><b>08</b></div>
        <div class="decision-card">
          <small>最终建议</small>
          <h2>{{ diagnosis?.recommendation.title }}</h2>
          <ol>
            <li v-for="action in diagnosis?.recommendation.actions" :key="action">{{ action }}</li>
          </ol>
        </div>
        <div class="decision-rationale">
          <span>为什么这样调</span>
          <p>{{ diagnosis?.recommendation.rationale }}</p>
        </div>
        <div class="guardrail-list">
          <strong>自动回退条件</strong>
          <span v-for="item in diagnosis?.recommendation.guardrails" :key="item"><i>!</i>{{ item }}</span>
        </div>
        <div class="expected-outcome">{{ diagnosis?.recommendation.expectedOutcome }}</div>
      </template>

      <template v-else>
        <div class="evidence-heading"><span>上游来源与落点</span><b>09</b></div>
        <div class="trace-summary">
          <span>源头治理优先级</span>
          <strong>{{ flowTrace?.summary.dominantSource }}</strong>
          <small>六跳主走廊累计解释 {{ flowTrace?.summary.coveredSharePct.toFixed(1) }}%</small>
        </div>
        <div class="trace-list complete">
          <div v-for="item in flowTrace?.mainCorridorChain" :key="item.nodeId">
            <b>{{ String(item.hop).padStart(2, '0') }}</b>
            <span>{{ flowTrace?.nodes.find((node) => node.id === item.nodeId)?.name }}</span>
            <strong>{{ item.sharePct.toFixed(1) }}%</strong>
            <i :style="{ width: `${Math.max(8, item.sharePct * 2.5)}%` }"></i>
            <small>累计 {{ item.cumulativePct.toFixed(1) }}%</small>
          </div>
        </div>
        <div class="trace-conclusion">{{ flowTrace?.summary.conclusion }}</div>
        <button class="primary-action report-entry" @click="emit('openReport')">
          <span>进入执行审批与效果追踪</span><b>→</b>
        </button>
      </template>

      <div class="analysis-source">
        <span>数据口径</span>
        <b>{{ diagnosis?.source.roadNetwork }}</b>
        <small>{{ diagnosis?.source.operationalEvidence }}</small>
      </div>
    </aside>

    <div v-if="expandedEvidence" class="evidence-modal" @click.self="expandedEvidence = false">
      <div class="modal-card">
        <button class="modal-close" @click="expandedEvidence = false">×</button>
        <div class="expanded-video">
          <span class="video-road horizontal"></span>
          <span class="video-road vertical"></span>
          <span class="video-cars"></span>
        </div>
        <div>
          <small>多模态证据 · 18:06:32</small>
          <h2>北进口排队已延伸至上游开口</h2>
          <p>现场影像与排队检测数据时间对齐，连续三个信号周期均超过动态阈值。</p>
        </div>
      </div>
    </div>
  </div>
</template>
