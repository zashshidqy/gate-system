import { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react'
import { UnitStatus, GateEvent, GateStatus } from '../types'
import { apiClient } from '../api/client'
import toast from 'react-hot-toast'

interface GateContextType {
  entryStatus: UnitStatus
  exitStatus: UnitStatus
  connect: () => void
  disconnect: () => void
  isConnected: boolean
  sendCommand: (unit: 'ENTRY' | 'EXIT', command: string) => Promise<void>
  connectionQuality: 'excellent' | 'good' | 'poor' | 'offline'
}

const GateContext = createContext<GateContextType | undefined>(undefined)

let ws: WebSocket | null = null
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10
const INITIAL_RECONNECT_DELAY = 1000
const MAX_RECONNECT_DELAY = 30000

export function GateProvider({ children }: { children: ReactNode }) {
  const [entryStatus, setEntryStatus] = useState<UnitStatus>({
    unit: 'ENTRY',
    status: null,
    connected: false,
    last_update: null,
  })
  const [exitStatus, setExitStatus] = useState<UnitStatus>({
    unit: 'EXIT',
    status: null,
    connected: false,
    last_update: null,
  })
  const [isConnected, setIsConnected] = useState(false)
  const [connectionQuality, setConnectionQuality] = useState<'excellent' | 'good' | 'poor' | 'offline'>('offline')
  const lastMessageTime = useRef<number>(Date.now())
  const messageCount = useRef<number>(0)

  const calculateConnectionQuality = () => {
    const timeSinceLastMessage = Date.now() - lastMessageTime.current
    const messagesPerSecond = messageCount.current / ((timeSinceLastMessage / 1000) + 1)

    if (timeSinceLastMessage > 10000) return 'offline'
    if (timeSinceLastMessage > 5000 || messagesPerSecond < 2) return 'poor'
    if (timeSinceLastMessage > 2000) return 'good'
    return 'excellent'
  }

  const connect = () => {
    if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/gates/ws`

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setIsConnected(true)
        reconnectAttempts = 0
        lastMessageTime.current = Date.now()
        messageCount.current = 0
        console.log('[GateContext] WebSocket connected')
        toast.success('Terhubung ke sistem gerbang', { position: 'bottom-right' })
      }

      ws.onmessage = (event) => {
        try {
          lastMessageTime.current = Date.now()
          messageCount.current++
          
          const data: GateEvent = JSON.parse(event.data)
          handleGateEvent(data)
          
          // Update connection quality periodically
          setConnectionQuality(calculateConnectionQuality())
        } catch (e) {
          console.error('[GateContext] Failed to parse gate event:', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        setConnectionQuality('offline')
        setEntryStatus((prev) => ({ ...prev, connected: false }))
        setExitStatus((prev) => ({ ...prev, connected: false }))
        
        // Attempt reconnection with exponential backoff
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts),
            MAX_RECONNECT_DELAY
          )
          reconnectAttempts++
          console.log(`[GateContext] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`)
          reconnectTimeout = setTimeout(connect, delay)
        } else {
          console.error('[GateContext] Max reconnection attempts reached')
          toast.error('Gagal terhubung ke sistem gerbang. Muat ulang halaman.', { position: 'bottom-right' })
        }
      }

      ws.onerror = (error) => {
        console.error('[GateContext] WebSocket error:', error)
        setConnectionQuality('offline')
      }
    } catch (e) {
      console.error('[GateContext] Failed to create WebSocket:', e)
      setConnectionQuality('offline')
    }
  }

  const disconnect = () => {
    if (reconnectTimeout) clearTimeout(reconnectTimeout)
    reconnectAttempts = 0
    if (ws) {
      ws.close()
      ws = null
    }
    setIsConnected(false)
    setConnectionQuality('offline')
  }

  const handleGateEvent = (event: GateEvent) => {
    const now = new Date().toISOString()

    if (event.type === 'GATE_STATUS' && event.unit) {
      const status: GateStatus = event.payload
      const unitStatus: UnitStatus = {
        unit: event.unit,
        status,
        connected: true,
        last_update: now,
      }

      if (event.unit === 'ENTRY') {
        setEntryStatus(unitStatus)
      } else if (event.unit === 'EXIT') {
        setExitStatus(unitStatus)
      }
    } else if (event.type === 'ERROR') {
      console.error('[GateContext] Gate error:', event.payload)
      toast.error(`Galat gerbang: ${event.payload?.message || 'Kesalahan tidak diketahui'}`, { position: 'bottom-right' })
    }
  }

  const sendCommand = async (unit: 'ENTRY' | 'EXIT', command: string) => {
    try {
      await apiClient.instance.post('/gates/command', null, {
        params: { unit, command },
      })
    } catch (error) {
      console.error('[GateContext] Failed to send command:', error)
      throw error
    }
  }

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [])

  // Periodic connection quality check
  useEffect(() => {
    const interval = setInterval(() => {
      if (isConnected) {
        setConnectionQuality(calculateConnectionQuality())
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [isConnected])

  return (
    <GateContext.Provider value={{ entryStatus, exitStatus, connect, disconnect, isConnected, sendCommand, connectionQuality }}>
      {children}
    </GateContext.Provider>
  )
}

export function useGates() {
  const context = useContext(GateContext)
  if (!context) {
    throw new Error('useGates must be used within a GateProvider')
  }
  return context
}
