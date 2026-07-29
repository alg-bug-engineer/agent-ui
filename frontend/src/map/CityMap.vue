<script setup lang="ts">
import AMapLoader from '@amap/amap-jsapi-loader'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { runtimeConfig } from '../config/runtime'
import { dataRepository } from '../services/dataRepository'
import { buildChannelizationGeometry } from '../../act2/channelizationGeometry'
import type {
  ActId,
  ChannelizationScene,
  DevicePoint,
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

let AMapApi: any = null
let map: any = null
let overlays: any[] = []
let scanTimer = 0
let renderGeneration = 0
const deferredTimers: number[] = []
const animationTimers: number[] = []
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
  overlays.push(overlay)
  map?.add?.(overlay)
  return overlay
}

function clearScene() {
  renderGeneration += 1
  window.clearInterval(scanTimer)
  scanTimer = 0
  deferredTimers.splice(0).forEach((timer) => window.clearTimeout(timer))
  animationTimers.splice(0).forEach((timer) => window.clearInterval(timer))
  flowParticles = []
  if (map && overlays.length) map.remove(overlays)
  overlays = []
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
      'geo-anchor-label',
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
        `<i></i><span><strong>${device.name}</strong><small>${device.lane} · ${device.status === 'online' ? '在线' : '离线'}</small></span>`,
      ),
      zIndex: 120,
      title: `${device.name} · ${device.lane}`,
    }))
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
    const stageMeta: Record<string, Record<string, string>> = {
      direction: {
        upstream: '上游来车 · 前两跳贡献 57.9%',
        target: '分析方向 · 北进口排队 129m',
        downstream: '下游承接 · 占有率 42%',
        branch: '垂直方向 · 东西向排队 63m',
      },
      cause: {
        upstream: '连续到达波 · 放大因素',
        target: '有效放行不足 · 直接原因',
        downstream: '仍有空间 · 排除下游阻塞',
        branch: '冲突方向当前稳定',
      },
      constraints: {
        upstream: '截流上限 12%',
        target: '目标排队 ≤ 85m',
        downstream: '占有率必须 < 65%',
        branch: '东西向排队必须 < 92m',
      },
      options: {
        upstream: '候选动作 · 上游削峰',
        target: '候选动作 · 适度加放',
        downstream: '候选动作 · 绿波协调',
        branch: '副作用检查 · 垂直等待',
      },
      simulation: {
        upstream: '组合方案 · 削峰 12%',
        target: '组合推演 · 129m → 78m',
        downstream: '组合推演 · 42% → 55%',
        branch: '组合推演 · 63m → 71m',
      },
      decision: {
        upstream: '执行 · 上游削峰 12%',
        target: '执行 · 北进口 +4s',
        downstream: '执行 · 下游绿波协调',
        branch: '护栏 · 东西向不超 92m',
      },
    }
    const meta = stageMeta[props.beat]?.[role] ?? feature.properties?.meta ?? ''
    addOverlay(new AMapApi.Marker({
      position: feature.geometry.coordinates,
      anchor: 'center',
      content: htmlElement(
        `geo-topology-node ${role}`,
        `<i></i><span><strong>${feature.properties?.name ?? ''}</strong><small>${meta}</small></span>`,
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
          'geo-trace-label target',
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
        offset: new AMapApi.Pixel(placeLeft ? -24 : 24, -18),
        content: htmlElement(
          'geo-trace-label main',
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
    cognition: { zoom: 18.65, center: [targetCenter[0], targetCenter[1] + 0.0002] },
    direction: { zoom: 16.3, center: [117.1113, 36.6647] },
    evidence: { zoom: 18.75, center: [targetCenter[0], targetCenter[1] + 0.00035] },
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

function renderScene() {
  if (!mapReady.value || !AMapApi) return
  clearScene()
  map.setMapStyle?.(props.beat === 'trace' ? 'amap://styles/dark' : runtimeConfig.amap.style)
  applyCamera()
  if (props.activeAct === 1) {
    renderAct1()
    return
  }
  if (props.activeAct === 6) return
  if (props.beat === 'cognition') {
    renderChannelization()
    renderDevices()
  } else if (props.beat === 'evidence') {
    renderChannelization()
  } else if (['direction', 'cause', 'constraints', 'options', 'simulation', 'decision'].includes(props.beat)) {
    renderTopology()
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
  const [intersectionData, deviceData, targetData, channelData, topologyData, traceData] = await Promise.all([
    dataRepository.intersections(),
    dataRepository.devices(),
    dataRepository.targetIntersection(),
    dataRepository.channelization(),
    dataRepository.topology(),
    dataRepository.flowTrace(),
  ])
  intersections.value = intersectionData
  devices.value = deviceData
  target.value = targetData
  channelization.value = channelData
  topology.value = topologyData
  flowTrace.value = traceData
  await nextTick()
  await loadMap()
})

onBeforeUnmount(() => {
  clearScene()
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
    <div class="map-coordinate-badge">
      <i></i>
      高德地图地理坐标图层 · 可拖拽缩放
    </div>
  </div>
</template>
