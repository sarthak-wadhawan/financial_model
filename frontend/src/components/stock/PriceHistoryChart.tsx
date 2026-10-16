import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ColorType, createChart, CrosshairMode, LineSeries, type IChartApi, type LineData, type Time } from 'lightweight-charts'
import { api, type BarData } from '../../services/api'
import { useTheme } from '../../context/ThemeContext'
import { SourceLink } from '../ui/ResearchData'
import './PriceHistoryChart.css'

type Range = '1W' | '1M' | '3M' | '1Y' | '5Y'
type Point = LineData<Time> & { time: string }

// Calendar arithmetic is UTC-only; clamp month ends instead of overflowing them.
export function priceHistoryBounds(range: Range, now = new Date()) {
  const end = now.toISOString().slice(0, 10)
  const start = new Date(`${end}T00:00:00Z`)
  if (range === '1W') start.setUTCDate(start.getUTCDate() - 7)
  else {
    const months = { '1M': 1, '3M': 3, '1Y': 12, '5Y': 60 }[range]
    const day = start.getUTCDate()
    start.setUTCDate(1)
    start.setUTCMonth(start.getUTCMonth() - months)
    const last = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 0)).getUTCDate()
    start.setUTCDate(Math.min(day, last))
  }
  return { start: start.toISOString().slice(0, 10), end }
}

export function normalizePriceHistory(bars: BarData['bars'], start: string, end: string): Point[] {
  const days = new Map<string, Point>()
  for (const bar of bars) {
    // Daily timestamps label sessions, not local instants. Never locale-convert them.
    if (typeof bar.t !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:$|T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$)/.test(bar.t)) continue
    if (!Number.isFinite(Date.parse(bar.t))) continue
    const day = bar.t.slice(0, 10)
    const date = new Date(`${day}T00:00:00Z`)
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== day) continue
    if (day < start || day >= end || typeof bar.c !== 'number' || !Number.isFinite(bar.c) || bar.c < 0) continue
    // First valid observation wins; never average or invent conflicting closes.
    if (!days.has(day)) days.set(day, { time: day, value: bar.c })
  }
  return [...days.values()].sort((a, b) => a.time.localeCompare(b.time))
}

const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(value)
const palette = (dark: boolean) => ({
  layout: { background: { type: ColorType.Solid, color: dark ? '#171D19' : '#ffffff' }, textColor: dark ? '#d4ddd6' : '#34473a', attributionLogo: true },
  grid: { vertLines: { color: dark ? '#202a23' : '#f3f6f4' }, horzLines: { color: dark ? '#2d3b31' : '#e1e8e3' } },
})

export function PriceHistoryChart({ symbol }: { symbol: string }) {
  // A new symbol remounts all inspection state and the canvas synchronously.
  return <PriceHistoryPanel key={symbol} symbol={symbol} />
}

function PriceHistoryPanel({ symbol }: { symbol: string }) {
  const [range, setRange] = useState<Range>('1M')
  const { start, end } = priceHistoryBounds(range)
  const query = useQuery({
    queryKey: ['priceHistory', symbol, '1Day', start, end],
    queryFn: () => api.getBars(symbol, '1Day', start, end, 5000),
    enabled: !!symbol, retry: false, placeholderData: undefined,
  })
  const response = query.data?.symbol === symbol && query.data.timeframe === '1Day' ? query.data : undefined
  const failed = query.isError || (!query.isPending && !!query.data && (!response || ['provider_error', 'error', 'unavailable', 'unsupported'].includes(response.status)))
  const points = useMemo(() => normalizePriceHistory(response?.bars ?? [], start, end), [response, start, end])
  const id = useId()

  return <section className="price-history" aria-labelledby={`${id}-title`}>
    <div className="price-history__heading"><div><h2 id={`${id}-title`}>Price history</h2><p>{symbol} · Completed daily closes · USD</p></div>
      <div className="price-history__ranges" role="group" aria-label="Price history range">
        <button disabled title="Intraday data is unsupported" aria-describedby={`${id}-limits`}>1D</button>
        {(['1W', '1M', '3M', '1Y', '5Y'] as const).map(item => <button key={item} aria-pressed={range === item} onClick={() => setRange(item)}>{item}</button>)}
        <button disabled title="Complete lifetime history is not established" aria-describedby={`${id}-limits`}>ALL</button>
      </div>
    </div>
    <p id={`${id}-limits`} className="price-history__note">1D unavailable: no intraday data. ALL unavailable: lifetime coverage unverified.</p>
    {query.isPending ? <div className="price-history__state" role="status">Loading {symbol} price history…</div>
      : failed ? <div className="price-history__state" role="alert">Price history is unavailable. <button onClick={() => void query.refetch()} disabled={query.isFetching}>Retry price history</button></div>
        : !points.length ? <div className="price-history__state" role="status">No valid completed daily closes returned for this range. <button onClick={() => void query.refetch()} disabled={query.isFetching}>Retry price history</button></div>
          : <HistoryPlot key={`${symbol}:${start}:${end}`} points={points} symbol={symbol} />}
    <p className="price-history__note">IEX · Unadjusted daily closes · Not a live quote{response?.mode === 'demo' ? ' · Demo/test data, not live evidence' : ''}.</p>
    <details className="price-history__details"><summary>Source and chart details</summary>
    <p className="price-history__note">Requested {start} – {end} (today’s session excluded).</p>
    {!failed && points.length > 0 && <p className="price-history__note">Returned range: {points[0].time} – {points[points.length - 1].time} · {points.length} observations. Returned bounds do not establish complete coverage. No missing sessions are filled; the line connects returned observations.</p>}
    <p className="price-history__note">Alpaca / IEX daily data, raw (unadjusted for splits or dividends); discontinuities may reflect corporate actions. Session dates are labels, not exact closing-trade times. Not a live quote. This window does not change the stock’s latest available price.</p>
    {response && <p className="price-history__note">Source: {response.source} · Status: {response.status}{response.mode === 'demo' ? ' · Demo/test data, not live evidence' : ''}{response.retrieved_at ? ` · Retrieved: ${response.retrieved_at}` : ''}</p>}
    {response && <SourceLink url={response.source_url}>Price history provider source</SourceLink>}
    </details>
    {/* Upstream v5.2.1 NOTICE (omitted from its npm tarball; verified in its tagged source). */}
    <p className="price-history__attribution">TradingView Lightweight Charts™<br />Copyright (с) 2025 TradingView, Inc. <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">https://www.tradingview.com/</a></p>
  </section>
}

