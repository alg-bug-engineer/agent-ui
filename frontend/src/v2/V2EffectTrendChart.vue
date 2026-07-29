<script setup lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { init, use, type EChartsType } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { EffectTrendScene } from '../types'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer])

const props = defineProps<{ trend: EffectTrendScene }>()
const chartRoot = ref<HTMLDivElement | null>(null)
let chartInstance: EChartsType | null = null

function renderChart() {
  if (!chartRoot.value) return
  chartInstance?.dispose()
  chartInstance = init(chartRoot.value, undefined, { renderer: 'svg' })
  chartInstance.setOption({
    animationDuration: 700,
    grid: { left: 38, right: 14, top: 38, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 12,
      itemHeight: 7,
      textStyle: { color: 'rgba(220,240,255,.72)', fontSize: 10 },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.trend.hourlyComparison.map((item) => item.hour.slice(0, 5)),
      axisLine: { lineStyle: { color: 'rgba(130,194,218,.24)' } },
      axisLabel: { color: 'rgba(206,232,244,.58)', fontSize: 9 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '排队长度（m）',
      nameTextStyle: { color: 'rgba(206,232,244,.58)', fontSize: 9 },
      min: 40,
      splitLine: { lineStyle: { color: 'rgba(255,255,255,.055)' } },
      axisLabel: { color: 'rgba(206,232,244,.58)', fontSize: 9 },
    },
    series: [
      {
        name: '下发前',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: props.trend.hourlyComparison.map((item) => item.before),
        lineStyle: { width: 2, color: '#ffc15c', type: 'dashed' },
        itemStyle: { color: '#ffc15c' },
      },
      {
        name: '下发后',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: props.trend.hourlyComparison.map((item) => item.after),
        lineStyle: { width: 3, color: '#4ee0aa' },
        itemStyle: { color: '#4ee0aa' },
        areaStyle: { color: 'rgba(78,224,170,.08)' },
      },
    ],
  })
}

function resizeChart() {
  chartInstance?.resize()
}

watch(
  () => props.trend,
  () => void nextTick().then(renderChart),
  { deep: true },
)

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chartInstance?.dispose()
})
</script>

<template>
  <div ref="chartRoot" class="v2-effect-trend-chart"></div>
</template>
