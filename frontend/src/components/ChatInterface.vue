<template>
  <div class="chat-interface">
    <div class="chat-header">
      <div class="chat-title-row">
        <h2>{{ chatStore.currentSession?.title || localeStore.t('chat.selectSession') }}</h2>
        <span
          v-if="chatStore.websocketStatus !== 'idle' && chatStore.hasCurrentSession"
          :class="['connection-badge', `is-${chatStore.websocketStatus}`]"
        >
          {{ chatStore.websocketStatusLabel }}
        </span>
      </div>
      <p
        v-if="chatStore.websocketStatus !== 'idle' && chatStore.hasCurrentSession"
        class="connection-message"
      >
        {{ chatStore.websocketStatusMessage }}
      </p>
    </div>

    <div v-if="!chatStore.hasCurrentSession" class="no-session">
      <el-icon :size="60"><ChatLineSquare /></el-icon>
      <p>{{ localeStore.t('chat.empty') }}</p>
    </div>

    <template v-else>
      <el-scrollbar ref="scrollbarRef" class="message-list">
        <div class="messages-container">
          <MessageItem
            v-for="message in chatStore.currentMessages"
            :key="message.id"
            :message="message"
            :can-retry="isLatestAssistantMessage(message.id)"
            @retry="handleRetry"
          />
          <div v-if="chatStore.isStreaming" class="streaming-message">
            <MessageItem
              :message="{
                id: -1,
                session_id: chatStore.currentSession!.id,
                role: 'assistant',
                content: chatStore.streamingContent,
                created_at: new Date().toISOString()
              }"
            />
          </div>
        </div>
      </el-scrollbar>

      <div class="input-area">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          :placeholder="localeStore.t('chat.placeholder')"
          :disabled="chatStore.isStreaming"
          @keydown.enter.ctrl="handleSend"
        />
        <div class="input-actions">
          <span class="hint">{{ localeStore.t('chat.sendHint') }}</span>
          <el-button
            type="primary"
            :loading="chatStore.isStreaming"
            :disabled="!inputMessage.trim()"
            @click="handleSend"
          >
            {{ chatStore.isStreaming ? localeStore.t('chat.thinking') : localeStore.t('chat.send') }}
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { ElScrollbar } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useLocaleStore } from '@/stores/locale'
import MessageItem from './MessageItem.vue'

const chatStore = useChatStore()
const localeStore = useLocaleStore()

const inputMessage = ref('')
const scrollbarRef = ref<InstanceType<typeof ElScrollbar>>()

function isLatestAssistantMessage(messageId: number): boolean {
  for (let index = chatStore.currentMessages.length - 1; index >= 0; index -= 1) {
    const message = chatStore.currentMessages[index]
    if (message.role === 'assistant') {
      return message.id === messageId
    }
  }
  return false
}

function handleSend(): void {
  const content = inputMessage.value.trim()
  if (!content || chatStore.isStreaming) return

  chatStore.sendMessage(content)
  inputMessage.value = ''

  // Scroll to bottom
  nextTick(() => {
    scrollToBottom()
  })
}

async function handleRetry(messageId: number): Promise<void> {
  if (chatStore.isStreaming) return

  await chatStore.retryAssistantMessage(messageId)

  nextTick(() => {
    scrollToBottom()
  })
}

function scrollToBottom(): void {
  if (scrollbarRef.value) {
    scrollbarRef.value.setScrollTop(999999)
  }
}

// Watch for new messages to scroll
watch(
  () => chatStore.currentMessages.length,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  }
)

// Watch for streaming content to scroll
watch(
  () => chatStore.streamingContent,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  }
)
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.chat-header {
  padding: 15px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.chat-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chat-header h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.connection-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.connection-badge.is-connecting,
.connection-badge.is-reconnecting {
  background: #fef3c7;
  color: #92400e;
}

.connection-badge.is-connected {
  background: #dcfce7;
  color: #166534;
}

.connection-badge.is-disconnected,
.connection-badge.is-error {
  background: #fee2e2;
  color: #991b1b;
}

.connection-message {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.no-session {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.no-session p {
  margin-top: 15px;
  font-size: 16px;
}

.message-list {
  flex: 1;
  overflow: hidden;
}

.messages-container {
  padding: 20px;
  min-height: 100%;
}

.streaming-message {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.input-area {
  padding: 15px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.hint {
  font-size: 12px;
  color: #909399;
}
</style>
