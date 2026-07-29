<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type {
  ChannelizationScene,
  DevicePoint,
  ExpertDiagnosis,
  FlowTraceScene,
  MetricItem,
  TargetIntersection,
} from '../src/types'

const emit = defineEmits<{
  beat: [value: string]
  openKnowledge: []
}>()

const beats = [
  {
    id: 'cognition',
    title: '路口认知',
    subtitle: '先看清路、方向与感知条件',
  },
  {
    id: 'evidence',
    title: '异常核验',
    subtitle: '先确认异常是否真实、是否持续',
  },
  {
    id: 'direction',
    title: '路口拓扑分析',
    subtitle: '把目标、冲突方向与上下游放进同一张路网',
  },
  {
    id: 'trace',
    title: '流量溯源',
    subtitle: '沿上游走廊追踪流量来源与贡献',
  },
  {
    id: 'cause',
    title: '问题验证',
    subtitle: '结合流量来源逐项核验问题成因',
  },
] as const

const currentIndex = ref(0)
const target = ref<TargetIntersection | null>(null)
const devices = ref<DevicePoint[]>([])
const metrics = ref<MetricItem[]>([])
const flowTrace = ref<FlowTraceScene | null>(null)
const channelization = ref<ChannelizationScene | null>(null)
const diagnosis = ref<ExpertDiagnosis | null>(null)
const expandedEvidence = ref(false)
const evidencePanel = ref<HTMLElement | null>(null)
const transitionDirection = ref<'forward' | 'backward'>('forward')

const current = computed(() => beats[currentIndex.value])
const stepTransitionName = computed(() => `step-flow-${transitionDirection.value}`)
const stepTrackProgress = computed(() =>
  beats.length <= 1 ? 1 : currentIndex.value / (beats.length - 1),
)
const completed = computed(() => currentIndex.value === beats.length - 1)
const overallProgress = computed(() => ((currentIndex.value + 1) / beats.length) * 100)

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

function moveToBeat(index: number) {
  if (index < 0 || index >= beats.length) return
  transitionDirection.value = index >= currentIndex.value ? 'forward' : 'backward'
  currentIndex.value = index
  emit('beat', beats[index].id)
  void nextTick(() => {
    evidencePanel.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function selectBeat(index: number) {
  moveToBeat(index)
}

function goPrev() {
  if (currentIndex.value > 0) moveToBeat(currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value < beats.length - 1) {
    moveToBeat(currentIndex.value + 1)
    return
  }
  emit('openKnowledge')
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
})
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

      <ol
        class="reasoning-steps"
        :style="{ '--step-track-progress': stepTrackProgress }"
      >
        <li
          v-for="(item, index) in beats"
          :key="item.id"
          :class="{ active: index === currentIndex, done: index < currentIndex }"
          :aria-current="index === currentIndex ? 'step' : undefined"
          role="button"
          tabindex="0"
          @click="selectBeat(index)"
          @keydown.enter="selectBeat(index)"
          @keydown.space.prevent="selectBeat(index)"
        >
          <span class="step-index">{{ index < currentIndex ? '✓' : String(index + 1).padStart(2, '0') }}</span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.subtitle }}</small>
          </div>
          <i v-if="index === currentIndex"></i>
        </li>
      </ol>

      <div class="step-check-bar">
        <div class="step-check-status">
          <span class="live-dot"></span>
          {{ completed ? '问题验证完成 · 诊断结论已确认' : `当前步骤已就绪 · ${current.title}` }}
        </div>
        <div class="step-check-nav">
          <button :disabled="currentIndex === 0" @click="goPrev">← 上一步</button>
          <button class="next-act" @click="goNext">
            {{ completed ? '进入知识匹配 →' : '下一步 →' }}
          </button>
        </div>
      </div>
    </aside>

    <aside ref="evidencePanel" class="glass-panel agent-dock evidence-panel">
      <div class="dock-cap evidence-cap">
        <span class="dock-live"><i></i> ANALYSIS WORKBENCH</span>
        <Transition name="step-label">
          <b :key="current.id">{{ current.title }}</b>
        </Transition>
        <small>LIVE</small>
      </div>

      <div class="evidence-stage-viewport">
        <Transition :name="stepTransitionName">
          <div :key="current.id" class="evidence-stage-frame">
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
        <div class="evidence-heading"><span>路口拓扑与运行关系</span><b>03</b></div>
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
          问题集中在北进口，垂直方向和下游尚未失稳；上游持续来车可能继续加剧排队。
        </div>
      </template>

      <template v-else-if="current.id === 'evidence'">
        <div class="evidence-heading"><span>异常成立性核验</span><b>02</b></div>
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

      <template v-else-if="current.id === 'trace'">
        <div class="evidence-heading"><span>上游流量来源与贡献</span><b>04</b></div>
        <div class="trace-summary">
          <span>主要流量来源</span>
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
      </template>

      <template v-else>
        <div class="evidence-heading"><span>关键问题逐项验证</span><b>05</b></div>
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
          <span>上游来车持续增加</span><i>叠加</i>
          <span>目标方向放行不足</span><i>导致</i>
          <strong>北进口排队增长</strong>
        </div>
        <div class="plain-conclusion">
          <b>验证结论</b>
          先改善目标方向放行，再用上游削峰压低到达强度；无需把下游当作病因处理。
        </div>
      </template>
          </div>
        </Transition>
      </div>

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
