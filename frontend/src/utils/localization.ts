import axios from 'axios'

import type { AppLocale } from '@/stores/locale'

type Translator = (key: string) => string

type LocaleContext = {
  locale: AppLocale
  dateLocale: string
  timeLocale: string
  t: Translator
}

type StructuredBackendDetail = {
  code?: string
  message?: string
  reason?: string
  recovery_hint?: string
  retryable?: boolean
  operation?: string
  query?: string
}

export type LocalizedApiErrorDetail = {
  code?: string
  message: string
  reason?: string
  recoveryHint?: string
  retryable: boolean
  operation?: string
  query?: string
}

const backendErrorKeyMap: Record<string, string> = {
  'Session not found': 'api.error.sessionNotFound',
  'Research task not found': 'api.error.researchTaskNotFound',
  'Research query cannot be empty': 'api.error.researchQueryEmpty',
  'Message not found': 'api.error.messageNotFound',
  'Only assistant messages can be retried': 'api.error.retryAssistantOnly',
  'Only the latest assistant message can be retried': 'api.error.retryLatestOnly',
  'Retry requires a previous user message': 'api.error.retryNeedsUserMessage',
  'Research task is not associated with a session': 'api.error.researchTaskNoSession',
  'Unsupported document type. Please upload TXT, MD, or PDF': 'api.error.documentUnsupportedType',
  'Uploaded document is empty': 'api.error.documentEmpty',
  'Uploaded document content is invalid': 'api.error.documentInvalid',
  'Uploaded document filename is required': 'api.error.documentFilenameRequired',
  'Uploaded text document must be UTF-8 encoded': 'api.error.documentEncoding',
  'Uploaded document does not contain readable text': 'api.error.documentUnreadable',
  'PDF parsing is unavailable because pypdf is not installed': 'api.error.documentPdfUnavailable',
}

const backendErrorCodeKeyMap: Record<string, string> = {
  research_execution_failed: 'api.error.researchExecutionFailed',
}

const backendRecoveryHintKeyMap: Record<string, string> = {
  retry_or_adjust_query: 'api.hint.researchRetryOrAdjustQuery',
}

export function formatSessionDate(date: string, locale: LocaleContext): string {
  return new Intl.DateTimeFormat(locale.dateLocale, locale.locale === 'zh'
    ? { month: 'numeric', day: 'numeric' }
    : { month: 'short', day: 'numeric' }).format(new Date(date))
}

export function formatHistoryDate(date: string, locale: LocaleContext): string {
  return new Intl.DateTimeFormat(locale.dateLocale, locale.locale === 'zh'
    ? { year: 'numeric', month: 'numeric', day: 'numeric' }
    : { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(date))
}

export function formatSourceDate(date: string | undefined, locale: LocaleContext): string {
  if (!date) {
    return ''
  }

  return new Intl.DateTimeFormat(locale.dateLocale, locale.locale === 'zh'
    ? { year: 'numeric', month: 'numeric', day: 'numeric' }
    : { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(date))
}

export function formatMessageTime(date: string, locale: LocaleContext): string {
  return new Intl.DateTimeFormat(locale.timeLocale, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function resolveLocalizedErrorMessage(
  error: unknown,
  locale: LocaleContext,
  fallbackKey: string,
): string {
  return resolveLocalizedApiError(error, locale, fallbackKey).message
}

export function resolveLocalizedApiError(
  error: unknown,
  locale: LocaleContext,
  fallbackKey: string,
): LocalizedApiErrorDetail {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      const mappedKey = backendErrorKeyMap[detail]
      if (mappedKey) {
        return {
          message: locale.t(mappedKey),
          retryable: false,
        }
      }

      if (detail.startsWith('Retry failed:')) {
        return {
          message: locale.t('api.error.retryFailed'),
          retryable: false,
        }
      }

      return {
        message: detail,
        retryable: false,
      }
    }

    if (detail && typeof detail === 'object') {
      const structured = detail as StructuredBackendDetail
      const mappedKey = structured.code ? backendErrorCodeKeyMap[structured.code] : undefined
      const recoveryHintKey = structured.recovery_hint
        ? backendRecoveryHintKeyMap[structured.recovery_hint]
        : undefined
      return {
        code: structured.code,
        message: mappedKey ? locale.t(mappedKey) : structured.message ?? locale.t(fallbackKey),
        reason: structured.reason,
        recoveryHint: recoveryHintKey ? locale.t(recoveryHintKey) : undefined,
        retryable: structured.retryable ?? false,
        operation: structured.operation,
        query: structured.query,
      }
    }
  }

  return {
    message: locale.t(fallbackKey),
    retryable: false,
  }
}
