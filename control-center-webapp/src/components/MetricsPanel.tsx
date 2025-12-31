import { useState } from 'react'
import { SimState, Decision, Robot, AnomalyAlert } from '../types'

interface MetricsPanelProps {
  simState: SimState | null
  robots: Robot[]
  decisions: Decision[]
  anomalies: AnomalyAlert[]
  onToggleVisibility: (visibility: 'normal' | 'degraded' | 'poor') => void
  onToggleConnectivity: (connectivity: 'normal' | 'degraded' | 'offline') => void
  onDecisionsExpandedChange: (expanded: boolean) => void
  onAnomaliesExpandedChange: (expanded: boolean) => void
  onRobotClick: (robot: Robot) => void
  onRobotHover: (robotId: string | null) => void
  onExplainAlert?: (alert: AnomalyAlert) => void
  onDismissAlert?: (alertId: string) => void
  onClearAllAlerts?: () => void
}

export function MetricsPanel({
  simState,
  robots,
  decisions,
  anomalies,
  onToggleVisibility,
  onToggleConnectivity,
  onDecisionsExpandedChange,
  onAnomaliesExpandedChange,
  onRobotClick,
  onRobotHover,
  onExplainAlert,
  onDismissAlert,
  onClearAllAlerts,
}: MetricsPanelProps) {
  const [decisionsExpanded, setDecisionsExpanded] = useState(true)
  const [robotsExpanded, setRobotsExpanded] = useState(true)
  const [anomaliesExpanded, setAnomaliesExpanded] = useState(true)

  const handleDecisionsToggle = () => {
    const newExpanded = !decisionsExpanded
    setDecisionsExpanded(newExpanded)
    onDecisionsExpandedChange(newExpanded)
  }

  const handleAnomaliesToggle = () => {
    const newExpanded = !anomaliesExpanded
    setAnomaliesExpanded(newExpanded)
    onAnomaliesExpandedChange(newExpanded)
  }

  const formatAlertType = (type: string): string => {
    switch (type) {
      case 'DECISION_RATE_SPIKE':
        return 'Rate Spike'
      case 'REPEATED_ROBOT_STOP':
        return 'Repeated Stop'
      case 'SENSOR_DISAGREEMENT_SPIKE':
        return 'Sensor Issue'
      default:
        return type
    }
  }

  const parseTimestamp = (ts: number | string): number => {
    if (typeof ts === 'number') return ts
    return new Date(ts).getTime()
  }

  const formatAlertTime = (timestamp: number | string): string => {
    const date = new Date(typeof timestamp === 'number' ? timestamp : timestamp)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  // Sort anomalies by detected_at (newest first) and limit to 20
  const sortedAnomalies = [...anomalies]
    .sort((a, b) => parseTimestamp(b.detected_at) - parseTimestamp(a.detected_at))
    .slice(0, 20)

  const getRobotStateClass = (robot: Robot): string => {
    if (robot.motion_state === 'yielding') return 'yielding'
    const action = robot.commanded_action?.toLowerCase() || 'continue'
    return action
  }

  return (
    <div className="right-drawer">
      {/* Stats */}
      <div className="drawer-section">
        <h4 className="drawer-title">Stats</h4>
        {simState ? (
          <div className="zone-stats">
            <div className="zone-stat">
              <div className="zone-stat-value">{simState.robot_count}</div>
              <div className="zone-stat-label">Robots</div>
            </div>
            <div className="zone-stat">
              <div className="zone-stat-value">{simState.human_count}</div>
              <div className="zone-stat-label">Humans</div>
            </div>
            <div className="zone-stat">
              <div className="zone-stat-value">
                {(simState.congestion_level * 100).toFixed(0)}%
              </div>
              <div className="zone-stat-label">Congestion</div>
            </div>
          </div>
        ) : (
          <div className="text-muted">No data</div>
        )}
      </div>

      {/* Scenario Toggles */}
      <div className="drawer-section">
        <h4 className="drawer-title">Scenario</h4>
        <div className="toggle-row">
          <span>Visibility</span>
          <select
            value={simState?.visibility || 'normal'}
            onChange={(e) =>
              onToggleVisibility(e.target.value as 'normal' | 'degraded' | 'poor')
            }
            style={{
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              padding: '4px 8px',
            }}
          >
            <option value="normal">Normal</option>
            <option value="degraded">Degraded</option>
            <option value="poor">Poor</option>
          </select>
        </div>
        <div className="toggle-row">
          <span>Connectivity</span>
          <select
            value={simState?.connectivity || 'normal'}
            onChange={(e) =>
              onToggleConnectivity(e.target.value as 'normal' | 'degraded' | 'offline')
            }
            style={{
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              padding: '4px 8px',
            }}
          >
            <option value="normal">Normal</option>
            <option value="degraded">Degraded</option>
            <option value="offline">Offline</option>
          </select>
        </div>
      </div>

      {/* Robots Grid */}
      <div className="drawer-section">
        <h4
          className="drawer-title collapsible"
          onClick={() => setRobotsExpanded(!robotsExpanded)}
        >
          <span>Robots</span>
          <span className="collapse-icon">{robotsExpanded ? '▼' : '▶'}</span>
        </h4>
        {robotsExpanded && (
          <>
          <div className="robot-legend">
            <span className="legend-item"><span className="legend-dot continue"></span>OK</span>
            <span className="legend-item"><span className="legend-dot slow"></span>Slow</span>
            <span className="legend-item"><span className="legend-dot stop"></span>Stop</span>
            <span className="legend-item"><span className="legend-dot yielding"></span>Yield</span>
            <span className="legend-item"><span className="legend-dot reroute"></span>Reroute</span>
          </div>
          <div className="robot-grid">
            {robots.map((robot) => (
              <div
                key={robot.robot_id}
                className={`robot-grid-item ${getRobotStateClass(robot)}`}
                onClick={() => onRobotClick(robot)}
                onMouseEnter={() => onRobotHover(robot.robot_id)}
                onMouseLeave={() => onRobotHover(null)}
                title={`${robot.robot_id} - ${robot.commanded_action || 'CONTINUE'}`}
              >
                <span className="robot-grid-id">
                  {robot.robot_id.replace('robot-', '')}
                </span>
              </div>
            ))}
            {robots.length === 0 && (
              <div className="text-muted text-small">No robots</div>
            )}
          </div>
          </>
        )}
      </div>

      {/* AI Alerts - Flink-detected anomalies */}
      <div className="drawer-section">
        <div className="drawer-title-row">
          <h4
            className="drawer-title collapsible"
            onClick={handleAnomaliesToggle}
          >
            <span>AI Alerts</span>
            {anomalies.length > 0 && (
              <span className="alert-count">{anomalies.length}</span>
            )}
            <span className="collapse-icon">{anomaliesExpanded ? '▼' : '▶'}</span>
          </h4>
          {anomalies.length > 0 && onClearAllAlerts && (
            <button
              className="btn-clear-all"
              onClick={(e) => {
                e.stopPropagation()
                onClearAllAlerts()
              }}
              title="Clear all alerts"
            >
              Clear All
            </button>
          )}
        </div>
        {anomaliesExpanded && (
          <div className="alert-list">
            {sortedAnomalies.length === 0 && (
              <div className="system-normal">
                <span className="system-normal-icon">✓</span>
                <span className="system-normal-text">System Normal</span>
              </div>
            )}
            {sortedAnomalies.map((a, idx) => {
              const alertKey = a.alert_id || `${a.alert_type}-${a.detected_at}-${a.robot_id || idx}`
              return (
              <div
                key={alertKey}
                className={`alert-item alert-${a.severity.toLowerCase()}`}
              >
                <div className="alert-item-header">
                  <span className={`alert-severity ${a.severity.toLowerCase()}`}>
                    {a.severity}
                  </span>
                  <span className="alert-type">{formatAlertType(a.alert_type)}</span>
                  <span className="alert-time">{formatAlertTime(a.detected_at)}</span>
                  {onDismissAlert && a.alert_id && (
                    <button
                      className="btn-dismiss"
                      onClick={(e) => {
                        e.stopPropagation()
                        onDismissAlert(a.alert_id!)
                      }}
                      title="Dismiss alert"
                    >
                      &times;
                    </button>
                  )}
                </div>
                {a.robot_id && (
                  <div className="alert-robot">{a.robot_id}</div>
                )}
                <div className="alert-context">{a.context}</div>
                {onExplainAlert && (
                  <button
                    className="btn-explain"
                    onClick={() => onExplainAlert(a)}
                  >
                    <svg className="gemini-icon" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z"/>
                    </svg>
                    Explain with Gemini
                  </button>
                )}
              </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
