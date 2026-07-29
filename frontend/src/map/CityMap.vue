<script setup lang="ts">
import AMapLoader from '@amap/amap-jsapi-loader'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { runtimeConfig } from '../config/runtime'
import { dataRepository } from '../services/dataRepository'
import { buildChannelizationGeometry } from '../../act2/channelizationGeometry'
import type {
  ActId,
  ChannelizationScene,
  DevicePoint,
  ExpertDiagnosis,
  FlowTraceScene,
  MonitoredIntersection,
  TargetIntersection,
} from '../types'

const props = defineProps<{ activeAct: ActId; beat: string }>()

const mapHost = ref<HTMLDivElement | null>(null)
const mapReady = ref(false)
const mapFailed = ref(false)
const intersections = ref<MonitoredIntersection[]>([])
const devices = ref<DevicePoint[]>([])
const target = ref<TargetIntersection | null>(null)
const channelization = ref<ChannelizationScene | null>(null)
const topology = ref<any>(null)
const flowTrace = ref<FlowTraceScene | null>(null)
const diagnosis = ref<ExpertDiagnosis | null>(null)
type SimulationScenarioId = 'baseline' | 'green-only' | 'combined'
const simulationScenario = ref<SimulationScenarioId>('baseline')

interface MapNarrative {
  chapter: string
  eyebrow: string
  headline: string
  summary: string
  tone: 'critical' | 'warning' | 'action' | 'success' | 'neutral'
  metrics: Array<{ label: string; value: string; status?: 'safe' | 'risk' }>
}

interface StrategyComparisonCard {
  id: SimulationScenarioId
  index: string
  name: string
  action: string
  verdict: string
  tone: 'critical' | 'warning' | 'success'
  status: string
  target: string
  conflict: string
  downstream: string
}

const strategyComparisonCards: StrategyComparisonCard[] = [
  {
    id: 'baseline',
    index: '01',
    name: '不干预',
    action: '保持当前配时，继续观察',
    verdict: '北进口排队继续增长，溢流风险无法解除。',
    tone: 'critical',
    status: '不采用',
    target: '129m ↗',
    conflict: '63m',
    downstream: '42%',
  },
  {
    id: 'green-only',
    index: '02',
    name: '单点加绿 +8s',
    action: '只增加北进口直行绿灯',
    verdict: '北进口缓解，但东西向升至 101m，压力发生转移。',
    tone: 'warning',
    status: '否决',
    target: '88m',
    conflict: '101m 越界',
    downstream: '61%',
  },
  {
    id: 'combined',
    index: '03',
    name: '协同组合',
    action: '目标 +4s · 上游削峰 12% · 下游绿波',
    verdict: '三个空间角色均在安全边界内，推荐执行。',
    tone: 'success',
    status: '推荐',
    target: '78m',
    conflict: '71m 安全',
    downstream: '55% 安全',
  },
]

const activeStrategyCard = computed(() =>
  strategyComparisonCards.find((item) => item.id === simulationScenario.value)
  ?? strategyComparisonCards[0],
)

const operatingPortrait = computed(() => diagnosis.value?.operatingPortrait ?? null)

const narrativeBeatOrder = [
  'cognition',
  'evidence',
  'direction',
  'cause',
  'constraints',
  'options',
  'simulation',
  'decision',
  'trace',
]

const narrativeProgress = computed(() => {
  if (props.activeAct === 1) return props.beat === 'scan' ? 8 : 14
  if (props.activeAct === 6) return 100
  const index = narrativeBeatOrder.indexOf(props.beat)
  return index < 0 ? 0 : Math.round(((index + 1) / narrativeBeatOrder.length) * 100)
})

const nextNarrative = computed(() => {
  const messages: Record<string, string> = {
    cognition: '下一步：把排队长度与动态阈值放到道路上核验',
    evidence: '下一步：镜头拉远，建立目标、冲突方向与上下游拓扑关系',
    direction: '下一步：沿拓扑关系逐项排除成因',
    cause: '下一步：先划定安全边界，再生成控制动作',
    constraints: '下一步：把三个治理动作放到地图具体位置',
    options: '下一步：对比不干预、单点加绿与协同组合',
    simulation: '三种方案逐项推演，地图与结果卡同步变化',
    decision: '下一步：继续向上游追溯流量源头',
    trace: '研判完成：进入知识匹配与策略生成',
  }
  return messages[props.beat] ?? ''
})

const simulationNarratives: Record<typeof simulationScenario.value, MapNarrative> = {
  baseline: {
    chapter: '反事实推演',
    eyebrow: '方案 01 · 不干预',
    headline: '北进口排队继续增长，溢流风险维持高位',
    summary: '仅观察、不采取动作，无法阻断连续到达波与放行不足的叠加。',
    tone: 'critical',
    metrics: [
      { label: '北进口', value: '129m', status: 'risk' },
      { label: '东西向', value: '63m', status: 'safe' },
      { label: '下游', value: '42%', status: 'safe' },
    ],
  },
  'green-only': {
    chapter: '反事实推演',
    eyebrow: '方案 02 · 单点 +8s',
    headline: '北进口得到缓解，但压力被转移到东西向',
    summary: '东西向排队升至 101m，突破 92m 警戒线，单点加绿不采用。',
    tone: 'warning',
    metrics: [
      { label: '北进口', value: '88m', status: 'safe' },
      { label: '东西向', value: '101m', status: 'risk' },
      { label: '下游', value: '61%', status: 'safe' },
    ],
  },
  combined: {
    chapter: '反事实推演',
    eyebrow: '方案 03 · 协同组合',
    headline: '三处均在安全边界内，组合方案通过推演',
    summary: '目标排队下降，冲突方向和下游承接保持安全，推荐执行。',
    tone: 'success',
    metrics: [
      { label: '北进口', value: '78m', status: 'safe' },
      { label: '东西向', value: '71m < 92m', status: 'safe' },
      { label: '下游', value: '55% < 65%', status: 'safe' },
    ],
  },
}

