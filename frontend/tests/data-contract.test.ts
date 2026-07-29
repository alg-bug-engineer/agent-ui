import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { buildChannelizationGeometry } from '../act2/channelizationGeometry'
import type { ChannelizationScene } from '../src/types'

function fixture<T>(path: string): T {
  return JSON.parse(
    readFileSync(resolve(process.cwd(), 'public/data', path), 'utf8'),
  ) as T
}

describe('运行数据契约', () => {
  it('Act 1 的扫描和自动处理时长均为 10 秒', () => {
    const area = fixture<{
      autoDetectionSeconds: number
      autoProcessSeconds: number
    }>('act1/monitoring-area.json')

    expect(area.autoDetectionSeconds).toBe(10)
    expect(area.autoProcessSeconds).toBe(10)
  })

  it('Act 2 使用补充需求指定的目标路口', () => {
    const target = fixture<{ name: string; center: number[] }>(
      'act2/target-intersection.json',
    )

    expect(target.name).toContain('奥体西路')
    expect(target.name).toContain('解放东路')
    expect(target.center).toHaveLength(2)
  })

  it('Act 2 指标包含被强调的排队长度动态阈值', () => {
    const metrics = fixture<Array<{
      id: string
      threshold?: number
      emphasis?: boolean
    }>>('act2/metrics.json')
    const queue = metrics.find((item) => item.id === 'queue')

    expect(queue?.emphasis).toBe(true)
    expect(queue?.threshold).toBeGreaterThan(0)
  })

  it('Act 2 所有设备均使用地理坐标，而不是屏幕百分比', () => {
    const devices = fixture<Array<{ position: number[]; screen?: number[] }>>(
      'act2/devices.json',
    )

    expect(devices.length).toBeGreaterThan(8)
    devices.forEach((device) => {
      expect(device.position).toHaveLength(2)
      expect(device.screen).toBeUndefined()
    })
  })

  it('Act 2 流量溯源包含六跳主走廊和汇入支路', () => {
    const trace = fixture<{
      nodes: unknown[]
      links: Array<{ role: string }>
      mainCorridorChain: Array<{ hop: number; cumulativePct: number }>
    }>('act2/flow-trace.json')

    expect(trace.nodes.length).toBeGreaterThanOrEqual(12)
    expect(trace.links.filter((item) => item.role === 'branch').length).toBeGreaterThanOrEqual(5)
    expect(trace.mainCorridorChain.map((item) => item.hop)).toEqual([1, 2, 3, 4, 5, 6])
    expect(trace.mainCorridorChain.at(-1)?.cumulativePct).toBeGreaterThan(90)
  })

  it('Act 2 专家诊断同时校验目标、垂直、下游和上游方向', () => {
    const diagnosis = fixture<{
      staticPortrait: {
        radiusM: number
        items: Array<{ id: string; positionOffsetM: number[] }>
      }
      operatingPortrait: {
        dimensions: Array<{ id: string; metrics: unknown[] }>
      }
      directions: Array<{ id: string }>
      hypotheses: Array<{ id: string; supported: boolean }>
      options: Array<{ id: string; recommended: boolean }>
      scenarios: Array<{ id: string; risk: string }>
    }>('act2/expert-diagnosis.json')

    expect(diagnosis.directions.map((item) => item.id))
      .toEqual(['target', 'conflict', 'downstream', 'upstream'])
    expect(diagnosis.staticPortrait.radiusM).toBe(600)
    expect(diagnosis.staticPortrait.items).toHaveLength(6)
    expect(diagnosis.staticPortrait.items.every((item) => item.positionOffsetM.length === 2))
      .toBe(true)
    expect(diagnosis.operatingPortrait.dimensions.map((item) => item.id))
      .toEqual(['supply', 'demand', 'status'])
    expect(diagnosis.operatingPortrait.dimensions.every((item) => item.metrics.length >= 3))
      .toBe(true)
    expect(diagnosis.hypotheses.find((item) => item.id === 'downstream-block')?.supported)
      .toBe(false)
    expect(diagnosis.options.find((item) => item.id === 'green-only')?.recommended)
      .toBe(false)
    expect(diagnosis.options.find((item) => item.id === 'combined')?.recommended)
      .toBe(true)
    expect(diagnosis.scenarios.find((item) => item.id === 'combined')?.risk)
      .toBe('低')
  })

  it('Act 2 渠化数据来自真实路网快照并完整区分进出口', () => {
    const channelization = fixture<{
      source: { kind: string; versionId: string }
      links: Array<{
        role: string
        direction: string
        laneCount: number
        laneInfo: string[]
      }>
    }>('act2/channelization-real.json')
    const entrances = channelization.links.filter((link) => link.role === 'entrance')
    const exits = channelization.links.filter((link) => link.role === 'exit')

    expect(channelization.source).toMatchObject({
      kind: 'postgres-snapshot',
      versionId: '20260501',
    })
    expect(entrances).toHaveLength(4)
    expect(exits).toHaveLength(4)
    expect(entrances.reduce((sum, link) => sum + link.laneCount, 0)).toBe(16)
    expect(exits.reduce((sum, link) => sum + link.laneCount, 0)).toBe(16)
    expect(entrances.find((link) => link.direction === '北进口')?.laneInfo)
      .toEqual(['B', 'C', 'C', 'DF'])
  })

  it('Act 2 仅在真实进口侧生成停止线和方向箭头', () => {
    const channelization = fixture<ChannelizationScene>(
      'act2/channelization-real.json',
    )
    const geometry = buildChannelizationGeometry(channelization)
    const center = channelization.intersection.center
    const arrows = (direction: string) =>
      geometry.arrows.filter((arrow) => arrow.direction === direction)

    expect(geometry.arrows).toHaveLength(16)
    expect(geometry.stopLines).toHaveLength(8)
    expect(arrows('北进口').every((arrow) => arrow.position[0] < center[0])).toBe(true)
    expect(arrows('东进口').every((arrow) => arrow.position[1] > center[1])).toBe(true)
    expect(arrows('南进口').every((arrow) => arrow.position[0] > center[0])).toBe(true)
    expect(arrows('西进口').every((arrow) => arrow.position[1] < center[1])).toBe(true)
  })

  it('Act 6 同时包含自动动作与人机协同动作', () => {
    const summary = fixture<{ actions: Array<{ name: string }> }>(
      'act6/daily-summary.json',
    )
    const collaboration = fixture<{
      timeline: unknown[]
      pending: unknown[]
      templates: Array<Record<string, string>>
    }>(
      'act6/human-collaboration.json',
    )

    expect(summary.actions.some((item) => item.name === '自动执行')).toBe(true)
    expect(collaboration.timeline.length).toBeGreaterThan(0)
    expect(collaboration.pending.length).toBeGreaterThan(0)
    expect(collaboration.templates[0]).toMatchObject({
      scene: expect.any(String),
      diagnosis: expect.any(String),
      strategy: expect.any(String),
      regulation: expect.any(String),
    })
  })
})
