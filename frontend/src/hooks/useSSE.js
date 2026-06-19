import { useEffect, useState, useRef, useCallback } from 'react'
import { getAccessToken } from '../api'

export default function useSSE(url) {
  const [event, setEvent] = useState(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const sourceRef = useRef(null)

  const resetCount = useCallback(() => setUnreadCount(0), [])

  useEffect(() => {
    if (!url) return

    const token = getAccessToken()
    if (!token) return

    const separator = url.includes('?') ? '&' : '?'
    const fullUrl = `${url}${separator}token=${token}`

    let cancelled = false
    let source = null
    const abortCtrl = new AbortController()

    fetch(fullUrl, { signal: abortCtrl.signal })
      .then((res) => {
        abortCtrl.abort()
        if (cancelled || !res.ok) return

        source = new EventSource(fullUrl)
        sourceRef.current = source

        source.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data)
            setEvent(data)
            setUnreadCount((c) => c + 1)
          } catch {
            setEvent({ message: e.data })
          }
        }

        source.onerror = () => {
          source.close()
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
      abortCtrl.abort()
      if (source) {
        source.close()
      }
      sourceRef.current = null
    }
  }, [url])

  return { event, unreadCount, resetCount }
}
