/**
 * WebSocket client for streaming chat.
 */

export type MessageType = 'user_message' | 'chunk' | 'done' | 'error'

export interface WebSocketMessage {
  type: MessageType
  message_id?: number
  content: string
  message?: string
}

export interface ChatWebSocketPayload {
  content: string
  display_content?: string
}

export type MessageCallback = (msg: WebSocketMessage) => void
export type ConnectionCallback = () => void
export type DisconnectCallback = (event: CloseEvent, willReconnect: boolean, attempt: number, maxAttempts: number) => void
export type ErrorCallback = (error: Event) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private sessionId: number
  private onMessage: MessageCallback
  private onConnect?: ConnectionCallback
  private onDisconnect?: DisconnectCallback
  private onError?: ErrorCallback
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectDelay: number = 1000

  constructor(
    sessionId: number,
    onMessage: MessageCallback,
    onConnect?: ConnectionCallback,
    onDisconnect?: DisconnectCallback,
    onError?: ErrorCallback
  ) {
    this.sessionId = sessionId
    this.onMessage = onMessage
    this.onConnect = onConnect
    this.onDisconnect = onDisconnect
    this.onError = onError
  }

  connect(): void {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/chat/${this.sessionId}`

    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.onConnect?.()
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage
        this.onMessage(data)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      const willReconnect = event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts
      const nextAttempt = willReconnect ? this.reconnectAttempts + 1 : this.reconnectAttempts
      this.onDisconnect?.(event, willReconnect, nextAttempt, this.maxReconnectAttempts)

      if (willReconnect) {
        this.reconnectAttempts++
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`)
        setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.onError?.(error)
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'User disconnected')
      this.ws = null
    }
  }

  send(payload: ChatWebSocketPayload): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

export function createChatWebSocket(
  sessionId: number,
  onMessage: MessageCallback,
  onConnect?: ConnectionCallback,
  onDisconnect?: DisconnectCallback,
  onError?: ErrorCallback
): ChatWebSocket {
  return new ChatWebSocket(sessionId, onMessage, onConnect, onDisconnect, onError)
}
