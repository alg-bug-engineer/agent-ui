import { computed, reactive } from 'vue'
import type { ActId } from '../types'

const state = reactive({
  activeAct: 1 as ActId,
  beat: 'scan',
  paused: false,
  replayToken: 0,
  taskSource: '被动扫描',
})

export function useNarrative() {
  const actLabels: Record<ActId, string> = {
    1: '全域感知',
    2: '问题诊断',
    3: '知识匹配',
    4: '方案生成',
    5: '效果验证',
    6: '复盘进化',
  }

  const actLabel = computed(() => actLabels[state.activeAct])

  const defaultBeats: Record<ActId, string> = {
    1: 'scan',
    2: 'cognition',
    3: 'knowledge-recall',
    4: 'plan-generation',
    5: 'deployment-confirm',
    6: 'report',
  }

  function goToAct(act: ActId, beat?: string) {
    state.activeAct = act
    state.beat = beat ?? defaultBeats[act]
    state.paused = false
    state.replayToken += 1
  }

  function setBeat(beat: string) {
    state.beat = beat
  }

  function togglePaused() {
    state.paused = !state.paused
  }

  function replay() {
    state.replayToken += 1
    state.paused = false
  }

  return { state, actLabel, goToAct, setBeat, togglePaused, replay }
}
