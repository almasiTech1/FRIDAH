# FRIDAH Mobile — React Native App

React Native 0.86 app for tenants/landlords on the go. Web-only features not yet
in this app: AI tools (property assistant, rent estimator, listing generator,
maintenance triage) — see the [root README](../README.md) for the full feature
list across all three sub-projects.

The agency portal (Dashboard, Properties, Staff, Statements, Messages, Expenses,
Audit Log, Profile) **is** included here via the `AgencyTabs` navigator — it
swaps in automatically for any user with an active agency membership. Log in as
`agency@fridah.co.ke` / `Fridah@2026` to see it populated; see the
[root README](../README.md#demo-logins) for the full account table.

Agencies can only be registered by an administrator (Admin → Properties → Agencies).
Once a user has been made an Agency Admin, the app switches to `AgencyTabs`
automatically. No other role has any option to create or become an agency.

> The `android/` and `ios/` native project folders **are included** in this repo
> and are already wired to the correct app identifier (`com.fridahmobile` /
> `FridahMobile`) — you do not need to regenerate them with the React Native CLI.

---

## Prerequisites

- Node 18+
- For Android: Android Studio + an emulator (or a physical device with USB
  debugging enabled)
- For iOS (macOS only): Xcode + CocoaPods (`sudo gem install cocoapods`)

Follow the [React Native environment setup guide](https://reactnative.dev/docs/set-up-your-environment)
if you haven't got Android Studio/Xcode configured yet — this is the same for
any React Native project, nothing FRIDAH-specific about it.

---

## Setup

```bash
npm install
```

**iOS only** — install native pods (this generates `ios/Podfile.lock`, which is
gitignored on purpose since it's a local build artifact):

```bash
cd ios && pod install && cd ..
```

## Running

```bash
npx react-native start          # Metro bundler, keep running in its own terminal
```

In a second terminal:

```bash
npx react-native run-android    # or
npx react-native run-ios
```

### Pointing at your local backend instead of production

By default the app talks to `https://api.fridah.co.ke/api/v1`. To point it at a
backend running on your machine (see `fridah-backend/README.md`), set
`FRIDAH_API_URL` as an actual shell environment variable when starting Metro —
see `.env.example` in this directory for the full explanation and the right
loopback address to use for the Android emulator vs. iOS simulator vs. a
physical device:

```bash
FRIDAH_API_URL=http://10.0.2.2:8000/api/v1 npx react-native start --reset-cache
```

`--reset-cache` is required the first time you change it, since Metro caches the
inlined value.

---

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run lint         # eslint (currently ~41 pre-existing errors — see note below)
npm test             # jest — no test files exist yet
```

CI runs all three on every push via `.github/workflows/mobile-ci.yml` (lint is
currently non-blocking there until the existing errors are cleaned up; tests run
with `--passWithNoTests` since none exist yet).

**Known gap:** real-device/simulator testing (actually launching the app and
exercising auth, navigation, API calls, and error handling end-to-end) has not
been done — see the project status doc. `typecheck`/`lint`/`build` passing is
not a substitute for that.

---

## Project layout

```
fridah-mobile/
├── src/              Screens, navigation, API client, stores
├── App.tsx            Entry point
├── android/, ios/      Native projects (included, already configured)
├── babel.config.js     Includes transform-inline-environment-variables,
│                        which is what makes FRIDAH_API_URL work (see above)
└── .env.example        Documents FRIDAH_API_URL (not an auto-loaded .env file —
                         this app doesn't use one, unlike fridah-web/fridah-backend)
```
