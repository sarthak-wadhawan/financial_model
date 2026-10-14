import { describe, expect, it } from 'vitest'
import { safeExternalUrl } from './safeExternalUrl'

describe('safeExternalUrl', () => {
  it.each([
    'https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm',
    'https://www.bls.gov/news.release/cpi.nr0.htm',
    'http://www.bls.gov/news.release/empsit.toc.htm',
    'HTTPS://WWW.SEC.GOV/Archives/?doc=a%20b&part=2#Item-2.02',
    'https://www.federalreserve.gov:443/newsevents/pressreleases.htm',
    'https://www.sec.gov',
    'https://www.sec.gov/path?next=https%3A%2F%2Fwww.bls.gov',
    'https://xn--bcher-kva.example/source',
    'https://www.sec.gov/source?title=Company%E2%80%99s%20results',
  ])('preserves an accepted source URL exactly: %s', (input) => {
    expect(safeExternalUrl(input)).toBe(input)
  })

  it.each([
    undefined, null, false, 42, {}, [], new URL('https://www.sec.gov'),
    '', ' ', '/source', '//www.sec.gov/source', 'www.sec.gov/source',
    'javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'data:text/html,test',
    'file:///etc/passwd', 'ftp://www.sec.gov/source', 'mailto:test@example.com',
    'https:example.com', 'https:/example.com', 'https:///example.com',
    'https:////example.com', 'https://', 'https://?query',
    ' https://www.sec.gov', 'https://www.sec.gov ',
    'https://www.sec.gov\r\nInjected: value', 'https://www.sec.gov/\nsource',
    'h\tttps://www.sec.gov', 'https://www.sec.gov/\u0000source',
    'https://www.sec.gov/\u007fsource', 'https://www.sec.gov/\u0085source',
    'https://www.sec.gov/%0d%0aInjected', 'https://www.sec.gov/%00',
    'https://www.sec.gov/%1f', 'https://www.sec.gov/%7F',
    'https://www.sec.gov/%C2%85', 'https://www.sec.gov/%09',
    'https://www.sec.gov/%FF',
    'https://www.sec.gov/%', 'https://www.sec.gov/%xy',
    'https://user:password@www.sec.gov/source', 'https://user@www.sec.gov',
    'https://@www.sec.gov', 'https://www.sec.gov@evil.example',
    'https://www.sec.gov\\@evil.example', 'https://www.sec.gov/\\evil.example',
    'https://%77ww.sec.gov/source', 'https://www.sec.gov%2Fevil.example',
    'https://www.sec.gov:invalid', 'https://www.sec.gov:65536',
    'https://www.sec.gov:', 'https://[invalid]/source',
    'https://127.1/source', 'https://0x7f000001/source',
    'https://bücher.example/source', 'https://www.sec.gov/a b',
    'https://www.sec.gov/<source>',
  ])('rejects unsafe, missing or ambiguous input: %s', (input) => {
    expect(safeExternalUrl(input)).toBeUndefined()
  })

  it('does not coerce untrusted objects to strings', () => {
    expect(safeExternalUrl({ toString: () => { throw new Error('must not execute') } })).toBeUndefined()
  })
})
