<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dataRepository } from '../src/services/dataRepository'
import type { TimingPlanScene } from '../src/types'

const emit = defineEmits<{
  beat: [value: string]
  openEffect: []
}>()

const beats = [
  {
    id: 'plan-generation',
    title: '方案生成',
    subtitle: '秒级测算周期、绿信比与相位差',
  },
  {
    id: 'plan-options',
    title: '方案对比',
    subtitle: '单点加绿 · 上游截流 · 协同组合',
  },
  {
    id: 'impact-preview',
    title: '影响预估',
    subtitle: '目标、垂直、上游、下游同屏评估',
  },
  {
    id: 'deployment',
    title: '落地执行',
    subtitle: '下发信号机并绑定自动回退护栏',
  },
] as const

const currentIndex = ref(0)
const plan = ref<TimingPlanScene | null>(null)
const activeOptionId = ref('')

const current = computed(() => beats[currentIndex.value])
const completed = computed(() => currentIndex.value === beats.length - 1)
const overallProgress = computed(() => ((currentIndex.value + 1) / beats.length) * 100)
const activeOption = computed(() =>
  plan.value?.options.find((item) => item.id === activeOptionId.value) ?? plan.value?.options[0],
)
const activeImpact = computed(() =>
  plan.value?.impacts.find((item) => item.optionId === activeOptionId.value) ?? plan.value?.impacts[0],
)
const speedupMultiple = computed(() => {
  if (!plan.value) return 0
  return Math.round((plan.value.manualBaselineMinutes * 60) / plan.value.generationSeconds)
})

function selectBeat(index: number) {
  currentIndex.value = index
  emit('beat', beats[index].id)
}

function goPrev() {
  if (currentIndex.value > 0) selectBeat(currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value < beats.length - 1) {
    selectBeat(currentIndex.value + 1)
    return
  }
  emit('openEffect')
}

onMounted(async () => {
  const planData = await dataRepository.timingPlan()
  plan.value = planData
  activeOptionId.value = planData.options.find((item) => item.recommended)?.id ?? planData.options[0]?.id ?? ''
  emit('beat', current.value.id)
})
</script>

