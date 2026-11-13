# FRIDAH Web — Vue 3 + TypeScript + Vite

Web portal for landlords, tenants, agency staff, service providers, hotel/BnB
owners, and admins, plus a public marketing site. Includes the AI tools (property
assistant, rent estimator, listing generator, maintenance triage) that aren't
yet in the mobile app.

**Requires:** Node 18+.

> This file covers the web app only. See the [root README](../README.md) for the
> full-stack Docker quick start and demo login credentials.

---

## Setup

```bash
npm install
```

The app talks to the backend at `http://localhost:8000/api/v1` by default. If
your backend runs somewhere else, or you want interactive maps (property/hotel
search, address autocomplete, the office location on the Contact page):

```bash
cp .env.example .env
# edit .env: VITE_API_BASE_URL, and optionally VITE_GOOGLE_MAPS_API_KEY
```

`VITE_GOOGLE_MAPS_API_KEY` is optional — get one from the
[Google Cloud Console](https://console.cloud.google.com/google/maps-apis) with
"Maps JavaScript API" enabled. Without it, map components show a clean "Map
unavailable" placeholder instead of breaking.

## Running

```bash
npm run dev
```

Opens at `http://localhost:5173`.

### Agency portal

Any logged-in user can start their own agency from the "🏢 Manage properties as
an Agency" link in the sidebar (routes to `/agency/dashboard`, which doubles as
the "+ Create an Agency" screen until they belong to one). For a pre-populated
demo, log in as `agency@fridah.co.ke` / `Fridah@2026` — see the
[root README](../README.md#demo-logins) for the full account table.

## Building for production

```bash
npm run build
```

Runs `vue-tsc -b` (type-check) then `vite build`; output goes to `dist/`. CI runs
this on every push via `.github/workflows/web-ci.yml`, along with `npm audit`.

## Preview a production build locally

```bash
npm run preview
```

## Imagery & animation

Property and hotel cards use the host's uploaded photos when they exist. When none
have been uploaded yet (e.g. fresh demo data), they fall back to real stock photography
from `src/utils/stockImages.ts` - hosted on Unsplash's CDN under the
[Unsplash License](https://unsplash.com/license) (free for commercial use, no
attribution required). The same file feeds the Home page hero and photo showcase.

For production, consider downloading the handful of images you keep and self-hosting
them from `public/` rather than hot-linking, so the site doesn't depend on a third-party CDN.

Scroll animations come from the shared `v-reveal` directive (`src/directives/reveal.ts`);
the hero float/Ken Burns effects are CSS-only and switch off automatically for visitors
who have "reduce motion" enabled.

## Static hosting (e.g. Cloudflare Pages)

`public/_redirects` makes browser-history routes (like `/agency/dashboard`) work on a
refresh or direct link. Build with `VITE_API_BASE_URL` set to your deployed backend,
then upload the contents of `dist/`.
