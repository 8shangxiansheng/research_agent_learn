/**
 * REST API client for the minimal research workflow.
 */
import axios from 'axios'

const API_BASE = '/api'

export interface ResearchTaskRequest {
  query: string
  max_sources?: number
  session_id?: number
}

export interface ResearchSource {
  source_id: string
  citation_label: string
  arxiv_id?: string | null
  title: string
  authors: string[]
  abstract: string
  published_at: string
  url: string
  pdf_url?: string | null
  primary_category?: string | null
  categories?: string[]
  comment?: string | null
  journal_ref?: string | null
  doi?: string | null
  citation_text?: string | null
  source_type: string
  score: number
}

export interface ResearchTaskResult {
  id: number
  session_id?: number | null
  query: string
  status: string
  generated_at: string
  report_filename: string
  plan: string[]
  sources: ResearchSource[]
  answer: string
  report_markdown: string
}

export interface ResearchReportDownload {
  blob: Blob
  filename: string
}

export async function runResearchTask(data: ResearchTaskRequest): Promise<ResearchTaskResult> {
  const response = await axios.post<ResearchTaskResult>(`${API_BASE}/research/tasks`, data)
  return response.data
}

export async function getResearchTask(taskId: number): Promise<ResearchTaskResult> {
  const response = await axios.get<ResearchTaskResult>(`${API_BASE}/research/tasks/${taskId}`)
  return response.data
}

export async function getSessionResearchTasks(sessionId: number): Promise<ResearchTaskResult[]> {
  const response = await axios.get<ResearchTaskResult[]>(`${API_BASE}/sessions/${sessionId}/research-tasks`)
  return response.data
}

export async function deleteResearchTask(taskId: number): Promise<void> {
  await axios.delete(`${API_BASE}/research/tasks/${taskId}`)
}

export async function downloadResearchTaskReport(taskId: number): Promise<ResearchReportDownload> {
  const response = await axios.get(`${API_BASE}/research/tasks/${taskId}/report/raw`, {
    responseType: 'blob',
  })
  const dispositionHeader = String(response.headers['content-disposition'] ?? '')
  const filenameMatch = dispositionHeader.match(/filename="([^"]+)"/)
  return {
    blob: response.data,
    filename: filenameMatch?.[1] ?? `research-task-${taskId}.md`,
  }
}
