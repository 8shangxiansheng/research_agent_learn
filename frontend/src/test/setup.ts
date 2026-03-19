import { config } from '@vue/test-utils'

config.global.stubs = {
  transition: false,
  'el-icon': {
    template: '<span><slot /></span>',
  },
  ChatLineSquare: true,
  Plus: true,
  Loading: true,
  MoreFilled: true,
  Edit: true,
  Delete: true,
  User: true,
  ChatDotSquare: true,
}
