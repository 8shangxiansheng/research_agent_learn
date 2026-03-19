import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const downloadResearchTaskReportMock = vi.fn()

const mockResearchStore = {
  currentTask: null as null | {
    id: number
    session_id?: number | null
    report_filename: string
    plan: string[]
    sources: Array<{
      source_id: string
      citation_label: string
      arxiv_id?: string
      title: string
      authors: string[]
      url: string
      pdf_url?: string | null
      source_type?: string
      published_at?: string
      categories?: string[]
      primary_category?: string
      journal_ref?: string
      doi?: string
      citation_text?: string
      abstract?: string
    }>
    answer: string
    report_markdown: string
  },
  tasks: [] as Array<{
    id: number
    query: string
    generated_at: string
  }>,
  filteredTasks: [] as Array<{
    id: number
    query: string
    generated_at: string
  }>,
  query: '',
  historyQuery: '',
  isRunning: false,
  isLoadingHistory: false,
  error: null as string | null,
  runTask: vi.fn(),
  fetchTasks: vi.fn(),
  selectTask: vi.fn(),
  renameTask: vi.fn(),
  removeTask: vi.fn(),
  clearTask: vi.fn(),
}

vi.mock('@/stores/research', () => ({
  useResearchStore: () => mockResearchStore,
}))

const mockChatStore = {
  currentSession: null as null | { id: number; title: string },
  appendResearchTask: vi.fn(),
}

vi.mock('@/stores/chat', () => ({
  useChatStore: () => mockChatStore,
}))

vi.mock('@/api/research', () => ({
  downloadResearchTaskReport: (...args: unknown[]) => downloadResearchTaskReportMock(...args),
}))

import ResearchPanel from '../ResearchPanel.vue'

