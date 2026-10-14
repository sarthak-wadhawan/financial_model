import { Link } from 'react-router-dom'
import { SourceLink } from '../ui/ResearchData'

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
              <li><SourceLink url="https://www.sec.gov/edgar">SEC EDGAR</SourceLink></li>
              <li><SourceLink url="https://www.bls.gov">BLS</SourceLink></li>
              <li><SourceLink url="https://www.federalreserve.gov">Federal Reserve</SourceLink></li>
              <li><SourceLink url="https://www.bea.gov">BEA</SourceLink></li>
              <li><SourceLink url="https://www.census.gov">Census Bureau</SourceLink></li>
              <li><SourceLink url="https://alpaca.markets">Alpaca Markets</SourceLink></li>
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
    </footer>
  )
}
