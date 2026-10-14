/** Validate a navigation target without fetching or rewriting source evidence. */
export function safeExternalUrl(input: unknown): string | undefined {
  if (typeof input !== 'string' || input.length === 0) return undefined

  // URL parsers silently strip whitespace/controls and treat backslashes as slashes.
  // Reject those inputs instead of repairing them into a different destination.
  // eslint-disable-next-line no-control-regex -- intentional control character rejection
  if (/[\s\u0000-\u001f\u007f-\u009f\\<>"`]/u.test(input)) return undefined
  if (/%(?![\da-f]{2})/i.test(input)) return undefined

  const match = /^(https?):\/\/([^/?#]+)(?:[/?#]|$)/i.exec(input)
  if (!match) return undefined
  const authority = match[2]
  // Even empty userinfo is disallowed; encoded hosts can conceal destinations.
  if (/[@%]/.test(authority)) return undefined
  const hostMatch = /^(\[[\da-f:.]+\]|[^:[\]]+)(?::(\d+))?$/i.exec(authority)
  if (!hostMatch) return undefined

  try {
    // Decode only for inspection, not output. Inspect characters rather than
    // individual UTF-8 bytes so legitimate percent-encoded Unicode survives.
    // eslint-disable-next-line no-control-regex -- intentional control character rejection
    if (/[\u0000-\u001f\u007f-\u009f]/u.test(decodeURI(input))) return undefined
    const url = new URL(input)
    if (!['https:', 'http:'].includes(url.protocol) || !url.hostname || url.username || url.password) {
      return undefined
    }
    // Reject shorthand/hex IPs, implicit IDN conversion and other host repairs.
    // Ordinary hostname case normalization is harmless.
    if (url.hostname.toLowerCase() !== hostMatch[1].toLowerCase()) return undefined
    return input
  } catch {
    return undefined
  }
}
