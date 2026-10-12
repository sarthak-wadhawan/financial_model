import React from 'react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  ariaLabel?: string
}

export function LoadingSpinner({ size = 'md', className = '', ariaLabel = 'Loading' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'spinner-sm',
    md: 'spinner-md',
    lg: 'spinner-lg',
  }

  return (
    <div
      className={`loading-spinner ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label={ariaLabel}
      aria-live="polite"
    >
      <svg className="spinner-svg" viewBox="0 0 50 50" aria-hidden="true">
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="90 150"
        />
      </svg>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function Skeleton({ className = '', variant = 'text', width, height }: {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}) {
  return (
    <div
      className={`skeleton skeleton-${variant} ${className}`}
      style={{
        width,
        height,
      } as React.CSSProperties}
      aria-hidden="true"
    />
  )
}

export function SkeletonText({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`skeleton-text ${className}`} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton-line" />
      )}
    </div>
  )
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`skeleton-card ${className}`} aria-hidden="true">
      <div className="skeleton skeleton-rectangular" style={{ width: '100%', height: '120px' }} />
      <div className="skeleton skeleton-text" style={{ width: '60%', height: '16px', marginTop: '12px' }} />
      <div className="skeleton skeleton-text" style={{ width: '80%', height: '16px', marginTop: '8px' }} />
      <div className="skeleton skeleton-text" style={{ width: '40%', height: '16px', marginTop: '8px' }} />
    </div>
  )
}

export function SkeletonTable({ rows = 5, columns = 4, className = '' }: { rows?: number; columns?: number; className?: string }) {
  return (
    <div className={`skeleton-table ${className}`} aria-hidden="true">
      <div className="skeleton-table-header">
        {Array.from({ length: 1 }, (_, i) => (
          <div key={i} className="skeleton-table-row">
            {Array.from({ length: 4 }, (_, j) => (
              <div key={j} className="skeleton skeleton-rectangular" style={{ width: '100%', height: '20px' }} />
            ))}
          </div>
        ))}
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-table-row">
          {Array.from({ length: columns }, (_, j) => (
            <div key={j} className="skeleton skeleton-rectangular" style={{ width: '100%', height: '20px' }} />
          ))}
        </div>
      ))}
    </div>
  )
}