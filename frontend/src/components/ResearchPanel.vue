<template>
  <section class="research-panel">
    <div class="panel-header">
      <div>
        <h3>{{ localeStore.t('research.title') }}</h3>
        <p>{{ localeStore.t('research.description') }}</p>
      </div>
      <div class="panel-actions">
        <el-button
          v-if="researchStore.currentTask"
          data-test="export-report"
          text
          @click="exportReport"
        >
          {{ localeStore.t('research.exportReport') }}
        </el-button>
        <el-button
          v-if="researchStore.currentTask"
          text
          @click="researchStore.clearTask()"
        >
          {{ localeStore.t('research.clear') }}
        </el-button>
      </div>
    </div>

    <div class="query-row">
      <el-input
        v-model="query"
        data-test="research-query"
        :placeholder="localeStore.t('research.queryPlaceholder')"
        :disabled="researchStore.isRunning"
        @keydown.enter.prevent="handleRun"
      />
      <el-button
        data-test="run-research"
        type="primary"
        :loading="researchStore.isRunning"
        :disabled="!query.trim()"
        @click="handleRun"
      >
        {{ researchStore.isRunning ? localeStore.t('research.running') : localeStore.t('research.run') }}
      </el-button>
    </div>

    <div class="document-row">
      <input
        ref="documentInput"
        data-test="research-file-input"
        class="document-input"
        type="file"
        accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf"
        @change="handleDocumentChange"
      >
      <el-button
        data-test="attach-document"
        text
        :disabled="researchStore.isRunning"
        @click="openDocumentPicker"
      >
        {{ selectedDocument ? localeStore.t('research.changeDocument') : localeStore.t('research.attachDocument') }}
      </el-button>
      <el-button
        v-if="selectedDocument"
        text
        :disabled="researchStore.isRunning"
        @click="clearDocument"
      >
        {{ localeStore.t('research.clearDocument') }}
      </el-button>
      <span class="document-formats">{{ localeStore.t('research.documentFormats') }}</span>
    </div>

    <div v-if="selectedDocument" class="document-chip">
      <strong>{{ localeStore.t('research.documentAttached') }}：</strong>
      <span>{{ selectedDocument.filename }}</span>
    </div>

    <section
      v-if="researchStore.visiblePhaseStatuses.length"
      class="progress-card"
      data-test="research-progress"
    >
      <h4>{{ localeStore.t('research.progress') }}</h4>
      <div class="phase-list">
        <div
          v-for="item in researchStore.visiblePhaseStatuses"
          :key="item.phase"
          :class="['phase-item', `is-${item.status}`]"
        >
          <div class="phase-row">
            <span class="phase-label">{{ localeStore.t(`research.phase.${item.phase}`) }}</span>
            <span class="phase-status">{{ item.status }}</span>
          </div>
          <p class="phase-detail">{{ item.detail }}</p>
        </div>
      </div>
    </section>

    <p v-if="researchStore.error" class="error-text">{{ researchStore.error }}</p>

    <section v-if="chatStore.currentSession" class="history-strip">
      <div class="history-header">
        <h4>{{ localeStore.t('research.history') }}</h4>
        <span v-if="researchStore.isLoadingHistory">{{ localeStore.t('research.loading') }}</span>
      </div>
      <div class="history-toolbar">
        <label class="history-select-all">
          <input
            data-test="history-select-all"
            type="checkbox"
            :checked="researchStore.allFilteredSelected"
            @change="toggleSelectAll($event)"
          >
          <span>{{ localeStore.t('research.selectAll') }}</span>
        </label>
        <select
          v-model="researchStore.historySourceFilter"
          data-test="history-source-filter"
          class="history-filter"
        >
          <option value="all">{{ localeStore.t('research.filter.all') }}</option>
          <option value="arxiv">{{ localeStore.t('research.filter.arxiv') }}</option>
          <option value="crossref">{{ localeStore.t('research.filter.crossref') }}</option>
          <option value="local">{{ localeStore.t('research.filter.local') }}</option>
        </select>
        <select
          v-model="researchStore.historySort"
          data-test="history-sort"
          class="history-filter"
        >
          <option value="newest">{{ localeStore.t('research.sort.newest') }}</option>
          <option value="oldest">{{ localeStore.t('research.sort.oldest') }}</option>
          <option value="title">{{ localeStore.t('research.sort.title') }}</option>
        </select>
        <button
          type="button"
          data-test="bulk-delete-history"
          class="history-bulk-delete"
          :disabled="!researchStore.hasSelectedTasks"
          @click="bulkRemoveTasks"
        >
          {{ localeStore.t('research.bulkDelete') }} ({{ researchStore.selectedCount }})
        </button>
      </div>
      <el-input
        v-model="researchStore.historyQuery"
        class="history-search"
        :placeholder="localeStore.t('research.historySearch')"
        clearable
      />
      <div v-if="researchStore.filteredTasks.length === 0" class="history-empty">
        {{ localeStore.t('research.historyEmpty') }}
      </div>
      <div v-else class="history-list">
        <div
          v-for="task in researchStore.filteredTasks"
          :key="task.id"
          :class="['history-item-shell', { active: researchStore.currentTask?.id === task.id }]"
        >
          <label class="history-check">
            <input
              :checked="researchStore.isTaskSelected(task.id)"
              :data-task-id="task.id"
              data-test="history-checkbox"
              type="checkbox"
              @click.stop
              @change="researchStore.toggleTaskSelection(task.id)"
            >
          </label>
          <button
            type="button"
            :class="['history-item', { active: researchStore.currentTask?.id === task.id }]"
            @click="researchStore.selectTask(task)"
          >
            <strong>{{ task.query }}</strong>
            <div class="history-item-row">
              <span>{{ formatTaskDate(task.generated_at) }}</span>
              <span
                class="history-rerun"
                @click.stop="rerunTask(task.id)"
              >
                {{ localeStore.t('research.rerun') }}
              </span>
              <span
                class="history-rerun-new"
                @click.stop="rerunTaskAsNew(task.id)"
              >
                {{ localeStore.t('research.rerunNew') }}
              </span>
              <span
                class="history-rename"
                @click.stop="renameTask(task.id, task.query)"
              >
                {{ localeStore.t('research.rename') }}
              </span>
              <span
                class="history-delete"
                @click.stop="removeTask(task.id)"
              >
                {{ localeStore.t('research.delete') }}
              </span>
            </div>
          </button>
        </div>
      </div>
    </section>

    <div v-if="researchStore.currentTask" class="result-grid" data-test="research-result">
      <section class="card">
        <h4>{{ localeStore.t('research.plan') }}</h4>
        <ol>
          <li v-for="step in researchStore.currentTask.plan" :key="step">{{ step }}</li>
        </ol>
      </section>

      <section class="card">
        <h4>{{ localeStore.t('research.sources') }}</h4>
        <ul class="source-list">
          <li v-for="source in researchStore.currentTask.sources" :key="source.source_id">
            <div class="source-meta">
              <span class="citation-chip">[{{ source.citation_label }}]</span>
              <span>{{ formatSourceType(source.source_type) }}</span>
              <span>{{ formatPublishedDate(source.published_at) }}</span>
              <span v-if="source.primary_category">{{ source.primary_category }}</span>
            </div>
            <a
              v-if="isRemoteSource(source.url)"
              :href="source.url"
              target="_blank"
              rel="noreferrer"
            >
              {{ source.title }}
            </a>
            <strong v-else class="local-source-title">{{ source.title }}</strong>
            <p>{{ source.authors.slice(0, 3).join(', ') }}</p>
            <p v-if="source.citation_text" class="citation-text">{{ source.citation_text }}</p>
            <p class="abstract">{{ source.abstract.slice(0, 180) }}{{ source.abstract.length > 180 ? '...' : '' }}</p>
            <div v-if="source.categories?.length" class="category-list">
              <span
                v-for="category in source.categories.slice(0, 4)"
                :key="category"
                class="category-chip"
              >
                {{ category }}
              </span>
            </div>
            <div class="source-extra">
              <span v-if="source.arxiv_id">arXiv: {{ source.arxiv_id }}</span>
              <span v-if="source.doi">DOI: {{ source.doi }}</span>
              <span v-if="source.journal_ref">{{ source.journal_ref }}</span>
            </div>
            <div class="source-links">
              <a
                v-if="isRemoteSource(source.url)"
                :href="source.url"
                target="_blank"
                rel="noreferrer"
              >
                {{ localeStore.t('research.abstract') }}
              </a>
              <a v-if="source.pdf_url" :href="source.pdf_url" target="_blank" rel="noreferrer">{{ localeStore.t('common.pdf') }}</a>
            </div>
          </li>
        </ul>
      </section>

      <section class="card">
        <h4>{{ localeStore.t('research.evidence') }}</h4>
        <ul v-if="researchStore.currentTask.evidence_map.length" class="evidence-list">
          <li
            v-for="item in researchStore.currentTask.evidence_map"
            :key="`${item.claim}-${item.citation_labels.join('-')}`"
            class="evidence-item"
          >
            <p class="evidence-claim">{{ item.claim }}</p>
            <div class="evidence-citations">
              <span
                v-for="label in item.citation_labels"
                :key="label"
                class="citation-chip"
              >
                [{{ label }}]
              </span>
            </div>
          </li>
        </ul>
        <p v-else class="history-empty">{{ localeStore.t('research.evidenceEmpty') }}</p>
      </section>

      <section class="card report-card" data-test="research-answer-card">
        <div class="report-header">
          <h4>{{ localeStore.t('research.answer') }}</h4>
          <div
            v-if="researchStore.currentTask && chatStore.currentSession"
            class="insert-actions"
          >
            <el-button
              size="small"
              @click="insertIntoChat('summary')"
            >
              {{ localeStore.t('research.insertSummary') }}
            </el-button>
            <el-button
              size="small"
              @click="insertIntoChat('full')"
            >
              {{ localeStore.t('research.insertFull') }}
            </el-button>
          </div>
        </div>
        <p class="answer" data-test="research-answer">{{ researchStore.currentTask.answer }}</p>
        <details>
          <summary>{{ localeStore.t('research.viewMarkdown') }}</summary>
          <pre>{{ researchStore.currentTask.report_markdown }}</pre>
        </details>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import type { ResearchDocumentPayload } from '@/api/research'