describe('ResearchPanel', () => {
  beforeEach(() => {
    mockResearchStore.currentTask = null
    mockResearchStore.tasks = []
    mockResearchStore.filteredTasks = []
    mockResearchStore.query = ''
    mockResearchStore.historyQuery = ''
    mockResearchStore.isRunning = false
    mockResearchStore.isLoadingHistory = false
    mockResearchStore.error = null
    mockChatStore.currentSession = null
    mockChatStore.appendResearchTask.mockReset()
    mockResearchStore.runTask.mockReset()
    mockResearchStore.fetchTasks.mockReset()
    mockResearchStore.selectTask.mockReset()
    mockResearchStore.renameTask.mockReset()
    mockResearchStore.removeTask.mockReset()
    mockResearchStore.clearTask.mockReset()
    downloadResearchTaskReportMock.mockReset()
  })

  it('runs a research task with trimmed query', async () => {
    mockChatStore.currentSession = { id: 7, title: 'Research Session' }
    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue', 'disabled'],
            emits: ['update:modelValue', 'keydown'],
            template:
              '<input data-test="research-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" @keydown="$emit(\'keydown\', $event)" />',
          },
          'el-button': {
            props: ['disabled', 'loading', 'text'],
            emits: ['click'],
            template: '<button data-test="run-research" :disabled="disabled || loading" @click="$emit(\'click\')"><slot /></button>',
          },
        },
      },
    })

    await wrapper.get('[data-test="research-input"]').setValue('  graph neural networks  ')
    await wrapper.get('[data-test="run-research"]').trigger('click')
    await nextTick()

    expect(mockResearchStore.runTask).toHaveBeenCalledWith('  graph neural networks  ', 7)
  })

  it('renders research results when a task exists', () => {
    mockChatStore.currentSession = { id: 7, title: 'Research Session' }
    mockResearchStore.currentTask = {
      id: 1,
      session_id: 7,
      report_filename: 'graph-neural-networks.md',
      plan: ['step one', 'step two'],
      sources: [
        {
          source_id: 'arxiv-1',
          citation_label: 'S1',
          arxiv_id: '2401.12345',
          title: 'Paper Title',
          authors: ['Author A', 'Author B'],
          url: 'https://example.com/paper',
          pdf_url: 'https://example.com/paper.pdf',
          source_type: 'arxiv',
          published_at: '2026-03-19T00:00:00Z',
          primary_category: 'cs.AI',
          categories: ['cs.AI', 'cs.LG'],
          journal_ref: 'NeurIPS 2025',
          doi: '10.1000/test-doi',
          citation_text: 'Author A, Author B (2026). Paper Title. NeurIPS 2025. DOI: 10.1000/test-doi',
          abstract: 'A concise abstract.',
        },
      ],
      answer: 'Structured answer',
      report_markdown: '# Report',
    }

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': true,
          'el-button': {
            template: '<button><slot /></button>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('step one')
    expect(wrapper.text()).toContain('Paper Title')
    expect(wrapper.text()).toContain('Structured answer')
    expect(wrapper.text()).toContain('View Markdown report')
    expect(wrapper.text()).toContain('[S1]')
    expect(wrapper.text()).toContain('cs.AI')
    expect(wrapper.text()).toContain('arXiv: 2401.12345')
    expect(wrapper.text()).toContain('DOI: 10.1000/test-doi')
    expect(wrapper.text()).toContain('NeurIPS 2025')
  })

  it('exports the markdown report through the backend download endpoint', async () => {
    mockChatStore.currentSession = { id: 7, title: 'Research Session' }
    const clickMock = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    const originalCreateObjectURL = URL.createObjectURL
    const originalRevokeObjectURL = URL.revokeObjectURL
    URL.createObjectURL = vi.fn(() => 'blob:mock')
    URL.revokeObjectURL = vi.fn()
    downloadResearchTaskReportMock.mockResolvedValue({
      blob: new Blob(['# Report'], { type: 'text/markdown;charset=utf-8' }),
      filename: 'graph-neural-networks.md',
    })
    const appendMock = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return {
          click: clickMock,
          set href(_value: string) {},
          set download(_value: string) {},
        } as unknown as HTMLElement
      }
      return originalCreateElement(tagName)
    })

    mockResearchStore.currentTask = {
      id: 1,
      session_id: 7,
      report_filename: 'graph-neural-networks.md',
      plan: ['step one'],
      sources: [],
      answer: 'Structured answer',
      report_markdown: '# Report',
    }

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': true,
          'el-button': {
            props: ['disabled', 'loading', 'text'],
            emits: ['click'],
            template: '<button data-test="generic-button" @click="$emit(\'click\')"><slot /></button>',
          },
        },
      },
    })

    const exportButton = wrapper.findAll('[data-test="generic-button"]').find(node => node.text() === 'Export Report')
    expect(exportButton).toBeDefined()
    await exportButton!.trigger('click')
    await nextTick()

    expect(downloadResearchTaskReportMock).toHaveBeenCalledWith(1)
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(clickMock).toHaveBeenCalled()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock')

    appendMock.mockRestore()
    URL.createObjectURL = originalCreateObjectURL
    URL.revokeObjectURL = originalRevokeObjectURL
  })

  it('fetches and renders research history for the active session', async () => {
    mockChatStore.currentSession = { id: 3, title: 'Session 3' }
    mockResearchStore.tasks = [
      {
        id: 9,
        query: 'attention mechanisms',
        generated_at: '2026-03-19T10:00:00Z',
      },
    ]
    mockResearchStore.filteredTasks = mockResearchStore.tasks

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input data-test="history-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': {
            template: '<button><slot /></button>',
          },
        },
      },
    })

    await nextTick()

    expect(mockResearchStore.fetchTasks).toHaveBeenCalledWith(3)
    expect(wrapper.text()).toContain('Research History')
    expect(wrapper.text()).toContain('attention mechanisms')

    await wrapper.get('.history-item').trigger('click')
    expect(mockResearchStore.selectTask).toHaveBeenCalledWith(mockResearchStore.tasks[0])
  })

  it('deletes a task from research history', async () => {
    mockChatStore.currentSession = { id: 3, title: 'Session 3' }
    mockResearchStore.tasks = [
      {
        id: 9,
        query: 'attention mechanisms',
        generated_at: '2026-03-19T10:00:00Z',
      },
    ]
    mockResearchStore.filteredTasks = mockResearchStore.tasks

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input data-test="history-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': {
            template: '<button><slot /></button>',
          },
        },
      },
    })

    await wrapper.get('.history-delete').trigger('click')
    expect(mockResearchStore.removeTask).toHaveBeenCalledWith(9)
  })

  it('renames a task from research history', async () => {
    mockChatStore.currentSession = { id: 3, title: 'Session 3' }
    mockResearchStore.tasks = [
      {
        id: 9,
        query: 'attention mechanisms',
        generated_at: '2026-03-19T10:00:00Z',
      },
    ]
    mockResearchStore.filteredTasks = mockResearchStore.tasks
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('transformer scaling laws')

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input data-test="history-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': {
            template: '<button><slot /></button>',
          },
        },
      },
    })

    await wrapper.get('.history-rename').trigger('click')
    expect(promptSpy).toHaveBeenCalledWith('Rename research task', 'attention mechanisms')
    expect(mockResearchStore.renameTask).toHaveBeenCalledWith(9, 'transformer scaling laws')
    promptSpy.mockRestore()
  })

  it('inserts the selected research brief into chat with summary mode', async () => {
    mockChatStore.currentSession = { id: 7, title: 'Research Session' }
    mockResearchStore.currentTask = {
      id: 11,
      session_id: 7,
      report_filename: 'graph-neural-networks.md',
      plan: ['step one'],
      sources: [],
      answer: 'Structured answer',
      report_markdown: '# Report',
    }

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': true,
          'el-button': {
            props: ['disabled', 'loading', 'text', 'size'],
            emits: ['click'],
            template: '<button data-test="generic-button" @click="$emit(\'click\')"><slot /></button>',
          },
        },
      },
    })

    const insertButton = wrapper.findAll('[data-test="generic-button"]').find(node => node.text() === 'Insert Summary')
    expect(insertButton).toBeDefined()
    await insertButton!.trigger('click')

    expect(mockChatStore.appendResearchTask).toHaveBeenCalledWith(11, 'summary')
  })

  it('inserts the selected research brief into chat with full mode', async () => {
    mockChatStore.currentSession = { id: 7, title: 'Research Session' }
    mockResearchStore.currentTask = {
      id: 11,
      session_id: 7,
      report_filename: 'graph-neural-networks.md',
      plan: ['step one'],
      sources: [],
      answer: 'Structured answer',
      report_markdown: '# Report',
    }

    const wrapper = mount(ResearchPanel, {
      global: {
        stubs: {
          'el-input': true,
          'el-button': {
            props: ['disabled', 'loading', 'text', 'size'],
            emits: ['click'],
            template: '<button data-test="generic-button" @click="$emit(\'click\')"><slot /></button>',
          },
        },
      },
    })

    const insertButton = wrapper.findAll('[data-test="generic-button"]').find(node => node.text() === 'Insert Full')
    expect(insertButton).toBeDefined()
    await insertButton!.trigger('click')

    expect(mockChatStore.appendResearchTask).toHaveBeenCalledWith(11, 'full')
  })
})
