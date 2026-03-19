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
    'common.pdf': 'PDF',
    'chat.selectSession': 'Select a session',
    'chat.empty': 'Select or create a session to start chatting',
    'chat.placeholder': 'Ask about academic papers, research topics, or concepts...',
    'chat.sendHint': 'Ctrl+Enter to send',
    'chat.send': 'Send',
    'chat.thinking': 'Thinking...',
    'chat.status.connecting': 'Connecting',
    'chat.status.connected': 'Live',
    'chat.status.reconnecting': 'Reconnecting',
    'chat.status.disconnected': 'Disconnected',
    'chat.status.error': 'Connection issue',
    'chat.status.connectingDetail': 'Connecting to live response channel...',
    'chat.status.connectedDetail': 'Live response channel is ready.',
    'chat.status.reconnectingDetail': 'Trying to reconnect live response channel',
    'chat.status.disconnectedDetail': 'Live response channel is offline.',
    'chat.status.errorDetail': 'Live response channel encountered an error.',
    'chat.defaultSessionTitle': 'New Chat',
    'chat.error.fetchSessions': 'Failed to fetch sessions',
    'chat.error.fetchMessages': 'Failed to fetch messages',
    'chat.error.createSession': 'Failed to create session',
    'chat.error.updateSession': 'Failed to update session',
    'chat.error.deleteSession': 'Failed to delete session',
    'chat.error.exportSession': 'Failed to export session',
    'chat.error.noActiveSession': 'No active session',
    'chat.error.retryAnswer': 'Failed to retry answer',
    'chat.error.appendResearch': 'Failed to add research brief to session',
    'chat.error.websocket': 'WebSocket connection error',
    'chat.error.websocketUnknown': 'Unknown error',
    'chat.error.websocketDisconnected': 'WebSocket not connected',
    'api.error.sessionNotFound': 'Session not found',
    'api.error.researchTaskNotFound': 'Research task not found',
    'api.error.researchQueryEmpty': 'Research query cannot be empty',
    'api.error.messageNotFound': 'Message not found',
    'api.error.retryAssistantOnly': 'Only assistant messages can be retried',
    'api.error.retryLatestOnly': 'Only the latest assistant message can be retried',
    'api.error.retryNeedsUserMessage': 'Retry requires a previous user message',
    'api.error.researchTaskNoSession': 'Research task is not associated with a session',
    'api.error.retryFailed': 'Retry failed',
    'api.error.documentUnsupportedType': 'Unsupported document type. Please upload TXT, MD, or PDF',
    'api.error.documentEmpty': 'Uploaded document is empty',
    'api.error.documentInvalid': 'Uploaded document content is invalid',
    'api.error.documentFilenameRequired': 'Uploaded document filename is required',
    'api.error.documentEncoding': 'Uploaded text document must be UTF-8 encoded',
    'api.error.documentUnreadable': 'Uploaded document does not contain readable text',
    'api.error.documentPdfUnavailable': 'PDF parsing is unavailable because the parser dependency is missing',
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
    'research.attachDocument': 'Attach Document',
    'research.changeDocument': 'Change Document',
    'research.clearDocument': 'Clear Document',
    'research.documentAttached': 'Attached document',
    'research.documentFormats': 'Supported: TXT, MD, PDF',
    'research.progress': 'Research Progress',
    'research.phase.planning': 'Planning',
    'research.phase.retrieving': 'Retrieving Sources',
    'research.phase.synthesizing': 'Synthesizing Answer',
    'research.phase.completed': 'Completed',
    'research.phase.planning.detail': 'Clarifying the research objective',
    'research.phase.retrieving.detail': 'Gathering relevant evidence sources',
    'research.phase.synthesizing.detail': 'Drafting a source-backed summary',
    'research.phase.completed.detail': 'Research brief is ready',
    'research.history': 'Research History',
    'research.loading': 'Loading...',
    'research.historySearch': 'Search research history',
    'research.historyEmpty': 'No research tasks for this session yet.',
    'research.evidenceEmpty': 'No structured evidence map yet.',
    'research.rerun': 'Rerun',
    'research.rerunNew': 'Rerun New',
    'research.rename': 'Rename',
    'research.delete': 'Delete',
    'research.plan': 'Plan',
    'research.sources': 'Sources',
    'research.sourceType.arxiv': 'arXiv',
    'research.sourceType.crossref': 'Crossref',
    'research.sourceType.local_document': 'Local Document',
    'research.sourceType.local_pdf': 'Local PDF',
    'research.evidence': 'Evidence Map',
    'research.answer': 'Research Answer',
    'research.insertSummary': 'Insert Summary',
    'research.insertFull': 'Insert Full',
    'research.viewMarkdown': 'View Markdown report',
    'research.abstract': 'Abstract',
    'research.renamePrompt': 'Rename research task',
    'research.error.emptyQuery': 'Research query cannot be empty',
    'research.error.readDocument': 'Failed to read local document',
    'research.error.run': 'Failed to run research task',
    'research.error.fetchHistory': 'Failed to fetch research history',
    'research.error.delete': 'Failed to delete research task',
    'research.error.rename': 'Failed to rename research task',
    'research.error.rerun': 'Failed to rerun research task',
    'research.error.rerunNew': 'Failed to create a new rerun task',
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
    'common.pdf': 'PDF',
    'chat.selectSession': '选择一个会话',
    'chat.empty': '请选择或创建一个会话后开始聊天',
    'chat.placeholder': '输入论文、研究主题或学术概念相关问题...',
    'chat.sendHint': '按 Ctrl+Enter 发送',
    'chat.send': '发送',
    'chat.thinking': '思考中...',
    'chat.status.connecting': '连接中',
    'chat.status.connected': '已连接',
    'chat.status.reconnecting': '重连中',
    'chat.status.disconnected': '已断开',
    'chat.status.error': '连接异常',
    'chat.status.connectingDetail': '正在连接实时响应通道...',
    'chat.status.connectedDetail': '实时响应通道已就绪。',
    'chat.status.reconnectingDetail': '正在尝试重新连接实时响应通道',
    'chat.status.disconnectedDetail': '实时响应通道当前不可用。',
    'chat.status.errorDetail': '实时响应通道发生错误。',
    'chat.defaultSessionTitle': '新建会话',
    'chat.error.fetchSessions': '获取会话失败',
    'chat.error.fetchMessages': '获取消息失败',
    'chat.error.createSession': '创建会话失败',
    'chat.error.updateSession': '更新会话失败',
    'chat.error.deleteSession': '删除会话失败',
    'chat.error.exportSession': '导出会话失败',
    'chat.error.noActiveSession': '当前没有活动会话',
    'chat.error.retryAnswer': '重试回答失败',
    'chat.error.appendResearch': '将研究摘要加入会话失败',
    'chat.error.websocket': 'WebSocket 连接错误',
    'chat.error.websocketUnknown': '未知错误',
    'chat.error.websocketDisconnected': 'WebSocket 未连接',
    'api.error.sessionNotFound': '会话不存在',
    'api.error.researchTaskNotFound': '研究任务不存在',
    'api.error.researchQueryEmpty': '研究问题不能为空',
    'api.error.messageNotFound': '消息不存在',
    'api.error.retryAssistantOnly': '只有助手消息可以重试',
    'api.error.retryLatestOnly': '只能重试最新一条助手消息',
    'api.error.retryNeedsUserMessage': '重试前必须有上一条用户消息',
    'api.error.researchTaskNoSession': '该研究任务没有关联会话',
    'api.error.retryFailed': '重试失败',
    'api.error.documentUnsupportedType': '不支持该文档类型，请上传 TXT、MD 或 PDF',
    'api.error.documentEmpty': '上传的文档为空',
    'api.error.documentInvalid': '上传的文档内容无效',
    'api.error.documentFilenameRequired': '上传文档必须包含文件名',
    'api.error.documentEncoding': '上传的文本文档必须使用 UTF-8 编码',
    'api.error.documentUnreadable': '上传的文档没有可读取文本',
    'api.error.documentPdfUnavailable': '当前环境缺少 PDF 解析依赖，暂时无法解析 PDF',
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
    'research.attachDocument': '附加文档',
    'research.changeDocument': '更换文档',
    'research.clearDocument': '清除文档',
    'research.documentAttached': '已附加文档',
    'research.documentFormats': '支持：TXT、MD、PDF',
    'research.progress': '研究进度',
    'research.phase.planning': '任务规划',
    'research.phase.retrieving': '检索来源',
    'research.phase.synthesizing': '综合生成',
    'research.phase.completed': '已完成',
    'research.phase.planning.detail': '正在明确研究目标',
    'research.phase.retrieving.detail': '正在收集相关证据来源',
    'research.phase.synthesizing.detail': '正在生成带引用的研究摘要',
    'research.phase.completed.detail': '研究摘要已生成',
    'research.history': '研究历史',
    'research.loading': '加载中...',
    'research.historySearch': '搜索研究历史',
    'research.historyEmpty': '当前会话还没有研究任务。',
    'research.evidenceEmpty': '当前还没有结构化证据映射。',
    'research.rerun': '重跑',
    'research.rerunNew': '另存后重跑',
    'research.rename': '重命名',
    'research.delete': '删除',
    'research.plan': '计划',
    'research.sources': '来源',
    'research.sourceType.arxiv': 'arXiv',
    'research.sourceType.crossref': 'Crossref',
    'research.sourceType.local_document': '本地文档',
    'research.sourceType.local_pdf': '本地 PDF',
    'research.evidence': '证据映射',
    'research.answer': '研究结论',
    'research.insertSummary': '插入摘要',
    'research.insertFull': '插入全文',
    'research.viewMarkdown': '查看 Markdown 报告',
    'research.abstract': '摘要',
    'research.renamePrompt': '重命名研究任务',
    'research.error.emptyQuery': '研究问题不能为空',
    'research.error.readDocument': '读取本地文档失败',
    'research.error.run': '运行研究任务失败',
    'research.error.fetchHistory': '获取研究历史失败',
    'research.error.delete': '删除研究任务失败',
    'research.error.rename': '重命名研究任务失败',
    'research.error.rerun': '重跑研究任务失败',
    'research.error.rerunNew': '另存重跑任务失败',
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

  function t(key: string): string {
    const normalizedKey = key as TranslationKey
    return messages[locale.value][normalizedKey] ?? messages.en[normalizedKey] ?? key
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