const beatNarratives: Record<string, MapNarrative> = {
  issue: {
    chapter: '发现',
    eyebrow: '全域扫描 · 主动发现',
    headline: '北进口排队 129m，连续 3 个周期超过动态阈值',
    summary: '系统从 12 个监控路口中锁定唯一重点异常。',
    tone: 'critical',
    metrics: [
      { label: '当前排队', value: '129m', status: 'risk' },
      { label: '动态阈值', value: '114.8m' },
      { label: '超限', value: '+12.4%', status: 'risk' },
    ],
  },
  pending: {
    chapter: '发现',
    eyebrow: '异常已锁定 · 等待研判',
    headline: '北进口排队 129m，连续 3 个周期超过动态阈值',
    summary: '目标路口、异常方向与触发证据已经完成空间绑定。',
    tone: 'critical',
    metrics: [
      { label: '当前排队', value: '129m', status: 'risk' },
      { label: '动态阈值', value: '114.8m' },
      { label: '异常方向', value: '北进口' },
    ],
  },
  cognition: {
    chapter: '路口认知',
    eyebrow: '真实渠化 · 方向锁定',
    headline: '诊断对象锁定为北进口向南直行',
    summary: '分析同步覆盖垂直冲突、下游承接和上游来车三个空间角色。',
    tone: 'neutral',
    metrics: [
      { label: '进口车道', value: '16' },
      { label: '在线设备', value: '24' },
      { label: '感知覆盖', value: '91.7%', status: 'safe' },
    ],
  },
  direction: {
    chapter: '路口拓扑分析',
    eyebrow: '路口拓扑 · 空间关系',
    headline: '问题集中在北进口，其他方向尚未失稳',
    summary: '上游连续来车可能放大排队，垂直方向与下游仍有安全余量。',
    tone: 'warning',
    metrics: [
      { label: '北进口', value: '129m', status: 'risk' },
      { label: '东西向', value: '63m', status: 'safe' },
      { label: '下游占有率', value: '42%', status: 'safe' },
    ],
  },
  evidence: {
    chapter: '异常核验',
    eyebrow: '道路实体证据 · 异常成立',
    headline: '排队长度越过 114.8m 动态阈值，并持续增长',
    summary: '道路长度尺、三个周期队尾和现场影像相互印证。',
    tone: 'critical',
    metrics: [
      { label: '实际排队', value: '129m', status: 'risk' },
      { label: '动态阈值', value: '114.8m' },
      { label: '持续周期', value: '3' },
    ],
  },
  cause: {
    chapter: '溢流判因',
    eyebrow: '因果链 · 逐项排除',
    headline: '上游来车放大排队，目标方向有效放行不足',
    summary: '下游仍有 168m 储车空间，排除下游阻塞型溢流。',
    tone: 'warning',
    metrics: [
      { label: '上游前两跳', value: '57.9%', status: 'risk' },
      { label: '绿灯利用率', value: '54.2%', status: 'risk' },
      { label: '下游占有率', value: '42%', status: 'safe' },
    ],
  },
  constraints: {
    chapter: '约束检查',
    eyebrow: '安全边界 · 先约束后调控',
    headline: '具备调控条件，但必须同时守住三条安全边界',
    summary: '东西向、下游与上游截流均设置自动回退条件。',
    tone: 'neutral',
    metrics: [
      { label: '东西向警戒', value: '92m' },
      { label: '下游上限', value: '65%' },
      { label: '截流上限', value: '12%' },
    ],
  },
  options: {
    chapter: '方案生成',
    eyebrow: '组合治理 · 动作落位',
    headline: '适度加放 + 上游削峰 + 下游协调',
    summary: '三个动作分别落在目标、上游和下游，避免单点调控转移风险。',
    tone: 'action',
    metrics: [
      { label: '目标相位', value: '+4s' },
      { label: '上游削峰', value: '12%' },
      { label: '下游动作', value: '绿波协调' },
    ],
  },
  decision: {
    chapter: '专家决策',
    eyebrow: '专家决策 · 带护栏执行',
    headline: '组合策略通过决策，三个周期内完成效果验证',
    summary: '动作、空间位置与自动回退条件已同时绑定。',
    tone: 'success',
    metrics: [
      { label: '北进口', value: '+4s' },
      { label: '上游', value: '-12%' },
      { label: '预计排队', value: '78m', status: 'safe' },
    ],
  },
  trace: {
    chapter: '源头治理',
    eyebrow: '源头治理 · 六跳溯源',
    headline: '奥体西路北侧连续来车波是主要源头',
    summary: '主走廊六跳累计解释 92.0% 到达流量，治理动作落到具体上游节点。',
    tone: 'action',
    metrics: [
      { label: '累计解释', value: '92.0%' },
      { label: '前两跳贡献', value: '57.9%' },
      { label: '主走廊', value: '6 跳' },
    ],
  },
}

const mapNarrative = computed<MapNarrative | null>(() => {
  if (props.activeAct === 6) return null
  if (props.beat === 'simulation') return simulationNarratives[simulationScenario.value]
  return beatNarratives[props.beat] ?? null
})

let AMapApi: any = null
let map: any = null
let baseOverlays: any[] = []
let stageOverlays: any[] = []
let overlayScope: 'base' | 'stage' = 'base'
let renderedSceneKind = ''
let simulationApplyScenario: ((id: SimulationScenarioId) => void) | null = null
let scanTimer = 0
let renderGeneration = 0
const deferredTimers: number[] = []
const animationTimers: number[] = []
const retirementFrames = new Set<number>()
let flowParticles: Array<{
  marker: any
  path: Array<[number, number]>
  phase: number
  speed: number
}> = []

function htmlElement(className: string, innerHTML = '') {
  const element = document.createElement('div')
  element.className = className
  element.innerHTML = innerHTML
  return element
}

function addOverlay<T>(overlay: T): T {
  if (overlayScope === 'stage') stageOverlays.push(overlay)
  else baseOverlays.push(overlay)
  map?.add?.(overlay)
  return overlay
}

function retireOverlays(overlays: any[], immediate = false) {
  if (!map || overlays.length === 0) return
  if (immediate) {
    map.remove(overlays)
    return
  }

  const duration = 420
  const startedAt = performance.now()
  const requestFadeFrame = (callback: FrameRequestCallback) => {
    const frame = window.requestAnimationFrame((now) => {
      retirementFrames.delete(frame)
      callback(now)
    })
    retirementFrames.add(frame)
  }
  const vectorStates = overlays.map((overlay) => {
    const content = overlay.getContent?.()
    if (content instanceof HTMLElement) content.classList.add('geo-overlay-leaving')
    const options = overlay.getOptions?.() ?? {}
    return {
      overlay,
      strokeOpacity: typeof options.strokeOpacity === 'number' ? options.strokeOpacity : null,
      fillOpacity: typeof options.fillOpacity === 'number' ? options.fillOpacity : null,
      opacity: typeof options.opacity === 'number' ? options.opacity : null,
    }
  })

  const fade = (now: number) => {
    const progress = Math.min(1, (now - startedAt) / duration)
    const eased = 1 - (1 - progress) ** 3
    vectorStates.forEach((state) => {
      const options: Record<string, number> = {}
      if (state.strokeOpacity !== null) options.strokeOpacity = state.strokeOpacity * (1 - eased)
      if (state.fillOpacity !== null) options.fillOpacity = state.fillOpacity * (1 - eased)
      if (state.opacity !== null) options.opacity = state.opacity * (1 - eased)
      if (Object.keys(options).length > 0) state.overlay.setOptions?.(options)
    })
    if (progress < 1) {
      requestFadeFrame(fade)
    } else {
      map?.remove?.(overlays)
    }
  }
  requestFadeFrame(fade)
}

function clearStageScene(immediate = false) {
  renderGeneration += 1
  window.clearInterval(scanTimer)
  scanTimer = 0
  deferredTimers.splice(0).forEach((timer) => window.clearTimeout(timer))
  animationTimers.splice(0).forEach((timer) => window.clearInterval(timer))
  flowParticles = []
  simulationScenario.value = 'baseline'
  simulationApplyScenario = null
  retireOverlays(stageOverlays, immediate)
  stageOverlays = []
}

function clearScene(immediate = false) {
  clearStageScene(immediate)
  retireOverlays(baseOverlays, immediate)
  baseOverlays = []
  overlayScope = 'base'
}

function metersToGeo(center: [number, number], eastM: number, northM: number): [number, number] {
  const latRadians = center[1] * Math.PI / 180
  return [
    center[0] + eastM / (111_320 * Math.cos(latRadians)),
    center[1] + northM / 110_540,
  ]
}

