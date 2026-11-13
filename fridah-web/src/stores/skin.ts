import { defineStore } from 'pinia'

/**
 * Skins reproduce the dashboard looks from the design references:
 *  aurora   – dark teal glass, floating sidebar          (Code XR admin)
 *  sand     – warm frosted glass, black pill top-nav     (CodeXR CRM)
 *  fintech  – clean light cards, blue pill top-nav       (Finance overview)
 *  lime     – white + lime gradients, black accents      (Lumen CRM)
 *  smoke    – smoked dark glass, icon rail, orange       (Lumen / Vision leads)
 *  lavender – soft pastel, solid purple sidebar          (Deals)
 */
export type SkinId = 'aurora' | 'sand' | 'fintech' | 'lime' | 'smoke' | 'lavender'
export type NavMode = 'sidebar' | 'topnav' | 'rail'

export interface SkinDef {
  id: SkinId
  name: string
  mode: 'light' | 'dark'
  nav: NavMode
  swatch: [string, string, string]
  blurb: string
}

export const SKINS: SkinDef[] = [
  { id: 'aurora',   name: 'Aurora Glass',  mode: 'dark',  nav: 'sidebar', swatch: ['#0b2a3d', '#1f6f9c', '#38bdf8'], blurb: 'Dark teal glass with a floating sidebar' },
  { id: 'sand',     name: 'Sand Glass',    mode: 'light', nav: 'topnav',  swatch: ['#efe6d6', '#111111', '#f5d63d'], blurb: 'Warm frosted glass, black pill navigation' },
  { id: 'fintech',  name: 'Fintech Light', mode: 'light', nav: 'topnav',  swatch: ['#eceef5', '#ffffff', '#2f5bff'], blurb: 'Clean white cards, electric blue accents' },
  { id: 'lime',     name: 'Lime CRM',      mode: 'light', nav: 'topnav',  swatch: ['#f6f6f2', '#0f0f0f', '#c9ec2c'], blurb: 'Crisp white with lime gradients' },
  { id: 'smoke',    name: 'Smoked Glass',  mode: 'dark',  nav: 'rail',    swatch: ['#1a1613', '#3a2f27', '#ff9a3c'], blurb: 'Warm dark glass, icon rail, orange glow' },
  { id: 'lavender', name: 'Lavender Soft', mode: 'light', nav: 'sidebar', swatch: ['#efe9fb', '#7a67d8', '#ffb86b'], blurb: 'Soft pastel with a solid purple sidebar' },
]

/** What each portal opens with until the person picks their own skin. */
export const PORTAL_DEFAULT_SKIN: Record<string, SkinId> = {
  public: 'sand', admin: 'aurora', landlord: 'fintech', tenant: 'sand', agency: 'lime', hotel: 'smoke', provider: 'lavender',
}

const PAIR: Record<SkinId, SkinId> = {
  aurora: 'fintech', fintech: 'aurora', smoke: 'sand', sand: 'smoke', lime: 'aurora', lavender: 'smoke',
}

const K_SKIN = 'fridah-skin'
const K_WALL = 'fridah-wallpaper'
const K_COLLAPSED = 'fridah-sidebar-collapsed'

const read = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const write = (k: string, v: string | null) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v) } catch { /* storage may be unavailable */ } }

export const useSkinStore = defineStore('skin', {
  state: () => ({
    chosen: (read(K_SKIN) as SkinId | null) ?? null,
    fallback: 'fintech' as SkinId,
    wallpaper: read(K_WALL) as string | null,
    collapsed: read(K_COLLAPSED) === '1',
    compact: false,
  }),
  getters: {
    id: (s): SkinId => s.chosen ?? s.fallback,
    def(): SkinDef { return SKINS.find((k) => k.id === this.id) ?? SKINS[0] },
    isDark(): boolean { return this.def.mode === 'dark' },
    navMode(): NavMode { return this.def.nav },
  },
  actions: {
    setPortalDefault(portal: string) { this.fallback = PORTAL_DEFAULT_SKIN[portal] ?? 'fintech' },
    set(id: SkinId) { this.chosen = id; write(K_SKIN, id); this.apply() },
    resetToPortalDefault() { this.chosen = null; write(K_SKIN, null); this.apply() },
    toggleMode() { this.set(PAIR[this.id]) },
    toggleCollapsed() { this.collapsed = !this.collapsed; write(K_COLLAPSED, this.collapsed ? '1' : '0') },
    setWallpaper(dataUrl: string | null) {
      this.wallpaper = dataUrl
      try { write(K_WALL, dataUrl) } catch { /* image too large for storage: keep it for this session only */ }
      this.apply()
    },
    apply() {
      const el = document.documentElement
      el.dataset.skin = this.id
      el.dataset.mode = this.def.mode
      el.classList.toggle('dark', this.isDark)
      if (this.wallpaper) el.style.setProperty('--wallpaper', `url("${this.wallpaper}")`)
      else el.style.removeProperty('--wallpaper')
    },
    /** Called when leaving the portals so the public site keeps its own light/dark theme. */
    release() {
      const el = document.documentElement
      delete el.dataset.skin
      delete el.dataset.mode
      el.style.removeProperty('--wallpaper')
    },
  },
})
