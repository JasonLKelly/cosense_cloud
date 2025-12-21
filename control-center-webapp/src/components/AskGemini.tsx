import { useState, KeyboardEvent } from 'react'
import { GeminiResponse } from '../types'

interface AskGeminiProps {
  loading: boolean
  response: GeminiResponse | null
  error: string | null
  onAsk: (question: string) => void
  onClear: () => void
  verboseMode: boolean
  onToggleVerbose: () => void
}

export function AskGemini({
  loading,
  response,
  error,
  onAsk,
  onClear,
  verboseMode,
  onToggleVerbose,
}: AskGeminiProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [question, setQuestion] = useState('')

  const handleSubmit = () => {
    if (question.trim() && !loading) {
      onAsk(question.trim())
      setQuestion('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }

  return (
    <div className={`bottom-drawer ${collapsed ? 'collapsed' : ''}`}>
      <div
        className="bottom-drawer-header"
        onClick={() => setCollapsed(!collapsed)}
      >
        <span className="drawer-title">Ask Gemini</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label
            style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="checkbox"
              checked={verboseMode}
              onChange={onToggleVerbose}
            />
            Verbose
          </label>
          <span>{collapsed ? '▲' : '▼'}</span>
        </div>
      </div>

      {!collapsed && (
        <div className="bottom-drawer-content">
          <div className="gemini-input-row">
            <input
              type="text"
              className="gemini-input"
              placeholder="Ask about robots, decisions, or zone status..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
            >
              {loading ? '...' : 'Ask'}
            </button>
            {(response || error) && (
              <button className="btn btn-secondary" onClick={onClear}>
                Clear
              </button>
            )}
          </div>

          {error && <div className="error">{error}</div>}

          {response && (
            <div className="gemini-response">
              {verboseMode && response.tool_calls.length > 0 && (
                <div className="gemini-tool-calls">
                  Tools called:{' '}
                  {response.tool_calls.map((tc, i) => (
                    <span key={i} className="gemini-tool-call">
                      {tc.tool}
                      {tc.success ? ' ✓' : ' ✗'}
                    </span>
                  ))}
                </div>
              )}

              <div style={{ marginBottom: 8 }}>
                <span
                  className={`gemini-confidence ${response.confidence.toLowerCase()}`}
                >
                  {response.confidence}
                </span>
              </div>

              <div>{response.summary}</div>

              {response.evidence.length > 0 && (
                <div style={{ marginTop: 12, fontSize: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Evidence:</div>
                  {response.evidence.map((e, i) => (
                    <div key={i} style={{ color: 'var(--text-muted)', marginBottom: 4 }}>
                      • {e.signal}: {e.value}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
