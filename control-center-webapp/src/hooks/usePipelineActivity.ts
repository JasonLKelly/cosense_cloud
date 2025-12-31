import { useState, useEffect, useCallback, useRef } from 'react'
import { ActivityEvent, API_URL } from '../types'

interface UsePipelineActivityOptions {
  maxEvents?: number
  enabled?: boolean
}

interface ActivityStats {
  toolCalls: number
  decisions: number
  anomalies: number
  anomaliesRaw: number
}

export function usePipelineActivity(options: UsePipelineActivityOptions = {}) {
  const { maxEvents = 100, enabled = true } = options
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [connected, setConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!enabled) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      setConnected(false)
      return
    }

    const eventSource = new EventSource(`${API_URL}/stream/activity`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setConnected(true)
    }

    eventSource.addEventListener('activity', (e: MessageEvent) => {
      try {
        const event: ActivityEvent = JSON.parse(e.data)
        setEvents(prev => {
          const updated = [...prev, event]
          // Keep only most recent events
          return updated.slice(-maxEvents)
        })
      } catch (err) {
        console.error('Failed to parse activity event:', err)
      }
    })

    eventSource.addEventListener('keepalive', () => {
      // Just keep connection alive, no action needed
    })

    eventSource.onerror = () => {
      setConnected(false)
    }

    return () => {
      eventSource.close()
    }
  }, [enabled, maxEvents])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  // Computed stats
  const stats: ActivityStats = {
    toolCalls: events.filter(e => e.type === 'tool_call').length,
    decisions: events.filter(e => e.type === 'decision').length,
    anomalies: events.filter(e => e.type === 'anomaly').length,
    anomaliesRaw: events.filter(e => e.type === 'anomaly_raw').length,
  }

  return {
    events,
    connected,
    stats,
    clearEvents,
  }
}
