# FRIDAH glass dashboards — design system

The signed-in portals (admin, landlord, tenant, agency, hotel, service provider) share one shell
(`src/layouts/PortalLayout.vue`) and one token file (`src/assets/skins.css`).

## Skins
Six looks reproduce the reference dashboards. Each portal opens with its own default until the person picks one
(stored in `localStorage` as `fridah-skin`).

| Skin | Look | Navigation | Portal default |
|---|---|---|---|
| `aurora` | dark teal glass, blue accent | floating sidebar | Admin |
| `fintech` | white cards, electric blue | black/blue pill top-nav | Landlord |
| `sand` | warm frosted glass, yellow accent | black pill top-nav | Tenant |
| `lime` | white + lime gradients | black pill top-nav | Agency |
| `smoke` | smoked dark glass, orange glow | icon rail | Hotel |
| `lavender` | pastel, solid purple sidebar | sidebar | Service provider |

Add a skin: add a token block in `skins.css` (`html[data-skin='name'] { … }`) and an entry in `SKINS` (`src/stores/skin.ts`).
Every colour in the shell and the dashboard blocks comes from the tokens (`--surface`, `--accent`, `--text`, `--c1…c5` …).

## Interactivity
- `Ctrl/⌘ + K` or `/` — command palette (pages, skins, sign out). Arrow keys + Enter.
- Palette icon in the top bar — switch skin live, upload a wallpaper (resized in-browser, stored locally), reset to the portal default.
- Collapsible sidebar / icon rail, mobile drawer, overflow "More" menu in top-nav skins.
- Bell popover with unread count, mark-all-read.
- Dashboards: 3/6/9-month range toggle, clickable bars, hoverable donut + legend, tick-off task lists, animated counters,
  pointer spotlight on cards, toasts, flip-card wallet, glass M-Pesa checkout.

## Building blocks (`src/components/ui`, `src/components/common/StatCard.vue`)
`StatCard` (KPI tile; variants `default | accent | inverse`), `InteractiveBars`, `DonutBreakdown`, `RingGauge`, `Sparkline`,
`SegTabs`, `TaskList`, `ActivityFeed`, `QuickTiles`, `DashHeader`, `CommandPalette`, `SkinSwitcher`, `NotifPopover`, `ToastHost`.
Existing screens (tables, forms, badges, cards) are re-skinned automatically by the overrides at the bottom of `skins.css`.

## Trend charts: real data
The landlord, hotel and admin dashboards plot real monthly figures from the API (`collected_by_month`, `revenue_by_month`,
`payouts_by_month`, produced by `monthly_totals()` in `apps/analytics/views.py`). If the API returns no history the chart
falls back to an estimated shape (`estimateSeries`) and is labelled "Estimated trend". Pass a `history` function to `useTrend`
to wire another dashboard.
