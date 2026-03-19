import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  mockStore,
  mockLocaleStore,
  messageSuccess,
  messageError,
  promptMock,
  confirmMock,
} = vi.hoisted(() => ({
  mockStore: {
    isLoading: false,
    sessions: [] as Array<{ id: number; title: string; created_at: string }>,
    currentSession: null as null | { id: number },
    fetchSessions: vi.fn(),
    createSession: vi.fn(),
    selectSession: vi.fn(),
    exportCurrentSession: vi.fn(),
    updateSessionTitle: vi.fn(),
    deleteSession: vi.fn(),
    sessionSearchQuery: '',
  },
  mockLocaleStore: {
    dateLocale: 'en-US',
    t: (key: string) => ({
      'session.title': 'Sessions',
      'session.new': 'New',
      'session.searchPlaceholder': 'Search sessions',
      'session.loading': 'Loading...',
      'session.empty': 'No sessions yet',
      'session.emptyFiltered': 'No matching sessions',
      'session.createFirst': 'Create First Session',
      'session.export': 'Export Markdown',
      'session.rename': 'Rename',
      'session.delete': 'Delete',
      'session.created': 'Session created',
      'session.createFailed': 'Failed to create session',
      'session.exported': 'Session exported',
      'session.exportFailed': 'Failed to export session',
      'session.renamed': 'Session renamed',
      'session.deleted': 'Session deleted',
      'session.renamePrompt': 'Enter new title',
      'session.renameTitle': 'Rename Session',
      'session.deletePrompt': 'Delete this session and all its messages?',
      'session.deleteTitle': 'Delete Session',
      'common.cancel': 'Cancel',
    }[key] ?? key),
  },
  messageSuccess: vi.fn(),
  messageError: vi.fn(),
  promptMock: vi.fn(),
  confirmMock: vi.fn(),
}))

vi.mock('@/stores/chat', () => ({
  useChatStore: () => mockStore,
}))

vi.mock('@/stores/locale', () => ({
  useLocaleStore: () => mockLocaleStore,
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: messageSuccess,
      error: messageError,
    },
    ElMessageBox: {
      prompt: promptMock,
      confirm: confirmMock,
    },
  }
})

import SessionList from '../SessionList.vue'

const baseStubs = {
  Plus: true,
  Loading: true,
  ChatLineSquare: true,
  MoreFilled: true,
  Download: true,
  Edit: true,
  Delete: true,
  'el-scrollbar': {
    template: '<div><slot /></div>',
  },
  'el-button': {
    template: '<button @click="$emit(\'click\')"><slot /></button>',
  },
  'el-input': {
    props: {
      modelValue: {
        type: String,
        default: '',
      },
    },
    emits: ['update:modelValue', 'input', 'clear'],
    template:
      '<input data-test="search-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value); $emit(\'input\', $event.target.value)" />',
  },
  'el-dropdown': {
    template: '<div><slot /><slot name="dropdown" /></div>',
  },
  'el-dropdown-menu': {
    template: '<div><slot /></div>',
  },
  'el-dropdown-item': {
    template: '<button><slot /></button>',
  },
}

describe('SessionList', () => {
  beforeEach(() => {
    mockStore.isLoading = false
    mockStore.sessions = []
    mockStore.currentSession = null
    mockStore.sessionSearchQuery = ''
    mockStore.fetchSessions.mockReset()
    mockStore.createSession.mockReset()
    mockStore.selectSession.mockReset()
    mockStore.exportCurrentSession.mockReset()
    messageSuccess.mockReset()
    messageError.mockReset()
  })

  it('fetches sessions on mount and shows empty state', () => {
    const wrapper = mount(SessionList, {
      global: {
        stubs: baseStubs,
      },
    })

    expect(mockStore.fetchSessions).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('No sessions yet')
  })

  it('creates and selects a session from the empty state action', async () => {
    mockStore.createSession.mockResolvedValue({
      id: 1,
      title: 'New Chat',
      created_at: '2026-03-18T12:00:00.000Z',
    })

    const wrapper = mount(SessionList, {
      global: {
        stubs: baseStubs,
      },
    })

    const buttons = wrapper.findAll('button')
    await buttons[1].trigger('click')
    await nextTick()

    expect(mockStore.createSession).toHaveBeenCalled()
    expect(mockStore.selectSession).toHaveBeenCalledWith({
      id: 1,
      title: 'New Chat',
      created_at: '2026-03-18T12:00:00.000Z',
    })
    expect(messageSuccess).toHaveBeenCalledWith('Session created')
  })

  it('filters sessions with the search input', async () => {
    const wrapper = mount(SessionList, {
      global: {
        stubs: baseStubs,
      },
    })

    await wrapper.get('[data-test="search-input"]').setValue('graph')

    expect(mockStore.fetchSessions).toHaveBeenNthCalledWith(1)
    expect(mockStore.fetchSessions).toHaveBeenNthCalledWith(2, 'graph')
  })

  it('exports a session from the command handler', async () => {
    const session = {
      id: 7,
      title: 'Export Me',
      created_at: '2026-03-18T12:00:00.000Z',
    }
    mockStore.sessions = [session]

    const wrapper = mount(SessionList, {
      global: {
        stubs: baseStubs,
      },
    })

    await (wrapper.vm as any).handleCommand('export', session)

    expect(mockStore.exportCurrentSession).toHaveBeenCalledWith(session)
    expect(messageSuccess).toHaveBeenCalledWith('Session exported')
  })
})
