<template>
  <div class="fx-shell" :class="skin.navMode === 'topnav' ? 'topnav' : ''">
    <div class="fx-ambient" :class="{ 'has-wall': !!skin.wallpaper }"><i class="fx-blob a" /><i class="fx-blob b" /></div>
    <div v-if="drawer" class="fx-scrim" @click="drawer = false" />

    <!-- Sidebar (sidebar + rail skins; becomes a drawer on small screens) -->
    <aside class="fx-sidebar" :class="{ rail: railed, open: drawer }" aria-label="Main navigation">
      <div class="fx-brand">
        <div class="fx-logo">F</div>
        <div class="fx-brand-text"><b>FRIDAH</b><span>{{ portalLabel }}</span></div>
        <button class="fx-collapse ml-auto" :title="railed ? 'Expand sidebar' : 'Collapse sidebar'" @click="skin.toggleCollapsed()"><ChevronsLeft :size="16" /></button>
      </div>
      <button class="fx-sb-search" @click="palette = true"><Search :size="16" /><span>Search…</span><kbd>{{ isMac ? '⌘' : 'Ctrl' }} K</kbd></button>
      <nav class="fx-nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" custom v-slot="{ isActive, navigate }">
          <button class="fx-nav-item" :class="{ active: isActive }" :title="item.label" @click="navigate(); drawer = false">
            <component :is="item.icon" />
            <span class="fx-label">{{ item.label }}</span>
            <span v-if="item.badge" class="fx-badge">{{ item.badge }}</span>
          </button>
        </RouterLink>
      </nav>
      <div class="fx-sb-foot">
        <div class="fx-user">
          <div class="fx-avatar">{{ initials }}</div>
          <div class="fx-user-meta"><b>{{ auth.user?.first_name }} {{ auth.user?.last_name }}</b><span>{{ auth.user?.email }}</span></div>
          <button class="fx-collapse" style="align-self:center" :title="$t('common.logout')" @click="handleLogout"><LogOut :size="15" /></button>
        </div>
      </div>
    </aside>

    <div ref="scroller" class="fx-main">
      <header class="fx-topbar">
        <button class="fx-icon-btn fx-burger" aria-label="Open menu" @click="drawer = true"><Menu /></button>
        <BackButton v-if="showBack" :fallback="navItems[0]?.to || '/'" />
        <div class="fx-brand-inline">
          <div class="fx-logo" style="width:36px;height:36px;border-radius:12px">F</div>
        </div>
        <nav v-if="skin.navMode === 'topnav'" class="fx-pills" aria-label="Sections">
          <RouterLink v-for="item in primary" :key="item.to" :to="item.to" class="fx-pill" active-class="active">{{ item.label }}</RouterLink>
          <div v-if="overflow.length" ref="moreRoot" class="fx-pop-wrap">
            <button class="fx-pill" :class="{ active: overflowActive }" @click="more = !more">More <ChevronDown :size="13" style="display:inline;vertical-align:-2px" /></button>
            <div v-if="more" class="fx-pop" style="right:auto;left:0;width:260px;transform-origin:top left">
              <RouterLink v-for="item in overflow" :key="item.to" :to="item.to" class="fx-pop-item" :class="{ sel: route.path.startsWith(item.to) }" @click="more = false">
                <span class="fx-ico"><component :is="item.icon" /></span><b class="font-semibold">{{ item.label }}</b>
              </RouterLink>
            </div>
          </div>
        </nav>
        <div class="fx-title">
          <h1>{{ currentPageTitle }}</h1>
          <p class="sub">{{ dateStr }}</p>
        </div>
        <div class="fx-grow" />
        <button class="fx-search" @click="palette = true"><Search :size="16" /><span>Search pages & actions</span><kbd>{{ isMac ? '⌘' : 'Ctrl' }} K</kbd></button>
        <button class="fx-icon-btn fx-search-icon" aria-label="Search" @click="palette = true"><Search /></button>
        <SkinSwitcher />
        <LanguageSwitcher class="hidden sm:block" />
        <button class="fx-icon-btn" :title="skin.isDark ? 'Light look' : 'Dark look'" aria-label="Toggle light or dark" @click="skin.toggleMode()"><Sun v-if="skin.isDark" /><Moon v-else /></button>
        <NotifPopover :route="notifRoute" />
        <div ref="userRoot" class="fx-pop-wrap">
          <button class="fx-avatar" style="width:40px;height:40px;border-radius:14px;font-size:13px;cursor:pointer" aria-label="Account" @click="userMenu = !userMenu">{{ initials }}</button>
          <div v-if="userMenu" class="fx-pop" style="width:250px">
            <div class="px-3 py-2"><b class="block text-sm">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</b><small style="color:var(--muted)">{{ auth.user?.email }}</small></div>
            <button v-if="profileRoute" class="fx-pop-item" @click="userMenu = false; router.push(profileRoute)"><span class="fx-ico"><User /></span><b class="font-semibold">My profile</b></button>
            <button class="fx-pop-item" @click="userMenu = false; palette = true"><span class="fx-ico"><Search /></span><b class="font-semibold">Quick search</b><span class="fx-kbd ml-auto">{{ isMac ? '⌘' : 'Ctrl' }} K</span></button>
            <button class="fx-pop-item" @click="handleLogout"><span class="fx-ico"><LogOut /></span><b class="font-semibold">{{ $t('common.logout') }}</b></button>
          </div>
        </div>
      </header>

      <main class="fx-content">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in"><component :is="Component" /></Transition>
        </RouterView>
      </main>
    </div>

    <CommandPalette v-model="palette" :nav-items="navItems" :notif-route="notifRoute" />
    <ToastHost />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { Search, Menu, Sun, Moon, LogOut, User, ChevronDown, ChevronsLeft } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useSkinStore } from '@/stores/skin'
