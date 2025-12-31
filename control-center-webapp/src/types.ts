// CoSense Control Center Types

export interface Robot {
  robot_id: string
  x: number
  y: number
  velocity: number
  heading: number
  motion_state: 'moving' | 'stopped' | 'slowing'
  commanded_action: 'CONTINUE' | 'SLOW' | 'STOP' | 'REROUTE'
  destination?: string
  manual_override?: boolean
}

export interface Human {
  human_id: string
  x: number
  y: number
  velocity: number
}

export interface SimState {
  sim_time: number
  running: boolean
  map_id: string
  width: number
  height: number
  visibility: 'normal' | 'degraded' | 'poor'
  connectivity: 'normal' | 'degraded' | 'offline'
  congestion_level: number
  robot_count: number
  human_count: number
  robots: Robot[]
  humans: Human[]
}

export interface Decision {
  decision_id: string
  robot_id: string
  action: 'CONTINUE' | 'SLOW' | 'STOP'
  reason_codes: string[]
  risk_score: number
  summary: string
  timestamp: number
}

export interface AnomalyAlert {
  alert_id?: string  // May not be present from Flink
  alert_type: 'DECISION_RATE_SPIKE' | 'REPEATED_ROBOT_STOP' | 'SENSOR_DISAGREEMENT_SPIKE'
  detected_at: number | string  // Can be epoch ms or ISO string
  robot_id: string | null
  metric_name: string
  actual_value: number
  forecast_value: number
  lower_bound: number
  upper_bound: number
  severity: 'HIGH' | 'MEDIUM'
  context: string
  ai_explanation: string
}

export interface ToolCallLog {
  tool: string
  params: Record<string, unknown>
  success: boolean
}

export interface GeminiResponse {
  summary: string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT'
  evidence: Array<{
    signal: string
    value: string
    relevance: string
  }>
  tool_calls: ToolCallLog[]
  error?: string
}

// Map types
export interface MapObstacle {
  id: string
  type: 'floor' | 'rack' | 'conveyor' | 'workstation' | 'dock' | 'wall' | 'charging'
  x: number
  y: number
  width: number
  height: number
  label?: string
  color?: string
  direction?: 'north' | 'south' | 'east' | 'west'
}

export interface MapWaypoint {
  id: string
  name: string
  x: number
  y: number
}

export interface WarehouseMap {
  id: string
  name: string
  version: string
  width: number
  height: number
  grid_resolution: number
  obstacles: MapObstacle[]
  waypoints: MapWaypoint[]
}

// Pipeline Activity Types
export type ActivityType = 'tool_call' | 'decision' | 'anomaly' | 'anomaly_raw'

export interface ActivityEvent {
  type: ActivityType
  timestamp_ms: number
  data: ToolCallActivityData | DecisionActivityData | AnomalyActivityData
}

export interface ToolCallActivityData {
  tool_name: string
  params: Record<string, unknown>
  question_id?: string
}

export interface DecisionActivityData {
  robot_id: string
  action: string
  reason_codes: string[]
  risk_score: number
}

export interface AnomalyActivityData {
  alert_type: string
  severity: string
  robot_id: string | null
  actual_value: number
  forecast_value: number
  deviation_percent: number
  ai_explanation?: string  // Only present for enriched anomalies
}

// API URL from environment
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

// Confluent UI URL - local Control Center or Confluent Cloud
export const CONFLUENT_URL = import.meta.env.VITE_CONFLUENT_URL || 'http://localhost:9021'

// Poll interval in ms (default 500ms for Cloud Run, 250ms for local)
export const POLL_INTERVAL = Number(import.meta.env.VITE_POLL_INTERVAL) || 500
