<script setup lang="ts">
import { LineChart, PieChart } from 'echarts/charts'
import { GraphicComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { init, use, type EChartsType } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type { DailySummary, HumanCollaboration } from '../src/types'
import HumanCollaborationWorkbench from './HumanCollaborationWorkbench.vue'

use([LineChart, PieChart, GraphicComponent, GridComponent, TooltipComponent, SVGRenderer])

interface EffectivenessData {
  metrics: Array<{
    name: string
    unit: string
    before: number
    after: number
    improvement: string
    direction: 'up' | 'down'
  }>
  hourly: Array<{ hour: string; detected: number; closed: number }>
}

interface ExperienceData {
  summary: Array<{ label: string; value: number; unit: string }>
  featured: Array<{ title: string; scene: string; result: string; tags: string[] }>
  pipeline: Array<{ name: string; count: number; status: string }>
}

const emit = defineEmits<{ beat: [value: string] }>()
const summary = ref<DailySummary | null>(null)
const collaboration = ref<HumanCollaboration | null>(null)
const effectiveness = ref<EffectivenessData | null>(null)
const experiences = ref<ExperienceData | null>(null)
const reportLoading = ref(true)
const reportLoadError = ref(false)
const activeReportView = ref<'overview' | 'collaboration'>('overview')
const reportRoot = ref<HTMLDivElement | null>(null)
const reportMapSpace = ref<HTMLDivElement | null>(null)
const actionChart = ref<HTMLDivElement | null>(null)
const trendChart = ref<HTMLDivElement | null>(null)
let actionChartInstance: EChartsType | null = null
let trendChartInstance: EChartsType | null = null

function renderCharts() {
  if (!summary.value || !effectiveness.value || !actionChart.value || !trendChart.value) return

  actionChartInstance?.dispose()
  trendChartInstance?.dispose()
  actionChartInstance = init(actionChart.value, undefined, { renderer: 'svg' })
  actionChartInstance.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['62%', '82%'],
      center: ['50%', '48%'],
      label: { show: false },
      itemStyle: { borderColor: '#ffffff', borderWidth: 3 },
      data: summary.value.actions.map((item) => ({
        value: item.value,
        name: item.name,
        itemStyle: { color: item.color },
      })),
    }],
    graphic: [{
      type: 'text',
      left: 'center',
      top: '38%',
      style: {
        text: `${summary.value.actions.reduce((sum, item) => sum + item.value, 0)}\n今日动作`,
        textAlign: 'center',
        fill: '#0d1b2e',
        font: '700 18px "DIN Alternate", sans-serif',
        lineHeight: 24,
      },
    }],
  })

  trendChartInstance = init(trendChart.value, undefined, { renderer: 'svg' })
  trendChartInstance.setOption({
    grid: { left: 32, right: 12, top: 16, bottom: 26 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: effectiveness.value.hourly.map((item) => item.hour),
      axisLine: { lineStyle: { color: '#c8daf5' } },
      axisLabel: { color: '#5f7a9c', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#dce8f8' } },
      axisLabel: { color: '#5f7a9c', fontSize: 12 },
    },
    series: [
      {
        name: '发现问题',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: effectiveness.value.hourly.map((item) => item.detected),
        lineStyle: { width: 3, color: '#e68a00' },
        itemStyle: { color: '#e68a00' },
        areaStyle: { color: 'rgba(230,138,0,.08)' },
      },
      {
        name: '闭环处置',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: effectiveness.value.hourly.map((item) => item.closed),
        lineStyle: { width: 3, color: '#00b5a3' },
        itemStyle: { color: '#00b5a3' },
      },
    ],
  })
}

async function mountCharts() {
  await nextTick()
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()))
  renderCharts()
  window.requestAnimationFrame(resizeCharts)
}

function resizeCharts() {
  actionChartInstance?.resize()
  trendChartInstance?.resize()
}

function scrollReportOutsideMap(event: WheelEvent) {
  const root = reportRoot.value
  if (!root || event.ctrlKey || event.deltaY === 0) return

  const mapRect = reportMapSpace.value?.getBoundingClientRect()
  const isInsideMap = Boolean(
    mapRect
    && event.clientX >= mapRect.left
    && event.clientX <= mapRect.right
    && event.clientY >= mapRect.top
    && event.clientY <= mapRect.bottom,
  )
  if (isInsideMap) return

  const nextScrollTop = Math.max(
    0,
    Math.min(root.scrollHeight - root.clientHeight, root.scrollTop + event.deltaY),
  )
  if (nextScrollTop === root.scrollTop) return

  root.scrollTop = nextScrollTop
  event.preventDefault()
}

