import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react'
import Markdown from 'react-markdown'
import { GeminiResponse } from '../types'

interface AskGeminiProps {
  loading: boolean
  response: GeminiResponse | null
  error: string | null
  streamingText: string
  streamingTools: string[]
  onAsk: (question: string) => void
  onClear: () => void
  verboseMode: boolean
  onToggleVerbose: () => void
}

const MIN_HEIGHT = 100
const MAX_HEIGHT = 600
const DEFAULT_HEIGHT = 240

export function AskGemini({
  loading,
  response,
  error,
  streamingText,
  streamingTools,
  onAsk,
  onClear,
  verboseMode,
  onToggleVerbose,
}: AskGeminiProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [question, setQuestion] = useState('')
  const [height, setHeight] = useState(DEFAULT_HEIGHT)
  const [isResizing, setIsResizing] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const streamingRef = useRef<HTMLDivElement>(null)
  const responseRef = useRef<HTMLDivElement>(null)

  // Refocus input after loading completes
  useEffect(() => {
    if (!loading && inputRef.current) {
      inputRef.current.focus()
    }
  }, [loading])

  // Auto-scroll to bottom when streaming text updates
  useEffect(() => {
    if (streamingRef.current && streamingText) {
      requestAnimationFrame(() => {
        if (streamingRef.current) {
          streamingRef.current.scrollTop = streamingRef.current.scrollHeight
        }
      })
    }
  }, [streamingText])

  // Scroll response to bottom when it first appears
  useEffect(() => {
    if (responseRef.current && response) {
      requestAnimationFrame(() => {
        if (responseRef.current) {
          responseRef.current.scrollTop = responseRef.current.scrollHeight
        }
      })
    }
  }, [response])

  // Handle resize drag
  const handleMouseMove = useCallback((e: MouseEvent) => {
    const newHeight = window.innerHeight - e.clientY
    setHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, newHeight)))
  }, [])

  const handleMouseUp = useCallback(() => {
    setIsResizing(false)
  }, [])

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ns-resize'
      document.body.style.userSelect = 'none'
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, handleMouseMove, handleMouseUp])

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
    <div
      className={`bottom-drawer ${collapsed ? 'collapsed' : ''}`}
      style={collapsed ? undefined : { height }}
    >
      {!collapsed && (
        <div
          className="resize-handle"
          onMouseDown={(e) => {
            e.preventDefault()
            setIsResizing(true)
          }}
        />
      )}
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
              ref={inputRef}
              type="text"
              className="gemini-input"
              placeholder="Ask about robots, decisions, or what's happening..."
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

          {loading && (
            <div className="gemini-streaming" ref={streamingRef}>
              {streamingTools.length > 0 && (
                <div className="streaming-tools">
                  {streamingTools.map((tool, i) => (
                    <span key={i} className="gemini-tool-call">{tool} ✓</span>
                  ))}
                </div>
              )}
              {streamingText ? (
                <div className="streaming-text">
                  <Markdown>{streamingText}</Markdown>
                  <span className="cursor">▊</span>
                </div>
              ) : (
                <div className="gemini-loading">
                  <div className="loading-spinner"></div>
                  <span>{streamingTools.length > 0 ? 'Processing...' : 'Gemini is thinking...'}</span>
                </div>
              )}
            </div>
          )}

          {error && <div className="error">{error}</div>}

          {response && (
            <div className="gemini-response" ref={responseRef}>
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
                  {response.confidence} CONFIDENCE
                </span>
              </div>

              <div className="response-text"><Markdown>{response.summary}</Markdown></div>

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
