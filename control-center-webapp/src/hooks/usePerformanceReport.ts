import { useState, useEffect, useCallback } from 'react'
import { ShiftSummary, API_URL } from '../types'

interface UsePerformanceReportOptions {
  /** Poll interval for fetching latest summary (default: 5000ms) */
  pollInterval?: number
}

export function usePerformanceReport(options: UsePerformanceReportOptions = {}) {
  const { pollInterval = 5000 } = options
  const [latestSummary, setLatestSummary] = useState<ShiftSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch the latest Flink-generated summary
  const fetchLatest = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/summary/latest`)
      if (res.ok) {
        const data = await res.json()
        if (data) {
          setLatestSummary(data)
        }
        setError(null)
      }
    } catch {
      // Silently ignore fetch errors - summary is optional
    }
  }, [])

  // Poll for new summaries from Flink
  useEffect(() => {
    fetchLatest()
    const interval = setInterval(fetchLatest, pollInterval)
    return () => clearInterval(interval)
  }, [fetchLatest, pollInterval])

  // Generate a summary on-demand (bypasses Flink)
  const generateSummary = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/summary/generate`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setLatestSummary(data)
        return data
      } else {
        throw new Error(`Failed to generate summary: ${res.status}`)
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error'
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    latestSummary,
    loading,
    error,
    generateSummary,
    refetch: fetchLatest,
  }
}
