import { useEffect, useState, useRef } from 'react'

export default function useSSE(url) {
  const [event, setEvent] = useState(null)
  const sourceRef = useRef(null)

  useEffect(() => {
    if (!url) return

    let cancelled = false
    let source = null
    const abortCtrl = new AbortController()

    fetch(url, { signal: abortCtrl.signal })
      .then((res) => {
        abortCtrl.abort()
        if (cancelled || !res.ok) return

        source = new EventSource(url)
        sourceRef.current = source

        source.onmessage = (e) => {
          try {
            setEvent(JSON.parse(e.data))
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

  return event
}
