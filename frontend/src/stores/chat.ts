/**
 * Pinia store for chat state management.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session, Message } from '@/api/sessions'
import * as api from '@/api/sessions'
import { ChatWebSocket, type WebSocketMessage } from '@/api/websocket'

export const useChatStore = defineStore('chat', () => {
  // State
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const messages = ref<Message[]>([])
  const sessionSearchQuery = ref('')
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const error = ref<string | null>(null)

  // WebSocket instance
  let websocket: ChatWebSocket | null = null

  // Getters
  const currentMessages = computed(() => messages.value)
  const hasCurrentSession = computed(() => currentSession.value !== null)

  // Actions

  /**
   * Fetch all sessions.
   */
  async function fetchSessions(query = sessionSearchQuery.value): Promise<void> {
    try {
      isLoading.value = true
      error.value = null
      sessionSearchQuery.value = query
      sessions.value = await api.getSessions(query)
    } catch (e) {
      error.value = 'Failed to fetch sessions'
      console.error(e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Select a session and load its messages.
   */
  async function selectSession(session: Session): Promise<void> {
    currentSession.value = session
    messages.value = session.messages || []

    // Fetch messages if not loaded
    if (!session.messages) {
      try {
        isLoading.value = true
        messages.value = await api.getMessages(session.id)
      } catch (e) {
        error.value = 'Failed to fetch messages'
        console.error(e)
      } finally {
        isLoading.value = false
      }
    }

    // Connect WebSocket
    connectWebSocket(session.id)
  }

  /**
   * Create a new session.
   */
  async function createSession(title: string = 'New Chat'): Promise<Session> {
    try {
      isLoading.value = true
      const session = await api.createSession({ title })
      sessions.value.unshift(session)
      return session
    } catch (e) {
      error.value = 'Failed to create session'
      console.error(e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update session title.
   */
  async function updateSessionTitle(sessionId: number, title: string): Promise<void> {
    try {
      const updated = await api.updateSession(sessionId, { title })
      const index = sessions.value.findIndex(s => s.id === sessionId)
      if (index !== -1) {
        sessions.value[index] = updated
      }
      if (currentSession.value?.id === sessionId) {
        currentSession.value = {
          ...currentSession.value,
          ...updated,
          messages: messages.value,
        }
      }
    } catch (e) {
      error.value = 'Failed to update session'
      console.error(e)
      throw e
    }
  }

  /**
   * Delete a session.
   */
  async function deleteSession(sessionId: number): Promise<void> {
    try {
      await api.deleteSession(sessionId)
      sessions.value = sessions.value.filter(s => s.id !== sessionId)
      if (currentSession.value?.id === sessionId) {
        currentSession.value = null
        messages.value = []
        disconnectWebSocket()
      }
    } catch (e) {
      error.value = 'Failed to delete session'
      console.error(e)
      throw e
    }
  }

  async function exportCurrentSession(session: Session): Promise<void> {
    try {
      const exported = await api.exportSession(session.id)
      const blob = new Blob([exported.content], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = exported.filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      error.value = 'Failed to export session'
      console.error(e)
      throw e
    }
  }

  async function retryAssistantMessage(messageId: number): Promise<void> {
    if (!currentSession.value) {
      error.value = 'No active session'
      return
    }

    try {
      isStreaming.value = true
      error.value = null
      const updated = await api.retryAssistantMessage(currentSession.value.id, messageId)
      messages.value = messages.value.map(message => (
        message.id === messageId ? updated : message
      ))
      currentSession.value = {
        ...currentSession.value,
        messages: messages.value,
      }
    } catch (e) {
      error.value = 'Failed to retry answer'
      console.error(e)
      throw e
    } finally {
      isStreaming.value = false
      streamingContent.value = ''
    }
  }

  async function appendResearchTask(taskId: number, mode: 'summary' | 'full' = 'summary'): Promise<void> {
    if (!currentSession.value) {
      error.value = 'No active session'
      return
    }

    try {
      error.value = null
      const message = await api.shareResearchTaskToSession(taskId, mode)
      messages.value = [...messages.value, message]
      currentSession.value = {
        ...currentSession.value,
        messages: messages.value,
      }
    } catch (e) {
      error.value = 'Failed to add research brief to session'
      console.error(e)
      throw e
    }
  }

  /**
   * Connect WebSocket for current session.
   */
  function connectWebSocket(sessionId: number): void {
    // Disconnect existing
    disconnectWebSocket()

    websocket = new ChatWebSocket(
      sessionId,
      handleWebSocketMessage,
      () => console.log('WebSocket connected'),
      () => console.log('WebSocket disconnected'),
      (e) => {
        error.value = 'WebSocket connection error'
        console.error(e)
      }
    )
    websocket.connect()
  }

  /**
   * Disconnect WebSocket.
   */
  function disconnectWebSocket(): void {
    if (websocket) {
      websocket.disconnect()
      websocket = null
    }
  }

  /**
   * Handle WebSocket messages.
   */
  function handleWebSocketMessage(msg: WebSocketMessage): void {
    switch (msg.type) {
      case 'user_message':
        // Add user message to list
        messages.value.push({
          id: msg.message_id!,
          session_id: currentSession.value!.id,
          role: 'user',
          content: msg.content,
          created_at: new Date().toISOString()
        })
        break

      case 'chunk':
        // Accumulate streaming content
        isStreaming.value = true
        streamingContent.value += msg.content
        break

      case 'done':
        // Add complete assistant message
        isStreaming.value = false
        messages.value.push({
          id: msg.message_id!,
          session_id: currentSession.value!.id,
          role: 'assistant',
          content: msg.content,
          created_at: new Date().toISOString()
        })
        streamingContent.value = ''
        break

      case 'error':
        isStreaming.value = false
        streamingContent.value = ''
        error.value = msg.message || 'Unknown error'
        break
    }
  }

  /**
   * Send a message via WebSocket.
   */
  function sendMessage(content: string): void {
    if (websocket && websocket.isConnected()) {
      websocket.send(content)
    } else {
      error.value = 'WebSocket not connected'
    }
  }

  /**
   * Clear error.
   */
  function clearError(): void {
    error.value = null
  }

  return {
    // State
    sessions,
    currentSession,
    messages,
    sessionSearchQuery,
    isLoading,
    isStreaming,
    streamingContent,
    error,

    // Getters
    currentMessages,
    hasCurrentSession,

    // Actions
    fetchSessions,
    selectSession,
    createSession,
    updateSessionTitle,
    deleteSession,
    exportCurrentSession,
    retryAssistantMessage,
    appendResearchTask,
    sendMessage,
    disconnectWebSocket,
    clearError
  }
})
