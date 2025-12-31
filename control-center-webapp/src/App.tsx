import { useState } from 'react'
import { Robot, AnomalyAlert, API_URL, CONFLUENT_URL, POLL_INTERVAL } from './types'
import { useSimState } from './hooks/useSimState'
import { useGemini } from './hooks/useGemini'
import { useMap } from './hooks/useMap'
import { EntityDrawer } from './components/EntityDrawer'
import { AskGemini } from './components/AskGemini'
import { MetricsPanel } from './components/MetricsPanel'
import { WarehouseMapView } from './components/WarehouseMap'
import { ResetDialog } from './components/ResetDialog'
import './styles.css'

export default function App() {
  const [pollDecisions, setPollDecisions] = useState(true)
  const [pollAnomalies, setPollAnomalies] = useState(true)
  const [pollInterval, setPollInterval] = useState(POLL_INTERVAL)

  const {
    state,
    decisions,
    anomalies,
    error: simError,
    startSim,
    stopSim,
    toggleVisibility,
    toggleConnectivity,
    stopRobot,
    startRobot,
    dismissAlert,
  } = useSimState({ pollDecisions, pollAnomalies, pollInterval })

  const {
    ask,
    clear,
    loading: geminiLoading,
    response: geminiResponse,
    error: geminiError,
    streamingText,
    streamingTools,
  } = useGemini()

  const { map, error: mapError } = useMap('zone-c')

  const [selectedRobotId, setSelectedRobotId] = useState<string | null>(null)
  const [hoveredRobotId, setHoveredRobotId] = useState<string | null>(null)
  const [showResetDialog, setShowResetDialog] = useState(false)

  // Get live robot data for selected robot
  const selectedRobot = state?.robots.find(r => r.robot_id === selectedRobotId) || null

  const handleRobotClick = (robot: Robot) => {
    setSelectedRobotId(robot.robot_id)
  }

  const handleCloseDrawer = () => {
    setSelectedRobotId(null)
  }

  const handleStopRobot = async (robotId: string) => {
    await stopRobot(robotId)
  }

  const handleStartRobot = async (robotId: string) => {
    await startRobot(robotId)
  }

  const handleResetClick = () => {
    setShowResetDialog(true)
  }

  const handleResetConfirm = async (params: {
    robots: number
    humans: number
    visibility: string
    connectivity: string
  }) => {
    setShowResetDialog(false)

    // Reset with all parameters
    await fetch(`${API_URL}/scenario/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
  }

  const handleExplainAlert = (alert: AnomalyAlert) => {
    const prompt = `Explain this ${alert.severity} severity ${alert.alert_type} alert${alert.robot_id ? ` involving ${alert.robot_id}` : ''}. Context: "${alert.context}". What might be causing this and what should the operator do?`
    ask(prompt)
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1 className="header-title">CoSense Control Center</h1>
        <div className="header-controls">
          <button className="btn btn-primary" onClick={startSim}>Start</button>
          <button className="btn btn-danger" onClick={stopSim}>Stop</button>
          <button className="btn btn-secondary" onClick={handleResetClick}>Reset</button>
        </div>
        <div className="header-status">
          {state && (
            <>
              <span>{state.running ? 'Running' : 'Stopped'}</span>
              <span>Time: {state.sim_time.toFixed(1)}s</span>
            </>
          )}
          <select
            className="poll-select"
            value={pollInterval}
            onChange={(e) => setPollInterval(Number(e.target.value))}
            title="Poll interval"
          >
            <option value={250}>250ms</option>
            <option value={500}>500ms</option>
            <option value={1000}>1s</option>
            <option value={2000}>2s</option>
            <option value={5000}>5s</option>
          </select>
          <a
            href="/activity"
            target="_blank"
            rel="noopener noreferrer"
            className="header-link"
          >
            Pipeline
          </a>
          <a
            href={CONFLUENT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="header-link"
          >
            Kafka UI
          </a>
        </div>
      </header>

      {/* Main Content */}
      <div className="main-content">
        {/* Map Container */}
        <div className="map-container">
          {(simError || mapError) && (
            <div className="error">{simError || mapError}</div>
          )}

          <WarehouseMapView
            map={map}
            robots={state?.robots || []}
            humans={state?.humans || []}
            selectedRobotId={selectedRobotId}
            hoveredRobotId={hoveredRobotId}
            onRobotClick={handleRobotClick}
          />
        </div>

        {/* Right Drawer - Metrics Panel */}
        <MetricsPanel
          simState={state}
          robots={state?.robots || []}
          decisions={decisions}
          anomalies={anomalies}
          onToggleVisibility={toggleVisibility}
          onToggleConnectivity={toggleConnectivity}
          onDecisionsExpandedChange={setPollDecisions}
          onAnomaliesExpandedChange={setPollAnomalies}
          onRobotClick={handleRobotClick}
          onRobotHover={setHoveredRobotId}
          onExplainAlert={handleExplainAlert}
          onDismissAlert={dismissAlert}
        />
      </div>

      {/* Bottom Drawer - Ask Gemini */}
      <AskGemini
        loading={geminiLoading}
        response={geminiResponse}
        error={geminiError}
        streamingText={streamingText}
        streamingTools={streamingTools}
        onAsk={ask}
        onClear={clear}
      />

      {/* Entity Drawer (slides in from right) */}
      <EntityDrawer
        robot={selectedRobot}
        onClose={handleCloseDrawer}
        onStop={handleStopRobot}
        onStart={handleStartRobot}
      />

      {/* Reset Dialog */}
      <ResetDialog
        isOpen={showResetDialog}
        currentRobots={state?.robots.length || 20}
        currentHumans={state?.humans.length || 10}
        onCancel={() => setShowResetDialog(false)}
        onReset={handleResetConfirm}
      />
    </div>
  )
}
