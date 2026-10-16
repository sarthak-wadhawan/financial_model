import { SourceLink } from '../ui/ResearchData'

export function Footer() {
  return <footer className="footer shell-footer">
    <p>Research, not financial advice. You make the decision.</p>
    <details><summary>Data sources</summary><div className="shell-sources">
      <SourceLink url="https://www.sec.gov/edgar">SEC EDGAR</SourceLink>
      <SourceLink url="https://www.bls.gov">BLS</SourceLink>
      <SourceLink url="https://www.federalreserve.gov">Federal Reserve</SourceLink>
      <SourceLink url="https://www.bea.gov">BEA</SourceLink>
      <SourceLink url="https://www.census.gov">Census Bureau</SourceLink>
      <SourceLink url="https://alpaca.markets">Alpaca Markets</SourceLink>
    </div></details>
  </footer>
}
