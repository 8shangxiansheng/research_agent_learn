import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import App from './App.vue'

describe('App locale toggle', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('toggles between English and Chinese in the header', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [pinia],
        stubs: {
          'el-container': { template: '<div><slot /></div>' },
          'el-header': { template: '<div><slot /></div>' },
          'el-main': { template: '<div><slot /></div>' },
          Home: {
            template: '<div />',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Academic Q&A Agent')
    expect(wrapper.text()).toContain('Language · 中文')

    await wrapper.get('.locale-toggle').trigger('click')

    expect(wrapper.text()).toContain('学术问答助手')
    expect(wrapper.text()).toContain('语言 · EN')
  })
})