function defer(callback: () => void, delay: number) {
  const generation = renderGeneration
  const timer = window.setTimeout(() => {
    if (generation === renderGeneration) callback()
  }, delay)
  deferredTimers.push(timer)
}

function addPolyline(path: Array<[number, number]>, options: Record<string, unknown> = {}) {
  return addOverlay(new AMapApi.Polyline({
    path,
    strokeColor: '#1c7f92',
    strokeWeight: 3,
    strokeOpacity: 0.82,
    lineJoin: 'round',
    lineCap: 'round',
    ...options,
  }))
}

function addTargetAnchor(label = '诊断路口', detail?: string) {
  if (!target.value) return
  addOverlay(new AMapApi.CircleMarker({
    center: target.value.center,
    radius: 25,
    strokeColor: '#16a394',
    strokeWeight: 2,
    strokeOpacity: 0.9,
    fillColor: '#27b6a8',
    fillOpacity: 0.12,
    zIndex: 108,
  }))
  addOverlay(new AMapApi.CircleMarker({
    center: target.value.center,
    radius: 7,
    strokeColor: '#ffffff',
    strokeWeight: 3,
    fillColor: '#0b847b',
    fillOpacity: 1,
    zIndex: 110,
  }))
  addOverlay(new AMapApi.Marker({
    position: target.value.center,
    anchor: 'bottom-left',
    offset: new AMapApi.Pixel(16, -10),
    content: htmlElement(
      'geo-map-info-card geo-anchor-label',
      `<strong>${label}</strong><span>${detail ?? target.value.name}</span>`,
    ),
    zIndex: 112,
  }))
}

function renderAct1() {
  intersections.value.forEach((item) => {
    addOverlay(new AMapApi.Marker({
      position: item.position,
      anchor: 'center',
      content: htmlElement(`geo-monitor-marker ${item.status}`, '<i></i><b></b>'),
      zIndex: item.status === 'attention' ? 95 : 80,
      title: item.name,
    }))
  })

  if (props.beat === 'scan') {
    const west = 117.1028
    const east = 117.1182
    const south = 36.6584
    const north = 36.6706
    const beamWidth = (east - west) * 0.055
    const texture = document.createElement('canvas')
    texture.width = 256
    texture.height = 64
    const context = texture.getContext('2d')
    const gradient = context?.createLinearGradient(0, 0, texture.width, 0)
    gradient?.addColorStop(0, 'rgba(0,255,255,0)')
    gradient?.addColorStop(0.38, 'rgba(0,255,255,.13)')
    gradient?.addColorStop(0.50, 'rgba(255,255,255,.96)')
    gradient?.addColorStop(0.62, 'rgba(0,255,255,.20)')
    gradient?.addColorStop(1, 'rgba(0,255,255,0)')
    if (context && gradient) {
      context.fillStyle = gradient
      context.fillRect(0, 0, texture.width, texture.height)
    }
    const boundsAt = (longitude: number) => new AMapApi.Bounds(
      [longitude - beamWidth / 2, south],
      [longitude + beamWidth / 2, north],
    )
    const beam = addOverlay(new AMapApi.ImageLayer({
      bounds: boundsAt(west - beamWidth),
      url: texture.toDataURL('image/png'),
      opacity: 0.72,
      zIndex: 93,
      zooms: [3, 20],
    }))
    const scanFrame = addOverlay(new AMapApi.Rectangle({
      bounds: new AMapApi.Bounds([west, south], [east, north]),
      strokeColor: '#00d4f0',
      strokeWeight: 1,
      strokeOpacity: 0.2,
      strokeStyle: 'dashed',
      strokeDasharray: [6, 8],
      fillOpacity: 0,
      zIndex: 68,
    }))
    scanFrame.setMap?.(map)
    const startedAt = performance.now()
    scanTimer = window.setInterval(() => {
      // 参考 cityScan：单向 3.2 秒扫过完整包围盒，然后立即开启下一轮。
      const progress = ((performance.now() - startedAt) % 3200) / 3200
      const longitude = west - beamWidth + (east - west + beamWidth * 2) * progress
      beam.setBounds(boundsAt(longitude))
      beam.setOpacity?.(Math.sin(progress * Math.PI) * 0.74)
    }, 32)
  }

  if (['issue', 'pending'].includes(props.beat) && target.value) {
    addOverlay(new AMapApi.Marker({
      position: target.value.center,
      anchor: 'bottom-left',
      offset: new AMapApi.Pixel(-21, 0),
      content: htmlElement(
        'geo-issue-pin',
        '<span class="pin-head"><b>!</b></span><span class="pin-caption"><strong>检测到排队异常</strong><small>北进口 · 连续 3 个周期超阈值</small></span>',
      ),
      zIndex: 150,
      title: '检测到排队异常',
    }))
  }
}

function renderDevices() {
  addTargetAnchor('设备核验中心')
  devices.value.forEach((device) => {
    addOverlay(new AMapApi.Marker({
      position: device.position,
      anchor: 'center',
      content: htmlElement(
        `geo-device-marker ${device.type} ${device.status}`,
        `<i></i><span class="geo-map-info-card"><strong>${device.name}</strong><small>${device.lane} · ${device.status === 'online' ? '在线' : '离线'}</small></span>`,
      ),
      zIndex: 120,
      title: `${device.name} · ${device.lane}`,
    }))
  })
}

function renderStaticPortrait() {
  const portrait = diagnosis.value?.staticPortrait
  if (!target.value || !portrait) return

  portrait.items.forEach((item, index) => {
    defer(() => {
      const position = metersToGeo(
        target.value!.center,
        item.positionOffsetM[0],
        item.positionOffsetM[1],
      )
      addOverlay(new AMapApi.Marker({
        position,
        anchor: 'bottom-center',
        content: htmlElement(
          `geo-map-info-card geo-operating-portrait geo-static-portrait ${item.tone}`,
          `<header>
             <div><strong>${item.label}</strong><small>${portrait.title} · ${portrait.radiusM}m</small></div>
             <span>${String(index + 1).padStart(2, '0')}</span>
           </header>
           <div class="operating-portrait-metrics">
             <span><small>吸引占比</small><strong>${item.sharePct}%</strong></span>
           </div>
           <footer>${item.caption}</footer>`,
        ),
        zIndex: 148 + index,
        title: `${item.label} · ${item.sharePct}% · ${portrait.source}`,
      }))
    }, 960 + index * 130)
  })
}

function laneArrowSvg(movements: Array<'left' | 'straight' | 'right'>) {
  const paths: string[] = []
  if (movements.includes('straight')) {
    paths.push('<path d="M20 36V10M13 17l7-8 7 8"/>')
  } else {
    paths.push('<path d="M20 36V24"/>')
  }
  if (movements.includes('left')) {
    paths.push('<path d="M20 25c0-8-4-11-12-11M14 8l-7 6 7 6"/>')
  }
  if (movements.includes('right')) {
    paths.push('<path d="M20 25c0-8 4-11 12-11M26 8l7 6-7 6"/>')
  }
  return `<svg viewBox="0 0 40 44" aria-hidden="true">${paths.join('')}</svg>`
}

