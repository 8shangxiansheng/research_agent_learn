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
})
