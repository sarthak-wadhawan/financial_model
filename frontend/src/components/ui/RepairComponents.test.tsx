import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import { Modal, ConfirmDialog } from './index'
import { Term, SourceLink, displayDate, displayNumber } from './ResearchData'
import { api } from '../../services/api'

describe('repair shared primitives', () => {
  it.each(['javascript:alert(1)', 'data:text/html,unsafe', 'vbscript:msgbox(1)', '//www.sec.gov/path', '/relative', 'https://user:secret@www.sec.gov/path', 'https://www.sec.gov/%0d%0aunsafe', 'https://www.sec.gov/ bad', 'https://127.1/path', 'https://www.sec.gov/%ZZ'])('renders rejected source URL as plain text: %s', url => {
    render(<SourceLink url={url}>Retained SEC evidence</SourceLink>)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.getByText('Retained SEC evidence — link unavailable')).toBeInTheDocument()
  })
  it('preserves an accepted external evidence URL verbatim', () => {
    const url = 'HTTPS://WWW.SEC.GOV/Archives/example?accession=abc#evidence'
    render(<SourceLink url={url}>Retained SEC evidence</SourceLink>)
    expect(screen.getByRole('link')).toHaveAttribute('href', url)
    expect(screen.getByRole('link')).toHaveAttribute('rel', 'noopener noreferrer')
  })
  it('opens a term on hover but never makes an unsafe Learn more target clickable', async () => {
    vi.spyOn(api, 'getTermDefinition').mockResolvedValue({ term: 'EPS', short_definition: 'Earnings per share', long_definition: null, external_reference_url: 'javascript:alert(1)', reference_type: 'SEC', category: 'earnings', related_terms: [] })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><Term term="EPS" /></QueryClientProvider>)
    fireEvent.mouseEnter(screen.getByRole('button', { name: 'EPS' }).parentElement!)
    expect(await screen.findByText('Earnings per share')).toBeInTheDocument()
    expect(screen.getByText('Learn more — SEC — link unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
  it('keeps zero and date-only precision without invented timestamps', () => {
    expect(displayNumber(0)).toBe('0.0')
    expect(displayNumber(null)).toBe('Unavailable')
    expect(displayNumber(NaN)).toBe('Unavailable')
    expect(displayDate('2026-10-14')).toBe('2026-10-14')
    expect(displayDate('2026-10-14T00:00:00Z')).toBe('2026-10-14')
  })
  it('labels one modal, traps focus, respects Escape policy and restores focus', () => {
    const onClose = vi.fn()
    const trigger = document.createElement('button')
    document.body.append(trigger); trigger.focus()
    const view = render(<Modal isOpen onClose={onClose} title="Research dialog" closeOnEscape={false}><input aria-label="Name" /><button>Save</button></Modal>)
    expect(screen.getAllByRole('dialog')).toHaveLength(1)
    expect(screen.getByRole('dialog', { name: 'Research dialog' })).toBeInTheDocument()
    const close = screen.getByRole('button', { name: 'Close' }), save = screen.getByRole('button', { name: 'Save' })
    expect(close).toHaveFocus()
    fireEvent.keyDown(close, { key: 'Tab', shiftKey: true }); expect(save).toHaveFocus()
    fireEvent.keyDown(save, { key: 'Tab' }); expect(close).toHaveFocus()
    fireEvent.keyDown(close, { key: 'Escape' }); expect(onClose).not.toHaveBeenCalled()
    const input = screen.getByLabelText('Name')
    input.focus()
    view.rerender(<Modal isOpen onClose={() => onClose()} title="Research dialog" closeOnEscape={false}><input aria-label="Name" /><button>Save</button></Modal>)
    expect(input).toHaveFocus()
    view.unmount(); expect(trigger).toHaveFocus(); trigger.remove()
  })
  it('does not close a confirmation when clicking inside it', () => {
    const onClose = vi.fn(), onConfirm = vi.fn()
    render(<ConfirmDialog isOpen title="Remove symbol" message="Review this change" onClose={onClose} onConfirm={onConfirm} />)
    fireEvent.click(screen.getByText('Review this change'))
    expect(onClose).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(onConfirm).toHaveBeenCalledOnce()
  })
  it('fetches the real term schema on focus and supports dismissal/tap', async () => {
    vi.spyOn(api, 'getTermDefinition').mockResolvedValue({ term: 'EPS', short_definition: 'Earnings per share', long_definition: null, external_reference_url: 'https://www.sec.gov/', reference_type: 'SEC', category: 'earnings', related_terms: [] })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><Term term="EPS" /></QueryClientProvider>)
    const trigger = screen.getByRole('button', { name: 'EPS' })
    fireEvent.focus(trigger)
    expect(await screen.findByText('Earnings per share')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Learn more/ })).toHaveAttribute('href', 'https://www.sec.gov/')
    fireEvent.keyDown(trigger, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByText('Earnings per share')).not.toBeInTheDocument())
    fireEvent.click(trigger)
    expect(await screen.findByText('Earnings per share')).toBeInTheDocument()
    vi.restoreAllMocks()
  })
})
