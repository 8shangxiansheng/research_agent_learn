import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { ResearchDocumentPayload, ResearchPhaseStatus, ResearchTaskResult } from '@/api/research'
import { deleteResearchTask, getSessionResearchTasks, rerunResearchTask, rerunResearchTaskAsNew, runResearchTask, updateResearchTask } from '@/api/research'
import { useLocaleStore } from '@/stores/locale'
import { resolveLocalizedApiError, resolveLocalizedErrorMessage } from '@/utils/localization'

const DEFAULT_PHASE_SEQUENCE: ResearchPhaseStatus['phase'][] = ['planning', 'retrieving', 'synthesizing', 'completed']
type ResearchHistorySort = 'newest' | 'oldest' | 'title'
type ResearchHistorySourceFilter = 'all' | 'arxiv' | 'crossref' | 'local'
type ResearchFailureOperation = 'run' | 'rerun' | 'rerun_as_new'

export type ResearchFailureState = {
  operation: ResearchFailureOperation
  taskId?: number
  query: string
  message: string
  reason?: string
  recoveryHint?: string
  retryable: boolean
  document?: ResearchDocumentPayload
}

export const useResearchStore = defineStore('research', () => {
  const localeStore = useLocaleStore()
  const currentTask = ref<ResearchTaskResult | null>(null)
  const tasks = ref<ResearchTaskResult[]>([])
  const query = ref('')
  const historyQuery = ref('')
  const historySort = ref<ResearchHistorySort>('newest')
  const historySourceFilter = ref<ResearchHistorySourceFilter>('all')
  const selectedTaskIds = ref<number[]>([])
  const isRunning = ref(false)
  const isLoadingHistory = ref(false)
  const error = ref<string | null>(null)
  const phaseStatuses = ref<ResearchPhaseStatus[]>([])
  const lastFailure = ref<ResearchFailureState | null>(null)
  let phaseTimer: ReturnType<typeof setTimeout> | null = null

  const selectedCount = computed(() => selectedTaskIds.value.length)
  const hasSelectedTasks = computed(() => selectedCount.value > 0)
  const allFilteredSelected = computed(() => (
    filteredTasks.value.length > 0
    && filteredTasks.value.every(task => selectedTaskIds.value.includes(task.id))
  ))

  function matchesSourceFilter(task: ResearchTaskResult, filter: ResearchHistorySourceFilter): boolean {
    if (filter === 'all') {
      return true
    }

    const sourceTypes = new Set(task.sources.map(source => source.source_type))
    if (filter === 'local') {
      return sourceTypes.has('local_document') || sourceTypes.has('local_pdf')
    }
    return sourceTypes.has(filter)
  }

  function sortTasks(items: ResearchTaskResult[], sortBy: ResearchHistorySort): ResearchTaskResult[] {
    return [...items].sort((left, right) => {
      if (sortBy === 'title') {
        return left.query.localeCompare(right.query)
      }
      const leftTime = new Date(left.generated_at).getTime()
      const rightTime = new Date(right.generated_at).getTime()
      return sortBy === 'oldest' ? leftTime - rightTime : rightTime - leftTime
    })
  }

  const filteredTasks = computed(() => {
    const normalizedQuery = historyQuery.value.trim().toLowerCase()
    const matchedTasks = tasks.value.filter(task => {
      if (normalizedQuery && !task.query.toLowerCase().includes(normalizedQuery)) {
        return false
      }
      return matchesSourceFilter(task, historySourceFilter.value)
    })
    return sortTasks(matchedTasks, historySort.value)
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

  function clearFailure(): void {
    lastFailure.value = null
  }

  function buildFailureState(
    operation: ResearchFailureOperation,
    taskQuery: string,
    resolvedError: ReturnType<typeof resolveLocalizedApiError>,
    options?: {
      taskId?: number
      document?: ResearchDocumentPayload
    },
  ): ResearchFailureState {
    return {
      operation,
      taskId: options?.taskId,
      query: resolvedError.query ?? taskQuery,
      message: resolvedError.message,
      reason: resolvedError.reason,
      recoveryHint: resolvedError.recoveryHint,
      retryable: resolvedError.retryable,
      document: options?.document,
    }
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
      clearFailure()
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
      const resolvedError = resolveLocalizedApiError(e, localeStore, 'research.error.run')
      error.value = resolvedError.message
      lastFailure.value = buildFailureState('run', normalizedQuery, resolvedError, { document })
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
      selectedTaskIds.value = []
      return
    }

    try {
      isLoadingHistory.value = true
      error.value = null
      clearFailure()
      tasks.value = await getSessionResearchTasks(sessionId)
      currentTask.value = tasks.value[0] ?? null
      selectedTaskIds.value = []
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

  function isTaskSelected(taskId: number): boolean {
    return selectedTaskIds.value.includes(taskId)
  }

  function toggleTaskSelection(taskId: number): void {
    selectedTaskIds.value = isTaskSelected(taskId)
      ? selectedTaskIds.value.filter(id => id !== taskId)
      : [...selectedTaskIds.value, taskId]
  }

  function setAllFilteredSelected(selected: boolean): void {
    if (selected) {
      selectedTaskIds.value = filteredTasks.value.map(task => task.id)
      return
    }
    selectedTaskIds.value = []
  }

  function clearSelection(): void {
    selectedTaskIds.value = []
  }

  async function removeTask(taskId: number): Promise<void> {
    try {
      error.value = null
      clearFailure()
      await deleteResearchTask(taskId)
      tasks.value = tasks.value.filter(task => task.id !== taskId)
      selectedTaskIds.value = selectedTaskIds.value.filter(id => id !== taskId)
      if (currentTask.value?.id === taskId) {
        currentTask.value = tasks.value[0] ?? null
      }
    } catch (e) {
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.delete')
      console.error(e)
      throw e
    }
  }

  async function bulkRemoveSelectedTasks(): Promise<void> {
    if (!selectedTaskIds.value.length) {
      return
    }

    try {
      error.value = null
      clearFailure()
      const idsToDelete = [...selectedTaskIds.value]
      await Promise.all(idsToDelete.map(taskId => deleteResearchTask(taskId)))
      tasks.value = tasks.value.filter(task => !idsToDelete.includes(task.id))
      if (currentTask.value && idsToDelete.includes(currentTask.value.id)) {
        currentTask.value = tasks.value[0] ?? null
      }
      selectedTaskIds.value = []
    } catch (e) {
      error.value = resolveLocalizedErrorMessage(e, localeStore, 'research.error.bulkDelete')
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
      clearFailure()
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
    const originalTask = tasks.value.find(task => task.id === taskId) ?? currentTask.value
    try {
      isRunning.value = true
      error.value = null
      clearFailure()
      startPhaseTracking()
      const updatedTask = await rerunResearchTask(taskId)
      tasks.value = tasks.value.map(task => task.id === taskId ? updatedTask : task)
      currentTask.value = updatedTask
      finishPhaseTracking(updatedTask.phase_statuses)
    } catch (e) {
      clearPhaseTimer()
      const resolvedError = resolveLocalizedApiError(e, localeStore, 'research.error.rerun')
      error.value = resolvedError.message
      lastFailure.value = buildFailureState(
        'rerun',
        originalTask?.query ?? query.value,
        resolvedError,
        { taskId },
      )
      console.error(e)
      throw e
    } finally {
      isRunning.value = false
    }
  }

  async function rerunTaskAsNew(taskId: number): Promise<void> {
    const originalTask = tasks.value.find(task => task.id === taskId) ?? currentTask.value
    try {
      isRunning.value = true
      error.value = null
      clearFailure()
      startPhaseTracking()
      const createdTask = await rerunResearchTaskAsNew(taskId)
      tasks.value = [createdTask, ...tasks.value.filter(task => task.id !== createdTask.id)]
      currentTask.value = createdTask
      finishPhaseTracking(createdTask.phase_statuses)
    } catch (e) {
      clearPhaseTimer()
      const resolvedError = resolveLocalizedApiError(e, localeStore, 'research.error.rerunNew')
      error.value = resolvedError.message
      lastFailure.value = buildFailureState(
        'rerun_as_new',
        originalTask?.query ?? query.value,
        resolvedError,
        { taskId },
      )
      console.error(e)
      throw e
    } finally {
      isRunning.value = false
    }
  }

  async function retryLastFailure(sessionId?: number): Promise<void> {
    if (!lastFailure.value || !lastFailure.value.retryable) {
      return
    }

    if (lastFailure.value.operation === 'run') {
      await runTask(lastFailure.value.query, sessionId, lastFailure.value.document)
      return
    }

    if (!lastFailure.value.taskId) {
      return
    }

    if (lastFailure.value.operation === 'rerun') {
      await rerunTask(lastFailure.value.taskId)
      return
    }

    await rerunTaskAsNew(lastFailure.value.taskId)
  }

  function clearTask(): void {
    currentTask.value = null
    phaseStatuses.value = []
    clearPhaseTimer()
    error.value = null
    clearFailure()
  }

  return {
    currentTask,
    tasks,
    filteredTasks,
    query,
    historyQuery,
    historySort,
    historySourceFilter,
    selectedTaskIds,
    selectedCount,
    hasSelectedTasks,
    allFilteredSelected,
    isRunning,
    isLoadingHistory,
    error,
    lastFailure,
    phaseStatuses,
    visiblePhaseStatuses,
    runTask,
    fetchTasks,
    selectTask,
    isTaskSelected,
    toggleTaskSelection,
    setAllFilteredSelected,
    clearSelection,
    renameTask,
    rerunTask,
    rerunTaskAsNew,
    retryLastFailure,
    removeTask,
    bulkRemoveSelectedTasks,
    clearFailure,
    clearTask,
  }
})
