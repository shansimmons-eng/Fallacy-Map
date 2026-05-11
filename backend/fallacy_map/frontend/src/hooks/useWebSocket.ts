import { useEffect, useRef, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'
import { useArgumentStore, Fallacy } from '../stores/argumentStore'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

interface WSMessage {
  type: string
  data?: any
  fallacy?: Fallacy
  V_active?: number
  V_cost?: number
  bypass_triggered?: boolean
  inverion_triggered?: boolean
  mesh_update?: number[][]
}

export function useWebSocket(argumentId: string | null) {
  const socketRef = useRef<Socket | null>(null)
  const {
    setVactive,
    addFallacy,
    setMeshData,
    addVeracityEvent,
    triggerInverion,
    getStateFromV
  } = useArgumentStore()

  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case 'connected':
        setVactive(msg.V_active ?? 1.0)
        break
      case 'fallacy_detected':
        if (msg.fallacy) {
          addFallacy(msg.fallacy)
          addVeracityEvent({
            V_before: msg.V_active! + msg.V_cost!,
            V_after: msg.V_active!,
            V_cost: msg.V_cost!,
            type: 'fallacy'
          })
        }
        setVactive(msg.V_active ?? 0)
        if (msg.mesh_update) {
          setMeshData(msg.mesh_update)
        }
        if (msg.bypass_triggered) {
          addVeracityEvent({
            V_before: (msg.V_active ?? 0) + (msg.V_cost ?? 0),
            V_after: msg.V_active ?? 0,
            V_cost: msg.V_cost ?? 0,
            type: 'bypass'
          })
        }
        if (msg.inverion_triggered && msg.fallacy) {
          triggerInverion(msg.fallacy.id)
          addVeracityEvent({
            V_before: 0.1,
            V_after: 0,
            V_cost: 0.1,
            type: 'divide'
          })
        }
        break
      case 'chunk_complete':
        setVactive(msg.V_active ?? 0)
        break
      case 'inverion_triggered':
        setVactive(0)
        triggerInverion('')
        break
      case 'error':
        console.error('WebSocket error:', msg)
        break
    }
  }, [setVactive, addFallacy, setMeshData, addVeracityEvent, triggerInverion])

  useEffect(() => {
    if (!argumentId) return

    const socket = io(WS_URL, {
      path: `/ws/${argumentId}`,
      transports: ['websocket']
    })

    socket.on('message', (data) => {
      handleMessage(JSON.parse(data))
    })

    socket.on('connect', () => {
      console.log('WebSocket connected')
    })

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
    })

    socketRef.current = socket

    return () => {
      socket.disconnect()
    }
  }, [argumentId, handleMessage])

  const sendAnalyzeChunk = useCallback((text: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('message', JSON.stringify({
        type: 'analyze_chunk',
        text
      }))
    }
  }, [])

  return { sendAnalyzeChunk }
}