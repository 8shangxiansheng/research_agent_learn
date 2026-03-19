<template>
  <div class="session-list">
    <div class="session-header">
      <h3>{{ localeStore.t('session.title') }}</h3>
      <el-button type="primary" size="small" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        {{ localeStore.t('session.new') }}
      </el-button>
    </div>

    <div class="session-search">
      <el-input
        v-model="searchQuery"
        clearable
        :placeholder="localeStore.t('session.searchPlaceholder')"
        @input="handleSearch"
        @clear="handleSearch"
      />
    </div>

    <el-scrollbar class="session-scroll">
      <div v-if="chatStore.isLoading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        {{ localeStore.t('session.loading') }}
      </div>

      <div v-else-if="chatStore.sessions.length === 0" class="empty">
        <el-icon><ChatLineSquare /></el-icon>
        <p>{{ searchQuery ? localeStore.t('session.emptyFiltered') : localeStore.t('session.empty') }}</p>
        <el-button type="primary" size="small" @click="handleCreate">
          {{ localeStore.t('session.createFirst') }}
        </el-button>
      </div>

      <div v-else class="session-items">
        <div
          v-for="session in chatStore.sessions"
          :key="session.id"
          :class="['session-item', { active: chatStore.currentSession?.id === session.id }]"
          @click="handleSelect(session)"
        >
          <div class="session-info">
            <span class="session-title">{{ session.title }}</span>
            <span class="session-date">{{ formatDate(session.created_at) }}</span>
          </div>
          <el-dropdown trigger="click" @command="(cmd: string) => handleCommand(cmd, session)">
            <el-button link size="small" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export">
                  <el-icon><Download /></el-icon> {{ localeStore.t('session.export') }}
                </el-dropdown-item>
                <el-dropdown-item command="rename">
                  <el-icon><Edit /></el-icon> {{ localeStore.t('session.rename') }}
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon><Delete /></el-icon> {{ localeStore.t('session.delete') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useLocaleStore } from '@/stores/locale'
import type { Session } from '@/api/sessions'
import { formatSessionDate } from '@/utils/localization'

const chatStore = useChatStore()
const localeStore = useLocaleStore()
const searchQuery = ref(chatStore.sessionSearchQuery)

onMounted(() => {
  chatStore.fetchSessions()
})

function formatDate(date: string): string {
  return formatSessionDate(date, localeStore)
}

function handleSearch(): void {
  chatStore.fetchSessions(searchQuery.value)
}

async function handleCreate(): Promise<void> {
  try {
    const session = await chatStore.createSession()
    chatStore.selectSession(session)
    ElMessage.success(localeStore.t('session.created'))
  } catch {
    ElMessage.error(localeStore.t('session.createFailed'))
  }
}

function handleSelect(session: Session): void {
  chatStore.selectSession(session)
}

async function handleCommand(command: string, session: Session): Promise<void> {
  if (command === 'export') {
    try {
      await chatStore.exportCurrentSession(session)
      ElMessage.success(localeStore.t('session.exported'))
    } catch {
      ElMessage.error(localeStore.t('session.exportFailed'))
    }
  } else if (command === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt(
        localeStore.t('session.renamePrompt'),
        localeStore.t('session.renameTitle'),
        {
          inputValue: session.title,
          confirmButtonText: localeStore.t('session.rename'),
          cancelButtonText: localeStore.t('common.cancel')
        }
      )
      if (value) {
        await chatStore.updateSessionTitle(session.id, value)
        ElMessage.success(localeStore.t('session.renamed'))
      }
    } catch {
      // Cancelled
    }
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        localeStore.t('session.deletePrompt'),
        localeStore.t('session.deleteTitle'),
        {
          confirmButtonText: localeStore.t('session.delete'),
          cancelButtonText: localeStore.t('common.cancel'),
          type: 'warning'
        }
      )
      await chatStore.deleteSession(session.id)
      ElMessage.success(localeStore.t('session.deleted'))
    } catch {
      // Cancelled
    }
  }
}
</script>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
}

.session-search {
  padding: 0 15px 12px;
  border-bottom: 1px solid #e4e7ed;
}

.session-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.session-scroll {
  flex: 1;
  overflow: hidden;
}

.loading, .empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  color: #909399;
}

.empty p {
  margin: 10px 0;
}

.session-items {
  padding: 10px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 5px;
  transition: all 0.2s;
}

.session-item:hover {
  background: #e6e8eb;
}

.session-item.active {
  background: #e6f0ff;
  border-left: 3px solid #409eff;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.session-title {
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-date {
  font-size: 12px;
  color: #909399;
}
</style>