function renderChannelization() {
  if (!channelization.value) return
  const geometry = buildChannelizationGeometry(channelization.value)

  geometry.roadPolygons.forEach((path) => {
    addOverlay(new AMapApi.Polygon({
      path,
      strokeColor: '#1e1e1e',
      strokeWeight: 1,
      strokeOpacity: 0.9,
      fillColor: '#2c2c2c',
      fillOpacity: 0.94,
      zIndex: 96,
    }))
  })
  defer(() => {
    geometry.curbs.forEach((path) => addPolyline(path, {
      strokeColor: '#b0b8c0',
      strokeWeight: 3,
      strokeOpacity: 0.96,
      zIndex: 106,
    }))
    geometry.dividers.forEach((path) => addPolyline(path, {
      strokeColor: '#ffcc00',
      strokeWeight: 2,
      strokeOpacity: 0.98,
      zIndex: 107,
    }))
    geometry.cornerLines.forEach((path) => addPolyline(path, {
      strokeColor: '#ffffff',
      strokeWeight: 3,
      strokeOpacity: 0.92,
      zIndex: 108,
    }))
  }, 150)
  defer(() => {
    geometry.laneLines.forEach((path) => addPolyline(path, {
      strokeColor: '#cccccc',
      strokeWeight: 2,
      strokeStyle: 'dashed',
      strokeDasharray: [8, 7],
      strokeOpacity: 0.88,
      zIndex: 109,
    }))
  }, 300)
  defer(() => {
    geometry.stopLines.forEach((path) => addPolyline(path, {
      strokeColor: '#ff4444',
      strokeWeight: 3,
      strokeOpacity: 0.98,
      zIndex: 112,
    }))
  }, 460)
  defer(() => {
    geometry.arrows.forEach((arrow, index) => {
      addOverlay(new AMapApi.Marker({
        position: arrow.position,
        anchor: 'center',
        content: htmlElement(
          'geo-lane-arrow',
          `<span style="--arrow-rotation:${arrow.rotation}deg;animation-delay:${index * 28}ms">${laneArrowSvg(arrow.movements)}</span>`,
        ),
        title: `${arrow.direction} · ${arrow.laneCode}`,
        zIndex: 120,
      }))
    })
  }, 620)
  defer(() => {
    geometry.roadLabels.forEach((label) => {
      addOverlay(new AMapApi.Marker({
        position: label.position,
        anchor: 'center',
        content: htmlElement(
          'geo-road-name',
          `<span style="transform:rotate(${label.rotation}deg)">${label.text}</span>`,
        ),
        title: `${label.direction} · ${label.text}`,
        zIndex: 128,
      }))
    })
  }, 760)
  if (['evidence', 'cause'].includes(props.beat)) {
    defer(() => {
      geometry.queueCars.forEach((car, index) => {
        addOverlay(new AMapApi.Marker({
          position: car.position,
          anchor: 'center',
          content: htmlElement(
            `geo-queue-car ${car.critical ? 'critical' : 'neutral'}`,
            `<span style="transform:rotate(${car.rotation}deg)"><i style="animation-delay:${Math.min(760, index * 22)}ms"></i><b></b></span>`,
          ),
          zIndex: 126,
        }))
      })
    }, 900)
  }
}

function addNarrativeMarker(
  position: [number, number],
  className: string,
  eyebrow: string,
  value: string,
  detail: string,
  options: { offsetX?: number; offsetY?: number; anchor?: string; zIndex?: number } = {},
) {
  return addOverlay(new AMapApi.Marker({
    position,
    anchor: options.anchor ?? 'bottom-center',
    offset: new AMapApi.Pixel(options.offsetX ?? 0, options.offsetY ?? -14),
    content: htmlElement(
      `geo-map-info-card geo-narrative-marker ${className}`,
      `<small>${eyebrow}</small><strong>${value}</strong><span>${detail}</span>`,
    ),
    zIndex: options.zIndex ?? 156,
  }))
}

function renderQueueRuler() {
  if (!target.value) return
  const center = target.value.center
  const stop = metersToGeo(center, -10.5, 31)
  const threshold = metersToGeo(center, -10.5, 145.8)
  const queueEnd = metersToGeo(center, -10.5, 160)

  addPolyline([stop, queueEnd], {
    strokeColor: '#e53935',
    strokeWeight: 8,
    strokeOpacity: 0.2,
    zIndex: 132,
  })
  addPolyline([stop, queueEnd], {
    strokeColor: '#ff5a57',
    strokeWeight: 3,
    strokeOpacity: 0.98,
    zIndex: 134,
  })
  addPolyline([
    metersToGeo(threshold, -16, 0),
    metersToGeo(threshold, 18, 0),
  ], {
    strokeColor: '#f5a623',
    strokeWeight: 4,
    strokeOpacity: 0.98,
    strokeStyle: 'dashed',
    strokeDasharray: [8, 5],
    zIndex: 138,
  })

  ;[
    { meters: 108, label: '周期 -2' },
    { meters: 118, label: '周期 -1' },
    { meters: 129, label: '当前' },
  ].forEach((item, index) => {
    const position = metersToGeo(stop, 0, item.meters)
    addPolyline([
      metersToGeo(position, -7 - index * 2, 0),
      metersToGeo(position, 7 + index * 2, 0),
    ], {
      strokeColor: index === 2 ? '#ff5a57' : '#ff9b82',
      strokeWeight: index === 2 ? 5 : 2,
      strokeOpacity: index === 2 ? 0.95 : 0.52,
      zIndex: 139,
    })
  })

  addOverlay(new AMapApi.Marker({
    position: metersToGeo(center, 36, 109),
    anchor: 'middle-left',
    content: htmlElement(
      'geo-queue-road-stats',
      `<span class="queue-road-stat current">
         <strong>129<small>m</small></strong>
         <em>当前排队</em>
       </span>
       <span class="queue-road-stat threshold">
         <strong>114.8<small>m</small></strong>
         <em>动态阈值</em>
       </span>`,
    ),
    zIndex: 160,
    title: '北进口当前排队 129m，动态阈值 114.8m',
  }))
}

function topologyPoints() {
  const points = new Map<string, Array<[number, number]>>()
  ;(topology.value?.features ?? [])
    .filter((feature: any) => feature.geometry.type === 'Point')
    .forEach((feature: any) => {
      const role = feature.properties?.role ?? 'context'
      const positions = points.get(role) ?? []
      positions.push(feature.geometry.coordinates)
      points.set(role, positions)
    })
  return points
}

function addActionLink(path: Array<[number, number]>, color: string, weight = 9) {
  addPolyline(path, {
    strokeColor: color,
    strokeWeight: weight + 8,
    strokeOpacity: 0.1,
    zIndex: 116,
  })
  addPolyline(path, {
    strokeColor: color,
    strokeWeight: weight,
    strokeOpacity: 0.9,
    showDir: true,
    zIndex: 118,
  })
}

