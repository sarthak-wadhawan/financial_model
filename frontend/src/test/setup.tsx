import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, expect, vi } from 'vitest'

// Keep real application/router/query behavior. Each test owns its API fixtures.
// Never let a missed API mock contact a running dev server (or the internet).
// Reject the transport AND fail the test, even if React Query catches the error.
let unmockedRequests: string[] = []
beforeEach(() => {
  unmockedRequests = []
  vi.spyOn(XMLHttpRequest.prototype, 'send').mockImplementation(() => {
    unmockedRequests.push('XMLHttpRequest')
    throw new Error('Unit tests must mock API requests; real XHR is blocked')
  })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    unmockedRequests.push(String(input))
    throw new Error('Unit tests must mock API requests; real fetch is blocked')
  })
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  window.localStorage.clear()
  expect(unmockedRequests, 'Unmocked unit-test network requests are forbidden').toEqual([])
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

class ResizeObserverStub implements ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)
