'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Opportunity, RiskSnapshot, StreamEvent } from '@/lib/types'

const MAX_SIGNALS = 50
const RECONNECT_MS = 2_000

export function useArbitrageStream(url: string) {
  const [connected, setConnected] = useState(false)
  const [signals, setSignals] = useState<Opportunity[]>([])
  const [risk, setRisk] = useState<RiskSnapshot>({})
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return

    let ws: WebSocket
    try {
      ws = new WebSocket(url)
    } catch {
      timerRef.current = setTimeout(connect, RECONNECT_MS)
      return
    }
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = ({ data }) => {
      try {
        const event = JSON.parse(data as string) as StreamEvent
        if (event.type === 'opportunity') {
          setSignals((prev) => [event.data, ...prev].slice(0, MAX_SIGNALS))
        } else if (event.type === 'risk') {
          setRisk(event.data)
        }
      } catch { /* ignore malformed frames */ }
    }

    ws.onclose = () => {
      setConnected(false)
      timerRef.current = setTimeout(connect, RECONNECT_MS)
    }

    ws.onerror = () => ws.close()
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected, signals, risk }
}