function renderCauseMap() {
  const points = topologyPoints()
  const upstream = points.get('upstream') ?? []
  const targetPoint = points.get('target')?.[0]
  const downstream = points.get('downstream')?.[0]
  const branches = points.get('branch') ?? []
  if (upstream.length && targetPoint) {
    const ordered = [...upstream].sort((a, b) => b[1] - a[1])
    addActionLink([...ordered, targetPoint], '#f5a623', 8)
    ordered.forEach((position, index) => addNarrativeMarker(
      position,
      'warning compact',
      index === 0 ? '上游连续到达波' : '上游汇入',
      index === 0 ? '57.9%' : '34.8%',
      index === 0 ? '前两跳贡献' : '单点贡献',
      { offsetX: index % 2 ? 126 : -126, offsetY: -8 },
    ))
  }
  if (targetPoint) {
    addOverlay(new AMapApi.CircleMarker({
      center: targetPoint,
      radius: 33,
      strokeColor: '#e53935',
      strokeWeight: 5,
      strokeOpacity: 0.92,
      fillColor: '#e53935',
      fillOpacity: 0.14,
      zIndex: 142,
    }))
    addNarrativeMarker(
      targetPoint,
      'critical',
      '直接原因',
      '有效放行不足',
      '饱和度 0.89 · 绿灯利用率 54.2%',
      { offsetX: 132, offsetY: -20 },
    )
  }
  if (downstream) {
    addNarrativeMarker(
      downstream,
      'success',
      '排除下游阻塞',
      '占有率 42%',
      '仍有约 168m 储车空间',
      { offsetX: 132, offsetY: -8 },
    )
  }
  branches.forEach((position, index) => {
    if (index > 0) return
    addNarrativeMarker(
      position,
      'neutral compact',
      '垂直方向',
      '当前稳定',
      '排队 63m < 警戒 92m',
      { offsetX: -132, offsetY: -8 },
    )
  })
}

function renderConstraintMap() {
  const points = topologyPoints()
  const targetPoint = points.get('target')?.[0]
  const downstream = points.get('downstream')?.[0]
  const upstream = points.get('upstream')?.[0]
  const branch = points.get('branch')?.[0]
  if (targetPoint) addNarrativeMarker(targetPoint, 'critical boundary', '目标边界', '排队 ≤ 85m', '首轮只增加 4 秒', { offsetX: 132 })
  if (branch) addNarrativeMarker(branch, 'warning boundary', '垂直护栏', '警戒 92m', '超过即回退 2 秒', { offsetX: -132 })
  if (downstream) addNarrativeMarker(downstream, 'success boundary', '下游护栏', '占有率 < 65%', '超过即停止加放', { offsetX: 132 })
  if (upstream) addNarrativeMarker(upstream, 'neutral boundary', '上游护栏', '削峰 ≤ 12%', '排队超过 30m 即降级', { offsetX: 132 })
}

function renderStrategyMap(decided = false) {
  const points = topologyPoints()
  const upstream = points.get('upstream') ?? []
  const targetPoint = points.get('target')?.[0]
  const downstream = points.get('downstream')?.[0]
  const branch = points.get('branch')?.[0]
  const actionClass = decided ? 'success action' : 'action'

  if (upstream.length && targetPoint) {
    const ordered = [...upstream].sort((a, b) => b[1] - a[1])
    addActionLink([...ordered, targetPoint], '#f5a623', 7)
    addNarrativeMarker(
      ordered[0],
      actionClass,
      decided ? '已绑定执行' : '动作 01 · 上游',
      '削峰 12%',
      '打散连续到达波',
      { offsetX: 132 },
    )
  }
  if (targetPoint) {
    addOverlay(new AMapApi.CircleMarker({
      center: targetPoint,
      radius: 36,
      strokeColor: decided ? '#22c55e' : '#00d4f0',
      strokeWeight: 5,
      strokeOpacity: 0.95,
      fillColor: decided ? '#22c55e' : '#00d4f0',
      fillOpacity: 0.14,
      zIndex: 142,
    }))
    addNarrativeMarker(
      targetPoint,
      actionClass,
      decided ? '已绑定执行' : '动作 02 · 目标',
      '北进口 +4s',
      '不采用激进 +8s',
      { offsetX: 136, offsetY: -20 },
    )
  }
  if (targetPoint && downstream) {
    addActionLink([targetPoint, downstream], '#22c55e', 7)
    addNarrativeMarker(
      downstream,
      actionClass,
      decided ? '已绑定执行' : '动作 03 · 下游',
      '绿波协调',
      '承接新增放行',
      { offsetX: 132 },
    )
  }
  if (branch) {
    addNarrativeMarker(
      branch,
      'warning compact',
      '持续监测',
      '东西向 < 92m',
      '触线自动回退',
      { offsetX: -136 },
    )
  }
}

function renderSimulationMap() {
  const points = topologyPoints()
  const targetPoint = points.get('target')?.[0]
  const downstream = points.get('downstream')?.[0]
  const branch = points.get('branch')?.[0]
  const upstream = points.get('upstream')?.[0]
  if (!targetPoint || !downstream || !branch) return

  const targetMarker = addNarrativeMarker(targetPoint, 'critical scenario', '方案结果', '北进口 129m', '高风险', { offsetX: 132 })
  const branchMarker = addNarrativeMarker(branch, 'neutral scenario', '垂直方向', '东西向 63m', '安全', { offsetX: -132 })
  const downstreamMarker = addNarrativeMarker(downstream, 'success scenario', '下游承接', '占有率 42%', '安全', { offsetX: 132 })
  const createActionMarker = (position: [number, number], role: string) => addOverlay(new AMapApi.Marker({
    position,
    anchor: 'center',
    content: htmlElement(`geo-scenario-action scenario-baseline role-${role}`, '<i></i><i></i><i></i><i></i>'),
    zIndex: 146,
    title: '策略动作空间位置',
  }))
  const actionMarkers = {
    target: createActionMarker(targetPoint, 'target'),
    branch: createActionMarker(branch, 'branch'),
    downstream: createActionMarker(downstream, 'downstream'),
    upstream: upstream ? createActionMarker(upstream, 'upstream') : null,
  }
  const scenarios = [
    { id: 'baseline' as const, target: '129m', conflict: '63m', downstream: '42%', targetTone: 'critical', conflictTone: 'neutral', downstreamTone: 'success', risk: '高风险', conflictState: '安全' },
    { id: 'green-only' as const, target: '88m', conflict: '101m', downstream: '61%', targetTone: 'success', conflictTone: 'critical', downstreamTone: 'warning', risk: '目标缓解', conflictState: '突破 92m 警戒' },
    { id: 'combined' as const, target: '78m', conflict: '71m', downstream: '55%', targetTone: 'success', conflictTone: 'success', downstreamTone: 'success', risk: '安全', conflictState: '安全' },
  ]
  const applyScenario = (id: SimulationScenarioId) => {
    const scenario = scenarios.find((item) => item.id === id) ?? scenarios[0]
    simulationScenario.value = scenario.id
    Object.entries(actionMarkers).forEach(([role, marker]) => {
      marker?.setContent(htmlElement(
        `geo-scenario-action scenario-${scenario.id} role-${role}`,
        '<i></i><i></i><i></i><i></i>',
      ))
    })
    targetMarker.setContent(htmlElement(
      `geo-map-info-card geo-narrative-marker ${scenario.targetTone} scenario`,
      `<small>北进口结果</small><strong>${scenario.target}</strong><span>${scenario.risk}</span>`,
    ))
    branchMarker.setContent(htmlElement(
      `geo-map-info-card geo-narrative-marker ${scenario.conflictTone} scenario`,
      `<small>东西向结果</small><strong>${scenario.conflict}</strong><span>${scenario.conflictState}</span>`,
    ))
    downstreamMarker.setContent(htmlElement(
      `geo-map-info-card geo-narrative-marker ${scenario.downstreamTone} scenario`,
      `<small>下游结果</small><strong>${scenario.downstream}</strong><span>上限 65%</span>`,
    ))
  }
  simulationApplyScenario = applyScenario
  applyScenario('baseline')
  const first = window.setTimeout(() => applyScenario('green-only'), 2400)
  const second = window.setTimeout(() => applyScenario('combined'), 5000)
  deferredTimers.push(first, second)
}

