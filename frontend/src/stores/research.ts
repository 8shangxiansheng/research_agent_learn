import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { ResearchDocumentPayload, ResearchPhaseStatus, ResearchTaskResult } from '@/api/research'
import { deleteResearchTask, getSessionResearchTasks, rerunResearchTask, rerunResearchTaskAsNew, runResearchTask, updateResearchTask } from '@/api/research'
import { useLocaleStore } from '@/stores/locale'
import { resolveLocalizedErrorMessage } from '@/utils/localization'

const DEFAULT_PHASE_SEQUENCE: ResearchPhaseStatus['phase'][] = ['planning', 'retrieving', 'synthesizing', 'completed']

export const useResearchStore = defineStore('research', () => {
  const localeStore = useLocaleStore()
  const currentTask = ref<ResearchTaskResult | null>(null)
  const tasks = ref<ResearchTaskResult[]>([])
  const query = ref('')
  const historyQuery = ref('')
  const isRunning = ref(false)
  const isLoadingHistory = ref(false)
  const error = ref<string | null>(null)
  const phaseStatuses = ref<ResearchPhaseStatus[]>([])
  let phaseTimer: ReturnType<typeof setTimeout> | null = null
  const filteredTasks = computed(() => {
    const normalizedQuery = historyQuery.value.trim().toLowerCase()
    if (!normalizedQuery) {
      return tasks.value
    }

    return tasks.value.filter(task => task.query.toLowerCase().includes(normalizedQuery))
  })
  const visiblePhaseStatuses = computed(() => {
    if (isRunning.value || phaseStatuses.value.length > 0) {
      return phaseStatuses.value
    }
    return currentTask.value?.phase_statuses ?? []
  })

  function getPhaseDetail(phase: ResearchPhaseStatus['phase']): string {
    return localeStore.t(`research.phase.${phase}.detail`)
  }

  function buildPendingPhaseStatuses(): ResearchPhaseStatus[] {
    return DEFAULT_PHASE_SEQUENCE.map((phase, index) => ({
      phase,
      status: index === 0 ? 'active' : 'pending',
      detail: getPhaseDetail(phase),
    }))
  }

  function clearPhaseTimer(): void {
    if (phaseTimer) {
      clearTimeout(phaseTimer)
      phaseTimer = null
    }
  }

  function advanceActivePhase(): void {
    const activeIndex = phaseStatuses.value.findIndex(item => item.status === 'active')
    if (activeIndex === -1 || activeIndex >= DEFAULT_PHASE_SEQUENCE.length - 1) {
      return
    }
    phaseStatuses.value = phaseStatuses.value.map((item, index) => {
      if (index < activeIndex + 1) {
        return { ...item, status: 'completed' }
      }
      if (index === activeIndex + 1) {
        return { ...item, status: 'active' }
      }
      return item
    })
    phaseTimer = setTimeout(advanceActivePhase, 450)
  }

  function startPhaseTracking(): void {
    clearPhaseTimer()
    phaseStatuses.value = buildPendingPhaseStatuses()
    phaseTimer = setTimeout(advanceActivePhase, 450)
  }

  function finishPhaseTracking(finalStatuses?: ResearchPhaseStatus[]): void {
    clearPhaseTimer()
    if (finalStatuses?.length) {
      phaseStatuses.value = finalStatuses
      return
    }
    phaseStatuses.value = DEFAULT_PHASE_SEQUENCE.map(phase => ({
      phase,
      status: 'completed',
      detail: getPhaseDetail(phase),
    }))
  }

  async function runTask(
    taskQuery = query.value,
    sessionId?: number,
    document?: ResearchDocumentPayload,
  ): Promise<void> {
    const normalizedQuery = taskQuery.trim()
    if (!normalizedQuery) {
      error.value = localeStore.t('research.error.emptyQuery')
      return
    }

    try {
      isRunning.value = true
      error.value = null
      startPhaseTracking()
      query.value = normalizedQuery
      currentTask.value = await runResearchTask({
        query: normalizedQuery,
        session_id: sessionId,
        document,
      })
      finishPhaseTracking(currentTask.value.phase_statuses)
      if (currentTask.value) {
        tasks.value = [currentTask.value, ...tasks.value.filter(task => task.id !== currentTask.value?.id)]
      }
    } catch (e) {
      clearPhaseTimer()
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.run')
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
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.fetchHistory')
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
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.delete')
      console.error(e)
      throw e
    }
  }

  async function renameTask(taskId: number, query: string): Promise<void> {
    const normalizedQuery = query.trim()
    if (!normalizedQuery) {
      error.value = localeStore.t('research.error.emptyQuery')
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
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.rename')
      console.error(e)
      throw e
    }
  }

  async function rerunTask(taskId: number): Promise<void> {
    try {
      isRunning.value = true
      error.value = null
      startPhaseTracking()
      const updatedTask = await rerunResearchTask(taskId)
      tasks.value = tasks.value.map(task => task.id === taskId ? updatedTask : task)
      currentTask.value = updatedTask
      finishPhaseTracking(updatedTask.phase_statuses)
    } catch (e) {
      clearPhaseTimer()
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.rerun')
      console.error(e)
      throw e
    } finally {
      isRunning.value = false
    }
  }

  async function rerunTaskAsNew(taskId: number): Promise<void> {
    try {
      isRunning.value = true
      error.value = null
      startPhaseTracking()
      const createdTask = await rerunResearchTaskAsNew(taskId)
      tasks.value = [createdTask, ...tasks.value.filter(task => task.id !== createdTask.id)]
      currentTask.value = createdTask
      finishPhaseTracking(createdTask.phase_statuses)
    } catch (e) {
      clearPhaseTimer()
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.rerunNew')
      console.error(e)
      throw e
    } finally {
      isRunning.value = false
    }
  }

  function clearTask(): void {
    currentTask.value = null
    phaseStatuses.value = []
    clearPhaseTimer()
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
    phaseStatuses,
    visiblePhaseStatuses,
    runTask,
    fetchTasks,
    selectTask,
    renameTask,
    rerunTask,
    rerunTaskAsNew,
    removeTask,
    clearTask,
  }
})
