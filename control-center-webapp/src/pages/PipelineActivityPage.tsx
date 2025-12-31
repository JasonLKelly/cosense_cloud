import { useState } from 'react'
import { usePipelineActivity } from '../hooks/usePipelineActivity'
import {
  ActivityEvent,
  ToolCallActivityData,
  DecisionActivityData,
  AnomalyActivityData,
} from '../types'
import '../styles.css'

type FilterType = 'all' | 'tool_call' | 'decision' | 'anomaly' | 'anomaly_raw'

export function PipelineActivityPage() {
  const { events, connected, stats, clearEvents } = usePipelineActivity({
    maxEvents: 200,
    enabled: true,
  })
  const [filter, setFilter] = useState<FilterType>('all')

  const filteredEvents = events
    .filter(e => {
      if (filter === 'all') return true
      if (filter === 'anomaly') return e.type === 'anomaly' || e.type === 'anomaly_raw'
      return e.type === filter
    })
    .slice()
    .reverse() // Most recent first

  const formatTime = (ms: number) => {
    const date = new Date(ms)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
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

  const renderEvent = (event: ActivityEvent, index: number) => {
    switch (event.type) {
      case 'tool_call': {
        const data = event.data as ToolCallActivityData
        return (
          <div key={index} className="activity-row activity-tool">
            <div className="activity-time">{formatTime(event.timestamp_ms)}</div>
            <div className="activity-icon">&#x1F527;</div>
            <div className="activity-main">
              <span className="activity-tool-name">{data.tool_name}</span>
            </div>
            {data.params && Object.keys(data.params).length > 0 && (
              <div className="activity-details">
                {Object.entries(data.params).map(([k, v]) => (
                  <span key={k} className="activity-param">
                    {k}: {String(v)}
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      }
      case 'decision': {
        const data = event.data as DecisionActivityData
        const actionClass = data.action.toLowerCase()
        return (
          <div key={index} className={`activity-row activity-decision ${actionClass}`}>
            <div className="activity-time">{formatTime(event.timestamp_ms)}</div>
            <div className="activity-icon">&#x26A1;</div>
            <div className="activity-main">
              <span className="activity-robot">{data.robot_id}</span>
              <span className="activity-arrow">&#x2192;</span>
              <span className={`activity-action ${actionClass}`}>{data.action}</span>
            </div>
            <div className="activity-details">
              <span className="activity-risk">
                Risk: {(data.risk_score * 100).toFixed(0)}%
              </span>
              {data.reason_codes.length > 0 && (
                <span className="activity-reasons">{data.reason_codes.join(', ')}</span>
              )}
            </div>
          </div>
        )
      }
      case 'anomaly': {
        const data = event.data as AnomalyActivityData
        return (
          <div
            key={index}
            className={`activity-row activity-anomaly enriched ${data.severity.toLowerCase()}`}
          >
            <div className="activity-time">{formatTime(event.timestamp_ms)}</div>
            <div className="activity-icon">
              <svg className="gemini-icon-activity" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z"/>
              </svg>
            </div>
            <div className="activity-main">
              <span className={`activity-severity ${data.severity.toLowerCase()}`}>
                {data.severity}
              </span>
              <span className="activity-alert-type">{formatAlertType(data.alert_type)}</span>
              <span className="activity-enriched-badge">AI Enriched</span>
            </div>
            <div className="activity-details">
              <span className="activity-deviation">
                Deviation: {data.deviation_percent > 0 ? '+' : ''}
                {data.deviation_percent.toFixed(0)}%
              </span>
              {data.robot_id && <span className="activity-robot-ref">{data.robot_id}</span>}
            </div>
          </div>
        )
      }
      case 'anomaly_raw': {
        const data = event.data as AnomalyActivityData
        return (
          <div
            key={index}
            className={`activity-row activity-anomaly raw ${data.severity.toLowerCase()}`}
          >
            <div className="activity-time">{formatTime(event.timestamp_ms)}</div>
            <div className="activity-icon">&#x1F6A8;</div>
            <div className="activity-main">
              <span className={`activity-severity ${data.severity.toLowerCase()}`}>
                {data.severity}
              </span>
              <span className="activity-alert-type">{formatAlertType(data.alert_type)}</span>
              <span className="activity-raw-badge">Flink ML</span>
            </div>
            <div className="activity-details">
              <span className="activity-deviation">
                Deviation: {data.deviation_percent > 0 ? '+' : ''}
                {data.deviation_percent.toFixed(0)}%
              </span>
              {data.robot_id && <span className="activity-robot-ref">{data.robot_id}</span>}
            </div>
          </div>
        )
      }
      default:
        return null
    }
  }

  return (
    <div className="activity-page">
      <header className="activity-header">
        <div className="activity-title">
          <span className={`connection-dot ${connected ? 'connected' : ''}`} />
          <h1>Pipeline Activity</h1>
        </div>
        <div className="activity-controls">
          <button className="btn-clear" onClick={clearEvents}>
            Clear
          </button>
        </div>
      </header>

      <div className="activity-stats">
        <div className="stat-card stat-tools">
          <div className="stat-icon">&#x1F527;</div>
          <div className="stat-value">{stats.toolCalls}</div>
          <div className="stat-label">Gemini Tools</div>
        </div>
        <div className="stat-card stat-decisions">
          <div className="stat-icon">&#x26A1;</div>
          <div className="stat-value">{stats.decisions}</div>
          <div className="stat-label">Decisions</div>
        </div>
        <div className="stat-card stat-anomalies-raw">
          <div className="stat-icon">&#x1F6A8;</div>
          <div className="stat-value">{stats.anomaliesRaw}</div>
          <div className="stat-label">Raw Anomalies</div>
        </div>
        <div className="stat-card stat-anomalies">
          <div className="stat-icon">
            <svg className="gemini-icon-stat" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z"/>
            </svg>
          </div>
          <div className="stat-value">{stats.anomalies}</div>
          <div className="stat-label">AI Enriched</div>
        </div>
      </div>

      <div className="activity-filters">
        <button
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        <button
          className={`filter-btn ${filter === 'tool_call' ? 'active' : ''}`}
          onClick={() => setFilter('tool_call')}
        >
          Tools
        </button>
        <button
          className={`filter-btn ${filter === 'decision' ? 'active' : ''}`}
          onClick={() => setFilter('decision')}
        >
          Decisions
        </button>
        <button
          className={`filter-btn ${filter === 'anomaly' ? 'active' : ''}`}
          onClick={() => setFilter('anomaly')}
        >
          Anomalies
        </button>
      </div>

      <div className="activity-list-container">
        {filteredEvents.length === 0 ? (
          <div className="activity-empty">
            No activity yet. Start the simulation or ask Gemini a question.
          </div>
        ) : (
          <div className="activity-list">
            {filteredEvents.map((event, i) => renderEvent(event, i))}
          </div>
        )}
      </div>
    </div>
  )
}
