import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
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
app.use(ElementPlus)
app.mount('#app')
