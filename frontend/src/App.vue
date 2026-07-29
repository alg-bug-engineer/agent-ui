<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Act1Experience from '../act1/Act1Experience.vue'
import Act2Experience from '../act2/Act2Experience.vue'
import CityMap from './map/CityMap.vue'
import { runtimeConfig } from './config/runtime'
import { useNarrative } from './state/narrative'
import type { ActId } from './types'

const Act3Experience = defineAsyncComponent(() => import('../act3/Act3Experience.vue'))
const Act4Experience = defineAsyncComponent(() => import('../act4/Act4Experience.vue'))
const Act5Experience = defineAsyncComponent(() => import('../act5/Act5Experience.vue'))
const Act6Report = defineAsyncComponent(() => import('../act6/Act6Report.vue'))

const { state, actLabel, goToAct, setBeat } = useNarrative()

const actNames: Record<ActId, string> = {
  1: '全域感知',
  2: '问题诊断',
  3: '知识匹配',
  4: '方案生成',
  5: '效果验证',
  6: '复盘进化',
}

const now = ref(new Date())
type PresentationMode = 'map' | 'detail'
const defaultPresentationMode = (act: ActId): PresentationMode => act === 2 ? 'map' : 'detail'
const presentationMode = ref<PresentationMode>(defaultPresentationMode(state.activeAct))
let clockTimer = 0

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

function switchAct(act: ActId) {
  goToAct(act)
}

function togglePresentationMode() {
  presentationMode.value = presentationMode.value === 'map' ? 'detail' : 'map'
  window.requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
}

watch(
  () => state.activeAct,
  (act) => {
    presentationMode.value = defaultPresentationMode(act)
    window.requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
  },
)

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))
</script>

<template>
  <main
    class="app-shell"
    :class="[`act-${state.activeAct}`, `${presentationMode}-focus-mode`]"
  >
    <CityMap :active-act="state.activeAct" :beat="state.beat" />

    <header class="command-header">
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true">
          <span></span><span></span><span></span>
        </div>
        <div>
          <p>JINAN TRAFFIC INTELLIGENCE</p>
          <h1>{{ runtimeConfig.app.title }}</h1>
        </div>
      </div>

      <nav class="act-navigation" aria-label="演示幕次">
        <button
          v-for="act in ([1, 2, 3, 4, 5, 6] as ActId[])"
          :key="act"
          :class="{ active: state.activeAct === act }"
          @click="switchAct(act)"
        >
          <small>ACT 0{{ act }}</small>
          <span>{{ actNames[act] }}</span>
        </button>
      </nav>

      <div class="system-status">
        <button
          class="presentation-mode-toggle"
          :class="{ active: presentationMode === 'detail' }"
          :aria-pressed="presentationMode === 'detail'"
          @click="togglePresentationMode"
        >
          <i></i>
          <span>{{ presentationMode === 'map' ? '展开研判' : '收起研判' }}</span>
        </button>
        <div class="status-copy">
          <span class="live-dot"></span>
          <div>
            <strong>智能体在线</strong>
            <small>{{ actLabel }} · 实时运行</small>
          </div>
        </div>
        <div class="clock">
          <strong>{{ currentTime }}</strong>
          <small>{{ currentDate }}</small>
        </div>
      </div>
    </header>

    <section class="act-stage">
      <Act1Experience
        v-if="state.activeAct === 1"
        :key="`act1-${state.replayToken}`"
        :paused="state.paused"
        @beat="setBeat"
        @enter-diagnosis="goToAct(2)"
      />
      <Act2Experience
        v-else-if="state.activeAct === 2"
        :key="`act2-${state.replayToken}`"
        @beat="setBeat"
        @open-knowledge="goToAct(3)"
      />
      <Act3Experience
        v-else-if="state.activeAct === 3"
        :key="`act3-${state.replayToken}`"
        @beat="setBeat"
        @open-plan="goToAct(4)"
      />
      <Act4Experience
        v-else-if="state.activeAct === 4"
        :key="`act4-${state.replayToken}`"
        @beat="setBeat"
        @open-effect="goToAct(5)"
      />
      <Act5Experience
        v-else-if="state.activeAct === 5"
        :key="`act5-${state.replayToken}`"
        @beat="setBeat"
        @open-review="goToAct(6)"
      />
      <Act6Report
        v-else
        :key="`act6-${state.replayToken}`"
        @beat="setBeat"
      />
    </section>
  </main>
</template>
