<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { runtimeConfig } from '../src/config/runtime'
import { dataRepository } from '../src/services/dataRepository'
import type { DetectedIssue, MonitoringArea } from '../src/types'

const props = defineProps<{ paused: boolean }>()
const emit = defineEmits<{
  beat: [value: string]
  enterDiagnosis: []
}>()

const area = ref<MonitoringArea | null>(null)
const issue = ref<DetectedIssue | null>(null)
const phase = ref<'loading' | 'scan' | 'pending' | 'submitting'>('loading')
const scanLeft = ref(10)
const processLeft = ref(10)
const prompt = ref('')
const scanProgress = computed(() => {
  const total = runtimeConfig.playback.detectionSeconds
  return Math.max(0, Math.min(100, ((total - scanLeft.value) / total) * 100))
})
const processProgress = computed(() => {
  const total = runtimeConfig.playback.autoProcessSeconds
  return Math.max(0, Math.min(100, (processLeft.value / total) * 100))
})
let timer = 0

function beginDiagnosis(source: 'auto' | 'manual') {
  window.clearInterval(timer)
  if (source === 'manual') {
    phase.value = 'submitting'
    emit('beat', 'pending')
    window.setTimeout(() => emit('enterDiagnosis'), 900)
  } else {
    emit('enterDiagnosis')
  }
}

function submitPrompt() {
  if (!prompt.value.trim() || phase.value === 'submitting') return
  beginDiagnosis('manual')
}

onMounted(async () => {
  const [areaData, issueData] = await Promise.all([
    dataRepository.monitoringArea(),
    dataRepository.detectedIssue(),
  ])
  area.value = areaData
  issue.value = issueData
  scanLeft.value = runtimeConfig.playback.detectionSeconds
  processLeft.value = runtimeConfig.playback.autoProcessSeconds
  phase.value = 'scan'
  emit('beat', 'scan')

  timer = window.setInterval(() => {
    if (props.paused) return
    if (phase.value === 'scan') {
      scanLeft.value = Math.max(0, scanLeft.value - 0.1)
      if (scanLeft.value <= 0) {
        phase.value = 'pending'
        emit('beat', 'issue')
      }
      return
    }
    if (phase.value === 'pending') {
      emit('beat', 'pending')
      processLeft.value = Math.max(0, processLeft.value - 0.1)
      if (processLeft.value <= 0) beginDiagnosis('auto')
    }
  }, 100)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="act-experience act1-experience">
    <aside class="glass-panel agent-dock area-panel">
      <div class="dock-cap">
        <span class="dock-live"><i></i> CITY SENSING</span>
        <b>当前城市运行态势</b>
        <small>LIVE</small>
      </div>
      <div class="panel-heading">
        <div>
          <h2>奥体片区实时监测</h2>
          <p>解放东路—奥体西路重点区域</p>
        </div>
        <span class="status-pill normal">运行中</span>
      </div>
      <div class="area-stats">
        <div class="ops-card ok"><small>监控路口</small><strong>12</strong><span>全量在线</span></div>
        <div class="ops-card ok"><small>融合数据源</small><strong>04</strong><span>链路正常</span></div>
        <div class="ops-card live"><small>刷新频率</small><strong>2.4<em>s</em></strong><span>实时采集</span></div>
        <div class="ops-card stable"><small>系统状态</small><strong>稳</strong><span>无阻断告警</span></div>
      </div>
      <div class="section-label"><span>多源感知接入</span><b>4 / 4</b></div>
      <div class="source-list">
        <span><i class="source-icon camera"></i>电警视频</span>
        <span><i class="source-icon coil"></i>地磁检测</span>
        <span><i class="source-icon road"></i>互联网路况</span>
        <span><i class="source-icon signal"></i>信号控制</span>
      </div>
    </aside>

    <aside v-if="phase === 'scan'" class="glass-panel agent-dock scan-panel">
      <div class="dock-cap">
        <span class="dock-live"><i></i> AREA SCAN</span>
        <b>区域智能扫描</b>
        <small>{{ Math.round(scanProgress) }}%</small>
      </div>
      <div class="scan-state">
        <span class="scanner-icon">
          <i></i>
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <circle cx="60" cy="60" r="52"></circle>
            <circle
              cx="60"
              cy="60"
              r="52"
              class="scan-ring-value"
              :style="{ strokeDashoffset: `${327 - 327 * scanProgress / 100}` }"
            ></circle>
          </svg>
          <b>{{ Math.round(scanProgress) }}</b>
        </span>
        <div>
          <small>多源时空特征检索</small>
          <strong>智能体正在理解城市运行状态</strong>
          <p>路口状态 · 排队波动 · 时段特征</p>
        </div>
      </div>
      <div class="scan-progress">
        <span :style="{ width: `${scanProgress}%` }"></span>
      </div>
      <div class="scan-meta">
        <span>已检查 {{ Math.floor(scanProgress / 8.4) }}/12 个路口</span>
        <span>预计 {{ Math.ceil(scanLeft) }} 秒</span>
      </div>
    </aside>

    <transition name="panel-slide">
      <aside v-if="phase === 'pending' && issue" class="glass-panel agent-dock issue-panel">
        <div class="dock-cap alert">
          <span class="dock-live"><i></i> ANOMALY FOUND</span>
          <b>主动感知事件</b>
          <small>{{ issue.detectedAt }}</small>
        </div>
        <div class="issue-header">
          <div class="alert-seal">!</div>
          <div>
            <small>主动感知 · 新异常</small>
            <h2>{{ issue.title }}</h2>
          </div>
          <span class="status-pill warning">{{ issue.severity }}</span>
        </div>
        <div class="issue-location">{{ issue.intersectionName }}</div>
        <p>{{ issue.description }}</p>
        <div class="evidence-row">
          <span>触发证据</span>
          <strong>{{ issue.triggerMetric }}</strong>
        </div>
        <button class="primary-action" @click="beginDiagnosis('manual')">
          <span>立即启动智能研判</span>
          <b>→</b>
        </button>
        <div class="auto-process">
          <div>
            <span>无人干预将自动处理</span>
            <strong>{{ Math.ceil(processLeft) }}s</strong>
          </div>
          <div class="countdown-track">
            <span :style="{ width: `${processProgress}%` }"></span>
          </div>
        </div>
      </aside>
    </transition>

    <div class="command-input-wrap">
      <div v-if="phase === 'submitting'" class="submission-state">
        <span class="live-dot"></span>
        正在解析主动任务并匹配目标路口…
      </div>
      <div class="command-input">
        <span class="agent-glyph">AI</span>
        <input
          v-model="prompt"
          :disabled="phase === 'submitting'"
          placeholder="输入您关注的交通问题，例如：分析奥体西路与解放东路晚高峰排队情况"
          @keyup.enter="submitPrompt"
        />
        <button :disabled="!prompt.trim() || phase === 'submitting'" @click="submitPrompt">
          发送研判
        </button>
      </div>
      <div class="command-hint">
        <span>支持路口、时段、方向和问题描述</span>
        <span>ENTER 发送</span>
      </div>
    </div>
  </div>
</template>
