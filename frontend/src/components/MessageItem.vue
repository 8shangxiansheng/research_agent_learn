<template>
  <div class="message-item" :class="[message.role]">
    <div class="message-avatar">
      <el-avatar :size="36" :icon="message.role === 'user' ? User : ChatDotSquare" />
    </div>
    <div class="message-content">
      <div class="message-header">
        <span class="message-role">{{ message.role === 'user' ? 'You' : 'Assistant' }}</span>
        <span class="message-time">{{ formatTime(message.created_at) }}</span>
        <el-button
          v-if="message.role === 'assistant' && props.canRetry !== false"
          class="retry-button"
          link
          size="small"
          @click="$emit('retry', message.id)"
        >
          <el-icon><RefreshRight /></el-icon>
          Retry
        </el-button>
      </div>
      <div class="message-text" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import { ChatDotSquare, User } from '@element-plus/icons-vue'
import type { Message } from '@/api/sessions'

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

const renderedContent = computed(() => {
  return md.render(props.message.content)
})

function formatTime(date: string): string {
  const d = new Date(date)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
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