function HistoryPlot({ points, symbol }: { points: Point[]; symbol: string }) {
  const { resolvedTheme } = useTheme()
  const host = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [selected, setSelected] = useState<Point | null>(null)
  const [canvasFailed, setCanvasFailed] = useState(false)
  const active = selected && points.includes(selected) ? selected : points[points.length - 1]
  const initialDark = useRef(resolvedTheme === 'dark')

  useEffect(() => {
    if (!host.current) return
    let chart: IChartApi
    try {
      chart = createChart(host.current, { ...palette(initialDark.current), height: 320, width: host.current.clientWidth || 320,
        rightPriceScale: { visible: true, borderVisible: false }, timeScale: { visible: true, borderVisible: false, timeVisible: false },
        crosshair: { mode: CrosshairMode.Magnet }, localization: { priceFormatter: money },
      })
    } catch {
      // Report imperative canvas initialization failure after this effect commits.
      let mounted = true
      queueMicrotask(() => { if (mounted) setCanvasFailed(true) })
      return () => { mounted = false }
    }
    chartRef.current = chart
    const series = chart.addSeries(LineSeries, { color: initialDark.current ? '#00C805' : '#008505', lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: true })
    series.setData(points)
    chart.timeScale().fitContent()
    const inspect = (event: Parameters<Parameters<IChartApi['subscribeCrosshairMove']>[0]>[0]) => {
      const datum = event.seriesData.get(series)
      if (datum && 'value' in datum) setSelected(points.find(point => point.time === datum.time) ?? null)
      else setSelected(null)
    }
    chart.subscribeCrosshairMove(inspect)
    chart.subscribeClick(inspect)
    const observer = new ResizeObserver(entries => {
      const width = entries[0]?.contentRect.width
      if (width && width > 0) chart.applyOptions({ width })
    })
    observer.observe(host.current)
    return () => {
      observer.disconnect()
      chart.unsubscribeCrosshairMove(inspect)
      chart.unsubscribeClick(inspect)
      chart.remove()
      chartRef.current = null
    }
  }, [points])

  useEffect(() => { chartRef.current?.applyOptions(palette(resolvedTheme === 'dark')) }, [resolvedTheme, points])

  return <>
    <output className="price-history__inspection" aria-label="Inspected daily close">{active.time} · Close {money(active.value)}</output>
    <div ref={host} className="price-history__canvas" role="img" aria-label={`${symbol} daily close line chart; use the inspection control or data table below for exact values`} />
    <p className="price-history__note">On touch screens, press and hold, then drag to inspect. Or use Inspect session with a keyboard.</p>
    {canvasFailed && <p role="status">Chart rendering is unavailable. All returned values remain accessible below.</p>}
    <label className="price-history__inspect">Inspect session <select value={active.time} onChange={event => setSelected(points.find(point => point.time === event.target.value) ?? null)}>{points.map(point => <option key={point.time} value={point.time}>{point.time} · {money(point.value)}</option>)}</select></label>
    <details className="price-history__table"><summary>Daily close data table ({points.length})</summary><div tabIndex={0} role="region" aria-label="Scrollable daily close table"><table><caption>{symbol} returned daily closes (USD)</caption><thead><tr><th scope="col">Session date</th><th scope="col">Close (USD)</th></tr></thead><tbody>{points.map(point => <tr key={point.time}><td>{point.time}</td><td>{money(point.value)}</td></tr>)}</tbody></table></div></details>
  </>
}
