// k6 load test for the FRIDAH API.  Run against STAGING, never production.
//   k6 run -e BASE_URL=https://staging-api.example.com -e PROFILE=load \
//          -e LANDLORD_EMAIL=... -e LANDLORD_PASSWORD=... -e TENANT_EMAIL=... -e TENANT_PASSWORD=... loadtest/load.js
// PROFILE: smoke (1 user, 1 min) | load (ramp to 100) | stress (ramp to 400) | soak (50 users, 30 min)
// Before running, raise the rate limits on the staging server (see .env.production.example):
//   THROTTLE_ANON=100000/hour THROTTLE_USER=100000/hour THROTTLE_LOGIN=1000/min
import http from 'k6/http'
import { check, group, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const BASE = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const API = `${BASE}/api/v1`
const errors = new Rate('app_errors')
const dashboardMs = new Trend('dashboard_ms', true)

const PROFILES = {
  smoke: [{ duration: '1m', target: 1 }],
  load: [{ duration: '2m', target: 25 }, { duration: '5m', target: 100 }, { duration: '2m', target: 0 }],
  stress: [{ duration: '2m', target: 100 }, { duration: '4m', target: 250 }, { duration: '4m', target: 400 }, { duration: '2m', target: 0 }],
  soak: [{ duration: '3m', target: 50 }, { duration: '30m', target: 50 }, { duration: '2m', target: 0 }],
}

export const options = {
  stages: PROFILES[__ENV.PROFILE || 'smoke'],
  thresholds: {
    http_req_failed: ['rate<0.01'],          // under 1% failed requests
    http_req_duration: ['p(95)<800'],        // 95% of requests under 800 ms
    app_errors: ['rate<0.01'],
    dashboard_ms: ['p(95)<1200'],
  },
}

function login(email, password) {
  if (!email) return null
  const r = http.post(`${API}/auth/login/`, JSON.stringify({ email, password }), { headers: { 'Content-Type': 'application/json' } })
  const body = r.status === 200 ? r.json() : null
  return body && (body.data?.access || body.access || body.data?.tokens?.access) || null
}

// Runs once: log in the test accounts so the virtual users reuse the tokens.
export function setup() {
  return {
    landlord: login(__ENV.LANDLORD_EMAIL, __ENV.LANDLORD_PASSWORD),
    tenant: login(__ENV.TENANT_EMAIL, __ENV.TENANT_PASSWORD),
  }
}

const auth = (t) => ({ headers: { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } })
const ok = (r, name) => { const pass = check(r, { [`${name} 2xx`]: (x) => x.status >= 200 && x.status < 300 }); errors.add(!pass); return pass }

export default function (tokens) {
  const roll = Math.random()

  if (roll < 0.5 || (!tokens.landlord && !tokens.tenant)) {
    // 50%: anonymous visitor browsing the public site
    group('visitor', () => {
      ok(http.get(`${BASE}/healthz`), 'healthz')
      ok(http.get(`${API}/properties/`), 'properties list')
      sleep(1 + Math.random() * 2)
      ok(http.get(`${API}/listings/`), 'listings list')
    })
  } else if (roll < 0.8 && tokens.tenant) {
    // 30%: tenant opens the dashboard and invoices
    group('tenant', () => {
      const d = http.get(`${API}/analytics/dashboard/tenant/`, auth(tokens.tenant)); dashboardMs.add(d.timings.duration); ok(d, 'tenant dashboard')
      ok(http.get(`${API}/invoices/`, auth(tokens.tenant)), 'tenant invoices')
      ok(http.get(`${API}/me/`, auth(tokens.tenant)), 'me')
    })
  } else if (tokens.landlord) {
    // 20%: landlord checks portfolio
    group('landlord', () => {
      const d = http.get(`${API}/analytics/dashboard/landlord/`, auth(tokens.landlord)); dashboardMs.add(d.timings.duration); ok(d, 'landlord dashboard')
      ok(http.get(`${API}/properties/`, auth(tokens.landlord)), 'landlord properties')
      ok(http.get(`${API}/invoices/`, auth(tokens.landlord)), 'landlord invoices')
    })
  }
  sleep(1 + Math.random() * 3)
}
