/**
 * REST API client for session management.
 */
import axios from 'axios'

const API_BASE = '/api'

export interface Session {
  id: number
  title: string
  created_at: string
  messages?: Message[]
}

export interface Message {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface CreateSessionRequest {
  title?: string
}

export interface UpdateSessionRequest {
  title?: string
}

// ========== Session API ==========

export interface SessionExportPayload {
  filename: string
  content: string
}

export async function getSessions(query = ''): Promise<Session[]> {
  const response = await axios.get<Session[]>(`${API_BASE}/sessions`, {
    params: query ? { query } : undefined,
  })
  return response.data
}

export async function getSession(sessionId: number): Promise<Session> {
  const response = await axios.get<Session>(`${API_BASE}/sessions/${sessionId}`)
  return response.data
}

export async function createSession(data: CreateSessionRequest = {}): Promise<Session> {
  const response = await axios.post<Session>(`${API_BASE}/sessions`, data)
  return response.data
}

export async function updateSession(sessionId: number, data: UpdateSessionRequest): Promise<Session> {
  const response = await axios.put<Session>(`${API_BASE}/sessions/${sessionId}`, data)
  return response.data
}

export async function deleteSession(sessionId: number): Promise<void> {
  await axios.delete(`${API_BASE}/sessions/${sessionId}`)
}

export async function exportSession(sessionId: number): Promise<SessionExportPayload> {
  const response = await axios.get<SessionExportPayload>(`${API_BASE}/sessions/${sessionId}/export`)
  return response.data
}

// ========== Message API ==========

export async function getMessages(sessionId: number): Promise<Message[]> {
  const response = await axios.get<Message[]>(`${API_BASE}/sessions/${sessionId}/messages`)
  return response.data
}

export async function createMessage(sessionId: number, role: 'user' | 'assistant', content: string): Promise<Message> {
  const response = await axios.post<Message>(`${API_BASE}/messages`, {
    session_id: sessionId,
    role,
    content
  })
  return response.data
}

export async function retryAssistantMessage(sessionId: number, messageId: number): Promise<Message> {
  const response = await axios.post<Message>(`${API_BASE}/sessions/${sessionId}/messages/${messageId}/retry`)
  return response.data
}
