<template>
  <section class="research-panel">
    <div class="panel-header">
      <div>
        <h3>Deep Research</h3>
        <p>Run a structured literature scan and generate a concise research brief.</p>
      </div>
      <div class="panel-actions">
        <el-button
          v-if="researchStore.currentTask"
          text
          @click="exportReport"
        >
          Export Report
        </el-button>
        <el-button
          v-if="researchStore.currentTask"
          text
          @click="researchStore.clearTask()"
        >
          Clear
        </el-button>
      </div>
    </div>

    <div class="query-row">
      <el-input
        v-model="query"
        placeholder="Enter a research topic or question"
        :disabled="researchStore.isRunning"
        @keydown.enter.prevent="handleRun"
      />
      <el-button
        type="primary"
        :loading="researchStore.isRunning"
        :disabled="!query.trim()"
        @click="handleRun"
      >
        {{ researchStore.isRunning ? 'Researching...' : 'Run Research' }}
      </el-button>
    </div>

    <p v-if="researchStore.error" class="error-text">{{ researchStore.error }}</p>

    <section v-if="chatStore.currentSession" class="history-strip">
      <div class="history-header">
        <h4>Research History</h4>
        <span v-if="researchStore.isLoadingHistory">Loading...</span>
      </div>
      <el-input
        v-model="researchStore.historyQuery"
        class="history-search"
        placeholder="Search research history"
        clearable
      />
      <div v-if="researchStore.filteredTasks.length === 0" class="history-empty">
        No research tasks for this session yet.
      </div>
      <div v-else class="history-list">
        <button
          v-for="task in researchStore.filteredTasks"
          :key="task.id"
          type="button"
          :class="['history-item', { active: researchStore.currentTask?.id === task.id }]"
          @click="researchStore.selectTask(task)"
        >
          <strong>{{ task.query }}</strong>
          <div class="history-item-row">
            <span>{{ task.generated_at.slice(0, 10) }}</span>
            <span
              class="history-rerun"
              @click.stop="rerunTask(task.id)"
            >
              Rerun
            </span>
            <span
              class="history-rerun-new"
              @click.stop="rerunTaskAsNew(task.id)"
            >
              Rerun New
            </span>
            <span
              class="history-rename"
              @click.stop="renameTask(task.id, task.query)"
            >
              Rename
            </span>
            <span
              class="history-delete"
              @click.stop="removeTask(task.id)"
            >
              Delete
            </span>
          </div>
        </button>
      </div>
    </section>

    <div v-if="researchStore.currentTask" class="result-grid">
      <section class="card">
        <h4>Plan</h4>
        <ol>
          <li v-for="step in researchStore.currentTask.plan" :key="step">{{ step }}</li>
        </ol>
      </section>

      <section class="card">
        <h4>Sources</h4>
        <ul class="source-list">
          <li v-for="source in researchStore.currentTask.sources" :key="source.source_id">
            <div class="source-meta">
              <span class="citation-chip">[{{ source.citation_label }}]</span>
              <span>{{ source.source_type }}</span>
              <span>{{ source.published_at.slice(0, 10) }}</span>
              <span v-if="source.primary_category">{{ source.primary_category }}</span>
            </div>
            <a :href="source.url" target="_blank" rel="noreferrer">{{ source.title }}</a>
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
              <a :href="source.url" target="_blank" rel="noreferrer">Abstract</a>
              <a v-if="source.pdf_url" :href="source.pdf_url" target="_blank" rel="noreferrer">PDF</a>
            </div>
          </li>
        </ul>
      </section>

      <section class="card report-card">
        <div class="report-header">
          <h4>Research Brief</h4>
          <div
            v-if="researchStore.currentTask && chatStore.currentSession"
            class="insert-actions"
          >
            <el-button
              size="small"
              @click="insertIntoChat('summary')"
            >
              Insert Summary
            </el-button>
            <el-button
              size="small"
              @click="insertIntoChat('full')"
            >
              Insert Full
            </el-button>
          </div>
        </div>
        <p class="answer">{{ researchStore.currentTask.answer }}</p>
        <details>
          <summary>View Markdown report</summary>
          <pre>{{ researchStore.currentTask.report_markdown }}</pre>
        </details>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import { downloadResearchTaskReport } from '@/api/research'
import { useChatStore } from '@/stores/chat'
import { useResearchStore } from '@/stores/research'

const chatStore = useChatStore()
const researchStore = useResearchStore()
const query = ref(researchStore.query)

async function handleRun(): Promise<void> {
  await researchStore.runTask(query.value, chatStore.currentSession?.id)
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

async function renameTask(taskId: number, currentQuery: string): Promise<void> {
  const nextQuery = window.prompt('Rename research task', currentQuery)
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

.history-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
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
}

@media (max-width: 720px) {
  .query-row {
    grid-template-columns: 1fr;
  }
}
</style>
