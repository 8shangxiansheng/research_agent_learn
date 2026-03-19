import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export type AppLocale = 'en' | 'zh'

const STORAGE_KEY = 'academic-qa-locale'

const messages = {
  en: {
    'app.title': 'Academic Q&A Agent',
    'app.subtitle': 'AI-powered academic paper research assistant',
    'app.language': 'Language',
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
    'chat.selectSession': 'Select a session',
    'chat.empty': 'Select or create a session to start chatting',
    'chat.placeholder': 'Ask about academic papers, research topics, or concepts...',
    'chat.sendHint': 'Ctrl+Enter to send',
    'chat.send': 'Send',
    'chat.thinking': 'Thinking...',
    'message.you': 'You',
    'message.assistant': 'Assistant',
    'message.research': 'Research',
    'message.retry': 'Retry',
    'message.expand': 'Expand',
    'message.collapse': 'Collapse',
    'research.title': 'Deep Research',
    'research.description': 'Run a structured literature scan and generate a concise research brief.',
    'research.exportReport': 'Export Report',
    'research.clear': 'Clear',
    'research.queryPlaceholder': 'Enter a research topic or question',
    'research.run': 'Run Research',
    'research.running': 'Researching...',
    'research.history': 'Research History',
    'research.loading': 'Loading...',
    'research.historySearch': 'Search research history',
    'research.historyEmpty': 'No research tasks for this session yet.',
    'research.rerun': 'Rerun',
    'research.rerunNew': 'Rerun New',
    'research.rename': 'Rename',
    'research.delete': 'Delete',
    'research.plan': 'Plan',
    'research.sources': 'Sources',
    'research.answer': 'Research Answer',
    'research.insertSummary': 'Insert Summary',
    'research.insertFull': 'Insert Full',
    'research.viewMarkdown': 'View Markdown report',
    'research.abstract': 'Abstract',
    'research.renamePrompt': 'Rename research task',
  },
  zh: {
    'app.title': '学术问答助手',
    'app.subtitle': '由 AI 驱动的学术论文研究助手',
    'app.language': '语言',
    'session.title': '会话',
    'session.new': '新建',
    'session.searchPlaceholder': '搜索会话',
    'session.loading': '加载中...',
    'session.empty': '还没有会话',
    'session.emptyFiltered': '没有匹配的会话',
    'session.createFirst': '创建第一个会话',
    'session.export': '导出 Markdown',
    'session.rename': '重命名',
    'session.delete': '删除',
    'session.created': '会话已创建',
    'session.createFailed': '创建会话失败',
    'session.exported': '会话已导出',
    'session.exportFailed': '导出会话失败',
    'session.renamed': '会话已重命名',
    'session.deleted': '会话已删除',
    'session.renamePrompt': '输入新标题',
    'session.renameTitle': '重命名会话',
    'session.deletePrompt': '删除该会话及其全部消息？',
    'session.deleteTitle': '删除会话',
    'common.cancel': '取消',
    'chat.selectSession': '选择一个会话',
    'chat.empty': '请选择或创建一个会话后开始聊天',
    'chat.placeholder': '输入论文、研究主题或学术概念相关问题...',
    'chat.sendHint': '按 Ctrl+Enter 发送',
    'chat.send': '发送',
    'chat.thinking': '思考中...',
    'message.you': '你',
    'message.assistant': '助手',
    'message.research': '研究',
    'message.retry': '重试',
    'message.expand': '展开',
    'message.collapse': '收起',
    'research.title': '深度研究',
    'research.description': '运行结构化文献扫描，并生成简明研究摘要。',
    'research.exportReport': '导出报告',
    'research.clear': '清空',
    'research.queryPlaceholder': '输入研究主题或问题',
    'research.run': '开始研究',
    'research.running': '研究中...',
    'research.history': '研究历史',
    'research.loading': '加载中...',
    'research.historySearch': '搜索研究历史',
    'research.historyEmpty': '当前会话还没有研究任务。',
    'research.rerun': '重跑',
    'research.rerunNew': '另存后重跑',
    'research.rename': '重命名',
    'research.delete': '删除',
    'research.plan': '计划',
    'research.sources': '来源',
    'research.answer': '研究结论',
    'research.insertSummary': '插入摘要',
    'research.insertFull': '插入全文',
    'research.viewMarkdown': '查看 Markdown 报告',
    'research.abstract': '摘要',
    'research.renamePrompt': '重命名研究任务',
  },
} as const

type TranslationKey = keyof typeof messages.en

function getBrowserLocale(): AppLocale {
  if (typeof navigator === 'undefined') {
    return 'en'
  }
  return navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en'
}

function getStorage(): Pick<Storage, 'getItem' | 'setItem'> | null {
  if (typeof window === 'undefined') {
    return null
  }

  const storage = window.localStorage as Partial<Storage>
  if (typeof storage?.getItem !== 'function' || typeof storage?.setItem !== 'function') {
    return null
  }

  return {
    getItem: storage.getItem.bind(window.localStorage),
    setItem: storage.setItem.bind(window.localStorage),
  }
}

function getStoredLocale(): AppLocale {
  const storage = getStorage()
  const stored = storage?.getItem(STORAGE_KEY)
  if (stored === 'en' || stored === 'zh') {
    return stored
  }

  return getBrowserLocale()
}

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<AppLocale>(getStoredLocale())
  const isEnglish = computed(() => locale.value === 'en')
  const nextLocaleLabel = computed(() => (locale.value === 'en' ? '中文' : 'EN'))
  const dateLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'))
  const timeLocale = computed(() => (locale.value === 'en' ? 'en-US' : 'zh-CN'))

  function setLocale(nextLocale: AppLocale): void {
    locale.value = nextLocale
    getStorage()?.setItem(STORAGE_KEY, nextLocale)
  }

  function toggleLocale(): void {
    setLocale(locale.value === 'en' ? 'zh' : 'en')
  }

  function t(key: TranslationKey): string {
    return messages[locale.value][key] ?? messages.en[key]
  }

  return {
    locale,
    isEnglish,
    nextLocaleLabel,
    dateLocale,
    timeLocale,
    setLocale,
    toggleLocale,
    t,
  }
})
