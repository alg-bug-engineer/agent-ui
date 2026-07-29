export type ActId = 1 | 2 | 6

export interface MonitoringArea {
  name: string
  center: [number, number]
  zoom: number
  autoDetectionSeconds: number
  autoProcessSeconds: number
}

export interface MonitoredIntersection {
  id: string
  name: string
  position: [number, number]
  screen: [number, number]
  status: 'normal' | 'attention'
}

export interface DetectedIssue {
  id: string
  intersectionId: string
  intersectionName: string
  title: string
  description: string
  severity: string
  triggerMetric: string
  detectedAt: string
}

export interface TargetIntersection {
  id: string
  name: string
  center: [number, number]
  roadEastWest: string
  roadNorthSouth: string
  problemApproach: string
  problemMovement: string
}

export interface ChannelizationLink {
  linkId: string
  role: 'entrance' | 'exit'
  approachAngle: number
  direction: string
  roadName: string
  laneCount: number
  laneInfo: string[]
  laneIds: string[]
  path: Array<[number, number]>
}

export interface ChannelizationScene {
  source: {
    kind: 'postgres-snapshot'
    schema: string
    versionId: string
    capturedAt: string
  }
  intersection: {
    id: string
    name: string
    center: [number, number]
  }
  links: ChannelizationLink[]
}

export interface DevicePoint {
  id: string
  name: string
  type: 'electricPolice' | 'geomagnetic' | 'checkpoint' | 'signal'
  status: 'online' | 'offline'
  position: [number, number]
  lane: string
}

export interface FlowTraceNode {
  id: string
  name: string
  position: [number, number]
  role: 'target' | 'upstream' | 'branch' | 'downstream'
  corridor: string
  hop: number | null
  coverage: number | null
}

export interface FlowTraceLink {
  id: string
  from: string
  to: string
  path: Array<[number, number]>
  role: 'main' | 'branch' | 'context'
  hop: number | null
  sharePct: number
  correlation: number
}

export interface FlowTraceScene {
  available: boolean
  traceDirection: 'upstream' | 'downstream'
  targetId: string
  nodes: FlowTraceNode[]
  links: FlowTraceLink[]
  mainCorridorChain: Array<{
    nodeId: string
    hop: number
    sharePct: number
    cumulativePct: number
  }>
  summary: {
    dominantSource: string
    coveredSharePct: number
    conclusion: string
  }
}

export interface MetricItem {
  id: string
  label: string
  value: number
  unit: string
  status: 'normal' | 'warning' | 'critical'
  trend: string
  threshold?: number
  emphasis?: boolean
}

export interface DiagnosticDirection {
  id: 'target' | 'conflict' | 'downstream' | 'upstream'
  label: string
  role: string
  primaryMetric: string
  secondaryMetric: string
  assessment: string
  tone: 'critical' | 'warning' | 'normal'
}

export interface DiagnosticHypothesis {
  id: string
  question: string
  evidence: string
  verdict: string
  supported: boolean
}

export interface StrategyOption {
  id: string
  name: string
  action: string
  targetEffect: string
  conflictEffect: string
  downstreamEffect: string
  verdict: string
  recommended: boolean
}

export interface ScenarioProjection {
  id: string
  name: string
  targetQueueM: number
  conflictQueueM: number
  downstreamOccupancyPct: number
  risk: '高' | '中' | '低'
  conclusion: string
}

export interface ExpertDiagnosis {
  source: {
    roadNetwork: string
    operationalEvidence: string
    strategyProjection: string
  }
  question: string
  directions: DiagnosticDirection[]
  hypotheses: DiagnosticHypothesis[]
  constraints: Array<{
    label: string
    value: string
    boundary: string
    conclusion: string
    tone: 'critical' | 'warning' | 'normal'
  }>
  options: StrategyOption[]
  scenarios: ScenarioProjection[]
  recommendation: {
    title: string
    actions: string[]
    rationale: string
    guardrails: string[]
    expectedOutcome: string
  }
}

export interface DailySummary {
  reportDate: string
  scope: string
  headline: string
  narrative: string
  kpis: Array<{ label: string; value: string; delta: string; tone: string }>
  actions: Array<{ name: string; value: number; color: string }>
}

export interface HumanCollaboration {
  overview: Array<{ label: string; value: number; tone: string }>
  timeline: Array<{
    time: string
    actor: string
    action: string
    target: string
    detail: string
    status: string
  }>
  pending: Array<{
    id: string
    level: 'intersection' | 'corridor' | 'region' | 'emergency'
    target: string
    strategy: string
    risk: string
    expiresAt: string
    parameters: Array<{ name: string; before: string; suggested: string }>
  }>
  templates: Array<{
    id: string
    name: string
    scene: string
    diagnosis: string
    strategy: string
    regulation: string
  }>
}
