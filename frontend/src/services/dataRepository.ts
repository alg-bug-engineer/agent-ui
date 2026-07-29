import type {
  ChannelizationScene,
  DailySummary,
  DetectedIssue,
  DevicePoint,
  ExpertDiagnosis,
  FlowTraceScene,
  HumanCollaboration,
  MetricItem,
  MonitoredIntersection,
  MonitoringArea,
  TargetIntersection,
} from '../types'
import { runtimeConfig } from '../config/runtime'

async function getJson<T>(path: string): Promise<T> {
  const url = `${runtimeConfig.data.baseUrl}/${path.replace(/^\/+/, '')}`
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`数据加载失败：${url} (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const dataRepository = {
  monitoringArea: () => getJson<MonitoringArea>('act1/monitoring-area.json'),
  intersections: () => getJson<MonitoredIntersection[]>('act1/intersections.json'),
  detectedIssue: () => getJson<DetectedIssue>('act1/detected-issue.json'),
  targetIntersection: () => getJson<TargetIntersection>('act2/target-intersection.json'),
  devices: () => getJson<DevicePoint[]>('act2/devices.json'),
  metrics: () => getJson<MetricItem[]>('act2/metrics.json'),
  channelization: () => getJson<ChannelizationScene>('act2/channelization-real.json'),
  topology: () => getJson<Record<string, unknown>>('act2/topology.geojson'),
  flowTrace: () => getJson<FlowTraceScene>('act2/flow-trace.json'),
  expertDiagnosis: () => getJson<ExpertDiagnosis>('act2/expert-diagnosis.json'),
  dailySummary: () => getJson<DailySummary>('act6/daily-summary.json'),
  humanCollaboration: () =>
    getJson<HumanCollaboration>('act6/human-collaboration.json'),
  effectiveness: () => getJson<Record<string, unknown>>('act6/effectiveness.json'),
  experiences: () => getJson<Record<string, unknown>>('act6/experiences.json'),
}
