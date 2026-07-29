<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import CityMap from './map/CityMap.vue'
import { runtimeConfig } from './config/runtime'
import type { ActId } from './types'
import V2ExecutiveExperience from './v2/V2ExecutiveExperience.vue'

type PresentationView = 'home' | 'flow'

const view = ref<PresentationView>('home')
const activeStage = ref<ActId>(1)
const now = ref(new Date())
let clockTimer = 0

const stages: Array<{ id: ActId; label: string; short: string }> = [
  { id: 1, label: '多源感知', short: '感知' },
  { id: 2, label: '智能研判', short: '研判' },
  { id: 3, label: '方案生成', short: '生成' },
  { id: 4, label: '落地执行', short: '执行' },
  { id: 5, label: '效果优化', short: '优化' },
  { id: 6, label: '持续优化', short: '进化' },
]

const stageMapBeats: Record<ActId, { activeAct: ActId; beat: string }> = {
  1: { activeAct: 2, beat: 'evidence' },
  2: { activeAct: 2, beat: 'trace' },
  3: { activeAct: 3, beat: 'similar-cases' },
  4: { activeAct: 4, beat: 'deployment' },
  5: { activeAct: 5, beat: 'before-after' },
  6: { activeAct: 6, beat: 'report' },
}

const mapState = computed(() =>
  view.value === 'home'
    ? { activeAct: 1 as ActId, beat: 'scan' }
    : stageMapBeats[activeStage.value],
)

const currentTime = computed(() =>
  now.value.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }),
)

const currentDate = computed(() =>
  now.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'short',
  }),
)

function openFlow() {
  activeStage.value = 1
  view.value = 'flow'
  requestResize()
}

function openHome() {
  view.value = 'home'
  requestResize()
}

function setStage(stage: ActId) {
  activeStage.value = stage
  requestResize()
}

function requestResize() {
  window.requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
}

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))
</script>

<template>
  <main
    class="app-shell v2-app"
    :class="[
      view === 'home' ? 'v2-home-mode act-1' : `v2-flow-mode act-${activeStage}`,
    ]"
  >
    <CityMap :active-act="mapState.activeAct" :beat="mapState.beat" />

    <header class="command-header v2-command-header">
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true">
          <span></span><span></span><span></span>
        </div>
        <div>
          <p>JINAN TRAFFIC CONTROL AGENT</p>
          <h1>{{ runtimeConfig.app.title }}</h1>
        </div>
      </div>

      <div v-if="view === 'home'" class="v2-home-headline">
        <span><i></i> AI 自主优化模式</span>
        <strong>感知 · 研判 · 生成 · 执行 · 评估 · 进化</strong>
      </div>

      <nav v-else class="v2-stage-navigation" aria-label="全流程信号优化">
        <button
          v-for="stage in stages"
          :key="stage.id"
          :class="{ active: activeStage === stage.id, done: activeStage > stage.id }"
          :aria-current="activeStage === stage.id ? 'step' : undefined"
          @click="setStage(stage.id)"
        >
          <span>{{ activeStage > stage.id ? '✓' : String(stage.id).padStart(2, '0') }}</span>
          <strong>{{ stage.label }}</strong>
        </button>
      </nav>

      <div class="system-status v2-system-status">
        <button v-if="view === 'flow'" class="v2-home-return" @click="openHome">
          <span>⌂</span> 返回扫描首页
        </button>
        <div class="status-copy">
          <span class="live-dot"></span>
          <div>
            <strong>智能体在线</strong>
            <small>{{ view === 'home' ? '全域持续扫描' : `闭环任务 · ${stages[activeStage - 1].label}` }}</small>
          </div>
        </div>
        <div class="clock">
          <strong>{{ currentTime }}</strong>
          <small>{{ currentDate }}</small>
        </div>
      </div>
    </header>

    <V2ExecutiveExperience
      :view="view"
      :active-stage="activeStage"
      @start="openFlow"
      @home="openHome"
      @stage="setStage"
    />
  </main>
</template>