watch(activeReportView, (view) => {
  if (view === 'overview') {
    void mountCharts()
  } else {
    actionChartInstance?.dispose()
    trendChartInstance?.dispose()
    actionChartInstance = null
    trendChartInstance = null
  }
})

function appendHumanRecord(record: HumanCollaboration['timeline'][number]) {
  if (!collaboration.value) return
  collaboration.value.timeline.unshift(record)
  const pending = collaboration.value.overview.find((item) => item.label === '待审批')
  if (pending && ['审批通过', '驳回方案'].includes(record.action)) {
    pending.value = Math.max(0, pending.value - 1)
  }
}

async function loadReportData() {
  reportLoading.value = true
  reportLoadError.value = false
  try {
    const [summaryData, collaborationData, effectivenessData, experienceData] = await Promise.all([
      dataRepository.dailySummary(),
      dataRepository.humanCollaboration(),
      dataRepository.effectiveness(),
      dataRepository.experiences(),
    ])
    summary.value = summaryData
    collaboration.value = collaborationData
    effectiveness.value = effectivenessData as unknown as EffectivenessData
    experiences.value = experienceData as unknown as ExperienceData
    await mountCharts()
  } catch (error) {
    console.error('[Act6Report] 运行复盘数据加载失败。', error)
    reportLoadError.value = true
  } finally {
    reportLoading.value = false
  }
}

onMounted(async () => {
  emit('beat', 'report')
  window.addEventListener('wheel', scrollReportOutsideMap, { capture: true, passive: false })
  window.addEventListener('resize', resizeCharts)
  await loadReportData()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  window.removeEventListener('wheel', scrollReportOutsideMap, { capture: true })
  actionChartInstance?.dispose()
  trendChartInstance?.dispose()
})
</script>

