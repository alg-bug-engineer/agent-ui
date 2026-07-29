<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { init, use, type EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type { EffectTrendScene } from '../src/types'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const emit = defineEmits<{
  beat: [value: string]
  openReview: []
}>()

const beats = [
  {
    id: 'deployment-confirm',
    title: '执行确认',
    subtitle: '方案已生效，进入效果闭环验证',
  },
  {
    id: 'before-after',
    title: '前后对比',
    subtitle: '排队、延误、效率、绿灯利用率',
  },
  {
    id: 'peak-verification',
    title: '晚高峰验证',
    subtitle: '逐周期跟踪，确认持续下降',
  },
  {
    id: 'closing',
    title: '持续跟踪',
    subtitle: '一周趋势确认无回弹，转入常态复盘',
  },
] as const

const currentIndex = ref(0)
const trend = ref<EffectTrendScene | null>(null)
const hourlyChart = ref<HTMLDivElement | null>(null)
const dailyChart = ref<HTMLDivElement | null>(null)
let hourlyChartInstance: EChartsType | null = null
let dailyChartInstance: EChartsType | null = null

const current = computed(() => beats[currentIndex.value])
const completed = computed(() => currentIndex.value === beats.length - 1)
const overallProgress = computed(() => ((currentIndex.value + 1) / beats.length) * 100)

function selectBeat(index: number) {
  currentIndex.value = index
  emit('beat', beats[index].id)
  if (beats[index].id === 'peak-verification') nextTick(renderHourlyChart)
  if (beats[index].id === 'closing') nextTick(renderDailyChart)
}

function goPrev() {
  if (currentIndex.value > 0) selectBeat(currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value < beats.length - 1) {
    selectBeat(currentIndex.value + 1)
    return
  }
  emit('openReview')
}

function darkAxis() {
  return {
    axisLine: { lineStyle: { color: 'rgba(220,240,255,.25)' } },
    axisLabel: { color: 'rgba(220,240,255,.45)', fontSize: 8 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,.06)' } },
  }
}

function renderHourlyChart() {
  if (!hourlyChart.value || !trend.value) return
  hourlyChartInstance = init(hourlyChart.value)
  hourlyChartInstance.setOption({
    grid: { left: 34, right: 12, top: 24, bottom: 24 },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      textStyle: { color: 'rgba(220,240,255,.6)', fontSize: 8 },
      itemWidth: 10,
      itemHeight: 6,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trend.value.hourlyComparison.map((item) => item.hour),
      ...darkAxis(),
    },
    yAxis: { type: 'value', name: '排队(m)', nameTextStyle: { color: 'rgba(220,240,255,.4)', fontSize: 8 }, ...darkAxis() },
    series: [
      {
        name: '下发前',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: trend.value.hourlyComparison.map((item) => item.before),
        lineStyle: { width: 2, color: '#f5a623', type: 'dashed' },
        itemStyle: { color: '#f5a623' },
      },
      {
        name: '下发后',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: trend.value.hourlyComparison.map((item) => item.after),
        lineStyle: { width: 2.5, color: '#3ddc97' },
        itemStyle: { color: '#3ddc97' },
        areaStyle: { color: 'rgba(61,220,151,.08)' },
      },
    ],
  })
}

function renderDailyChart() {
  if (!dailyChart.value || !trend.value) return
  dailyChartInstance = init(dailyChart.value)
  dailyChartInstance.setOption({
    grid: { left: 34, right: 12, top: 24, bottom: 24 },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      textStyle: { color: 'rgba(220,240,255,.6)', fontSize: 8 },
      itemWidth: 10,
      itemHeight: 6,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trend.value.dailyTrend.map((item) => item.day),
      ...darkAxis(),
    },
    yAxis: { type: 'value', name: '排队(m)', nameTextStyle: { color: 'rgba(220,240,255,.4)', fontSize: 8 }, ...darkAxis() },
    series: [
      {
        name: '下发前',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: trend.value.dailyTrend.map((item) => item.queueBeforeM),
        lineStyle: { width: 2, color: '#f5a623', type: 'dashed' },
        itemStyle: { color: '#f5a623' },
      },
      {
        name: '下发后',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: trend.value.dailyTrend.map((item) => item.queueAfterM),
        lineStyle: { width: 2.5, color: '#3ddc97' },
        itemStyle: { color: '#3ddc97' },
        areaStyle: { color: 'rgba(61,220,151,.08)' },
      },
    ],
  })
}

