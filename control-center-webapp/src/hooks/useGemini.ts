import { useState, useCallback } from 'react'
import { GeminiResponse, API_URL } from '../types'

export function useGemini() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<GeminiResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ask = useCallback(async (question: string) => {
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      if (res.ok) {
        const data = await res.json()
        setResponse(data)
      } else {
        setError(`Request failed: ${res.status}`)
      }
    } catch (e) {
      setError(`Network error: ${e}`)
    } finally {
      setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    setResponse(null)
    setError(null)
  }, [])

  return {
    ask,
    clear,
    loading,
    response,
    error,
  }
}
