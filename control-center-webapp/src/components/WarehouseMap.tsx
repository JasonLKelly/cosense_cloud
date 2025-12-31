import { useRef, useState, useEffect } from 'react'
import { WarehouseMap, Robot, Human, MapObstacle } from '../types'

interface WarehouseMapProps {
  map: WarehouseMap | null
  robots: Robot[]
  humans: Human[]
  selectedRobotId: string | null
  hoveredRobotId: string | null
  onRobotClick: (robot: Robot) => void
}

// Default colors by obstacle type
const OBSTACLE_COLORS: Record<string, string> = {
  rack: '#8b7355',
  conveyor: '#5588aa',
  workstation: '#7c5a9b',
  dock: '#5a8b5a',
  wall: '#333344',
  charging: '#b8b832',
  floor: 'transparent',
}

// Robot colors by commanded action
const ROBOT_COLORS: Record<string, string> = {
  CONTINUE: '#4ade80',
  SLOW: '#facc15',
  STOP: '#f87171',
  REROUTE: '#a78bfa',
}

function ObstacleRect({ obstacle, scale }: { obstacle: MapObstacle; scale: number }) {
  const color = obstacle.color || OBSTACLE_COLORS[obstacle.type] || '#666'
  const isWall = obstacle.type === 'wall'

  return (
    <div
      className="obstacle"
      style={{
        position: 'absolute',
        left: obstacle.x * scale,
        top: obstacle.y * scale,
        width: obstacle.width * scale,
        height: obstacle.height * scale,
        background: color,
        borderRadius: isWall ? 0 : 2,
        opacity: obstacle.type === 'floor' ? 0 : 0.9,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 12,
        fontWeight: 600,
        color: '#fff',
        textShadow: '0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7)',
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
      title={`${obstacle.type}: ${obstacle.label || obstacle.id}`}
    >
      {obstacle.label && obstacle.width * scale > 30 && (
        <span style={{ opacity: 0.8 }}>{obstacle.label}</span>
      )}
    </div>
  )
}

function ConveyorRect({ obstacle, scale }: { obstacle: MapObstacle; scale: number }) {
  const color = obstacle.color || OBSTACLE_COLORS.conveyor
  const isVertical = obstacle.height > obstacle.width

  // Animated stripes for conveyor
  const stripeStyle = isVertical
    ? { backgroundSize: '100% 20px' }
    : { backgroundSize: '20px 100%' }

  return (
    <div
      className="conveyor"
      style={{
        position: 'absolute',
        left: obstacle.x * scale,
        top: obstacle.y * scale,
        width: obstacle.width * scale,
        height: obstacle.height * scale,
        background: `repeating-linear-gradient(
          ${isVertical ? '0deg' : '90deg'},
          ${color},
          ${color} 8px,
          ${color}dd 8px,
          ${color}dd 16px
        )`,
        borderRadius: 2,
        ...stripeStyle,
      }}
      title={`Conveyor: ${obstacle.label || obstacle.id}`}
    />
  )
}

export function WarehouseMapView({
  map,
  robots,
  humans,
  selectedRobotId,
  hoveredRobotId,
  onRobotClick,
}: WarehouseMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(10)

  // Calculate scale to fit container
  useEffect(() => {
    if (!map || !containerRef.current) return

    const updateScale = () => {
      const container = containerRef.current
      if (!container) return

      const containerWidth = container.clientWidth - 32 // padding
      const containerHeight = container.clientHeight - 32

      const scaleX = containerWidth / map.width
      const scaleY = containerHeight / map.height
      const newScale = Math.min(scaleX, scaleY, 20) // cap at 20px/m

      setScale(Math.max(5, newScale)) // minimum 5px/m
    }

    updateScale()
    window.addEventListener('resize', updateScale)
    return () => window.removeEventListener('resize', updateScale)
  }, [map])

  if (!map) {
    return (
      <div className="map-container" ref={containerRef}>
        <div className="map" style={{ width: '100%', height: '100%' }}>
          <div className="loading">Loading map...</div>
        </div>
      </div>
    )
  }

  return (
    <div
      className="map-wrapper"
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        className="map"
        style={{
          width: map.width * scale,
          height: map.height * scale,
          position: 'relative',
          flexShrink: 0,
        }}
      >
      {/* Obstacles */}
      {map.obstacles.map((obs) =>
        obs.type === 'conveyor' ? (
          <ConveyorRect key={obs.id} obstacle={obs} scale={scale} />
        ) : (
          <ObstacleRect key={obs.id} obstacle={obs} scale={scale} />
        )
      )}

      {/* Humans (below robots) */}
      {humans.map((human) => (
        <div
          key={human.human_id}
          className="map-entity human"
          style={{
            left: human.x * scale - 7,
            top: human.y * scale - 7,
          }}
          title={human.human_id}
        />
      ))}

      {/* Robots (top layer) */}
      {robots.map((robot) => {
        const color = ROBOT_COLORS[robot.commanded_action] || ROBOT_COLORS.CONTINUE
        const isSelected = selectedRobotId === robot.robot_id
        const isHovered = hoveredRobotId === robot.robot_id

        return (
          <div
            key={robot.robot_id}
            className={`map-entity robot ${robot.motion_state === 'yielding' ? 'yielding' : robot.commanded_action.toLowerCase()} ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
            style={{
              left: robot.x * scale - 10,
              top: robot.y * scale - 10,
              background: robot.motion_state === 'yielding' ? '#fb923c' : color,
            }}
            onClick={() => onRobotClick(robot)}
            title={`${robot.robot_id}: ${robot.motion_state} → ${robot.commanded_action}`}
          >
            <span className="entity-label">{robot.robot_id.replace('robot-', 'R')}</span>
          </div>
        )
      })}

      {/* Destination marker for selected robot */}
      {(() => {
        const selectedRobot = robots.find(r => r.robot_id === selectedRobotId)
        if (!selectedRobot?.destination) return null
        const waypoint = map.waypoints.find(wp => wp.id === selectedRobot.destination)
        if (!waypoint) return null
        return (
          <div
            className="destination-marker"
            style={{
              position: 'absolute',
              left: waypoint.x * scale - 12,
              top: waypoint.y * scale - 12,
              width: 24,
              height: 24,
              border: '3px solid #4ade80',
              borderRadius: '50%',
              background: 'rgba(74, 222, 128, 0.2)',
              pointerEvents: 'none',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
            title={`Destination: ${waypoint.name}`}
          >
            <div style={{
              position: 'absolute',
              top: -22,
              left: '50%',
              transform: 'translateX(-50%)',
              fontSize: 12,
              color: '#4ade80',
              whiteSpace: 'nowrap',
              fontWeight: 700,
              textShadow: '0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7)',
            }}>
              {waypoint.name}
            </div>
          </div>
        )
      })()}
      </div>
    </div>
  )
}
