<script setup lang="ts">
import { LineChart, PieChart } from 'echarts/charts'
import { GraphicComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { init, use, type EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type { DailySummary, HumanCollaboration } from '../src/types'
import HumanCollaborationWorkbench from './HumanCollaborationWorkbench.vue'

use([LineChart, PieChart, GraphicComponent, GridComponent, TooltipComponent, CanvasRenderer])

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
const activeReportView = ref<'overview' | 'collaboration'>('overview')
const actionChart = ref<HTMLDivElement | null>(null)
const trendChart = ref<HTMLDivElement | null>(null)
let actionChartInstance: EChartsType | null = null
let trendChartInstance: EChartsType | null = null

function renderCharts() {
  if (!summary.value || !effectiveness.value || !actionChart.value || !trendChart.value) return

  actionChartInstance = init(actionChart.value)
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

  trendChartInstance = init(trendChart.value)
  trendChartInstance.setOption({
    grid: { left: 32, right: 12, top: 16, bottom: 26 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: effectiveness.value.hourly.map((item) => item.hour),
      axisLine: { lineStyle: { color: '#c8daf5' } },
      axisLabel: { color: '#5f7a9c', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#dce8f8' } },
      axisLabel: { color: '#5f7a9c', fontSize: 10 },
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

function resizeCharts() {
  actionChartInstance?.resize()
  trendChartInstance?.resize()
}

function appendHumanRecord(record: HumanCollaboration['timeline'][number]) {
  if (!collaboration.value) return
  collaboration.value.timeline.unshift(record)
  const pending = collaboration.value.overview.find((item) => item.label === '待审批')
  if (pending && ['审批通过', '驳回方案'].includes(record.action)) {
    pending.value = Math.max(0, pending.value - 1)
  }
}

onMounted(async () => {
  emit('beat', 'report')
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
  await nextTick()
  renderCharts()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  actionChartInstance?.dispose()
  trendChartInstance?.dispose()
})
</script>

<template>
  <div v-if="summary && collaboration && effectiveness && experiences" class="act-experience act6-experience">
    <section class="report-heading">
      <div>
        <span>AI TRAFFIC OPERATIONS DAILY</span>
        <h2>城市信控智能体运行日报</h2>
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

    <section v-if="activeReportView === 'overview'" class="report-kpis">
      <article v-for="item in summary.kpis" :key="item.label" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.delta }}</small>
      </article>
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
        <header><div><small>04</small><h3>人机协同与安全留痕</h3></div><span>AI 建议 + 专家把关</span></header>
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

      <article class="report-card ai-summary">
        <header><div><small>06</small><h3>AI 日报总结</h3></div><span>自动生成</span></header>
        <div class="summary-seal">AI</div>
        <h4>{{ summary.headline }}</h4>
        <p>{{ summary.narrative }}</p>
        <div class="summary-footer">
          <span>✓ 运行稳定</span><span>✓ 风险可控</span><span>✓ 经验已归档</span>
        </div>
      </article>
    </section>

    <HumanCollaborationWorkbench
      v-else
      :collaboration="collaboration"
      @record="appendHumanRecord"
    />
  </div>
</template>
