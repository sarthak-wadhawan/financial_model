import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { api, type BarData } from '../../services/api'
import { PriceHistoryChart, normalizePriceHistory, priceHistoryBounds } from './PriceHistoryChart'

const mocks = vi.hoisted(() => ({
  theme: 'light', create: vi.fn(), setData: vi.fn(), addSeries: vi.fn(), fit: vi.fn(), apply: vi.fn(),
  subscribe: vi.fn(), unsubscribe: vi.fn(), click: vi.fn(), unclick: vi.fn(), remove: vi.fn(), observe: vi.fn(), disconnect: vi.fn(), resize: vi.fn(),
}))
vi.mock('../../context/ThemeContext', () => ({ useTheme: () => ({ resolvedTheme: mocks.theme }) }))
vi.mock('lightweight-charts', () => ({
  ColorType: { Solid: 'solid' }, CrosshairMode: { Magnet: 1 }, LineSeries: 'line-series-v5', createChart: mocks.create,
}))
const bar = (t: string, c = 120) => ({ t, c, o: c, h: c, l: c, v: 10 })
const data = (bars = [bar('2026-10-13'), bar('2026-10-15', 125)], symbol = 'AAPL'): BarData => ({ symbol, timeframe: '1Day', bars, status: bars.length ? 'available' : 'empty', reason: null, source: 'offline fixture', mode: 'demo' })
function mount(symbol = 'AAPL') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const tree = (value: string) => <QueryClientProvider client={client}><PriceHistoryChart symbol={value} /></QueryClientProvider>
  const view = render(tree(symbol))
  return { ...view, changeSymbol: (value: string) => view.rerender(tree(value)), refresh: () => view.rerender(tree(symbol)) }
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-10-16T01:00:00Z'))
  mocks.theme = 'light'
  mocks.create.mockReturnValue({ addSeries: mocks.addSeries, timeScale: () => ({ fitContent: mocks.fit }), applyOptions: mocks.apply, subscribeCrosshairMove: mocks.subscribe, unsubscribeCrosshairMove: mocks.unsubscribe, subscribeClick: mocks.click, unsubscribeClick: mocks.unclick, remove: mocks.remove })
  mocks.addSeries.mockReturnValue({ setData: mocks.setData })
  vi.stubGlobal('ResizeObserver', class { constructor(callback: ResizeObserverCallback) { mocks.resize.mockImplementation(callback) } observe = mocks.observe; disconnect = mocks.disconnect })
  vi.spyOn(api, 'getBars').mockResolvedValue(data())
})
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })

describe('price history calendar and data contracts', () => {
  it('uses explicit UTC calendar ranges and clamps leap/month ends', () => {
    const now = new Date('2026-10-16T23:59:59Z')
    expect(priceHistoryBounds('1W', now)).toEqual({ start: '2026-10-09', end: '2026-10-16' })
    expect(priceHistoryBounds('1M', now).start).toBe('2026-09-16')
    expect(priceHistoryBounds('3M', now).start).toBe('2026-07-16')
    expect(priceHistoryBounds('1Y', now).start).toBe('2025-10-16')
    expect(priceHistoryBounds('5Y', now).start).toBe('2021-10-16')
    expect(priceHistoryBounds('1M', new Date('2024-03-31Z')).start).toBe('2024-02-29')
    expect(priceHistoryBounds('1Y', new Date('2024-02-29Z')).start).toBe('2023-02-28')
  })
  it('strictly validates, sorts and deduplicates dates without shifting session labels or filling gaps', () => {
    const bars = [bar('2026-10-15T00:00:00+14:00', 15), bar('2026-10-12', 12), bar('2026-10-12T04:00:00Z', 99), bar('2026-10-14', 0), bar('2026-02-30'), bar('garbage'), bar('2026-10-13junk'), bar('2026-10-13T99:99:99Z'), bar('2026-10-11', NaN), bar('2026-10-10', Infinity), bar('2026-10-09', -1), bar('2026-09-01'), bar('2026-10-16'), bar('2026-10-17')]
    expect(normalizePriceHistory(bars, '2026-09-16', '2026-10-16')).toEqual([{ time: '2026-10-12', value: 12 }, { time: '2026-10-14', value: 0 }, { time: '2026-10-15', value: 15 }])
  })
})

