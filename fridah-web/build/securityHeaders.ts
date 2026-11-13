/**
 * Browser security headers for the deployed web app, generated at build time so the policy always matches the
 * configured API address. Cloudflare Pages / Netlify read `dist/_headers`; for nginx include the generated snippet.
 *
 * The Content-Security-Policy is the main defence for login tokens kept in the browser: even if some script tried to
 * run, it could not load from any other website, send data to any other website, or be injected inline.
 */
export function apiOrigin(apiBaseUrl: string | undefined): string {
  try { return new URL(apiBaseUrl || 'https://api.fridah.co.ke/api/v1').origin } catch { return "'self'" }
}

export function contentSecurityPolicy(apiBaseUrl?: string): string {
  const api = apiOrigin(apiBaseUrl)
  // Hosts Google Maps needs (see developers.google.com/maps/documentation/javascript/content-security-policy).
  const google = 'https://*.googleapis.com https://*.gstatic.com https://*.google.com'
  return [
    "default-src 'self'",
    `script-src 'self' ${google} blob:`,
    `style-src 'self' 'unsafe-inline' ${google}`,
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: blob: https:",
    `connect-src 'self' ${api} ${google} data: blob:`,
    "worker-src 'self' blob:",
    "frame-src 'self' https://*.google.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    'upgrade-insecure-requests',
  ].join('; ')
}

export function securityHeaders(apiBaseUrl?: string): Record<string, string> {
  return {
    'Content-Security-Policy': contentSecurityPolicy(apiBaseUrl),
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(self), payment=()',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  }
}

/** Format for Cloudflare Pages and Netlify (`_headers`). */
export function headersFile(apiBaseUrl?: string): string {
  const lines = Object.entries(securityHeaders(apiBaseUrl)).map(([k, v]) => `  ${k}: ${v}`)
  return `/*\n${lines.join('\n')}\n\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n`
}

/** Format for nginx: `include security-headers.nginx.conf;` inside the server block. */
export function nginxSnippet(apiBaseUrl?: string): string {
  return Object.entries(securityHeaders(apiBaseUrl)).map(([k, v]) => `add_header ${k} "${v}" always;`).join('\n') + '\n'
}
