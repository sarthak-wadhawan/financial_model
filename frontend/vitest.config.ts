import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.tsx'],
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['src/test/e2e/**', 'node_modules/**', 'dist/**'],
    globals: true,
    css: true,
    pool: 'vmForks',
    deps: {
      external: ['@csstools/css-calc', '@csstools/css-color-parser', '@csstools/css-parser-algorithms', '@csstools/css-tokenizer', '@asamuzakjp/css-color'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})