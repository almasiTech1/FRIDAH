import { describe, it, expect } from 'vitest'
import { contentSecurityPolicy, headersFile, nginxSnippet, apiOrigin } from '../../build/securityHeaders'

describe('web security headers', () => {
  it('only allows scripts from this site and Google Maps, never inline or eval', () => {
    const csp = contentSecurityPolicy('https://api.example.co.ke/api/v1')
    const script = csp.split('; ').find((d) => d.startsWith('script-src'))!
    expect(script).not.toMatch(/unsafe-inline|unsafe-eval/)
    expect(script).not.toContain(' https: ')               // never "any website"
    expect(script).not.toMatch(/\*\s|\s\*(\s|$)/)
    expect(csp).toContain("object-src 'none'")
    expect(csp).toContain("frame-ancestors 'none'")
  })
  it('lets the app talk only to its own API address', () => {
    expect(apiOrigin('https://api.example.co.ke/api/v1')).toBe('https://api.example.co.ke')
    expect(contentSecurityPolicy('https://api.example.co.ke/api/v1')).toContain("connect-src 'self' https://api.example.co.ke ")
    expect(apiOrigin('not a url')).toBe("'self'")
  })
  it('lets Google Maps load (its script, tiles, fonts and place search) without opening the door wider', () => {
    const csp = contentSecurityPolicy()
    const dir = (n: string) => csp.split('; ').find((d) => d.startsWith(n))!
    for (const host of ['https://*.googleapis.com', 'https://*.gstatic.com', 'https://*.google.com']) {
      expect(dir('script-src')).toContain(host); expect(dir('connect-src')).toContain(host); expect(dir('style-src')).toContain(host)
    }
    expect(dir('worker-src')).toContain('blob:')
    expect(dir('img-src')).toContain('https:')             // map tiles and photos
    expect(dir('script-src')).not.toContain('http:')
  })
  it('produces both deployment formats', () => {
    expect(headersFile()).toMatch(/^\/\*\n {2}Content-Security-Policy: .+\n/)
    expect(headersFile()).toContain('Strict-Transport-Security')
    expect(nginxSnippet()).toMatch(/add_header Content-Security-Policy ".+" always;/)
  })
})