<template>
  <div
    ref="reportRoot"
    class="act-experience act6-experience"
  >
    <section
      v-if="!summary || !collaboration || !effectiveness || !experiences"
      class="report-loading-state"
      :class="{ failed: reportLoadError }"
    >
      <i v-if="reportLoading"></i>
      <small>CONTINUOUS LEARNING · DAILY REVIEW</small>
      <strong>{{ reportLoadError ? '运行复盘暂未加载完整' : '正在汇总城市信号控制运行复盘' }}</strong>
      <p>
        {{
          reportLoadError
            ? '治理结果地图保持可用，可重新加载日报、协同记录与经验沉淀面板。'
            : '治理结果、运行指标与经验沉淀正在形成完整复盘。'
        }}
      </p>
      <button v-if="reportLoadError" @click="loadReportData">重新加载面板</button>
    </section>

    <template v-else>
    <section class="report-heading">
      <div>
        <span>CITY SIGNAL CONTROL · DAILY BRIEF</span>
        <h2>城市信号控制运行日报</h2>
        <p>{{ summary.reportDate }} · {{ summary.scope }}</p>
      </div>
      <div class="report-verdict">
        <small>今日运行评价</small>
        <strong>稳定 · 有效 · 可控</strong>
        <span>闭环完成率 96.8%</span>
      </div>
    </section>

    <nav class="report-view-switch">
      <button :class="{ active: activeReportView === 'overview' }" @click="activeReportView = 'overview'">
        运行复盘总览
      </button>
      <button :class="{ active: activeReportView === 'collaboration' }" @click="activeReportView = 'collaboration'">
        人机协同处置
        <b>{{ collaboration.pending.length }}</b>
      </button>
    </nav>

    <section v-if="activeReportView === 'overview'" class="report-map-overview">
      <div ref="reportMapSpace" class="report-map-space">
        <div class="report-map-caption">
          <span><i></i> 城市治理结果地图</span>
          <small>支持拖拽与缩放 · 绿色高亮为本次代表性治理结果</small>
        </div>
        <div class="report-map-legend">
          <span><i class="closed"></i>已闭环</span>
          <span><i class="focus"></i>代表案例</span>
          <span><i class="watch"></i>持续监测</span>
        </div>
      </div>
      <aside class="report-map-result">
        <small>REPRESENTATIVE OUTCOME · 18:21</small>
        <h3>解放东路与奥体西路</h3>
        <p>组合策略执行 3 个周期后，目标排队明显消散，周边方向均保持在安全边界内。</p>
        <div class="report-result-primary">
          <span>北进口排队</span>
          <strong>129<small>m</small><i>→</i>78<small>m</small></strong>
          <b>下降 39.5%</b>
        </div>
        <div class="report-result-guards">
          <span><b>71m</b>东西向<br><small>低于 92m 警戒</small></span>
          <span><b>55%</b>下游占有率<br><small>低于 65% 上限</small></span>
          <span><b>3</b>验证周期<br><small>持续稳定</small></span>
        </div>
        <div class="report-result-verdict">
          <i></i>
          <span><b>治理结论</b>方案有效，未将压力转移至相邻方向</span>
        </div>
      </aside>
    </section>

    <section v-if="activeReportView === 'overview'" class="report-kpis">
      <article v-for="item in summary.kpis" :key="item.label" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.delta }}</small>
      </article>
    </section>

    <section v-if="activeReportView === 'overview'" class="executive-summary">
      <div class="executive-copy">
        <small>运行综述</small>
        <h3>{{ summary.headline }}</h3>
        <p>{{ summary.narrative }}</p>
      </div>
      <div class="executive-findings">
        <span><b>运行状态</b>重点路口风险处置及时</span>
        <span><b>安全边界</b>高风险动作均保留人工确认</span>
        <span><b>经验沉淀</b>有效处置过程已进入知识库</span>
      </div>
    </section>

    <section v-if="activeReportView === 'overview'" class="report-grid">
      <article class="report-card action-distribution">
        <header><div><small>01</small><h3>智能体动作分布</h3></div><span>全天累计</span></header>
        <div class="action-content">
          <div ref="actionChart" class="action-chart"></div>
          <div class="action-legend">
            <div v-for="item in summary.actions" :key="item.name">
              <i :style="{ background: item.color }"></i>
              <span>{{ item.name }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </div>
      </article>

      <article class="report-card operation-trend">
        <header><div><small>02</small><h3>问题发现与闭环趋势</h3></div><span>小时级</span></header>
        <div ref="trendChart" class="trend-chart"></div>
        <div class="chart-caption"><i class="amber"></i>发现问题 <i class="green"></i>闭环处置</div>
      </article>

      <article class="report-card effect-overview">
        <header><div><small>03</small><h3>治理效果</h3></div><span>执行前后对比</span></header>
        <div class="effect-list">
          <div v-for="item in effectiveness.metrics" :key="item.name">
            <div class="effect-name"><span>{{ item.name }}</span><b>{{ item.improvement }}</b></div>
            <div class="effect-values">
              <span>{{ item.before }}<small>{{ item.unit }}</small></span>
              <i>→</i>
              <strong>{{ item.after }}<small>{{ item.unit }}</small></strong>
            </div>
          </div>
        </div>
      </article>

      <article class="report-card human-loop">
        <header><div><small>04</small><h3>人机协同与安全留痕</h3></div><span>智能建议 · 专家把关</span></header>
        <div class="collaboration-stats">
          <div v-for="item in collaboration.overview" :key="item.label" :class="item.tone">
            <strong>{{ item.value }}</strong><span>{{ item.label }}</span>
          </div>
        </div>
        <div class="human-timeline">
          <div v-for="item in collaboration.timeline.slice(0, 3)" :key="`${item.time}-${item.action}`">
            <time>{{ item.time }}</time>
            <i></i>
            <div>
              <strong>{{ item.action }} · {{ item.target }}</strong>
              <span>{{ item.actor }}｜{{ item.detail }}</span>
            </div>
            <b>{{ item.status }}</b>
          </div>
        </div>
      </article>

      <article class="report-card experience-card">
        <header><div><small>05</small><h3>经验沉淀与持续进化</h3></div><span>知识资产新增</span></header>
        <div class="experience-pipeline">
          <div v-for="(item, index) in experiences.pipeline" :key="item.name">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <strong>{{ item.name }}</strong>
            <b>{{ item.count }}</b>
            <small>{{ item.status }}</small>
            <i v-if="index < experiences.pipeline.length - 1">→</i>
          </div>
        </div>
        <div class="featured-experience">
          <div>
            <small>今日代表经验</small>
            <strong>{{ experiences.featured[0].title }}</strong>
            <p>{{ experiences.featured[0].result }}</p>
          </div>
          <span v-for="tag in experiences.featured[0].tags" :key="tag">{{ tag }}</span>
        </div>
      </article>
    </section>

    <HumanCollaborationWorkbench
      v-else
      :collaboration="collaboration"
      @record="appendHumanRecord"
    />
    </template>
  </div>
</template>
