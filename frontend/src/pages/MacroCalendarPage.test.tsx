import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MacroCalendarPage } from '../pages/MacroCalendarPage'

describe('MacroCalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page title and subtitle', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByRole('heading', { name: /Macro Calendar/i })).toBeInTheDocument()
    expect(screen.getByText(/Track market-moving economic events/i)).toBeInTheDocument()
  })

  it('renders importance filter dropdown', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByLabelText(/Importance/i)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /All Importance/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /CRITICAL/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /HIGH/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /MEDIUM/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /LOW/i })).toBeInTheDocument()
  })

  it('renders event type filter dropdown', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByLabelText(/Event Type/i)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /All Types/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /FOMC/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /CPI/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /NFP/i })).toBeInTheDocument()
  })

  it('renders tab navigation for Upcoming/Recent/All Events', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByRole('tab', { name: /Upcoming/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Recent/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /All Events/i })).toBeInTheDocument()
  })

  it('renders events table with correct headers', () => {
    render(<MacroCalendarPage />)
    const headers = ['Date', 'Event', 'Type', 'Actual', 'Forecast', 'Previous', 'Importance', 'Status', 'Source']
    headers.forEach(header => {
      expect(screen.getByRole('columnheader', { name: header })).toBeInTheDocument()
    })
  })

  it('renders legend for importance levels', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByRole('heading', { name: /Importance Levels/i })).toBeInTheDocument()
    expect(screen.getByText(/Market-moving events/i)).toBeInTheDocument()
    expect(screen.getByText(/Significant market impact expected/i)).toBeInTheDocument()
    expect(screen.getByText(/Moderate market impact/i)).toBeInTheDocument()
    expect(screen.getByText(/Minor market impact/i)).toBeInTheDocument()
  })

  it('renders legend for status', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByRole('heading', { name: /Status/i })).toBeInTheDocument()
    expect(screen.getByText(/RELEASED/i)).toBeInTheDocument()
    expect(screen.getByText(/SCHEDULED/i)).toBeInTheDocument()
    expect(screen.getByText(/UPDATED/i)).toBeInTheDocument()
  })

  it('filters events by importance', () => {
    render(<MacroCalendarPage />)
    const importanceSelect = screen.getByLabelText(/Importance/i)
    fireEvent.change(importanceSelect, { target: { value: 'CRITICAL' } })
    expect(importanceSelect).toHaveValue('CRITICAL')
  })

  it('filters events by type', () => {
    render(<MacroCalendarPage />)
    const typeSelect = screen.getByLabelText(/Event Type/i)
    fireEvent.change(typeSelect, { target: { value: 'FOMC' } })
    expect(typeSelect).toHaveValue('FOMC')
  })

  it('clears filters when clear button clicked', () => {
    render(<MacroCalendarPage />)
    const importanceSelect = screen.getByLabelText(/Importance/i)
    fireEvent.change(importanceSelect, { target: { value: 'CRITICAL' } })
    const clearButton = screen.getByRole('button', { name: /Clear Filters/i })
    fireEvent.click(clearButton)
    expect(importanceSelect).toHaveValue('all')
  })

  it('switches between Upcoming, Recent, and All Events tabs', () => {
    render(<MacroCalendarPage />)
    expect(screen.getByRole('tab', { name: /Upcoming/i })).toHaveAttribute('aria-selected', 'true')
    
    fireEvent.click(screen.getByRole('tab', { name: /Recent/i }))
    expect(screen.getByRole('tab', { name: /Recent/i })).toHaveAttribute('aria-selected', 'true')
    
    fireEvent.click(screen.getByRole('tab', { name: /All Events/i }))
    expect(screen.getByRole('tab', { name: /All Events/i })).toHaveAttribute('aria-selected', 'true')
  })
})