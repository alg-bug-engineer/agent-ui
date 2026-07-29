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
  const actLabel = computed(() => {
    if (state.activeAct === 1) return '全域感知'
    if (state.activeAct === 2) return '问题诊断'
    return '复盘进化'
  })

  function goToAct(act: ActId, beat?: string) {
    state.activeAct = act
    state.beat = beat ?? (act === 1 ? 'scan' : act === 2 ? 'locate' : 'report')
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