<template>
  <div class="act-experience act4-experience">
    <aside class="glass-panel agent-dock reasoning-panel">
      <div class="dock-cap">
        <span class="dock-live"><i></i> PLAN GENERATION</span>
        <b>方案生成链</b>
        <small>{{ String(currentIndex + 1).padStart(2, '0') }} / {{ String(beats.length).padStart(2, '0') }}</small>
      </div>

      <div class="diagnosis-title">
        <div class="agent-emblem"><span></span><span></span><span></span></div>
        <div>
          <h2>配时方案自主测算</h2>
          <p>周期 · 绿信比 · 相位差 · 落地执行</p>
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
          {{ completed ? '方案已下发 · 进入效果追踪' : `待检查 · ${current.title}` }}
        </div>
        <div class="step-check-nav">
          <button :disabled="currentIndex === 0" @click="goPrev">← 上一步</button>
          <button class="next-act" @click="goNext">
            {{ completed ? '进入效果验证 →' : '下一步 →' }}
          </button>
        </div>
      </div>
    </aside>

    <aside v-if="plan" class="glass-panel agent-dock evidence-panel">
      <div class="dock-cap evidence-cap">
        <span class="dock-live"><i></i> ANALYSIS WORKBENCH</span>
        <b>{{ current.title }}</b>
        <small>LIVE</small>
      </div>

      <template v-if="current.id === 'plan-generation'">
        <div class="evidence-heading"><span>秒级测算，替代人工调参</span><b>01</b></div>
        <div class="speed-compare">
          <div><span>人工调参基线</span><strong>{{ plan.manualBaselineMinutes }}<small>分钟</small></strong></div>
          <i>vs</i>
          <div class="highlight"><span>智能体测算</span><strong>{{ plan.generationSeconds }}<small>秒</small></strong></div>
        </div>
        <div class="plain-conclusion">
          <b>效率结论</b>
          较人工提速约 {{ speedupMultiple }} 倍，响应能力从“分钟级”跃升至“秒级”。
        </div>
        <div class="timing-plan-grid">
          <div class="timing-plan-head">
            <span>相位</span><span>当前绿灯</span><span>建议绿灯</span><span>占周期比</span>
          </div>
          <div v-for="phase in plan.recommended.phases" :key="phase.name" class="timing-plan-row">
            <strong>{{ phase.name }}</strong>
            <span>{{ phase.currentGreen }}s</span>
            <b :class="{ changed: phase.currentGreen !== phase.proposedGreen }">{{ phase.proposedGreen }}s</b>
            <em>{{ Math.round(phase.ratio * 100) }}%</em>
          </div>
        </div>
        <div class="cycle-meta">
          <span>信号周期</span><strong>{{ plan.recommended.cycleSeconds }}s（不变）</strong>
          <span>相位差调整</span><strong>{{ plan.recommended.phaseDiffSeconds }}s</strong>
        </div>
      </template>

      <template v-else-if="current.id === 'plan-options'">
        <div class="evidence-heading"><span>三种候选方案</span><b>02</b></div>
        <div class="strategy-list">
          <article
            v-for="item in plan.options"
            :key="item.id"
            :class="{ recommended: item.recommended, active: item.id === activeOptionId }"
            @click="activeOptionId = item.id"
          >
            <header>
              <strong>{{ item.name }}</strong>
              <span>{{ item.recommended ? '推荐执行' : '对照方案' }}</span>
            </header>
            <h3>{{ item.summary }}</h3>
            <div>
              <p><span>周期</span>{{ item.cycleSeconds }}s</p>
              <p><span>目标方向增量</span>+{{ item.targetGreenDeltaSeconds }}s</p>
              <p><span>上游削峰</span>{{ item.upstreamMeteringPct }}%</p>
            </div>
          </article>
        </div>
        <div class="plain-conclusion">
          <b>选择结论</b>
          单点加绿见效快但转移压力，上游截流安全但偏慢，协同组合三处均在安全边界内，作为推荐执行方案。
        </div>
      </template>

      <template v-else-if="current.id === 'impact-preview' && activeImpact">
        <div class="evidence-heading"><span>方案影响预估 · 四维同屏</span><b>03</b></div>
        <div class="plan-tab-row">
          <button
            v-for="item in plan.options"
            :key="item.id"
            :class="{ active: item.id === activeOptionId }"
            @click="activeOptionId = item.id"
          >
            <small>{{ item.recommended ? '推荐' : '对照' }}</small>
            <strong>{{ item.name }}</strong>
          </button>
        </div>
        <div class="impact-grid">
          <article :class="activeImpact.target.tone">
            <span>目标方向 · 北进口</span>
            <div><b>{{ activeImpact.target.before }}</b><i>→</i><strong>{{ activeImpact.target.after }}</strong></div>
          </article>
          <article :class="activeImpact.conflict.tone">
            <span>垂直冲突 · 东西向</span>
            <div><b>{{ activeImpact.conflict.before }}</b><i>→</i><strong>{{ activeImpact.conflict.after }}</strong></div>
          </article>
          <article :class="activeImpact.upstream.tone">
            <span>上游来车强度</span>
            <div><b>{{ activeImpact.upstream.before }}</b><i>→</i><strong>{{ activeImpact.upstream.after }}</strong></div>
          </article>
          <article :class="activeImpact.downstream.tone">
            <span>下游承接 · 占有率</span>
            <div><b>{{ activeImpact.downstream.before }}</b><i>→</i><strong>{{ activeImpact.downstream.after }}</strong></div>
          </article>
        </div>
        <div class="plain-conclusion" :class="{ warning: activeOption && !activeOption.recommended }">
          <b>影响结论</b>
          {{ activeOption?.recommended
            ? '推荐方案让四个方向的变化都保持在安全边界内，未把压力转移给其他方向。'
            : '该方案在目标方向见效，但会把压力转移给其他方向，仅作对照。' }}
        </div>
      </template>

      <template v-else>
        <div class="evidence-heading"><span>方案落地执行</span><b>04</b></div>
        <div class="decision-card">
          <small>已下发信号机</small>
          <h2>{{ plan.options.find((item) => item.recommended)?.name }}</h2>
          <ol>
            <li>{{ plan.deployment.controller }}</li>
            <li>{{ plan.deployment.status }}</li>
            <li>{{ plan.deployment.effectiveAt }}</li>
          </ol>
        </div>
        <div class="guardrail-list">
          <strong>自动回退条件</strong>
          <span v-for="item in plan.deployment.rollbackConditions" :key="item"><i>!</i>{{ item }}</span>
        </div>
        <div class="expected-outcome">方案已生效，进入执行效果追踪与前后对比验证。</div>
        <button class="primary-action report-entry" @click="emit('openEffect')">
          <span>进入执行效果验证</span><b>→</b>
        </button>
      </template>

      <div class="analysis-source">
        <span>数据口径</span>
        <b>路口路网快照真实 · 配时参数与影响预估来自专业模型测算</b>
        <small>用于支撑智能体自主测算与副作用控制</small>
      </div>
    </aside>
  </div>
</template>
