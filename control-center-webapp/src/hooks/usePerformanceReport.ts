import { useState, useEffect, useCallback, useRef } from 'react'
import { ShiftSummary, API_URL } from '../types'

interface UsePerformanceReportOptions {
  /** Auto-refresh interval in ms (default: 60000 = 1 minute) */
  autoRefreshInterval?: number
}

export function usePerformanceReport(options: UsePerformanceReportOptions = {}) {
  const { autoRefreshInterval = 60000 } = options
  const [latestSummary, setLatestSummary] = useState<ShiftSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const hasFetched = useRef(false)

  // Generate a summary on-demand
  const generateSummaryInternal = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/summary/generate`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setLatestSummary(data)
        return data
      }
    } catch {
      // Silently ignore errors
    } finally {
      if (showLoading) setLoading(false)
    }
    return null
  }, [])

  // Auto-generate on mount and periodically
  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true
      generateSummaryInternal(true)
    }
    const interval = setInterval(() => generateSummaryInternal(false), autoRefreshInterval)
    return () => clearInterval(interval)
  }, [generateSummaryInternal, autoRefreshInterval])

  return {
    latestSummary,
    loading,
    error,
    generateSummary: () => generateSummaryInternal(true),
  }
}
