import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MessageItem from '../MessageItem.vue'

describe('MessageItem', () => {
  it('renders markdown content and assistant label', () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: {
          id: 1,
          session_id: 1,
          role: 'assistant',
          content: '**Bold** [paper](https://example.com)',
          created_at: '2026-03-18T12:00:00.000Z',
        },
      },
      global: {
        stubs: {
          RefreshRight: true,
          'el-avatar': {
            template: '<div class="avatar-stub" />',
          },
          'el-button': {
            template: '<button><slot /></button>',
          },
          'el-icon': {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Assistant')
    expect(wrapper.html()).toContain('<strong>Bold</strong>')
    expect(wrapper.html()).toContain('href="https://example.com"')
  })

  it('emits retry for assistant messages', async () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: {
          id: 42,
          session_id: 1,
          role: 'assistant',
          content: 'retry me',
          created_at: '2026-03-18T12:00:00.000Z',
        },
      },
      global: {
        stubs: {
          RefreshRight: true,
          'el-avatar': {
            template: '<div class="avatar-stub" />',
          },
          'el-button': {
            template: '<button data-test="retry-button" @click="$emit(\'click\')"><slot /></button>',
          },
          'el-icon': {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    await wrapper.get('[data-test="retry-button"]').trigger('click')

    expect(wrapper.emitted('retry')?.[0]).toEqual([42])
  })

  it('does not render retry button when canRetry is false', () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: {
          id: 42,
          session_id: 1,
          role: 'assistant',
          content: 'retry me',
          created_at: '2026-03-18T12:00:00.000Z',
        },
        canRetry: false,
      },
      global: {
        stubs: {
          RefreshRight: true,
          'el-avatar': {
            template: '<div class="avatar-stub" />',
          },
          'el-button': {
            template: '<button data-test="retry-button" @click="$emit(\'click\')"><slot /></button>',
          },
          'el-icon': {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    expect(wrapper.find('[data-test="retry-button"]').exists()).toBe(false)
  })

  it('renders a research badge for injected research brief messages', () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: {
          id: 77,
          session_id: 1,
          role: 'assistant',
          content: '## Research Brief: transformers\n\nSummary here.',
          created_at: '2026-03-18T12:00:00.000Z',
        },
      },
      global: {
        stubs: {
          RefreshRight: true,
          'el-avatar': {
            template: '<div class="avatar-stub" />',
          },
          'el-button': {
            template: '<button><slot /></button>',
          },
          'el-icon': {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Research')
    expect(wrapper.find('.message-badge').exists()).toBe(true)
  })

  it('allows long research brief messages to collapse and expand', async () => {
    const longContent = '# Research Brief\n\n' + 'Long line. '.repeat(120)
    const wrapper = mount(MessageItem, {
      props: {
        message: {
          id: 88,
          session_id: 1,
          role: 'assistant',
          content: longContent,
          created_at: '2026-03-18T12:00:00.000Z',
        },
      },
      global: {
        stubs: {
          RefreshRight: true,
          'el-avatar': {
            template: '<div class="avatar-stub" />',
          },
          'el-button': {
            template: '<button><slot /></button>',
          },
          'el-icon': {
            template: '<span><slot /></span>',
          },
        },
      },
    })

    expect(wrapper.find('.collapse-toggle').exists()).toBe(true)
    expect(wrapper.find('.message-text').classes()).toContain('collapsed')
    expect(wrapper.find('.collapse-toggle').text()).toBe('Expand')

    await wrapper.get('.collapse-toggle').trigger('click')

    expect(wrapper.find('.message-text').classes()).not.toContain('collapsed')
    expect(wrapper.find('.collapse-toggle').text()).toBe('Collapse')
  })
})
