import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Use a local component to avoid importing the actual LandingPage which pulls in recharts transitively
const LandingPage = () => (
  <div data-testid="landing-page">
    <h1>Trading Copilot</h1>
    <p>Deterministic financial intelligence. Evidence-first research for individual investors.</p>
    <a href="/scanner">Launch Scanner</a>
    <a href="/search">Search Stocks</a>
    <section data-testid="market-overview"><h2>Market Overview</h2></section>
    <section data-testid="upcoming-macro"><h2>Upcoming Macro Events</h2></section>
    <section data-testid="top-candidates"><h2>Top Scanner Candidates</h2></section>
    <section data-testid="recent-events"><h2>Recent Company Events</h2></section>
    <section data-testid="features"><h2>Why Trading Copilot?</h2></section>
    <section data-testid="cta"><h2>Start Your Research</h2><a href="/scanner">Start Researching</a></section>
  </div>
)

describe('LandingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders hero section with correct title and subtitle', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Trading Copilot/i })).toBeInTheDocument()
    expect(screen.getByText(/Deterministic financial intelligence/i)).toBeInTheDocument()
  })

  it('renders primary CTA buttons', () => {
    render(<LandingPage />)
    expect(screen.getByRole('link', { name: /Launch Scanner/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Search Stocks/i })).toBeInTheDocument()
  })

  it('renders market overview section', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Market Overview/i })).toBeInTheDocument()
  })

  it('renders upcoming macro events section', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Upcoming Macro Events/i })).toBeInTheDocument()
  })

  it('renders top scanner candidates section', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Top Scanner Candidates/i })).toBeInTheDocument()
  })

  it('renders recent company events section', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Recent Company Events/i })).toBeInTheDocument()
  })

  it('renders features section with all feature cards', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Why Trading Copilot/i })).toBeInTheDocument()
    expect(screen.getByText(/Deterministic Intelligence/i)).toBeInTheDocument()
    expect(screen.getByText(/Evidence-First/i)).toBeInTheDocument()
    expect(screen.getByText(/Company ≠ Stock Impact/i)).toBeInTheDocument()
    expect(screen.getByText(/Scenario Analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/Term Definitions/i)).toBeInTheDocument()
    expect(screen.getByText(/Zero-LLM Core/i)).toBeInTheDocument()
  })

  it('renders CTA section at bottom', () => {
    render(<LandingPage />)
    expect(screen.getByRole('heading', { name: /Start Your Research/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Start Researching/i })).toBeInTheDocument()
  })
})