# S3 shared external-link policy

`frontend/src/utils/safeExternalUrl.ts` exports:

```ts
safeExternalUrl(input: unknown): string | undefined
```

This pure navigation validator makes no requests. Accepted absolute HTTP/HTTPS links
are returned **verbatim**, preserving source paths, queries, fragments and casing.
SEC, BLS and other public source domains are not restricted to an allowlist.

Rejected inputs: non-strings/empty strings, relative or protocol-relative URLs,
non-HTTP(S) schemes, missing/invalid hosts or ports, userinfo (including empty
userinfo), literal whitespace/C0/C1 controls, percent-encoded C0/C1 controls,
malformed percent escapes/encoded UTF-8, literal backslashes/angle brackets/double quotes/backticks,
encoded authorities, and hostname rewrites (e.g. shorthand/hex IPs or Unicode hosts
requiring implicit punycode conversion). Explicit punycode hosts are supported.
Standard hostname case normalization is permitted. Validation does not trim, decode,
repair, mutate stored evidence, or establish that the destination is trustworthy.
It is not a server-side SSRF/private-network filter or redirect safety guarantee.

## Page/component owner integration

For files directly in `frontend/src/pages` or `frontend/src/components`:

```tsx
import { safeExternalUrl } from '../utils/safeExternalUrl'

const sourceHref = safeExternalUrl(evidence.source_url)
// Keep the label/provenance visible even when the target is rejected.
return sourceHref ? (
  <a href={sourceHref} target="_blank" rel="noopener noreferrer">Source</a>
) : (
  <span>Source unavailable</span>
)
```

For `frontend/src/components/ui/ResearchData.tsx` (and other nested components),
use `import { safeExternalUrl } from '../../utils/safeExternalUrl'`.
Apply the helper to **every supplied external href**, including evidence, term,
filing, macro-calendar and landing-page source links. Do not fall back to the raw
URL, `#`, or a clickable empty href when validation fails. Preserve existing
labels/source metadata and `noopener noreferrer`. Page/component edits belong to
the page owner; this node does not integrate them or claim S3 is fully closed.

## Offline regression verification

From `frontend`, using the project-supported Node version:

```sh
npm test -- src/utils/safeExternalUrl.test.ts
```

Tests cover verbatim SEC/BLS HTTP(S) source links, hostile schemes, CRLF/control
characters, userinfo, malformed authorities/escapes, and parser surprises. They
do not fetch URLs or claim that browser script execution was demonstrated.
The toolchain owner manages Vitest/config/package repairs; this node changes none.
