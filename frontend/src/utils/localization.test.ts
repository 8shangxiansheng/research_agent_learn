import { describe, expect, it } from 'vitest'

import {
  formatHistoryDate,
  formatMessageTime,
  formatSessionDate,
  formatSourceDate,
  resolveLocalizedApiError,
  resolveLocalizedErrorMessage,
} from './localization'

const enLocale = {
  locale: 'en' as const,
  dateLocale: 'en-US',
  timeLocale: 'en-US',
  t: (key: string) => ({
    'chat.error.fetchSessions': 'Failed to fetch sessions',
    'api.error.sessionNotFound': 'Session not found',
    'api.error.retryFailed': 'Retry failed',
    'api.error.researchExecutionFailed': 'Research task failed before completion',
    'api.hint.researchRetryOrAdjustQuery': 'Retry the task, or narrow the query and try again.',
  }[key] ?? key),
}

const zhLocale = {
  locale: 'zh' as const,
  dateLocale: 'zh-CN',
  timeLocale: 'zh-CN',
  t: (key: string) => ({
    'chat.error.fetchSessions': '获取会话失败',
    'api.error.sessionNotFound': '会话不存在',
    'api.error.retryFailed': '重试失败',
    'api.error.researchExecutionFailed': '研究任务未能完成',
    'api.hint.researchRetryOrAdjustQuery': '请重试该任务，或缩小问题范围后再试。',
  }[key] ?? key),
}

describe('localization utils', () => {
  it('formats session and history dates by locale', () => {
    const date = '2026-03-19T10:30:00Z'

    expect(formatSessionDate(date, enLocale)).toMatch(/Mar|19/)
    expect(formatHistoryDate(date, enLocale)).toMatch(/2026/)
    expect(formatSessionDate(date, zhLocale)).toContain('3')
    expect(formatHistoryDate(date, zhLocale)).toContain('2026')
    expect(formatSourceDate(date, zhLocale)).toContain('2026')
  })

  it('formats message time by locale', () => {
    const time = formatMessageTime('2026-03-19T10:30:00Z', enLocale)
    expect(time.length).toBeGreaterThan(0)
  })

  it('maps backend detail to localized frontend copy', () => {
    const sessionNotFoundError = {
      isAxiosError: true,
      response: {
        data: {
          detail: 'Session not found',
        },
      },
    }

    const retryFailedError = {
      isAxiosError: true,
      response: {
        data: {
          detail: 'Retry failed: mock failure',
        },
      },
    }

    expect(resolveLocalizedErrorMessage(sessionNotFoundError, zhLocale, 'chat.error.fetchSessions')).toBe('会话不存在')
    expect(resolveLocalizedErrorMessage(retryFailedError, zhLocale, 'chat.error.fetchSessions')).toBe('重试失败')
    expect(resolveLocalizedErrorMessage(new Error('boom'), zhLocale, 'chat.error.fetchSessions')).toBe('获取会话失败')
  })

  it('resolves structured backend error detail for recovery flows', () => {
    const structuredError = {
      isAxiosError: true,
      response: {
        data: {
          detail: {
            code: 'research_execution_failed',
            reason: 'RuntimeError',
            recovery_hint: 'retry_or_adjust_query',
            retryable: true,
            operation: 'run',
            query: 'transformer interpretability',
          },
        },
      },
    }

    expect(resolveLocalizedApiError(structuredError, zhLocale, 'chat.error.fetchSessions')).toEqual({
      code: 'research_execution_failed',
      message: '研究任务未能完成',
      reason: 'RuntimeError',
      recoveryHint: '请重试该任务，或缩小问题范围后再试。',
      retryable: true,
      operation: 'run',
      query: 'transformer interpretability',
    })
  })
})
