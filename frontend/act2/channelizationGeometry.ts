import type {
  ChannelizationLink,
  ChannelizationScene,
} from '../src/types'

export type GeoPoint = [number, number]

export interface ChannelizationArm {
  key: 'north' | 'east' | 'south' | 'west'
  angle: number
  roadName: string
  entrance?: ChannelizationLink
  exit?: ChannelizationLink
}

export interface LaneArrowGeometry {
  position: GeoPoint
  rotation: number
  movements: Array<'left' | 'straight' | 'right'>
  laneCode: string
  direction: string
}

export interface ChannelizationGeometry {
  arms: ChannelizationArm[]
  roadPolygons: GeoPoint[][]
  curbs: GeoPoint[][]
  dividers: GeoPoint[][]
  laneLines: GeoPoint[][]
  stopLines: GeoPoint[][]
  cornerLines: GeoPoint[][]
  arrows: LaneArrowGeometry[]
  roadLabels: Array<{ position: GeoPoint; rotation: number; text: string; direction: string }>
  queueCars: Array<{ position: GeoPoint; rotation: number; critical: boolean }>
}

const LANE_WIDTH_M = 3.45
const ARM_LENGTH_M = 154
const MIN_BOX_RADIUS_M = 22

function angleDiff(a: number, b: number) {
  const delta = Math.abs(((a - b) % 360 + 360) % 360)
  return delta > 180 ? 360 - delta : delta
}

function cardinalFromAngle(angle: number): ChannelizationArm['key'] {
  const value = ((angle % 360) + 360) % 360
  if (value >= 315 || value < 45) return 'north'
  if (value < 135) return 'east'
  if (value < 225) return 'south'
  return 'west'
}

function metersToGeo(center: GeoPoint, eastM: number, northM: number): GeoPoint {
  const latRadians = center[1] * Math.PI / 180
  return [
    center[0] + eastM / (111_320 * Math.cos(latRadians)),
    center[1] + northM / 110_540,
  ]
}

/**
 * 局部坐标约定严格对齐 agent-loop：
 * forward 为沿路臂向路口外，lateral > 0 为俯视路臂右侧。
 * 进口道位于右侧，出口道位于左侧。
 */
function armPoint(center: GeoPoint, angle: number, lateralM: number, forwardM: number): GeoPoint {
  const radians = angle * Math.PI / 180
  // 与参考层 armToWorld 完全一致：
  // worldX = forward*sin(angle) - lateral*cos(angle)
  // geoNorth = lateral*sin(angle) + forward*cos(angle)
  const eastM = Math.sin(radians) * forwardM - Math.cos(radians) * lateralM
  const northM = Math.cos(radians) * forwardM + Math.sin(radians) * lateralM
  return metersToGeo(center, eastM, northM)
}

function laneMovements(code: string): LaneArrowGeometry['movements'] {
  let normalized = String(code || 'C').toUpperCase()
  if (normalized.includes('Z') && !normalized.includes('C')) {
    normalized = normalized.replace(/Z/g, 'C')
  }
  normalized = normalized.replace(/[FGLRTO]/g, '')
  const movements: LaneArrowGeometry['movements'] = []
  if (normalized.includes('A') || normalized.includes('B')) movements.push('left')
  if (normalized.includes('C')) movements.push('straight')
  if (normalized.includes('D') || normalized.includes('E')) movements.push('right')
  return movements.length ? movements : ['straight']
}

function gatherArms(links: ChannelizationLink[]): ChannelizationArm[] {
  const arms: ChannelizationArm[] = []
  links.forEach((link) => {
    let arm = arms.find((candidate) => angleDiff(candidate.angle, link.approachAngle) < 22)
    if (!arm) {
      arm = {
        key: cardinalFromAngle(link.approachAngle),
        angle: link.approachAngle,
        roadName: link.roadName,
      }
      arms.push(arm)
    }
    if (link.role === 'entrance') {
      arm.entrance = link
      arm.angle = link.approachAngle
    } else {
      arm.exit = link
    }
    if (!arm.roadName) arm.roadName = link.roadName
  })
  return arms.sort((a, b) => a.angle - b.angle)
}

function boxRadius(arms: ChannelizationArm[]) {
  if (arms.length < 2) return MIN_BOX_RADIUS_M
  let radius = MIN_BOX_RADIUS_M
  for (let index = 0; index < arms.length; index += 1) {
    const current = arms[index]
    const next = arms[(index + 1) % arms.length]
    const delta = ((next.angle - current.angle) + 360) % 360
    const currentHalfWidth = (
      (current.entrance?.laneCount ?? 0) + (current.exit?.laneCount ?? 0)
    ) * LANE_WIDTH_M / 2
    const nextHalfWidth = (
      (next.entrance?.laneCount ?? 0) + (next.exit?.laneCount ?? 0)
    ) * LANE_WIDTH_M / 2
    const sine = Math.sin(delta * Math.PI / 360)
    if (sine > 0.01) radius = Math.max(radius, (currentHalfWidth + nextHalfWidth) / sine * 0.55)
  }
  return Math.min(42, radius)
}

