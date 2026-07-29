<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkAreaComponent, TooltipComponent } from 'echarts/components'
import { init, use, type EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type {
  KnowledgeBaseStats,
  SimilarCase,
  StrategyBrief,
  TidalFlowScene,
} from '../src/types'

use([LineChart, GridComponent, MarkAreaComponent, TooltipComponent, CanvasRenderer])

const emit = defineEmits<{
  beat: [value: string]
  openPlan: []
}>()

const beats = [
  {
    id: 'knowledge-recall',
    title: '知识检索',
    subtitle: '从案例库召回贴近现场的处置经验',
  },
  {
    id: 'similar-cases',
    title: '相似案例',
    subtitle: '晚高峰排队溢出的真实处置对照',
  },
  {
    id: 'tidal-pattern',
    title: '潮汐特征',
    subtitle: '早晚双峰，晚高峰显著更重',
  },
  {
    id: 'strategy-brief',
    title: '治理方向',
    subtitle: '摒弃通用模板，定制现场策略',
  },
] as const

const currentIndex = ref(0)
const knowledgeBase = ref<KnowledgeBaseStats | null>(null)
const similarCases = ref<SimilarCase[]>([])
const tidalFlow = ref<TidalFlowScene | null>(null)
const strategyBrief = ref<StrategyBrief | null>(null)
const activeCaseId = ref('')
const tidalChart = ref<HTMLDivElement | null>(null)
const objectListReady = ref(false)
let tidalChartInstance: EChartsType | null = null
let objectListTimer = 0

const current = computed(() => beats[currentIndex.value])
const completed = computed(() => currentIndex.value === beats.length - 1)
const showStrategySlots = computed(() => current.value.id === 'strategy-brief')
const activeCase = computed(() =>
  similarCases.value.find((item) => item.id === activeCaseId.value) ?? similarCases.value[0],
)

function selectBeat(index: number) {
  currentIndex.value = index
  emit('beat', beats[index].id)
  if (beats[index].id === 'tidal-pattern') nextTick(() => {
    renderTidalChart()
    resizeChart()
  })
}

function selectCase(id: string) {
  activeCaseId.value = id
  const index = beats.findIndex((item) => item.id === 'similar-cases')
  if (index !== currentIndex.value) selectBeat(index)
}

function goPrev() {
  if (currentIndex.value > 0) selectBeat(currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value < beats.length - 1) {
    selectBeat(currentIndex.value + 1)
    return
  }
  emit('openPlan')
}

function renderTidalChart() {
  if (!tidalChart.value || !tidalFlow.value) return
  tidalChartInstance = init(tidalChart.value)
  const hours = tidalFlow.value.hourly.map((item) => item.hour)
  const rangeOf = (period: 'morning-peak' | 'evening-peak') => {
    const indexes = tidalFlow.value!.hourly
      .map((item, index) => (item.period === period ? index : -1))
      .filter((index) => index >= 0)
    return indexes.length
      ? [hours[indexes[0]], hours[indexes[indexes.length - 1]]] as const
      : null
  }
  const morning = rangeOf('morning-peak')
  const evening = rangeOf('evening-peak')
  tidalChartInstance.setOption({
    grid: { left: 34, right: 12, top: 16, bottom: 24 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: hours,
      axisLine: { lineStyle: { color: 'rgba(23,54,77,.16)' } },
      axisLabel: { color: '#7c96a6', fontSize: 8, interval: 2 },
    },
    yAxis: {
      type: 'value',
      name: '排队长度(m)',
      nameTextStyle: { color: '#93a3ad', fontSize: 8 },
      splitLine: { lineStyle: { color: 'rgba(23,54,77,.07)' } },
      axisLabel: { color: '#7c96a6', fontSize: 8 },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: tidalFlow.value.hourly.map((item) => item.queueM),
        lineStyle: { width: 2.5, color: '#179d8e' },
        areaStyle: { color: 'rgba(23,157,142,.1)' },
        markArea: {
          silent: true,
          data: [
            ...(morning
              ? [[{
                  xAxis: morning[0],
                  itemStyle: { color: 'rgba(216,149,42,.12)' },
                }, { xAxis: morning[1] }]]
              : []),
            ...(evening
              ? [[{
                  xAxis: evening[0],
                  itemStyle: { color: 'rgba(217,83,79,.14)' },
                }, { xAxis: evening[1] }]]
              : []),
          ],
        },
      },
    ],
  })
}

function resizeChart() {
  tidalChartInstance?.resize()
}