function chooseSimulationScenario(id: SimulationScenarioId) {
  deferredTimers.splice(0).forEach((timer) => window.clearTimeout(timer))
  simulationScenario.value = id
  simulationApplyScenario?.(id)
}

function renderReportOutcome() {
  intersections.value.forEach((item) => {
    addOverlay(new AMapApi.Marker({
      position: item.position,
      anchor: 'center',
      content: htmlElement('geo-city-outcome-point', '<i></i>'),
      zIndex: 88,
      title: `${item.name} · 今日已纳入闭环监测`,
    }))
  })
  if (!target.value) return
  addOverlay(new AMapApi.CircleMarker({
    center: target.value.center,
    radius: 42,
    strokeColor: '#22c55e',
    strokeWeight: 5,
    strokeOpacity: 0.96,
    fillColor: '#22c55e',
    fillOpacity: 0.18,
    zIndex: 140,
  }))
  addNarrativeMarker(
    target.value.center,
    'success city-result',
    '本次治理已完成',
    '129m → 78m',
    '东西向 71m · 下游 55% · 均在安全边界内',
    { offsetX: 118, offsetY: -16, zIndex: 160 },
  )
}

function renderTopology() {
  const features = topology.value?.features ?? []
  features.filter((feature: any) => feature.geometry.type === 'LineString').forEach((feature: any) => {
    const isAnalysisAxis = feature.properties?.name?.includes('奥体西路')
    const isConflictAxis = feature.properties?.name?.includes('解放东路')
    addPolyline(feature.geometry.coordinates, {
      strokeColor: isAnalysisAxis ? '#f5a623' : isConflictAxis ? '#1a7fff' : '#6e8997',
      strokeWeight: feature.properties?.axis === 'primary' ? 7 : 3,
      strokeOpacity: feature.properties?.axis === 'primary' ? 0.8 : 0.42,
      showDir: true,
      zIndex: 82,
    })
  })
  features.filter((feature: any) => feature.geometry.type === 'Point').forEach((feature: any) => {
    const role = feature.properties?.role ?? 'context'
    const roleMeta: Record<string, string> = {
      upstream: '上游来车',
      target: '分析目标',
      downstream: '下游承接',
      branch: '垂直冲突方向',
    }
    const meta = roleMeta[role] ?? feature.properties?.meta ?? ''
    addOverlay(new AMapApi.Marker({
      position: feature.geometry.coordinates,
      anchor: 'center',
      content: htmlElement(
        `geo-topology-node ${role}`,
        `<i></i><span class="geo-map-info-card"><strong>${feature.properties?.name ?? ''}</strong><small>${meta}</small></span>`,
      ),
      zIndex: 105,
    }))
  })
}

function traceEdgeWeight(coverage: number | null | undefined) {
  const value = Math.max(0, Math.min(100, Number(coverage) || 0))
  return 2.8 + Math.sqrt(value / 100) * 5.7
}

function sampleGeoPath(path: Array<[number, number]>, phase: number): [number, number] {
  if (path.length <= 1) return path[0] ?? runtimeConfig.map.target
  const lengths: number[] = []
  let total = 0
  for (let index = 0; index < path.length - 1; index += 1) {
    const a = path[index]
    const b = path[index + 1]
    const length = Math.hypot((b[0] - a[0]) * 0.8, b[1] - a[1])
    lengths.push(length)
    total += length
  }
  let distance = Math.max(0, Math.min(1, phase)) * total
  for (let index = 0; index < lengths.length; index += 1) {
    if (distance <= lengths[index]) {
      const ratio = lengths[index] > 0 ? distance / lengths[index] : 0
      return [
        path[index][0] + (path[index + 1][0] - path[index][0]) * ratio,
        path[index][1] + (path[index + 1][1] - path[index][1]) * ratio,
      ]
    }
    distance -= lengths[index]
  }
  return path[path.length - 1]
}

function addDualTraceLine(
  path: Array<[number, number]>,
  palette: { glow: string; core: string },
  weight: number,
  options: { arrows?: boolean; muted?: boolean; zIndex?: number } = {},
) {
  const zIndex = options.zIndex ?? 112
  addPolyline(path, {
    strokeColor: palette.glow,
    strokeWeight: Math.max(6, weight * 2.15),
    strokeOpacity: options.muted ? 0.13 : 0.22,
    zIndex,
  })
  addPolyline(path, {
    strokeColor: palette.core,
    strokeWeight: Math.max(2.5, weight),
    strokeOpacity: options.muted ? 0.62 : 0.94,
    showDir: options.arrows === true,
    zIndex: zIndex + 1,
  })
}

function addTraceParticles(path: Array<[number, number]>, hop: number) {
  const arrowCount = 5
  Array.from({ length: arrowCount }, (_, index) => (index + 0.5) / arrowCount)
    .forEach((phase, index) => {
      const marker = addOverlay(new AMapApi.Marker({
        position: sampleGeoPath(path, phase),
        anchor: 'center',
        content: htmlElement(
          'geo-trace-particle',
          `<i style="animation-delay:${index * 110}ms">›</i>`,
        ),
        zIndex: 136,
      }))
      flowParticles.push({
        marker,
        path,
        phase,
        speed: 0.105 + hop * 0.004,
      })
    })
}

function stripIntersectionSuffix(name: string) {
  return name.replace(/(?:交叉口|路口)$/u, '').trim()
}

