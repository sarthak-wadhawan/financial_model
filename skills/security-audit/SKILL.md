---
name: security-audit
description: Audit application security, secrets, input handling, external content, and provider integrations.
---

# Instructions

Check:
- committed secrets
- frontend bundle secrets
- .env exposure
- API error leakage
- SQL parameterization
- XSS / unsafe HTML
- SSRF
- arbitrary file access
- redirects
- CORS
- webhook safety
- symbol/input validation
- provider rate limits
- external links

Never print secret values.

Report only secret type/location and remediation.

Return PASS / PARTIAL / FAIL.