import { useThemeStore } from '@/stores/theme'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import SkinSwitcher from '@/components/ui/SkinSwitcher.vue'
import NotifPopover from '@/components/ui/NotifPopover.vue'
import CommandPalette from '@/components/ui/CommandPalette.vue'
import ToastHost from '@/components/ui/ToastHost.vue'
import BackButton from '@/components/ui/BackButton.vue'

const props = defineProps<{
  gradient?: [string, string]
  portalLabel: string
  navItems: { to: string; label: string; icon: any; badge?: string | number }[]
  notifRoute?: string
}>()

const auth = useAuthStore(); const notifStore = useNotificationsStore(); const skin = useSkinStore(); const theme = useThemeStore()
const route = useRoute(); const router = useRouter()

const portal = computed(() => route.path.split('/')[1] || 'tenant')
skin.setPortalDefault(portal.value)
skin.apply()

const palette = ref(false); const drawer = ref(false); const more = ref(false); const userMenu = ref(false)
const moreRoot = ref<HTMLElement>(); const userRoot = ref<HTMLElement>(); const scroller = ref<HTMLElement>()
onClickOutside(moreRoot, () => (more.value = false)); onClickOutside(userRoot, () => (userMenu.value = false))

const railed = computed(() => skin.navMode === 'rail' || skin.collapsed)
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
const PRIMARY_COUNT = 6
const primary = computed(() => props.navItems.slice(0, PRIMARY_COUNT))
const overflow = computed(() => props.navItems.slice(PRIMARY_COUNT))
const overflowActive = computed(() => overflow.value.some((i) => route.path.startsWith(i.to)))
const showBack = computed(() => !!props.navItems.length && route.path !== props.navItems[0].to)
const profileRoute = computed(() => props.navItems.find((n) => /profile/.test(n.to))?.to)

const initials = computed(() => {
  const u = auth.user
  if (!u) return '?'
  return ((u.first_name?.[0] || '') + (u.last_name?.[0] || '')).toUpperCase() || u.username?.[0]?.toUpperCase() || '?'
})
const currentPageTitle = computed(() => props.navItems.find((n) => route.path.startsWith(n.to))?.label || props.portalLabel)
const dateStr = new Date().toLocaleDateString('en-KE', { weekday: 'long', day: 'numeric', month: 'long' })

watch(() => route.path, () => { drawer.value = false; more.value = false; scroller.value?.scrollTo?.({ top: 0 }) })

function onKey(e: KeyboardEvent) {
  const t = e.target as HTMLElement
  const typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); palette.value = !palette.value }
  else if (e.key === '/' && !typing && !palette.value) { e.preventDefault(); palette.value = true }
  else if (e.key === 'Escape') { drawer.value = false; more.value = false; userMenu.value = false }
}
async function handleLogout() { await auth.logout(); router.push('/login') }

onMounted(() => { window.addEventListener('keydown', onKey); notifStore.fetchUnreadCount().catch(() => {}) })
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  // Only hand the page back to the public theme when no portal shell replaced this one.
  setTimeout(() => { if (!document.querySelector('.fx-shell, .fx-public')) { skin.release(); theme.apply() } }, 0)
})
</script>

<style scoped>
.page-enter-active, .page-leave-active { transition: opacity .22s ease, transform .22s ease; }
.page-enter-from { opacity: 0; transform: translateY(10px); }
.page-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