function resizeCharts() {
  hourlyChartInstance?.resize()
  dailyChartInstance?.resize()
}

onMounted(async () => {
  trend.value = await dataRepository.effectTrend()
  emit('beat', current.value.id)
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  hourlyChartInstance?.dispose()
  dailyChartInstance?.dispose()
})
</script>

<template>
  <div class="act-experience act5-experience">
    <aside class="glass-panel agent-dock reasoning-panel">
      <div class="dock-cap">
        <span class="dock-live"><i></i> EFFECT VERIFICATION</span>
        <b>效果验证链</b>
        <small>{{ String(currentIndex + 1).padStart(2, '0') }} / {{ String(beats.length).padStart(2, '0') }}</small>
      </div>

      <div class="diagnosis-title">
        <div class="agent-emblem"><span></span><span></span><span></span></div>
        <div>
          <h2>治理效果闭环验证</h2>
          <p>下发前后对比 · 持续跟踪不回弹</p>
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
          {{ completed ? '效果验证完成 · 进入每日复盘' : `待检查 · ${current.title}` }}
        </div>
        <div class="step-check-nav">
          <button :disabled="currentIndex === 0" @click="goPrev">← 上一步</button>
          <button class="next-act" @click="goNext">
            {{ completed ? '进入复盘进化 →' : '下一步 →' }}
          </button>
        </div>
      </div>
    </aside>

    <aside v-if="trend" class="glass-panel agent-dock evidence-panel">
      <div class="dock-cap evidence-cap">
        <span class="dock-live"><i></i> ANALYSIS WORKBENCH</span>
        <b>{{ current.title }}</b>
        <small>LIVE</small>
      </div>

      <template v-if="current.id === 'deployment-confirm'">
        <div class="evidence-heading"><span>执行确认</span><b>01</b></div>
        <div class="target-card">
          <small>已下发并生效</small>
          <h2>{{ trend.deployment.planName }}</h2>
          <p>生效时间 {{ trend.deployment.deployedAt }} · 已跟踪 {{ trend.deployment.effectiveCycles }} 个信号周期</p>
        </div>
        <div class="plain-conclusion">
          <b>确认结论</b>
          方案在护栏约束内平稳生效，未触发任何自动回退条件，进入效果对比环节。
        </div>
      </template>

      <template v-else-if="current.id === 'before-after'">
        <div class="evidence-heading"><span>关键指标前后对比</span><b>02</b></div>
        <div class="outcome-grid">
          <article v-for="item in trend.metrics" :key="item.id">
            <span>{{ item.label }}</span>
            <div class="outcome-values">
              <b>{{ item.before }}<small>{{ item.unit }}</small></b>
              <i>→</i>
              <strong>{{ item.after }}<small>{{ item.unit }}</small></strong>
            </div>
            <em :class="item.direction">{{ item.direction === 'down' ? '↓' : '↑' }} {{ item.improvementPct }}%</em>
          </article>
        </div>
        <div class="plain-conclusion">
          <b>对比结论</b>
          四项核心指标均同步改善，且改善幅度均衡，未出现“拆东墙补西墙”。
        </div>
      </template>

      <template v-else-if="current.id === 'peak-verification'">
        <div class="evidence-heading"><span>晚高峰逐周期验证</span><b>03</b></div>
        <div class="tidal-chart-panel">
          <div ref="hourlyChart" class="tidal-chart"></div>
          <div class="tidal-chart-caption"><i></i>下发后（绿）持续低于下发前（橙）</div>
        </div>
        <div class="plain-conclusion">
          <b>验证结论</b>
          晚高峰窗口内逐周期排队长度稳定低于历史基线，未出现执行初期见效、后期反弹的情况。
        </div>
      </template>

      <template v-else>
        <div class="evidence-heading"><span>一周持续跟踪</span><b>04</b></div>
        <div class="tidal-chart-panel">
          <div ref="dailyChart" class="tidal-chart"></div>
          <div class="tidal-chart-caption"><i></i>一周内下发后（绿）持续低于下发前（橙），未见回弹</div>
        </div>
        <div class="expected-outcome">{{ trend.conclusion }}</div>
        <button class="primary-action report-entry" @click="emit('openReview')">
          <span>进入复盘进化与经验沉淀</span><b>→</b>
        </button>
      </template>

      <div class="analysis-source">
        <span>数据口径</span>
        <b>目标路口真实路网快照</b>
        <small>前后对比与多日趋势为演示数据，用于呈现执行效果闭环验证逻辑</small>
      </div>
    </aside>
  </div>
</template>
