import { expect, test } from '@playwright/test'

test.describe('Academic Q&A Agent E2E', () => {
  test('切换中英文界面', async ({ page }) => {
    await page.goto('/')

    const title = page.getByRole('heading', { level: 1 })
    const initialTitle = await title.textContent()

    await page.getByTestId('locale-toggle').click()

    await expect(title).not.toHaveText(initialTitle ?? '')
    await expect(title).toHaveText(/Academic Q&A Agent|学术问答助手/)
    await expect(page.getByTestId('new-session')).toHaveText(/New|新建/)
  })

  test('创建会话后完成聊天与研究导出链路', async ({ page }) => {
    await page.goto('/')

    await page.getByTestId('new-session').click()

    await expect(page.getByTestId('chat-title')).toHaveText(/New Chat|新建会话/)
    await expect(page.getByTestId('websocket-badge')).toHaveText(/Live|已连接|连接中/)

    await page.locator('[data-test="chat-input"] textarea, textarea[data-test="chat-input"]').fill('Explain retrieval augmented generation.')
    await page.getByTestId('send-button').click()

    await expect(page.getByText('Mock assistant response for: Explain retrieval augmented generation.')).toBeVisible()

    await page.locator('[data-test="research-query"] input, input[data-test="research-query"]').fill('graph neural networks')
    await page.getByTestId('run-research').click()

    await expect(page.getByTestId('research-progress')).toBeVisible()
    await expect(page.getByTestId('research-result')).toBeVisible()
    await expect(page.getByTestId('research-answer')).toContainText('Graph Neural Networks')
    await expect(page.getByRole('link', { name: 'Mock evidence for graph neural networks' })).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('export-report').click()
    const download = await downloadPromise

    expect(download.suggestedFilename()).toContain('research-brief-graph-neural-networks')
  })
})
