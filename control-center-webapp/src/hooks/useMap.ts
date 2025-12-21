import { useState, useEffect } from 'react'
import { WarehouseMap, API_URL } from '../types'

export function useMap(mapId: string = 'zone-c') {
  const [map, setMap] = useState<WarehouseMap | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMap = async () => {
      try {
        setLoading(true)
        const res = await fetch(`${API_URL}/map/${mapId}`)
        if (res.ok) {
          const data = await res.json()
          setMap(data)
          setError(null)
        } else {
          setError(`Failed to load map: ${res.status}`)
        }
      } catch (e) {
        setError(`Network error loading map: ${e}`)
      } finally {
        setLoading(false)
      }
    }

    fetchMap()
  }, [mapId])

  return { map, loading, error }
}