import { downloadResearchTaskReport } from '@/api/research'
import { useChatStore } from '@/stores/chat'
import { useLocaleStore } from '@/stores/locale'
import { useResearchStore } from '@/stores/research'
import { formatHistoryDate, formatSourceDate } from '@/utils/localization'

const chatStore = useChatStore()
const localeStore = useLocaleStore()
const researchStore = useResearchStore()
const query = ref(researchStore.query)
const documentInput = ref<HTMLInputElement | null>(null)
const selectedDocument = ref<ResearchDocumentPayload | null>(null)

async function handleRun(): Promise<void> {
  await researchStore.runTask(query.value, chatStore.currentSession?.id, selectedDocument.value ?? undefined)
}

async function insertIntoChat(mode: 'summary' | 'full'): Promise<void> {
  if (!researchStore.currentTask) {
    return
  }
  await chatStore.appendResearchTask(researchStore.currentTask.id, mode)
}

async function removeTask(taskId: number): Promise<void> {
  await researchStore.removeTask(taskId)
}

async function bulkRemoveTasks(): Promise<void> {
  await researchStore.bulkRemoveSelectedTasks()
}

async function renameTask(taskId: number, currentQuery: string): Promise<void> {
  const nextQuery = window.prompt(localeStore.t('research.renamePrompt'), currentQuery)
  if (nextQuery === null) {
    return
  }

  await researchStore.renameTask(taskId, nextQuery)
}

