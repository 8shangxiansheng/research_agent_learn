import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockStore = {
  currentSession: null as null | { id: number; title: string },
  hasCurrentSession: false,
  currentMessages: [] as Array<{
    id: number
    session_id: number
    role: 'user' | 'assistant'
    content: string
    created_at: string
  }>,
  isStreaming: false,
  streamingContent: '',
  websocketStatus: 'idle' as 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error',
  websocketStatusLabel: '',
  websocketStatusMessage: '',
  sendMessage: vi.fn(),
  retryAssistantMessage: vi.fn(),
}

const mockLocaleStore = {
  t: (key: string) => ({
    'chat.selectSession': 'Select a session',
    'chat.empty': 'Select or create a session to start chatting',
    'chat.placeholder': 'Ask about academic papers, research topics, or concepts...',
    'chat.sendHint': 'Ctrl+Enter to send',
    'chat.send': 'Send',
    'chat.thinking': 'Thinking...',
    'chat.status.connecting': 'Connecting',
    'chat.status.reconnecting': 'Reconnecting',
  }[key] ?? key),
}

vi.mock('@/stores/chat', () => ({
  useChatStore: () => mockStore,
}))

vi.mock('@/stores/locale', () => ({
  useLocaleStore: () => mockLocaleStore,
}))

import ChatInterface from '../ChatInterface.vue'

const ElScrollbarStub = defineComponent({
  template: '<div class="scrollbar-stub"><slot /></div>',
  setup(_, { expose }) {
    expose({
      setScrollTop: vi.fn(),
    })
    return {}
  },
})

const ElInputStub = defineComponent({
  props: {
    modelValue: {
      type: String,
      default: '',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue', 'keydown'],
  template:
    '<textarea data-test="chat-input" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" @keydown="$emit(\'keydown\', $event)" />',
})

const ElButtonStub = defineComponent({
  props: {
    disabled: {
      type: Boolean,
      default: false,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['click'],
  template:
    '<button data-test="send-button" :disabled="disabled || loading" @click="$emit(\'click\')"><slot /></button>',
})

describe('ChatInterface', () => {
  beforeEach(() => {
    mockStore.currentSession = null
    mockStore.hasCurrentSession = false
    mockStore.currentMessages = []
    mockStore.isStreaming = false
    mockStore.streamingContent = ''
    mockStore.websocketStatus = 'idle'
    mockStore.websocketStatusLabel = ''
    mockStore.websocketStatusMessage = ''
    mockStore.sendMessage.mockReset()
    mockStore.retryAssistantMessage.mockReset()
  })

  it('renders empty state when no session is selected', () => {
    const wrapper = mount(ChatInterface, {
      global: {
        stubs: {
          MessageItem: true,
          ElScrollbar: ElScrollbarStub,
          ElInput: ElInputStub,
          ElButton: ElButtonStub,
        },
      },
    })

    expect(wrapper.text()).toContain('Select or create a session to start chatting')
  })

  it('renders localized websocket status when reconnecting', () => {
    mockStore.currentSession = { id: 1, title: 'Research' }
    mockStore.hasCurrentSession = true
    mockStore.websocketStatus = 'reconnecting'
    mockStore.websocketStatusLabel = 'Reconnecting'
    mockStore.websocketStatusMessage = 'Trying to reconnect live response channel (2)'

    const wrapper = mount(ChatInterface, {
      global: {
        stubs: {
          MessageItem: true,
          ElScrollbar: ElScrollbarStub,
          ElInput: ElInputStub,
          ElButton: ElButtonStub,
        },
      },
    })

    expect(wrapper.text()).toContain('Reconnecting')
    expect(wrapper.text()).toContain('Trying to reconnect live response channel (2)')
    expect(wrapper.find('.connection-badge').classes()).toContain('is-reconnecting')
  })

  it('sends trimmed message and clears input', async () => {
    mockStore.currentSession = { id: 1, title: 'Research' }
    mockStore.hasCurrentSession = true

    const wrapper = mount(ChatInterface, {
      global: {
        stubs: {
          MessageItem: true,
          ElScrollbar: ElScrollbarStub,
          ElInput: ElInputStub,
          ElButton: ElButtonStub,
        },
      },
    })

    await wrapper.get('[data-test="chat-input"]').setValue('  hello world  ')
    await wrapper.get('[data-test="send-button"]').trigger('click')
    await nextTick()

    expect(mockStore.sendMessage).toHaveBeenCalledWith('hello world')
    expect((wrapper.get('[data-test="chat-input"]').element as HTMLTextAreaElement).value).toBe('')
  })

  it('retries an assistant message from the message list', async () => {
    mockStore.currentSession = { id: 1, title: 'Research' }
    mockStore.hasCurrentSession = true
    mockStore.currentMessages = [
      {
        id: 99,
        session_id: 1,
        role: 'assistant',
        content: 'Initial answer',
        created_at: '2026-03-18T12:00:00.000Z',
      },
    ]

    const RetryMessageStub = defineComponent({
      emits: ['retry'],
      template: '<button data-test="retry-message" @click="$emit(\'retry\', 99)">Retry</button>',
    })

    const wrapper = mount(ChatInterface, {
      global: {
        stubs: {
          MessageItem: RetryMessageStub,
          ElScrollbar: ElScrollbarStub,
          ElInput: ElInputStub,
          ElButton: ElButtonStub,
        },
      },
    })

    await wrapper.get('[data-test="retry-message"]').trigger('click')

    expect(mockStore.retryAssistantMessage).toHaveBeenCalledWith(99)
  })

  it('only enables retry for the latest assistant message', () => {
    mockStore.currentSession = { id: 1, title: 'Research' }
    mockStore.hasCurrentSession = true
    mockStore.currentMessages = [
      {
        id: 1,
        session_id: 1,
        role: 'assistant',
        content: 'Older answer',
        created_at: '2026-03-18T12:00:00.000Z',
      },
      {
        id: 2,
        session_id: 1,
        role: 'user',
        content: 'follow up',
        created_at: '2026-03-18T12:01:00.000Z',
      },
      {
        id: 3,
        session_id: 1,
        role: 'assistant',
        content: 'Latest answer',
        created_at: '2026-03-18T12:02:00.000Z',
      },
    ]

    const RetryMessageStub = defineComponent({
      props: {
        canRetry: {
          type: Boolean,
          default: false,
        },
      },
      template: '<div class="retry-flag">{{ canRetry ? "yes" : "no" }}</div>',
    })

    const wrapper = mount(ChatInterface, {
      global: {
        stubs: {
          MessageItem: RetryMessageStub,
          ElScrollbar: ElScrollbarStub,
          ElInput: ElInputStub,
          ElButton: ElButtonStub,
        },
      },
    })

    const flags = wrapper.findAll('.retry-flag').map(node => node.text())
    expect(flags).toEqual(['no', 'no', 'yes'])
  })
})
