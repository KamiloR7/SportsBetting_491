import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

const reports = path.resolve(process.env.SPRINT5_REPORT_DIR || '../build/sprint5-qa')

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
    reporters: ['default', 'junit', 'json'],
    outputFile: {
      junit: path.join(reports, 'component-results.xml'),
      json: path.join(reports, 'component-results.json'),
    },
  },
})
