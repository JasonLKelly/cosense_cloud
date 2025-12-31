import { useState, useEffect, useCallback } from 'react'
import { SimState, Decision, AnomalyAlert, API_URL, POLL_INTERVAL } from '../types'

interface UseSimStateOptions {
  pollInterval?: number
  pollDecisions?: boolean
  pollAnomalies?: boolean
}

export function useSimState(options: UseSimStateOptions = {}) {
  const { pollInterval = POLL_INTERVAL, pollDecisions = true, pollAnomalies = true } = options
  const [state, setState] = useState<SimState | null>(null)
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [anomalies, setAnomalies] = useState<AnomalyAlert[]>([])
  const [error, setError] = useState<string | null>(null)

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/simulator/state`)
      if (res.ok) {
        setState(await res.json())
        setError(null)
      }
    } catch {
      setError('Cannot connect to API')
    }
  }, [])

  const fetchDecisions = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/decisions?limit=20`)
      if (res.ok) {
        setDecisions(await res.json())
      }
    } catch {
      // ignore
    }
  }, [])

  const fetchAnomalies = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/anomalies?limit=20`)
      if (res.ok) {
        setAnomalies(await res.json())
      }
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchState()
    if (pollDecisions) {
      fetchDecisions()
    }
    if (pollAnomalies) {
      fetchAnomalies()
    }
    const interval = setInterval(() => {
      fetchState()
      if (pollDecisions) {
        fetchDecisions()
      }
      if (pollAnomalies) {
        fetchAnomalies()
      }
    }, pollInterval)
    return () => clearInterval(interval)
  }, [fetchState, fetchDecisions, fetchAnomalies, pollInterval, pollDecisions, pollAnomalies])

  const startSim = useCallback(async () => {
    await fetch(`${API_URL}/scenario/start`, { method: 'POST' })
  }, [])

  const stopSim = useCallback(async () => {
    await fetch(`${API_URL}/scenario/stop`, { method: 'POST' })
  }, [])

  const resetSim = useCallback(async () => {
    await fetch(`${API_URL}/scenario/reset`, { method: 'POST' })
  }, [])

  const toggleVisibility = useCallback(async (visibility: 'normal' | 'degraded' | 'poor') => {
    await fetch(`${API_URL}/scenario/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visibility }),
    })
  }, [])

  const toggleConnectivity = useCallback(async (connectivity: 'normal' | 'degraded' | 'offline') => {
    await fetch(`${API_URL}/scenario/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ connectivity }),
    })
  }, [])

  const stopRobot = useCallback(async (robotId: string) => {
    await fetch(`${API_URL}/robots/${robotId}/stop`, { method: 'POST' })
  }, [])

  const startRobot = useCallback(async (robotId: string) => {
    await fetch(`${API_URL}/robots/${robotId}/start`, { method: 'POST' })
  }, [])

  return {
    state,
    decisions,
    anomalies,
    error,
    startSim,
    stopSim,
    resetSim,
    toggleVisibility,
    toggleConnectivity,
    stopRobot,
    startRobot,
  }
}