function renderFlowTrace() {
  const scene = flowTrace.value
  if (!scene) return
  const minimumCoverage = 10
  const nodeMap = new Map(scene.nodes.map((node) => [node.id, node]))
  const mainIds = new Set([scene.targetId, ...scene.mainCorridorChain.map((item) => item.nodeId)])
  const visibleNodes = scene.nodes.filter((node) =>
    mainIds.has(node.id)
    || (node.coverage != null && node.coverage >= minimumCoverage),
  )
  const visibleIds = new Set(visibleNodes.map((node) => node.id))

  const contextPalette = { glow: '#64748b', core: '#94a3b8' }
  const branchPalette = { glow: '#3b82f6', core: '#93c5fd' }
  const mainPalette = { glow: '#f5a623', core: '#ffcf7a' }

  scene.links
    .filter((link) => link.role === 'context' && visibleIds.has(link.from) && visibleIds.has(link.to))
    .forEach((link) => addDualTraceLine(link.path, contextPalette, 2.8, { muted: true, zIndex: 76 }))

  // 对齐参考实现：旁支仅使用真实 link.path，冷色弱化且不显示方向箭头。
  scene.links
    .filter((link) => link.role === 'branch' && visibleIds.has(link.from) && visibleIds.has(link.to))
    .forEach((link) => {
      const branchNode = nodeMap.get(link.from)
      addDualTraceLine(
        link.path,
        branchPalette,
        traceEdgeWeight(branchNode?.coverage) * 0.72,
        { muted: true, zIndex: 88 },
      )
    })

  visibleNodes.forEach((node) => {
    const nodeRole = node.role === 'target' ? 'target' : mainIds.has(node.id) ? 'main' : 'branch'
    addOverlay(new AMapApi.Marker({
      position: node.position,
      anchor: 'center',
      content: htmlElement(`geo-trace-node ${nodeRole}`, '<i></i>'),
      zIndex: node.role === 'target' ? 132 : mainIds.has(node.id) ? 112 : 96,
      title: node.name,
    }))

    if (node.role === 'target') {
      addOverlay(new AMapApi.Marker({
        position: node.position,
        anchor: 'bottom-center',
        offset: new AMapApi.Pixel(0, -18),
        content: htmlElement(
          'geo-map-info-card geo-trace-label target',
          `<strong>${stripIntersectionSuffix(node.name)}</strong><span>目标 · 100%</span>`,
        ),
        zIndex: 145,
      }))
    }
  })

  const ordered = [...scene.mainCorridorChain].sort((a, b) => a.hop - b.hop)
  let downstreamNode = nodeMap.get(scene.targetId)
  ordered.forEach((item, index) => {
    const upstreamNode = nodeMap.get(item.nodeId)
    if (!upstreamNode || !downstreamNode) return
    const path: Array<[number, number]> = [upstreamNode.position, downstreamNode.position]
    defer(() => {
      addDualTraceLine(path, mainPalette, traceEdgeWeight(item.sharePct), { arrows: true, zIndex: 116 })
      addTraceParticles(path, item.hop)
      const placeLeft = item.hop % 2 === 0
      addOverlay(new AMapApi.Marker({
        position: upstreamNode.position,
        anchor: 'bottom-center',
        offset: new AMapApi.Pixel(placeLeft ? -72 : 72, -22),
        content: htmlElement(
          'geo-map-info-card geo-trace-label main',
          `<strong>${stripIntersectionSuffix(upstreamNode.name)}</strong><span>主走廊 · 第 ${item.hop} 跳 · ${item.sharePct.toFixed(1)}%</span>`,
        ),
        zIndex: 140,
      }))
    }, 240 + index * 330)
    downstreamNode = upstreamNode
  })

  animationTimers.push(window.setInterval(() => {
    flowParticles.forEach((particle) => {
      particle.phase = (particle.phase + particle.speed * 0.04) % 1
      particle.marker.setPosition(sampleGeoPath(particle.path, particle.phase))
    })
  }, 40))
}

function applyCamera() {
  if (!map) return
  const targetCenter = runtimeConfig.map.target
  const overviewCenter = runtimeConfig.map.center
  const shots: Record<string, { zoom: number; center: [number, number] }> = {
    scan: { zoom: runtimeConfig.map.overviewZoom, center: overviewCenter },
    issue: { zoom: 16.5, center: targetCenter },
    pending: { zoom: 16.5, center: targetCenter },
    cognition: { zoom: 17.75, center: [targetCenter[0], targetCenter[1] + 0.00028] },
    direction: { zoom: 16.3, center: [117.1113, 36.6642] },
    evidence: { zoom: 18.1, center: [targetCenter[0], targetCenter[1] + 0.00048] },
    cause: { zoom: 16.3, center: [117.1113, 36.6647] },
    constraints: { zoom: 16.3, center: [117.1113, 36.6647] },
    options: { zoom: 16.3, center: [117.1113, 36.6647] },
    simulation: { zoom: 16.3, center: [117.1113, 36.6647] },
    decision: { zoom: 16.3, center: [117.1113, 36.6647] },
    trace: { zoom: 14.45, center: [117.1112, 36.6717] },
    'knowledge-recall': { zoom: 17.6, center: targetCenter },
    'similar-cases': { zoom: 17.6, center: targetCenter },
    'tidal-pattern': { zoom: 17.6, center: targetCenter },
    'strategy-brief': { zoom: 17.6, center: targetCenter },
    'plan-generation': { zoom: 16.5, center: targetCenter },
    'plan-options': { zoom: 16.3, center: [117.1113, 36.6647] },
    'impact-preview': { zoom: 16.3, center: [117.1113, 36.6647] },
    deployment: { zoom: 16.5, center: targetCenter },
    'deployment-confirm': { zoom: 16.5, center: targetCenter },
    'before-after': { zoom: 16.5, center: targetCenter },
    'peak-verification': { zoom: 16.3, center: [117.1113, 36.6647] },
    closing: { zoom: 14.9, center: overviewCenter },
    report: { zoom: 14.9, center: overviewCenter },
  }
  const shot = shots[props.beat] ?? shots.scan
  map.setZoomAndCenter(shot.zoom, shot.center, true, 900)
}

const topologyBeats = new Set(['direction', 'cause', 'constraints', 'options', 'simulation', 'decision'])

function renderTopologyStage() {
  overlayScope = 'stage'
  if (props.beat === 'cause') renderCauseMap()
  if (props.beat === 'constraints') renderConstraintMap()
  if (props.beat === 'options') renderStrategyMap()
  if (props.beat === 'simulation') renderSimulationMap()
  if (props.beat === 'decision') renderStrategyMap(true)
  overlayScope = 'base'
}

function resolveSceneKind() {
  if (props.activeAct === 1) return `act1-${props.beat}`
  if (props.activeAct === 6) return 'report'
  if (topologyBeats.has(props.beat)) return 'topology'
  return `act2-${props.beat}`
}

function renderScene() {
  if (!mapReady.value || !AMapApi) return
  const nextSceneKind = resolveSceneKind()
  const preserveTopology = nextSceneKind === 'topology' && renderedSceneKind === 'topology'
  if (preserveTopology) {
    clearStageScene()
    renderTopologyStage()
    return
  }

  clearScene()
  map.setMapStyle?.(runtimeConfig.amap.style)
  applyCamera()
  renderedSceneKind = nextSceneKind
  overlayScope = 'base'
  if (props.activeAct === 1) {
    renderAct1()
    return
  }
  if (props.activeAct === 6) {
    renderReportOutcome()
    return
  }
  if (props.beat === 'cognition') {
    renderChannelization()
    renderDevices()
    renderStaticPortrait()
  } else if (props.beat === 'evidence') {
    renderChannelization()
    renderQueueRuler()
  } else if (topologyBeats.has(props.beat)) {
    renderTopology()
    renderTopologyStage()
  } else if (props.beat === 'trace') {
    renderFlowTrace()
  } else if (['plan-options', 'impact-preview', 'peak-verification'].includes(props.beat)) {
    renderTopology()
  } else if (props.beat === 'knowledge-recall') {
    addTargetAnchor('相似案例匹配')
  } else if (props.beat === 'similar-cases') {
    addTargetAnchor('案例匹配完成')
  } else if (props.beat === 'tidal-pattern') {
    addTargetAnchor('潮汐特征研判')
  } else if (props.beat === 'strategy-brief') {
    addTargetAnchor('治理方向已确定')
  } else if (['plan-generation', 'deployment'].includes(props.beat)) {
    addTargetAnchor('配时方案锁定路口')
  } else if (['deployment-confirm', 'before-after', 'closing'].includes(props.beat)) {
    addTargetAnchor('执行效果追踪中')
  } else {
    addTargetAnchor('目标已锁定')
  }
}

