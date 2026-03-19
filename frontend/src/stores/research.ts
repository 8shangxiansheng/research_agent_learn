import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { ResearchTaskResult } from '@/api/research'
import { deleteResearchTask, getSessionResearchTasks, rerunResearchTask, runResearchTask, updateResearchTask } from '@/api/research'

export const useResearchStore = defineStore('research', () => {
  const currentTask = ref<ResearchTaskResult | null>(null)
  const tasks = ref<ResearchTaskResult[]>([])
  const query = ref('')
  const historyQuery = ref('')
  const isRunning = ref(false)
  const isLoadingHistory = ref(false)
  const error = ref<string | null>(null)
  const filteredTasks = computed(() => {
    const normalizedQuery = historyQuery.value.trim().toLowerCase()
    if (!normalizedQuery) {
      return tasks.value
    }

    return tasks.value.filter(task => task.query.toLowerCase().includes(normalizedQuery))
  })

  async function runTask(taskQuery = query.value, sessionId?: number): Promise<void> {
    const normalizedQuery = taskQuery.trim()
    if (!normalizedQuery) {
      error.value = 'Research query cannot be empty'
      return
    }

    try {
      isRunning.value = true
      error.value = null
      query.value = normalizedQuery
      currentTask.value = await runResearchTask({
        query: normalizedQuery,
        session_id: sessionId,
      })
      if (currentTask.value) {
        tasks.value = [currentTask.value, ...tasks.value.filter(task => task.id !== currentTask.value?.id)]
      }
    } catch (e) {
      error.value = 'Failed to run research task'
      console.error(e)
      throw e
    } finally {
      isRunning.value = false
    }
  }

  async function fetchTasks(sessionId?: number | null): Promise<void> {
    if (!sessionId) {
      tasks.value = []
      currentTask.value = null
      return
    }

    try {
      isLoadingHistory.value = true
      error.value = null
      tasks.value = await getSessionResearchTasks(sessionId)
      currentTask.value = tasks.value[0] ?? null
    } catch (e) {
      error.value = 'Failed to fetch research history'
      console.error(e)
    } finally {
      isLoadingHistory.value = false
    }
  }

  function selectTask(task: ResearchTaskResult): void {
    currentTask.value = task
  }

  async function removeTask(taskId: number): Promise<void> {
    try {
      error.value = null
      await deleteResearchTask(taskId)
      tasks.value = tasks.value.filter(task => task.id !== taskId)
      if (currentTask.value?.id === taskId) {
        currentTask.value = tasks.value[0] ?? null
      }
    } catch (e) {
      error.value = 'Failed to delete research task'
      console.error(e)
      throw e
    }
  }

  async function renameTask(taskId: number, query: string): Promise<void> {
    const normalizedQuery = query.trim()
    if (!normalizedQuery) {
      error.value = 'Research query cannot be empty'
      return
    }

    try {
      error.value = null
      const updatedTask = await updateResearchTask(taskId, { query: normalizedQuery })
      tasks.value = tasks.value.map(task => task.id === taskId ? updatedTask : task)
      if (currentTask.value?.id === taskId) {
        currentTask.value = updatedTask
      }
    } catch (e) {
      error.value = 'Failed to rename research task'
      console.error(e)
      throw e
    }
  }

  async function rerunTask(taskId: number): Promise<void> {
    try {
      isRunning.value = true
      error.value = null
      const updatedTask = await rerunResearchTask(taskId)
      tasks.value = tasks.value.map(task => task.id === taskId ? updatedTask : task)
      currentTask.value = updatedTask
    } catch (e) {
      error.value = 'Failed to rerun research task'
      console.error(e)
      throw e
    } finally {
      isRunning.value = false
    }
  }

  function clearTask(): void {
    currentTask.value = null
    error.value = null
  }

  return {
    currentTask,
    tasks,
    filteredTasks,
    query,
    historyQuery,
    isRunning,
    isLoadingHistory,
    error,
    runTask,
    fetchTasks,
    selectTask,
    renameTask,
    rerunTask,
    removeTask,
    clearTask,
  }
})
