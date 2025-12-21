// CoSense Control Center Types

export interface Robot {
  robot_id: string
  zone_id: string
  x: number
  y: number
  velocity: number
  heading: number
  motion_state: 'moving' | 'stopped' | 'slowing'
  commanded_action: 'CONTINUE' | 'SLOW' | 'STOP' | 'REROUTE'
  destination?: string
}

export interface Human {
  human_id: string
  zone_id: string
  x: number
  y: number
  velocity: number
}

export interface Zone {
  zone_id: string
  width: number
  height: number
  visibility: 'normal' | 'degraded' | 'poor'
  connectivity: 'normal' | 'degraded' | 'offline'
  congestion_level: number
  robot_count: number
  human_count: number
}

export interface SimState {
  sim_time: number
  running: boolean
  zone: Zone
  robots: Robot[]
  humans: Human[]
}

export interface Decision {
  decision_id: string
  robot_id: string
  zone_id: string
  action: 'CONTINUE' | 'SLOW' | 'STOP' | 'REROUTE'
  reason_codes: string[]
  risk_score: number
  summary: string
  timestamp: number
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
export interface MapZone {
  id: string
  name: string
  x: number
  y: number
  width: number
  height: number
  color: string
}

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
  zone_id?: string
}

export interface WarehouseMap {
  id: string
  name: string
  version: string
  width: number
  height: number
  grid_resolution: number
  zones: MapZone[]
  obstacles: MapObstacle[]
  waypoints: MapWaypoint[]
  robot_spawn_zone?: string
  human_spawn_zones: string[]
}

// API URL from environment
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'
