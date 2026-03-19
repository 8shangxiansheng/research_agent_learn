import axios from 'axios'

import type { AppLocale } from '@/stores/locale'

type Translator = (key: string) => string

type LocaleContext = {
  locale: AppLocale
  dateLocale: string
  timeLocale: string
  t: Translator
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
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      const mappedKey = backendErrorKeyMap[detail]
      if (mappedKey) {
        return locale.t(mappedKey)
      }

      if (detail.startsWith('Retry failed:')) {
        return locale.t('api.error.retryFailed')
      }

      return detail
    }
  }

  return locale.t(fallbackKey)
}
