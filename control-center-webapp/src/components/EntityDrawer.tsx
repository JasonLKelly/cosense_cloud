import { Robot } from '../types'

interface EntityDrawerProps {
  robot: Robot | null
  onClose: () => void
  onStop: (robotId: string) => void
  onStart: (robotId: string) => void
}

export function EntityDrawer({ robot, onClose, onStop, onStart }: EntityDrawerProps) {
  return (
    <div className={`entity-drawer ${robot ? 'open' : ''}`}>
      {robot && (
        <>
          <div className="entity-drawer-header">
            <h3 className="entity-drawer-title">{robot.robot_id}</h3>
            <button className="entity-drawer-close" onClick={onClose}>×</button>
          </div>

          <div className="entity-info">
            <div className="entity-info-row">
              <span className="entity-info-label">Position</span>
              <span className="entity-info-value">({robot.x.toFixed(1)}, {robot.y.toFixed(1)})</span>
            </div>
            <div className="entity-info-row">
              <span className="entity-info-label">Velocity</span>
              <span className="entity-info-value">{robot.velocity.toFixed(2)} m/s</span>
            </div>
            <div className="entity-info-row">
              <span className="entity-info-label">Heading</span>
              <span className="entity-info-value">{robot.heading.toFixed(0)}°</span>
            </div>
            <div className="entity-info-row">
              <span className="entity-info-label">Motion State</span>
              <span className="entity-info-value">{robot.motion_state}</span>
            </div>
            <div className="entity-info-row">
              <span className="entity-info-label">Command</span>
              <span className="entity-info-value">
                {robot.commanded_action}
                {robot.manual_override && ' (Manual)'}
              </span>
            </div>
            <div className="entity-info-row">
              <span className="entity-info-label">Destination</span>
              <span className="entity-info-value">{robot.destination || 'None'}</span>
            </div>
          </div>

          <div className="entity-actions">
            {robot.manual_override ? (
              <button
                className="btn btn-primary"
                onClick={() => onStart(robot.robot_id)}
              >
                Release Manual Stop
              </button>
            ) : robot.motion_state === 'yielding' ? (
              <button className="btn btn-secondary" disabled>
                Yielding to Other Robot
              </button>
            ) : robot.motion_state !== 'stopped' ? (
              <button
                className="btn btn-danger"
                onClick={() => onStop(robot.robot_id)}
              >
                Stop Robot
              </button>
            ) : (
              <button
                className="btn btn-primary"
                onClick={() => onStart(robot.robot_id)}
              >
                Start Robot
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
