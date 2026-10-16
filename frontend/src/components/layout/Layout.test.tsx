import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { createRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../../App'
import { ThemeProvider } from '../../context/ThemeContext'
import { api } from '../../services/api'
import { Header } from './Header'

function HistoryControls() {
  const navigate = useNavigate()
  return <><button onClick={() => navigate(-1)}>Back</button><button onClick={() => navigate(1)}>Forward</button><button onClick={() => navigate('/stocks/TMO')}>Open stock</button></>
}
function mountHeader(route = '/search?q=TMO') {
  return render(<MemoryRouter initialEntries={[route]}><ThemeProvider><Header navigationExpanded onToggleNavigation={() => {}} toggleRef={createRef<HTMLButtonElement>()} /><HistoryControls /><Location /></ThemeProvider></MemoryRouter>)
}

function Location() { return <output aria-label="Current route">{useLocation().search}</output> }
function mount(mobile = false, route = '/search') {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({ matches: mobile && query.includes('max-width'), media: query, addEventListener: vi.fn(), removeEventListener: vi.fn() })))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[route]}><ThemeProvider><App /><Location /></ThemeProvider></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  localStorage.clear()
  vi.spyOn(api, 'searchSymbols').mockResolvedValue([{ symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', type: 'stock', source: 'fixture' }])
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('UX1 application shell', () => {
  it('synchronizes global search with direct URLs and Back/Forward history', async () => {
    mountHeader()
    const user = userEvent.setup()
    const input = screen.getByRole('searchbox', { name: 'Search stocks or companies' })
    expect(input).toHaveValue('TMO')
    await user.clear(input)
    await user.type(input, 'MSFT{Enter}')
    expect(screen.getByLabelText('Current route')).toHaveTextContent('?q=MSFT')
    await user.click(screen.getByRole('button', { name: 'Back', exact: true }))
    expect(screen.getByLabelText('Current route')).toHaveTextContent('?q=TMO')
    expect(input).toHaveValue('TMO')
    await user.click(screen.getByRole('button', { name: 'Forward', exact: true }))
    expect(input).toHaveValue('MSFT')
  })
  it('preserves unsubmitted typing across unrelated rerenders and stock navigation', async () => {
    mountHeader()
    const user = userEvent.setup()
    const input = screen.getByRole('searchbox', { name: 'Search stocks or companies' })
    await user.clear(input)
    await user.type(input, 'Apple & Co')
    await user.click(screen.getByRole('button', { name: 'Dark theme', exact: true }))
    expect(input).toHaveValue('Apple & Co')
    await user.click(screen.getByRole('button', { name: 'Open stock', exact: true }))
    expect(input).toHaveValue('Apple & Co')
    await user.click(screen.getByRole('button', { name: 'Back', exact: true }))
    expect(input).toHaveValue('TMO')
  })
  it('submits trimmed and encoded global queries to a working result route', async () => {
    mount()
    await screen.findByRole('heading', { name: 'Search Stocks' })
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search stocks or companies' }), { target: { value: '  Apple & Co  ' } })
    fireEvent.submit(screen.getByRole('search', { name: 'Global stock search' }))
    expect(screen.getByLabelText('Current route')).toHaveTextContent('?q=Apple%20%26%20Co')
    expect(await screen.findByRole('link', { name: /AAPL Apple Inc/ })).toHaveAttribute('href', '/stocks/AAPL')
    expect(api.searchSymbols).toHaveBeenCalledWith('Apple & Co')
  })
  it('does not submit blank searches', async () => {
    mount()
    await screen.findByRole('heading', { name: 'Search Stocks' })
    fireEvent.submit(screen.getByRole('search', { name: 'Global stock search' }))
    expect(screen.getByLabelText('Current route')).toBeEmptyDOMElement()
    expect(api.searchSymbols).not.toHaveBeenCalled()
  })
  it('loads a directly shared search URL and reports provider failure honestly', async () => {
    vi.mocked(api.searchSymbols).mockRejectedValueOnce(new Error('offline'))
    mount(false, '/search?q=V')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load matching stocks')
    fireEvent.click(screen.getByRole('button', { name: 'Retry search' }))
    expect(await screen.findByRole('link', { name: /AAPL Apple Inc/ })).toBeInTheDocument()
    expect(api.searchSymbols).toHaveBeenCalledWith('V')
  })
  it('distinguishes empty URL search results from failure', async () => {
    vi.mocked(api.searchSymbols).mockResolvedValue([])
    mount(false, '/search?q=ZZZZ')
    expect(await screen.findByText('No matching stocks available.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
  it('collapses the desktop sidebar while preserving labeled route access', async () => {
    const { container } = mount()
    await screen.findByRole('heading', { name: 'Search Stocks' })
    const user = userEvent.setup()
    screen.getByRole('button', { name: 'Collapse navigation' }).focus()
    await user.keyboard('{Enter}')
    expect(container.querySelector('.shell-layout')).toHaveClass('navigation-collapsed')
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('link', { name: 'Watchlists' })).toHaveAttribute('href', '/watchlists')
    expect(screen.getAllByRole('navigation', { name: 'Main navigation' })).toHaveLength(1)
    await user.keyboard(' ')
    expect(container.querySelector('.shell-layout')).not.toHaveClass('navigation-collapsed')
  })
  it('opens one mobile navigation and Escape returns focus to its toggle', async () => {
    mount(true)
    await screen.findByRole('heading', { name: 'Search Stocks' })
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).not.toBeInTheDocument()
    const user = userEvent.setup()
    const toggle = screen.getByRole('button', { name: 'Expand navigation' })
    toggle.focus()
    await user.keyboard('{Enter}')
    screen.getByRole('link', { name: 'Scanner' }).focus()
    await user.keyboard('{Escape}')
    expect(toggle).toHaveFocus()
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).not.toBeInTheDocument()
  })
  it('closes mobile navigation after choosing a route', async () => {
    mount(true)
    await screen.findByRole('heading', { name: 'Search Stocks' })
    fireEvent.click(screen.getByRole('button', { name: 'Expand navigation' }))
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveFocus()
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).not.toBeInTheDocument()
  })
  it('supports keyboard theme selection through the existing persistent context', async () => {
    mount()
    await screen.findByRole('heading', { name: 'Search Stocks' })
    const user = userEvent.setup()
    screen.getByRole('button', { name: 'Dark theme' }).focus()
    await user.keyboard(' ')
    await waitFor(() => expect(document.documentElement).toHaveClass('dark'))
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(screen.getByRole('button', { name: 'Dark theme' })).toHaveAttribute('aria-pressed', 'true')
    screen.getByRole('button', { name: 'Light theme' }).focus()
    await user.keyboard('{Enter}')
    expect(document.documentElement).toHaveClass('light')
    screen.getByRole('button', { name: 'System theme' }).focus()
    await user.keyboard('{Enter}')
    expect(localStorage.getItem('theme')).toBe('system')
  })
})
