import React from 'react'
import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="footer" role="contentinfo">
      <div className="footer-container">
        <div className="footer-section">
          <h4>Product</h4>
          <nav aria-label="Product links">
            <ul>
              <li><Link to="/scanner">Scanner</Link></li>
              <li><Link to="/macro">Macro Calendar</Link></li>
              <li><Link to="/search">Search</Link></li>
              <li><Link to="/settings">Settings</Link></li>
            </ul>
          </nav>
        </div>

        <div className="footer-section">
          <h4>Data Sources</h4>
          <nav aria-label="Data sources">
            <ul>
              <li><a href="https://www.sec.gov/edgar" target="_blank" rel="noopener noreferrer">SEC EDGAR</a></li>
              <li><a href="https://www.bls.gov" target="_blank" rel="noopener noreferrer">BLS</a></li>
              <li><a href="https://www.federalreserve.gov" target="_blank" rel="noopener noreferrer">Federal Reserve</a></li>
              <li><a href="https://www.bea.gov" target="_blank" rel="noopener noreferrer">BEA</a></li>
              <li><a href="https://www.census.gov" target="_blank" rel="noopener noreferrer">Census Bureau</a></li>
              <li><a href="https://alpaca.markets" target="_blank" rel="noopener noreferrer">Alpaca Markets</a></li>
            </ul>
          </nav>
        </div>

        <div className="footer-section">
          <h4>Legal</h4>
          <nav aria-label="Legal links">
            <ul>
              <li><Link to="/privacy">Privacy Policy</Link></li>
              <li><Link to="/terms">Terms of Service</Link></li>
              <li><Link to="/disclaimer">Disclaimer</Link></li>
            </ul>
          </nav>
        </div>

        <div className="footer-section">
          <h4>Resources</h4>
          <nav aria-label="Resources">
            <ul>
              <li><Link to="/docs">Documentation</Link></li>
              <li><Link to="/api/docs">API Docs</Link></li>
              <li><Link to="/github">GitHub</Link></li>
              <li><Link to="/changelog">Changelog</Link></li>
            </ul>
          </nav>
        </div>
      </div>

      <div className="footer-bottom">
        <p>Trading Copilot - Deterministic Financial Intelligence. Not financial advice.</p>
        <p>Data provided by SEC EDGAR, BLS, Federal Reserve, BEA, Census, Alpaca Markets.</p>
      </div>
    </div>
  )
}