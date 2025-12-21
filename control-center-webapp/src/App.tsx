import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

interface Robot {
  robot_id: string
  x: number
  y: number
  velocity: number
  heading: number
  motion_state: string
  commanded_action?: string
}

interface Human {
  human_id: string
  x: number
  y: number
  velocity: number
}

interface SimState {
  sim_time: number
  running: boolean
  zone: {
    zone_id: string
    width: number
    height: number
    visibility: string
    connectivity: string
    congestion_level: number
  }
  robots: Robot[]
  humans: Human[]
}

interface Decision {
  decision_id: string
  robot_id: string
  action: string
  reason_codes: string[]
  summary: string
  timestamp: number
}

export default function App() {
  const [state, setState] = useState<SimState | null>(null)
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [error, setError] = useState<string | null>(null)

  const fetchState = async () => {
    try {
      const res = await fetch(`${API_URL}/simulator/state`)
      if (res.ok) {
        setState(await res.json())
        setError(null)
      }
    } catch (e) {
      setError('Cannot connect to API')
    }
  }

  const fetchDecisions = async () => {
    try {
      const res = await fetch(`${API_URL}/decisions?limit=10`)
      if (res.ok) {
        setDecisions(await res.json())
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    fetchState()
    fetchDecisions()
    const interval = setInterval(() => {
      fetchState()
      fetchDecisions()
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const startSim = () => fetch(`${API_URL}/scenario/start`, { method: 'POST' })
  const stopSim = () => fetch(`${API_URL}/scenario/stop`, { method: 'POST' })
  const resetSim = () => fetch(`${API_URL}/scenario/reset`, { method: 'POST' })

  const scale = 10 // pixels per meter

  return (
    <div style={{ padding: 20 }}>
      <h1 style={{ marginBottom: 20 }}>CoSense Control Center</h1>

      {error && <div style={{ color: '#f66', marginBottom: 10 }}>{error}</div>}

      <div style={{ marginBottom: 20 }}>
        <button onClick={startSim} style={btnStyle}>Start</button>
        <button onClick={stopSim} style={btnStyle}>Stop</button>
        <button onClick={resetSim} style={btnStyle}>Reset</button>
        {state && (
          <span style={{ marginLeft: 20 }}>
            {state.running ? '🟢 Running' : '⚪ Stopped'} |
            Time: {state.sim_time.toFixed(1)}s |
            Robots: {state.robots.length} |
            Humans: {state.humans.length}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 20 }}>
        {/* Map */}
        <div style={{
          position: 'relative',
          width: (state?.zone.width || 50) * scale,
          height: (state?.zone.height || 30) * scale,
          background: '#2a2a4a',
          border: '2px solid #444',
          borderRadius: 8,
        }}>
          {state?.robots.map(robot => (
            <div
              key={robot.robot_id}
              style={{
                position: 'absolute',
                left: robot.x * scale - 8,
                top: robot.y * scale - 8,
                width: 16,
                height: 16,
                background: robot.commanded_action === 'STOP' ? '#f44' :
                           robot.commanded_action === 'SLOW' ? '#fa0' : '#4f4',
                borderRadius: '50%',
                border: '2px solid #fff',
                transform: `rotate(${robot.heading}deg)`,
              }}
              title={`${robot.robot_id}: ${robot.motion_state} (${robot.commanded_action || 'CONTINUE'})`}
            >
              <div style={{
                position: 'absolute',
                top: -20,
                left: -10,
                fontSize: 10,
                whiteSpace: 'nowrap',
                color: '#aaa',
              }}>
                {robot.robot_id}
              </div>
            </div>
          ))}
          {state?.humans.map(human => (
            <div
              key={human.human_id}
              style={{
                position: 'absolute',
                left: human.x * scale - 6,
                top: human.y * scale - 6,
                width: 12,
                height: 12,
                background: '#66f',
                borderRadius: '50%',
              }}
              title={human.human_id}
            />
          ))}
        </div>

        {/* Decisions */}
        <div style={{ flex: 1, maxWidth: 400 }}>
          <h3>Recent Decisions</h3>
          <div style={{ fontSize: 12, maxHeight: 300, overflow: 'auto' }}>
            {decisions.length === 0 && <div style={{ color: '#666' }}>No decisions yet</div>}
            {decisions.slice().reverse().map(d => (
              <div key={d.decision_id} style={{
                padding: 8,
                marginBottom: 4,
                background: '#2a2a4a',
                borderRadius: 4,
                borderLeft: `3px solid ${d.action === 'STOP' ? '#f44' : d.action === 'SLOW' ? '#fa0' : '#4f4'}`,
              }}>
                <div><strong>{d.robot_id}</strong>: {d.action}</div>
                <div style={{ color: '#888' }}>{d.summary}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Zone Info */}
      {state && (
        <div style={{ marginTop: 20, fontSize: 12, color: '#888' }}>
          Zone: {state.zone.zone_id} |
          Visibility: {state.zone.visibility} |
          Connectivity: {state.zone.connectivity} |
          Congestion: {(state.zone.congestion_level * 100).toFixed(0)}%
        </div>
      )}
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  marginRight: 8,
  background: '#4a4a6a',
  border: 'none',
  borderRadius: 4,
  color: '#fff',
  cursor: 'pointer',
}
