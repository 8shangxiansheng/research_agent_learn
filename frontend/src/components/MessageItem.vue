<template>
  <div class="message-item" :class="[message.role, { research: isResearchMessage }]">
    <div class="message-avatar">
      <el-avatar :size="36" :icon="message.role === 'user' ? User : ChatDotSquare" />
    </div>
    <div class="message-content">
      <div class="message-header">
        <span class="message-role">{{ message.role === 'user' ? localeStore.t('message.you') : localeStore.t('message.assistant') }}</span>
        <span v-if="isResearchMessage" class="message-badge">{{ localeStore.t('message.research') }}</span>
        <span class="message-time">{{ formatTime(message.created_at) }}</span>
        <el-button
          v-if="message.role === 'assistant' && props.canRetry !== false"
          class="retry-button"
          link
          size="small"
          @click="$emit('retry', message.id)"
        >
          <el-icon><RefreshRight /></el-icon>
          {{ localeStore.t('message.retry') }}
        </el-button>
      </div>
      <div
        class="message-text"
        :class="{ collapsed: showCollapseToggle && !isExpanded }"
        v-html="renderedContent"
      ></div>
      <button
        v-if="showCollapseToggle"
        type="button"
        class="collapse-toggle"
        @click="isExpanded = !isExpanded"
      >
        {{ isExpanded ? localeStore.t('message.collapse') : localeStore.t('message.expand') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import { ChatDotSquare, User } from '@element-plus/icons-vue'
import type { Message } from '@/api/sessions'
import { useLocaleStore } from '@/stores/locale'
import { formatMessageTime } from '@/utils/localization'

const props = withDefaults(defineProps<{
  message: Message
  canRetry?: boolean
}>(), {
  canRetry: true,
})

defineEmits<{
  retry: [messageId: number]
}>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
})
const localeStore = useLocaleStore()

const renderedContent = computed(() => {
  return md.render(props.message.content)
})

const isExpanded = ref(false)

const isResearchMessage = computed(() => {
  if (props.message.role !== 'assistant') {
    return false
  }

  const content = props.message.content.trimStart()
  return content.startsWith('## Research Brief:') || content.startsWith('# Research Brief')
})

const showCollapseToggle = computed(() => {
  if (!isResearchMessage.value) {
    return false
  }

  const content = props.message.content.trimStart()
  return content.startsWith('# Research Brief') || content.length > 500
})

function formatTime(date: string): string {
  return formatMessageTime(date, localeStore)
}
</script>

<style scoped>
.message-item {
  display: flex;
  gap: 12px;
  padding: 15px 20px;
  margin: 10px 0;
  border-radius: 10px;
}

.message-item.user {
  background: #f0f7ff;
  flex-direction: row-reverse;
}

.message-item.assistant {
  background: #f5f7fa;
}

.message-item.assistant.research {
  background: linear-gradient(180deg, #f3f7ff 0%, #f8fafc 100%);
  border: 1px solid #dbeafe;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.message-role {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.message-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.message-time {
  font-size: 12px;
  color: #909399;
}

.retry-button {
  margin-left: auto;
}

.message-text {
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
  overflow-wrap: break-word;
}

.message-text.collapsed {
  max-height: 220px;
  overflow: hidden;
  position: relative;
}

.message-text.collapsed::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 56px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, rgba(248, 250, 252, 0.96) 100%);
}

.collapse-toggle {
  margin-top: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.message-text :deep(p) {
  margin: 0 0 10px 0;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 15px;
  border-radius: 5px;
  overflow-x: auto;
  margin: 10px 0;
}

.message-text :deep(code) {
  background: #e4e7ed;
  padding: 2px 5px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
}

.message-text :deep(pre code) {
  background: transparent;
  padding: 0;
}

.message-text :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}
</style>