function cornerCurve(
  center: GeoPoint,
  fromArm: ChannelizationArm,
  toArm: ChannelizationArm,
  radius: number,
): GeoPoint[] {
  const fromExit = fromArm.exit?.laneCount ?? 0
  const toEntrance = toArm.entrance?.laneCount ?? 0
  const start = armPoint(center, fromArm.angle, -fromExit * LANE_WIDTH_M, radius)
  const end = armPoint(center, toArm.angle, toEntrance * LANE_WIDTH_M, radius)
  const points: GeoPoint[] = []
  for (let index = 0; index <= 18; index += 1) {
    const t = index / 18
    const inverse = 1 - t
    points.push([
      inverse * inverse * start[0] + 2 * inverse * t * center[0] + t * t * end[0],
      inverse * inverse * start[1] + 2 * inverse * t * center[1] + t * t * end[1],
    ])
  }
  return points
}

export function buildChannelizationGeometry(scene: ChannelizationScene): ChannelizationGeometry {
  const center = scene.intersection.center
  const arms = gatherArms(scene.links)
  const radius = boxRadius(arms)
  const output: ChannelizationGeometry = {
    arms,
    roadPolygons: [],
    curbs: [],
    dividers: [],
    laneLines: [],
    stopLines: [],
    cornerLines: [],
    arrows: [],
    roadLabels: [],
    queueCars: [],
  }

  arms.forEach((arm) => {
    const entranceCount = arm.entrance?.laneCount ?? 0
    const exitCount = arm.exit?.laneCount ?? 0
    const entranceWidth = entranceCount * LANE_WIDTH_M
    const exitWidth = exitCount * LANE_WIDTH_M
    const outer = radius + ARM_LENGTH_M

    output.roadPolygons.push([
      armPoint(center, arm.angle, -exitWidth, radius),
      armPoint(center, arm.angle, entranceWidth, radius),
      armPoint(center, arm.angle, entranceWidth, outer),
      armPoint(center, arm.angle, -exitWidth, outer),
    ])
    if (entranceCount) {
      output.curbs.push([
        armPoint(center, arm.angle, entranceWidth, radius),
        armPoint(center, arm.angle, entranceWidth, outer),
      ])
    }
    if (exitCount) {
      output.curbs.push([
        armPoint(center, arm.angle, -exitWidth, radius),
        armPoint(center, arm.angle, -exitWidth, outer),
      ])
    }
    if (entranceCount && exitCount) {
      output.dividers.push([
        armPoint(center, arm.angle, 0, radius),
        armPoint(center, arm.angle, 0, outer),
      ])
    }
    for (let lane = 1; lane < entranceCount; lane += 1) {
      output.laneLines.push([
        armPoint(center, arm.angle, lane * LANE_WIDTH_M, radius),
        armPoint(center, arm.angle, lane * LANE_WIDTH_M, outer),
      ])
    }
    for (let lane = 1; lane < exitCount; lane += 1) {
      output.laneLines.push([
        armPoint(center, arm.angle, -lane * LANE_WIDTH_M, radius),
        armPoint(center, arm.angle, -lane * LANE_WIDTH_M, outer),
      ])
    }
    if (entranceCount) {
      ;[radius, radius + 1.5].forEach((forward) => {
        output.stopLines.push([
          armPoint(center, arm.angle, 0, forward),
          armPoint(center, arm.angle, entranceWidth, forward),
        ])
      })
      const laneCodes = arm.entrance?.laneInfo ?? Array(entranceCount).fill('C')
      laneCodes.forEach((code, lane) => {
        output.arrows.push({
          position: armPoint(center, arm.angle, (lane + 0.5) * LANE_WIDTH_M, radius + 23),
          rotation: (arm.angle + 180) % 360,
          movements: laneMovements(code),
          laneCode: code,
          direction: arm.entrance?.direction ?? '',
        })
      })
    }
    output.roadLabels.push({
      position: armPoint(center, arm.angle, (entranceWidth - exitWidth) / 2, radius + 112),
      rotation: arm.key === 'north' || arm.key === 'south' ? -90 : 0,
      text: arm.roadName,
      direction: arm.entrance?.direction ?? arm.exit?.direction ?? '',
    })
  })

  arms.forEach((arm, index) => {
    output.cornerLines.push(cornerCurve(center, arm, arms[(index + 1) % arms.length], radius))
  })

  // 北进口是当前真实异常进口。排队长度 129m，参考层按 queueM / 8 估算车辆，
  // 且只在进口侧生成车辆，出口保持通畅。
  arms.forEach((arm) => {
    if (!arm.entrance) return
    const critical = arm.key === 'north'
    const baseCars = critical ? Math.round(129 / 8) : 3
    const codes = arm.entrance.laneInfo
    codes.forEach((code, lane) => {
      const movements = laneMovements(code)
      const ratio = movements.length > 1 ? 0.65 : movements.includes('straight') ? 1 : 0.4
      const count = critical ? Math.max(2, Math.round(baseCars * ratio)) : Math.max(1, baseCars - lane)
      for (let car = 0; car < count; car += 1) {
        const distance = radius + 6 + car * 7.4 + (lane % 2) * 1.6
        if (distance > radius + ARM_LENGTH_M * 0.94) break
        output.queueCars.push({
          position: armPoint(center, arm.angle, (lane + 0.5) * LANE_WIDTH_M, distance),
          rotation: (arm.angle + 180) % 360,
          critical,
        })
      }
    })
  })

  return output
}
