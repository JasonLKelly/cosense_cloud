import { useState } from 'react'

interface ResetDialogProps {
  isOpen: boolean
  currentRobots: number
  currentHumans: number
  onCancel: () => void
  onReset: (params: { robots: number; humans: number; visibility: string; connectivity: string }) => void
}

export function ResetDialog({
  isOpen,
  currentRobots,
  currentHumans,
  onCancel,
  onReset,
}: ResetDialogProps) {
  const [robots, setRobots] = useState(currentRobots)
  const [humans, setHumans] = useState(currentHumans)
  const [visibility, setVisibility] = useState('normal')
  const [connectivity, setConnectivity] = useState('normal')

  if (!isOpen) return null

  const handleReset = () => {
    onReset({ robots, humans, visibility, connectivity })
  }

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3 className="dialog-title">Reset Simulation</h3>
          <button className="dialog-close" onClick={onCancel}>×</button>
        </div>

        <div className="dialog-content">
          <div className="dialog-field">
            <label>Robots</label>
            <input
              type="number"
              min={1}
              max={50}
              value={robots}
              onChange={(e) => setRobots(parseInt(e.target.value) || 1)}
            />
          </div>

          <div className="dialog-field">
            <label>Humans</label>
            <input
              type="number"
              min={1}
              max={30}
              value={humans}
              onChange={(e) => setHumans(parseInt(e.target.value) || 1)}
            />
          </div>

          <div className="dialog-field">
            <label>Visibility</label>
            <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
              <option value="normal">Normal</option>
              <option value="degraded">Degraded</option>
              <option value="poor">Poor</option>
            </select>
          </div>

          <div className="dialog-field">
            <label>Connectivity</label>
            <select value={connectivity} onChange={(e) => setConnectivity(e.target.value)}>
              <option value="normal">Normal</option>
              <option value="degraded">Degraded</option>
              <option value="offline">Offline</option>
            </select>
          </div>
        </div>

        <div className="dialog-actions">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn btn-primary" onClick={handleReset}>Reset</button>
        </div>
      </div>
    </div>
  )
}