onMounted(async () => {
  const [knowledgeData, caseData, tidalData, strategyData] = await Promise.all([
    dataRepository.knowledgeBase(),
    dataRepository.similarCases(),
    dataRepository.tidalFlow(),
    dataRepository.strategyBrief(),
  ])
  knowledgeBase.value = knowledgeData
  similarCases.value = caseData
  tidalFlow.value = tidalData
  strategyBrief.value = strategyData
  activeCaseId.value = caseData[0]?.id ?? ''
  emit('beat', current.value.id)
  await nextTick()
  renderTidalChart()
  window.addEventListener('resize', resizeChart)
  objectListTimer = window.setTimeout(() => {
    objectListReady.value = true
  }, 1000)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  window.clearTimeout(objectListTimer)
  tidalChartInstance?.dispose()
})
</script>

<template>
  <div class="act-experience act3-experience act3-dashboard">
    <div v-if="!objectListReady" class="act3-object-list act3-object-list-loading">
      <span class="live-dot"></span>
      正在检索交管知识库…
    </div>

    <Transition name="act3-list-pop">
      <aside v-if="objectListReady" class="act3-object-list">
        <template v-if="showStrategySlots && strategyBrief">
          <div class="act3-list-head">
            <span class="live-dot"></span>
            分时段治理方向
          </div>

          <div class="act3-slot-list act3-slot-list-side">
            <article
              v-for="item in strategyBrief.timeSlots"
              :key="item.period"
              :class="['act3-slot', item.tone]"
            >
              <span>{{ item.period }}</span>
              <strong>{{ item.label }}</strong>
              <p>{{ item.strategy }}</p>
            </article>
          </div>

          <div class="act3-list-foot">
            <span>本次重点</span>
            晚高峰窗口启用专属组合策略
          </div>
        </template>

        <template v-else>
          <div class="act3-list-head">
            <span class="live-dot"></span>
            案例库检索对象
          </div>

          <div v-if="knowledgeBase" class="act3-list-stats">
            <div><strong>{{ knowledgeBase.totalCases }}</strong><span>实战案例</span></div>
            <div><strong>{{ knowledgeBase.sceneFeatures }}</strong><span>场景语义</span></div>
            <div><strong>{{ knowledgeBase.reasoningRules }}</strong><span>推理规则</span></div>
          </div>

          <div class="act3-list-items">
            <button
              v-for="item in similarCases"
              :key="item.id"
              class="act3-object-item"
              :class="{ active: item.id === activeCaseId }"
              @click="selectCase(item.id)"
            >
              <span class="act3-object-badge">{{ item.matchScore }}%</span>
              <div>
                <strong>{{ item.location }}</strong>
                <small>{{ item.title }}</small>
              </div>
            </button>
          </div>

          <div class="act3-list-foot">
            <span>数据口径</span>
            交管知识库（knowledge_qa_tagged）
          </div>
        </template>
      </aside>
    </Transition>

    <section class="act3-panel">
      <header class="act3-panel-head">
        <div class="act3-panel-heading">
          <strong>解放东路 × 奥体西路</strong>
          <em class="act3-tag critical">晚高峰 · 排队溢出</em>
        </div>
        <small class="act3-panel-index">{{ String(currentIndex + 1).padStart(2, '0') }} / {{ String(beats.length).padStart(2, '0') }}</small>
      </header>

      <nav class="act3-step-tabs">
        <button
          v-for="(item, index) in beats"
          :key="item.id"
          :class="{ active: index === currentIndex, done: index < currentIndex }"
          @click="selectBeat(index)"
        >
          <em>{{ index < currentIndex ? '✓' : index + 1 }}</em>
          <span>{{ item.title }}</span>
        </button>
      </nav>

      <div class="act3-panel-body">
        <template v-if="current.id === 'knowledge-recall' && knowledgeBase">
          <div class="act3-info-card">
            <span>检索条件</span>
            {{ knowledgeBase.retrievalQuery.problemType }} · {{ knowledgeBase.retrievalQuery.period }} · {{ knowledgeBase.retrievalQuery.geometry }}
          </div>

          <div class="act3-tag-row">
            <b v-for="keyword in knowledgeBase.retrievalQuery.keywords" :key="keyword" class="act3-chip">{{ keyword }}</b>
          </div>

          <div class="act3-judgement success">
            <span class="act3-judgement-badge">✓</span>
            <div>
              <strong>已命中 {{ knowledgeBase.matchedCaseCount }} 个高相似度案例</strong>
              <p>检索耗时 {{ knowledgeBase.matchLatencySeconds }}s，均命中「晚高峰 + 排队溢出」标签体系</p>
            </div>
          </div>
        </template>

        <template v-else-if="current.id === 'similar-cases' && activeCase">
          <p class="act3-panel-hint">从左侧列表切换其他案例进行比对</p>

          <article class="act3-case-card">
            <header>
              <strong>{{ activeCase.title }}</strong>
              <em class="act3-tag critical">匹配度 {{ activeCase.matchScore }}%</em>
            </header>

            <div class="act3-match-block">
              <div class="act3-match-label">命中标签 <small>{{ activeCase.hitTags.length }} 项</small></div>
              <div class="act3-tag-row">
                <b
                  v-for="tag in activeCase.hitTags"
                  :key="`${tag.dimension}-${tag.value}`"
                  class="act3-chip matched"
                >
                  <em>{{ tag.dimension }}</em>{{ tag.value }}
                </b>
              </div>
            </div>

            <div class="act3-match-block">
              <div class="act3-match-label">命中高阶语义 <small>{{ activeCase.hitSemantics.length }} 项</small></div>
              <div class="act3-tag-row">
                <b
                  v-for="item in activeCase.hitSemantics"
                  :key="`${item.dimension}-${item.value}`"
                  class="act3-chip semantic"
                >
                  <em>{{ item.dimension }}</em>{{ item.value }}
                </b>
              </div>
            </div>

            <div class="act3-case-body">
              <p><span>场景</span>{{ activeCase.scenario }}</p>
              <p><span>诊断</span>{{ activeCase.diagnosis }}</p>
              <p><span>治理</span>{{ activeCase.treatment }}</p>
            </div>

            <div class="act3-case-effect"><span>效果</span>{{ activeCase.effect }}</div>
            <footer>来源：{{ activeCase.source.title }}</footer>
          </article>

          <div class="act3-judgement info">
            <span class="act3-judgement-badge">Σ</span>
            <div>
              <strong>比对结论</strong>
              <p>3 个真实案例均命中「晚高峰 + 排队溢出 + 信号配时短板」标签，并共享「潮汐失稳 / 有效放行不足 / 排队回传」等高阶语义，支撑定向加放而非全天大幅加绿。</p>
            </div>
          </div>
        </template>

        <template v-else-if="current.id === 'tidal-pattern' && tidalFlow">
          <div class="act3-chart-card">
            <div ref="tidalChart" class="act3-chart"></div>
            <div class="act3-chart-caption">早高峰有抬升 · 晚高峰 17:00–19:00 显著更重</div>
          </div>

          <div class="act3-stat-row">
            <article class="act3-stat-card critical">
              <div><span>晚高峰</span><strong>17:00–19:00</strong></div>
              <b>饱和度 0.76～0.89</b>
              <small>排队峰值 129m</small>
              <p>{{ tidalFlow.insight.peakSummary }}</p>
            </article>
            <article class="act3-stat-card warning">
              <div><span>早高峰</span><strong>07:00–09:00</strong></div>
              <b>饱和度 0.58～0.71</b>
              <small>排队峰值 74m</small>
              <p>{{ tidalFlow.insight.morningSummary }}</p>
            </article>
            <article class="act3-stat-card normal">
              <div><span>平峰</span><strong>其余时段</strong></div>
              <b>饱和度 ≤ 0.50</b>
              <small>排队 ≤ 32m</small>
              <p>{{ tidalFlow.insight.offpeakSummary }}</p>
            </article>
          </div>

          <div class="act3-judgement critical">
            <span class="act3-judgement-badge">!</span>
            <div><strong>潮汐结论</strong><p>{{ tidalFlow.insight.conclusion }}</p></div>
          </div>
        </template>

        <template v-else-if="current.id === 'strategy-brief' && strategyBrief">
          <div class="act3-principle-list">
            <div class="act3-principle-head">治理原则</div>
            <article v-for="(item, index) in strategyBrief.principles" :key="item" class="act3-principle-item">
              <em>{{ index + 1 }}</em>
              <p>{{ item }}</p>
            </article>
          </div>

          <div class="act3-info-card">
            <span>推荐方向</span>
            {{ strategyBrief.recommendedDirection }}
          </div>

          <div class="act3-judgement success">
            <span class="act3-judgement-badge">✓</span>
            <div><strong>预期成效</strong><p>{{ strategyBrief.conclusion }}</p></div>
          </div>

          <button class="act3-cta" @click="emit('openPlan')">
            <span>进入配时方案生成</span><b>→</b>
          </button>

          <div class="act3-source-note">
            <span>数据口径</span>
            真实案例摘自交管知识库（knowledge_qa_tagged）；潮汐曲线与策略结论为演示数据，用于呈现专家分析逻辑
          </div>
        </template>
      </div>

      <footer class="act3-step-check-bar">
        <div class="act3-step-check-status">
          <span class="live-dot"></span>
          {{ completed ? '治理方向已确定 · 可进入配时方案生成' : `待检查 · ${current.title}` }}
        </div>
        <div class="act3-step-check-nav">
          <button :disabled="currentIndex === 0" @click="goPrev">← 上一步</button>
          <button class="next-act" @click="goNext">
            {{ completed ? '进入方案生成 →' : '下一步 →' }}
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