describe('PriceHistoryChart offline mocked chart lifecycle', () => {
  it('requests bounded daily history, uses v5 line series and provides evidence/inspection/table/attribution', async () => {
    mount()
    expect(await screen.findByLabelText('Inspected daily close')).toHaveTextContent('2026-10-15 · Close $125.00')
    expect(api.getBars).toHaveBeenCalledWith('AAPL', '1Day', '2026-09-16', '2026-10-16', 5000)
    expect(mocks.addSeries).toHaveBeenCalledWith('line-series-v5', expect.objectContaining({ lineWidth: 2 }))
    expect(mocks.setData).toHaveBeenCalledWith([{ time: '2026-10-13', value: 120 }, { time: '2026-10-15', value: 125 }])
    expect(mocks.create).toHaveBeenCalledWith(expect.any(HTMLElement), expect.objectContaining({ rightPriceScale: expect.objectContaining({ visible: true }), timeScale: expect.objectContaining({ visible: true, timeVisible: false }) }))
    expect(screen.getByRole('button', { name: '1D' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'ALL' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '1M' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.change(screen.getByLabelText('Inspect session'), { target: { value: '2026-10-13' } })
    expect(screen.getByLabelText('Inspected daily close')).toHaveTextContent('2026-10-13 · Close $120.00')
    fireEvent.click(screen.getByText('Daily close data table (2)'))
    expect(screen.getByRole('table')).toHaveAccessibleName('AAPL returned daily closes (USD)')
    expect(screen.getByText(/Returned bounds do not establish complete coverage/)).toBeInTheDocument()
    expect(screen.getByText(/raw \(unadjusted for splits or dividends\)/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://www.tradingview.com/' })).toHaveAttribute('href', 'https://www.tradingview.com/')
    expect(screen.getByText(/Copyright \(с\) 2025 TradingView, Inc./)).toBeInTheDocument()
  })
  it('changes every supported window without requesting intraday or claiming ALL', async () => {
    mount()
    await screen.findByLabelText('Inspected daily close')
    for (const [range, start] of [['1W', '2026-10-09'], ['3M', '2026-07-16'], ['1Y', '2025-10-16'], ['5Y', '2021-10-16'], ['1M', '2026-09-16']]) {
      fireEvent.click(screen.getByRole('button', { name: range }))
      await waitFor(() => expect(api.getBars).toHaveBeenLastCalledWith('AAPL', '1Day', start, '2026-10-16', 5000))
    }
  })
  it('shows loading, empty and retry without manufacturing points', async () => {
    let resolve!: (value: BarData) => void
    vi.mocked(api.getBars).mockReturnValueOnce(new Promise(done => { resolve = done }))
    mount()
    expect(screen.getByRole('status')).toHaveTextContent('Loading AAPL')
    await act(async () => resolve(data([])))
    expect(await screen.findByText(/No valid completed daily closes/)).toBeInTheDocument()
    expect(mocks.create).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry price history' }))
    expect(await screen.findByLabelText('Inspected daily close')).toBeInTheDocument()
  })
  it('handles sanitized transport failure and retry', async () => {
    vi.mocked(api.getBars).mockRejectedValueOnce(new Error('private-provider-secret'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Price history is unavailable')
    expect(screen.queryByText('private-provider-secret')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry price history' }))
    expect(await screen.findByLabelText('Inspected daily close')).toBeInTheDocument()
  })
  it('does not plot bars accompanying a provider error or mismatched symbol', async () => {
    vi.mocked(api.getBars).mockResolvedValueOnce({ ...data(), status: 'provider_error' })
    const view = mount()
    await screen.findByRole('alert')
    expect(mocks.create).not.toHaveBeenCalled()
    vi.mocked(api.getBars).mockResolvedValueOnce(data())
    view.changeSymbol('MSFT')
    await screen.findByRole('alert')
    expect(mocks.create).not.toHaveBeenCalled()
  })
  it('immediately clears old symbol canvas/inspection and ignores late response', async () => {
    const view = mount()
    await screen.findByLabelText('Inspected daily close')
    let resolve!: (value: BarData) => void
    vi.mocked(api.getBars).mockReturnValueOnce(new Promise(done => { resolve = done }))
    view.changeSymbol('MSFT')
    expect(screen.queryByLabelText('Inspected daily close')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Loading MSFT')
    expect(mocks.remove).toHaveBeenCalledTimes(1)
    view.changeSymbol('V')
    await screen.findByRole('alert') // fixture symbol AAPL does not match V
    await act(async () => resolve(data([bar('2026-10-15', 999)], 'MSFT')))
    expect(screen.queryByText(/999/)).not.toBeInTheDocument()
  })
  it('clears the old range while its replacement loads', async () => {
    mount()
    await screen.findByLabelText('Inspected daily close')
    let resolve!: (value: BarData) => void
    vi.mocked(api.getBars).mockReturnValueOnce(new Promise(done => { resolve = done }))
    fireEvent.click(screen.getByRole('button', { name: '5Y' }))
    expect(screen.queryByLabelText('Inspected daily close')).not.toBeInTheDocument()
    expect(mocks.remove).toHaveBeenCalled()
    await act(async () => resolve(data([])))
    await screen.findByText(/No valid completed daily closes/)
  })
  it('supports hover/tap, responsive resize, theme updates and symmetrical cleanup', async () => {
    const view = mount()
    await screen.findByLabelText('Inspected daily close')
    const series = mocks.addSeries.mock.results[0].value
    const event = { seriesData: new Map([[series, { time: '2026-10-13', value: 120 }]]) }
    act(() => mocks.subscribe.mock.calls[0][0](event))
    expect(screen.getByLabelText('Inspected daily close')).toHaveTextContent('2026-10-13')
    act(() => mocks.click.mock.calls[0][0]({ seriesData: new Map() }))
    expect(screen.getByLabelText('Inspected daily close')).toHaveTextContent('2026-10-15')
    act(() => mocks.resize([{ contentRect: { width: 640 } }]))
    expect(mocks.apply).toHaveBeenLastCalledWith({ width: 640 })
    mocks.theme = 'dark'
    view.refresh()
    expect(mocks.apply).toHaveBeenLastCalledWith(expect.objectContaining({ layout: expect.objectContaining({ background: { type: 'solid', color: '#111827' } }) }))
    view.unmount()
    expect(mocks.unsubscribe).toHaveBeenCalledWith(mocks.subscribe.mock.calls[0][0])
    expect(mocks.unclick).toHaveBeenCalledWith(mocks.click.mock.calls[0][0])
    expect(mocks.disconnect).toHaveBeenCalledTimes(1)
    expect(mocks.remove).toHaveBeenCalledTimes(1)
  })
  it('keeps the exact values accessible when canvas construction is unavailable', async () => {
    mocks.create.mockImplementationOnce(() => { throw new Error('canvas unavailable') })
    mount()
    expect(await screen.findByText(/Chart rendering is unavailable/)).toBeInTheDocument()
    expect(screen.getByLabelText('Inspect session')).toBeInTheDocument()
  })
})
