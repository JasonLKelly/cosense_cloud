import { useState } from 'react'
import { Zone, Decision, Robot } from '../types'

interface MetricsPanelProps {
  zone: Zone | null
  robots: Robot[]
  decisions: Decision[]
  onToggleVisibility: (visibility: 'normal' | 'degraded' | 'poor') => void
  onToggleConnectivity: (connectivity: 'normal' | 'degraded' | 'offline') => void
  onDecisionsExpandedChange: (expanded: boolean) => void
  onRobotClick: (robot: Robot) => void
  onRobotHover: (robotId: string | null) => void
}

export function MetricsPanel({
  zone,
  robots,
  decisions,
  onToggleVisibility,
  onToggleConnectivity,
  onDecisionsExpandedChange,
  onRobotClick,
  onRobotHover,
}: MetricsPanelProps) {
  const [decisionsExpanded, setDecisionsExpanded] = useState(true)
  const [robotsExpanded, setRobotsExpanded] = useState(true)

  const handleDecisionsToggle = () => {
    const newExpanded = !decisionsExpanded
    setDecisionsExpanded(newExpanded)
    onDecisionsExpandedChange(newExpanded)
  }

  const getRobotStateClass = (robot: Robot): string => {
    const action = robot.commanded_action?.toLowerCase() || 'continue'
    return action
  }

  return (
    <div className="right-drawer">
      {/* Zone Stats */}
      <div className="drawer-section">
        <h4 className="drawer-title">Zone Stats</h4>
        {zone ? (
          <div className="zone-stats">
            <div className="zone-stat">
              <div className="zone-stat-value">{zone.robot_count}</div>
              <div className="zone-stat-label">Robots</div>
            </div>
            <div className="zone-stat">
              <div className="zone-stat-value">{zone.human_count}</div>
              <div className="zone-stat-label">Humans</div>
            </div>
            <div className="zone-stat">
              <div className="zone-stat-value">
                {(zone.congestion_level * 100).toFixed(0)}%
              </div>
              <div className="zone-stat-label">Congestion</div>
            </div>
            <div className="zone-stat">
              <div className="zone-stat-value">{zone.zone_id}</div>
              <div className="zone-stat-label">Zone</div>
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
            value={zone?.visibility || 'normal'}
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
            value={zone?.connectivity || 'normal'}
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
    </div>
  )
}
