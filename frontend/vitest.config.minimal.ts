import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/pages/LandingPage.test.tsx'],
    pool: 'vmThreads',
    deps: {
      external: ['@csstools/css-calc', '@csstools/css-color-parser', '@csstools/css-parser-algorithms', '@csstools/css-tokenizer', '@asamuzakjp/css-color', 'recharts'],
    },
  },
})