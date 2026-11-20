import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'

const reports = path.resolve(process.env.SPRINT5_REPORT_DIR || '../build/sprint5-qa')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  workers: 2,
  retries: 0,
  reporter: [
    ['list'],
    ['junit', { outputFile: path.join(reports, 'browser-results.xml') }],
    ['json', { outputFile: path.join(reports, 'browser-results.json') }],
  ],
  outputDir: path.join(reports, 'browser-artifacts'),
  use: { baseURL: 'http://127.0.0.1:5195', trace: 'off', video: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5195 --strictPort',
    url: 'http://127.0.0.1:5195',
    reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
  },
})
