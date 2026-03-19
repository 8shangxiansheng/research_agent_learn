import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { ElAvatar } from 'element-plus/es/components/avatar/index'
import { ElButton } from 'element-plus/es/components/button/index'
import { ElAside, ElContainer, ElMain } from 'element-plus/es/components/container/index'
import { ElDropdown, ElDropdownItem, ElDropdownMenu } from 'element-plus/es/components/dropdown/index'
import { ElIcon } from 'element-plus/es/components/icon/index'
import { ElInput } from 'element-plus/es/components/input/index'
import { ElScrollbar } from 'element-plus/es/components/scrollbar/index'
import 'element-plus/es/components/aside/style/css'
import 'element-plus/es/components/avatar/style/css'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/container/style/css'
import 'element-plus/es/components/dropdown/style/css'
import 'element-plus/es/components/dropdown-item/style/css'
import 'element-plus/es/components/dropdown-menu/style/css'
import 'element-plus/es/components/icon/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/main/style/css'
import 'element-plus/es/components/scrollbar/style/css'
import {
  ChatLineSquare,
  Download,
  Delete,
  Edit,
  Loading,
  MoreFilled,
  Plus,
  RefreshRight,
} from '@element-plus/icons-vue'

import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.component('Plus', Plus)
app.component('Loading', Loading)
app.component('ChatLineSquare', ChatLineSquare)
app.component('MoreFilled', MoreFilled)
app.component('Edit', Edit)
app.component('Delete', Delete)
app.component('Download', Download)
app.component('RefreshRight', RefreshRight)

app.use(pinia)
app.use(ElContainer)
app.use(ElAside)
app.use(ElMain)
app.use(ElButton)
app.use(ElInput)
app.use(ElScrollbar)
app.use(ElIcon)
app.use(ElAvatar)
app.use(ElDropdown)
app.use(ElDropdownMenu)
app.use(ElDropdownItem)
app.mount('#app')
