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

  const getRobotStateClass = (robot: Robot): string => {
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

      {/* Recent Decisions */}
      <div className="drawer-section">
        <h4
          className="drawer-title collapsible"
          onClick={handleDecisionsToggle}
        >
          <span>Recent Decisions</span>
          <span className="collapse-icon">{decisionsExpanded ? '▼' : '▶'}</span>
        </h4>
        {decisionsExpanded && (
          <div className="decision-list">
            {decisions.length === 0 && (
              <div className="text-muted text-small">No decisions yet</div>
            )}
            {decisions.map((d) => (
              <div
                key={d.decision_id}
                className={`decision-item ${d.action.toLowerCase()}`}
              >
                <div className="decision-item-header">
                  <span className="decision-item-robot">{d.robot_id}</span>
                  <span className="decision-item-action">{d.action}</span>
                </div>
                <div className="decision-item-summary">{d.summary}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Alerts - Flink-detected anomalies */}
      <div className="drawer-section">
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
        {anomaliesExpanded && (
          <div className="alert-list">
            {anomalies.length === 0 && (
              <div className="text-muted text-small">No alerts - system normal</div>
            )}
            {anomalies.slice().reverse().map((a) => (
              <div
                key={a.alert_id}
                className={`alert-item alert-${a.severity.toLowerCase()}`}
              >
                <div className="alert-item-header">
                  <span className={`alert-severity ${a.severity.toLowerCase()}`}>
                    {a.severity}
                  </span>
                  <span className="alert-type">{formatAlertType(a.alert_type)}</span>
                </div>
                {a.robot_id && (
                  <div className="alert-robot">{a.robot_id}</div>
                )}
                <div className="alert-context">{a.context}</div>
                <div className="alert-explanation">{a.ai_explanation}</div>
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
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
