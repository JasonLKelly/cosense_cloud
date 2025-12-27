import { useState, useCallback, useRef } from 'react'
import { GeminiResponse, API_URL } from '../types'

interface ChatMessage {
  role: 'user' | 'model'
  content: string
}

interface StreamEvent {
  type: 'tool' | 'chunk' | 'done' | 'error'
  name?: string
  text?: string
  confidence?: string
  message?: string
}

export function useGemini() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<GeminiResponse | null>(null)
  const [streamingText, setStreamingText] = useState<string>('')
  const [streamingTools, setStreamingTools] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const historyRef = useRef<ChatMessage[]>([])

  const ask = useCallback(async (question: string) => {
    setLoading(true)
    setError(null)
    setResponse(null)
    setStreamingText('')
    setStreamingTools([])

    try {
      const res = await fetch(`${API_URL}/ask/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          history: historyRef.current,
        }),
      })

      if (!res.ok) {
        setError(`Request failed: ${res.status}`)
        setLoading(false)
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        setError('No response body')
        setLoading(false)
        return
      }

      const decoder = new TextDecoder()
      let fullText = ''
      const tools: string[] = []
      let confidence = 'MEDIUM'

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: StreamEvent = JSON.parse(line.slice(6))

              if (event.type === 'tool' && event.name) {
                tools.push(event.name)
                setStreamingTools([...tools])
              } else if (event.type === 'chunk' && event.text) {
                fullText += event.text
                setStreamingText(fullText)
              } else if (event.type === 'done') {
                confidence = event.confidence || 'MEDIUM'
              } else if (event.type === 'error') {
                setError(event.message || 'Unknown error')
              }
            } catch {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }

      // Build final response
      const finalResponse: GeminiResponse = {
        summary: fullText || 'No response',
        confidence: confidence as 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT',
        evidence: [],
        tool_calls: tools.map(name => ({ tool: name, params: {}, success: true })),
      }
      setResponse(finalResponse)

      // Add to history
      historyRef.current = [
        ...historyRef.current,
        { role: 'user', content: question },
        { role: 'model', content: fullText },
      ]
    } catch (e) {
      setError(`Network error: ${e}`)
    } finally {
      setLoading(false)
      setStreamingText('')
      setStreamingTools([])
    }
  }, [])

  const clear = useCallback(() => {
    setResponse(null)
    setError(null)
    setStreamingText('')
    setStreamingTools([])
    historyRef.current = []
  }, [])

  return {
    ask,
    clear,
    loading,
    response,
    error,
    streamingText,
    streamingTools,
  }
}
