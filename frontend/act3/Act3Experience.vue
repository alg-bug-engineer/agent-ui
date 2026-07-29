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
    title: '治理策略',
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
let tidalChartInstance: EChartsType | null = null

const current = computed(() => beats[currentIndex.value])
const completed = computed(() => currentIndex.value === beats.length - 1)
const overallProgress = computed(() => ((currentIndex.value + 1) / beats.length) * 100)
const activeCase = computed(() =>
  similarCases.value.find((item) => item.id === activeCaseId.value) ?? similarCases.value[0],
)

function selectBeat(index: number) {
  currentIndex.value = index
  emit('beat', beats[index].id)
  if (beats[index].id === 'tidal-pattern') nextTick(renderTidalChart)
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
      axisLine: { lineStyle: { color: 'rgba(220,240,255,.25)' } },
      axisLabel: { color: 'rgba(220,240,255,.45)', fontSize: 8, interval: 2 },
    },
    yAxis: {
      type: 'value',
      name: '排队长度(m)',
      nameTextStyle: { color: 'rgba(220,240,255,.4)', fontSize: 8 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,.06)' } },
      axisLabel: { color: 'rgba(220,240,255,.45)', fontSize: 8 },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: tidalFlow.value.hourly.map((item) => item.queueM),
        lineStyle: { width: 2.5, color: '#66e0ff' },
        areaStyle: { color: 'rgba(102,224,255,.08)' },
        markArea: {
          silent: true,
          data: [
            ...(morning
              ? [[{
                  xAxis: morning[0],
                  itemStyle: { color: 'rgba(245,166,35,.10)' },
                }, { xAxis: morning[1] }]]
              : []),
            ...(evening
              ? [[{
                  xAxis: evening[0],
                  itemStyle: { color: 'rgba(245,166,35,.22)' },
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
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  tidalChartInstance?.dispose()
})
</script>

<template>
  <div class="act-experience act3-experience">
    <aside class="glass-panel agent-dock reasoning-panel">
      <div class="dock-cap">
        <span class="dock-live"><i></i> KNOWLEDGE MATCHING</span>
        <b>知识匹配链</b>
        <small>{{ String(currentIndex + 1).padStart(2, '0') }} / {{ String(beats.length).padStart(2, '0') }}</small>
      </div>

      <div class="diagnosis-title">
        <div class="agent-emblem"><span></span><span></span><span></span></div>
        <div>
          <h2>案例与策略匹配</h2>
          <p>解放东路×奥体西路 · 晚高峰排队溢出</p>
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

      <div class="step-check-bar">
        <div class="step-check-status">
          <span class="live-dot"></span>
          {{ completed ? '策略匹配完成 · 已形成现场专属方向' : `待检查 · ${current.title}` }}
        </div>
        <div class="step-check-nav">
          <button :disabled="currentIndex === 0" @click="goPrev">← 上一步</button>
          <button class="next-act" @click="goNext">
            {{ completed ? '进入方案生成 →' : '下一步 →' }}
          </button>
        </div>
      </div>
    </aside>

    <aside class="glass-panel agent-dock evidence-panel">
      <div class="dock-cap evidence-cap">
        <span class="dock-live"><i></i> ANALYSIS WORKBENCH</span>
        <b>{{ current.title }}</b>
        <small>LIVE</small>
      </div>

      <template v-if="current.id === 'knowledge-recall' && knowledgeBase">
        <div class="evidence-heading"><span>交管知识库检索</span><b>01</b></div>
        <div class="knowledge-stats">
          <div><strong>{{ knowledgeBase.totalCases.toLocaleString() }}</strong><span>一线实战处置案例</span></div>
          <div><strong>{{ knowledgeBase.sceneFeatures.toLocaleString() }}</strong><span>场景语义</span></div>
          <div><strong>{{ knowledgeBase.reasoningRules }}</strong><span>推理规则</span></div>
        </div>
        <div class="target-card">
          <small>本次检索条件</small>
          <h2>{{ knowledgeBase.retrievalQuery.problemType }}</h2>
          <p>{{ knowledgeBase.retrievalQuery.period }} · {{ knowledgeBase.retrievalQuery.geometry }}</p>
        </div>
        <div class="keyword-tags">
          <span v-for="keyword in knowledgeBase.retrievalQuery.keywords" :key="keyword">{{ keyword }}</span>
        </div>
        <div class="plain-conclusion">
          <b>检索结论</b>
          {{ knowledgeBase.matchLatencySeconds }}s 内从知识库命中 {{ knowledgeBase.matchedCaseCount }} 个高相似度案例，进入案例比对环节。
        </div>
      </template>

      <template v-else-if="current.id === 'similar-cases'">
        <div class="evidence-heading"><span>晚高峰排队溢出真实案例</span><b>02</b></div>
        <div class="case-tab-row">
          <button
            v-for="item in similarCases"
            :key="item.id"
            :class="{ active: item.id === activeCaseId }"
            @click="activeCaseId = item.id"
          >
            <small>匹配度 {{ item.matchScore }}%</small>
            <strong>{{ item.location }}</strong>
          </button>
        </div>
        <article v-if="activeCase" class="case-card">
          <header>
            <strong>{{ activeCase.title }}</strong>
            <span>匹配度 {{ activeCase.matchScore }}%</span>
          </header>
          <div class="match-block">
            <div class="match-label">命中标签 <small>{{ activeCase.hitTags.length }} 项</small></div>
            <div class="hit-tag-row">
              <b
                v-for="tag in activeCase.hitTags"
                :key="`${tag.dimension}-${tag.value}`"
                class="hit-tag matched"
              >
                <em>{{ tag.dimension }}</em>{{ tag.value }}
              </b>
            </div>
          </div>
          <div class="match-block">
            <div class="match-label">命中高阶语义 <small>{{ activeCase.hitSemantics.length }} 项</small></div>
            <div class="hit-tag-row">
              <b
                v-for="item in activeCase.hitSemantics"
                :key="`${item.dimension}-${item.value}`"
                class="hit-tag matched"
              >
                <em>{{ item.dimension }}</em>{{ item.value }}
              </b>
            </div>
          </div>
          <p><span>场景</span>{{ activeCase.scenario }}</p>
          <p><span>诊断</span>{{ activeCase.diagnosis }}</p>
          <p><span>治理</span>{{ activeCase.treatment }}</p>
          <div class="case-effect"><span>效果</span>{{ activeCase.effect }}</div>
          <footer>来源：{{ activeCase.source.title }}</footer>
        </article>
        <div class="plain-conclusion">
          <b>比对结论</b>
          3 个真实案例均命中「晚高峰 + 排队溢出 + 信号配时短板」标签，并共享「潮汐失稳 / 有效放行不足 / 排队回传」等高阶语义，支撑定向加放而非全天大幅加绿。
        </div>
      </template>

      <template v-else-if="current.id === 'tidal-pattern' && tidalFlow">
        <div class="evidence-heading"><span>{{ tidalFlow.insight.title }}</span><b>03</b></div>
        <div class="tidal-chart-panel">
          <div ref="tidalChart" class="tidal-chart"></div>
          <div class="tidal-chart-caption"><i></i>早高峰有抬升 · 晚高峰 17:00–19:00 显著更重</div>
        </div>
        <div class="direction-list tidal-summary tidal-summary-triple">
          <article class="direction-card normal">
            <div><span>平峰</span><strong>其余时段</strong></div>
            <b>饱和度 ≤ 0.50</b>
            <small>排队 ≤ 32m</small>
            <p>{{ tidalFlow.insight.offpeakSummary }}</p>
          </article>
          <article class="direction-card warning">
            <div><span>早高峰</span><strong>07:00–09:00</strong></div>
            <b>饱和度 0.58～0.71</b>
            <small>排队峰值 74m</small>
            <p>{{ tidalFlow.insight.morningSummary }}</p>
          </article>
          <article class="direction-card critical">
            <div><span>晚高峰</span><strong>17:00–19:00</strong></div>
            <b>饱和度 0.76～0.89</b>
            <small>排队峰值 129m</small>
            <p>{{ tidalFlow.insight.peakSummary }}</p>
          </article>
        </div>
        <div class="plain-conclusion critical">
          <b>潮汐结论</b>
          {{ tidalFlow.insight.conclusion }}
        </div>
      </template>

      <template v-else-if="current.id === 'strategy-brief' && strategyBrief">
        <div class="evidence-heading"><span>{{ strategyBrief.title }}</span><b>04</b></div>
        <div class="principle-list">
          <span v-for="item in strategyBrief.principles" :key="item">{{ item }}</span>
        </div>
        <div class="timeslot-list">
          <article v-for="item in strategyBrief.timeSlots" :key="item.period" :class="item.tone">
            <span>{{ item.period }}</span>
            <strong>{{ item.label }}</strong>
            <p>{{ item.strategy }}</p>
          </article>
        </div>
        <div class="decision-rationale">
          <span>推荐方向</span>
          <p>{{ strategyBrief.recommendedDirection }}</p>
        </div>
        <div class="expected-outcome">{{ strategyBrief.conclusion }}</div>
        <button class="primary-action report-entry" @click="emit('openPlan')">
          <span>进入配时方案生成</span><b>→</b>
        </button>
      </template>

      <div class="analysis-source">
        <span>数据口径</span>
        <b>真实案例摘自交管知识库（knowledge_qa_tagged）</b>
        <small>潮汐曲线与策略结论为演示数据，用于呈现专家分析逻辑</small>
      </div>
    </aside>
  </div>
</template>