async function loadMap() {
  if (!runtimeConfig.amap.key || !mapHost.value) {
    mapFailed.value = true
    return
  }
  if (runtimeConfig.amap.securityCode) {
    ;(window as any)._AMapSecurityConfig = { securityJsCode: runtimeConfig.amap.securityCode }
  }
  try {
    AMapApi = await AMapLoader.load({
      key: runtimeConfig.amap.key,
      version: runtimeConfig.amap.version,
      plugins: [],
    })
    map = new AMapApi.Map(mapHost.value, {
      center: runtimeConfig.map.center,
      zoom: runtimeConfig.map.overviewZoom,
      viewMode: runtimeConfig.amap.viewMode,
      mapStyle: runtimeConfig.amap.style,
      showLabel: true,
      dragEnable: true,
      zoomEnable: true,
      doubleClickZoom: true,
      keyboardEnable: true,
      zooms: [13, 20],
    })
    mapReady.value = true
    renderScene()
  } catch (error) {
    console.error('[CityMap] 高德地图加载失败。', error)
    mapFailed.value = true
  }
}

watch([() => props.activeAct, () => props.beat], renderScene)

onMounted(async () => {
  const [
    intersectionData,
    deviceData,
    targetData,
    channelData,
    topologyData,
    traceData,
    diagnosisData,
  ] = await Promise.all([
    dataRepository.intersections(),
    dataRepository.devices(),
    dataRepository.targetIntersection(),
    dataRepository.channelization(),
    dataRepository.topology(),
    dataRepository.flowTrace(),
    dataRepository.expertDiagnosis(),
  ])
  intersections.value = intersectionData
  devices.value = deviceData
  target.value = targetData
  channelization.value = channelData
  topology.value = topologyData
  flowTrace.value = traceData
  diagnosis.value = diagnosisData
  await nextTick()
  await loadMap()
})

onBeforeUnmount(() => {
  retirementFrames.forEach((frame) => window.cancelAnimationFrame(frame))
  retirementFrames.clear()
  clearScene(true)
  map?.destroy?.()
  map = null
  AMapApi = null
})
</script>

<template>
  <div class="city-map" :class="[`beat-${beat}`, { 'map-live': mapReady }]">
    <div ref="mapHost" class="amap-host"></div>
    <div v-if="mapFailed" class="map-load-failure">
      <strong>地图服务未连接</strong>
      <span>请检查 VITE_AMAP_KEY 与 VITE_AMAP_SECURITY_CODE</span>
    </div>
    <div class="map-vignette"></div>
    <transition name="portrait-row">
      <section
        v-if="activeAct === 2 && beat === 'direction' && operatingPortrait"
        class="operating-portrait-row"
        :aria-label="operatingPortrait.title"
      >
        <article
          v-for="(dimension, index) in operatingPortrait.dimensions"
          :key="dimension.id"
          :class="['geo-map-info-card', 'geo-operating-portrait', dimension.tone]"
          :style="{ animationDelay: `${index * 90}ms` }"
        >
          <header>
            <div>
              <strong>{{ dimension.title }}</strong>
              <small>{{ dimension.subtitle }}</small>
            </div>
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
          </header>
          <div class="operating-portrait-metrics">
            <span
              v-for="metric in dimension.metrics"
              :key="metric.label"
              :class="metric.tone"
            >
              <small>{{ metric.label }}</small>
              <strong>{{ metric.value }}</strong>
            </span>
          </div>
          <div class="operating-portrait-level">
            <i :style="{ width: `${Math.max(0, Math.min(100, dimension.levelPct))}%` }"></i>
          </div>
          <footer>{{ dimension.summary }}</footer>
        </article>
      </section>
    </transition>
    <transition name="map-verdict">
      <section
        v-if="mapNarrative"
        :key="`${activeAct}-${beat}`"
        :class="['map-executive-verdict', mapNarrative.tone]"
        aria-live="polite"
      >
        <div class="verdict-chapter">
          <span>{{ mapNarrative.chapter }}</span>
          <small>{{ mapNarrative.eyebrow }}</small>
        </div>
        <div class="verdict-copy">
          <strong>{{ mapNarrative.headline }}</strong>
          <p>{{ mapNarrative.summary }}</p>
          <small v-if="nextNarrative" class="verdict-next">{{ nextNarrative }}</small>
        </div>
        <div class="verdict-metrics">
          <div v-for="metric in mapNarrative.metrics" :key="metric.label" :class="metric.status">
            <span>{{ metric.label }}</span>
            <b>{{ metric.value }}</b>
          </div>
        </div>
        <div class="verdict-flow">
          <span :style="{ width: `${narrativeProgress}%` }"></span>
        </div>
      </section>
    </transition>

    <transition name="strategy-drawer">
      <aside
        v-if="activeAct === 2 && beat === 'simulation'"
        :class="['strategy-comparison-drawer', activeStrategyCard.tone]"
      >
        <header>
          <div>
            <small>COUNTERFACTUAL SIMULATION</small>
            <strong>如果这样调，路网会发生什么？</strong>
          </div>
          <b>{{ activeStrategyCard.index }} / 03</b>
        </header>

        <nav aria-label="三种策略推演">
          <button
            v-for="item in strategyComparisonCards"
            :key="item.id"
            :class="[item.tone, { active: item.id === simulationScenario }]"
            @click="chooseSimulationScenario(item.id)"
          >
            <span>{{ item.index }}</span>
            <strong>{{ item.name }}</strong>
            <small>{{ item.status }}</small>
          </button>
        </nav>

        <div class="strategy-active-card">
          <div class="strategy-card-heading">
            <span>{{ activeStrategyCard.name }}</span>
            <b>{{ activeStrategyCard.status }}</b>
          </div>
          <h3>{{ activeStrategyCard.action }}</h3>
          <div
            :class="['strategy-action-visual', `scenario-${activeStrategyCard.id}`]"
            :aria-label="`${activeStrategyCard.name}动作示意`"
          >
            <div class="strategy-road vertical"></div>
            <div class="strategy-road horizontal"></div>
            <div class="strategy-flow">
              <i></i><i></i><i></i><i></i><i></i>
            </div>
            <span class="strategy-action-node upstream"><i></i><i></i></span>
            <span class="strategy-action-node target"><i></i><i></i><i></i></span>
            <span class="strategy-action-node branch"><i></i><i></i><i></i></span>
            <span class="strategy-action-node downstream"><i></i><i></i><i></i></span>
            <small class="label-upstream">上游削峰</small>
            <small class="label-target">目标放行</small>
            <small class="label-branch">东西向</small>
            <small class="label-downstream">下游绿波</small>
          </div>
          <div class="strategy-impact-grid">
            <span><small>北进口</small><strong>{{ activeStrategyCard.target }}</strong></span>
            <span><small>东西向</small><strong>{{ activeStrategyCard.conflict }}</strong></span>
            <span><small>下游占有率</small><strong>{{ activeStrategyCard.downstream }}</strong></span>
          </div>
          <p>{{ activeStrategyCard.verdict }}</p>
        </div>

        <footer>
          <i></i>
          地图上的三个结果点会随当前方案同步变化
        </footer>
      </aside>
    </transition>
  </div>
</template>