async function rerunTask(taskId: number): Promise<void> {
  await researchStore.rerunTask(taskId)
}

async function rerunTaskAsNew(taskId: number): Promise<void> {
  await researchStore.rerunTaskAsNew(taskId)
}

async function exportReport(): Promise<void> {
  if (!researchStore.currentTask) {
    return
  }

  const { blob, filename } = await downloadResearchTaskReport(researchStore.currentTask.id)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function formatTaskDate(date: string): string {
  return formatHistoryDate(date, localeStore)
}

function formatPublishedDate(date?: string): string {
  return formatSourceDate(date, localeStore)
}

function formatSourceType(sourceType: string): string {
  const key = `research.sourceType.${sourceType}`
  const translated = localeStore.t(key)
  return translated === key ? sourceType : translated
}

function toggleSelectAll(event: Event): void {
  const target = event.target as HTMLInputElement
  researchStore.setAllFilteredSelected(target.checked)
}

function isRemoteSource(url: string): boolean {
  return /^https?:\/\//.test(url)
}

function openDocumentPicker(): void {
  documentInput.value?.click()
}

function clearDocument(): void {
  selectedDocument.value = null
  if (documentInput.value) {
    documentInput.value.value = ''
  }
}

function toBase64(bytes: Uint8Array): string {
  let binary = ''
  const chunkSize = 0x8000
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize))
  }
  return btoa(binary)
}

async function handleDocumentChange(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) {
    selectedDocument.value = null
    return
  }

  try {
    const buffer = await file.arrayBuffer()
    selectedDocument.value = {
      filename: file.name,
      mime_type: file.type || undefined,
      content_base64: toBase64(new Uint8Array(buffer)),
    }
    researchStore.error = null
  } catch (error) {
    console.error(error)
    researchStore.error = localeStore.t('research.error.readDocument')
    clearDocument()
  }
}

watch(
  () => chatStore.currentSession?.id ?? null,
  (sessionId) => {
    researchStore.fetchTasks(sessionId)
  },
  { immediate: true }
)
</script>

<style scoped>
.research-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fcfcfd;
  min-height: 260px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-header h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #1f2937;
}

.panel-header p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.query-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}

.document-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.document-input {
  display: none;
}

.document-formats {
  font-size: 12px;
  color: #6b7280;
}

.document-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #eff6ff;
  color: #1e3a8a;
  font-size: 13px;
}

.progress-card {
  padding: 12px 14px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #f8fbff;
}

.progress-card h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #1e3a8a;
}

.phase-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.phase-item {
  padding: 10px;
  border-radius: 10px;
  border: 1px solid #dbeafe;
  background: white;
}

.phase-item.is-active {
  border-color: #2563eb;
  background: #eff6ff;
}

.phase-item.is-completed {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.phase-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.phase-label {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
}

.phase-status {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #2563eb;
}

.phase-item.is-completed .phase-status {
  color: #15803d;
}

.phase-detail {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: #4b5563;
}

.error-text {
  color: #d14343;
  font-size: 13px;
}

.history-strip {
  padding: 12px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #ffffff;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.history-header h4 {
  margin: 0;
  font-size: 14px;
  color: #111827;
}

.history-empty {
  font-size: 13px;
  color: #6b7280;
}

.history-search {
  margin-bottom: 10px;
}

.history-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.history-select-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #374151;
}

.history-filter {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  font-size: 12px;
  padding: 6px 8px;
}

.history-bulk-delete {
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff1f2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  cursor: pointer;
}

.history-bulk-delete:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.history-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.history-item-shell {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.history-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding-top: 10px;
}

.history-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 180px;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #f9fafb;
  text-align: left;
  cursor: pointer;
}

.history-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.history-item strong {
  font-size: 13px;
  color: #111827;
}

.history-item span {
  font-size: 12px;
  color: #6b7280;
}

.history-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.history-rename {
  color: #2563eb;
  font-weight: 600;
}

.history-rerun {
  color: #0f766e;
  font-weight: 600;
}

.history-rerun-new {
  color: #7c3aed;
  font-weight: 600;
}

.history-delete {
  color: #dc2626;
  font-weight: 600;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.card {
  padding: 14px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: white;
  overflow: hidden;
}

.card h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #111827;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.insert-actions {
  display: flex;
  gap: 8px;
}

.report-header h4 {
  margin: 0;
}

.card ol,
.card ul {
  margin: 0;
  padding-left: 18px;
}

.source-list li + li {
  margin-top: 10px;
}

.source-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
}

.citation-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
}

.source-list a {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
}

.local-source-title {
  display: inline-block;
  color: #111827;
  font-weight: 600;
}

.source-list p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.abstract {
  line-height: 1.5;
}

.citation-text {
  font-size: 12px;
  color: #374151;
  font-style: italic;
}

.category-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.category-chip {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 11px;
  font-weight: 600;
}

.source-extra {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
  font-size: 11px;
  color: #6b7280;
}

.source-links {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.source-links a {
  font-size: 12px;
  font-weight: 500;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-left: 0;
  list-style: none;
}

.evidence-item {
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
}

.evidence-claim {
  margin: 0 0 8px;
  color: #1f2937;
  line-height: 1.5;
}

.evidence-citations {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.report-card {
  grid-column: span 1;
}

.answer {
  margin: 0 0 10px;
  white-space: pre-wrap;
  color: #374151;
  line-height: 1.5;
}

pre {
  margin: 10px 0 0;
  padding: 10px;
  background: #f3f4f6;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

@media (max-width: 1100px) {
  .result-grid {
    grid-template-columns: 1fr;
  }

  .phase-list {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .query-row {
    grid-template-columns: 1fr;
  }

  .phase-list {
    grid-template-columns: 1fr;
  }
}
</style>
