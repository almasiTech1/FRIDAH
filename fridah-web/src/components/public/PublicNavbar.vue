<template>
  <header class="fx-pubnav-wrap sticky top-0 z-40">
    <nav class="fx-pubnav" aria-label="Main">
      <RouterLink to="/" class="flex items-center gap-2 pr-2">
        <div class="fx-logo" style="width:38px;height:38px;border-radius:13px">F</div>
        <span class="font-extrabold text-base tracking-wide hidden sm:inline" style="color:var(--text)">FRIDAH</span>
      </RouterLink>

      <div class="fx-pills mx-auto">
        <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="fx-pill" active-class="" exact-active-class="active">{{ link.label }}</RouterLink>
      </div>
      <div class="fx-grow lg:hidden" />

      <SkinSwitcher />
      <button class="fx-icon-btn" :aria-label="skin.isDark ? 'Light look' : 'Dark look'" @click="skin.toggleMode()"><Sun v-if="skin.isDark" /><Moon v-else /></button>
      <LanguageSwitcher class="hidden xl:block" />
      <template v-if="auth.isAuthenticated">
        <RouterLink to="/my-bookings" class="fx-btn hidden xl:inline-flex" style="height:40px">My Bookings</RouterLink>
        <RouterLink :to="dashboardHome" class="fx-btn primary hidden sm:inline-flex" style="height:40px"><LayoutDashboard /> Dashboard</RouterLink>
      </template>
      <template v-else>
        <RouterLink to="/login" class="fx-btn hidden sm:inline-flex" style="height:40px">Login</RouterLink>
        <RouterLink to="/register" class="fx-btn accent hidden sm:inline-flex" style="height:40px">Get Started</RouterLink>
      </template>
      <button class="fx-icon-btn lg:hidden" :aria-label="mobileOpen ? 'Close menu' : 'Open menu'" @click="mobileOpen = !mobileOpen"><X v-if="mobileOpen" /><Menu v-else /></button>

      <div v-if="mobileOpen" class="fx-pubmenu">
        <RouterLink v-for="link in links" :key="link.to" :to="link.to" @click="mobileOpen = false">{{ link.label }}</RouterLink>
        <div class="flex gap-2 pt-2">
          <template v-if="auth.isAuthenticated">
            <RouterLink to="/my-bookings" class="fx-btn flex-1" style="justify-content:center" @click="mobileOpen = false">My Bookings</RouterLink>
            <RouterLink :to="dashboardHome" class="fx-btn primary flex-1" style="justify-content:center" @click="mobileOpen = false">Dashboard</RouterLink>
          </template>
          <template v-else>
            <RouterLink to="/login" class="fx-btn flex-1" style="justify-content:center" @click="mobileOpen = false">Login</RouterLink>
            <RouterLink to="/register" class="fx-btn accent flex-1" style="justify-content:center" @click="mobileOpen = false">Get Started</RouterLink>
          </template>
        </div>
        <LanguageSwitcher class="pt-2" />
      </div>
    </nav>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Sun, Moon, Menu, X, LayoutDashboard } from 'lucide-vue-next'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import SkinSwitcher from '@/components/ui/SkinSwitcher.vue'
import { useAuthStore } from '@/stores/auth'
import { useSkinStore } from '@/stores/skin'

const auth = useAuthStore(); const skin = useSkinStore(); const route = useRoute()
const dashboardHome = computed(() => {
  if (auth.isAgencyStaff) return '/agency/dashboard'
  const map: Record<string, string> = {
    tenant: '/tenant/dashboard', landlord: '/landlord/dashboard', admin: '/admin/dashboard',
    service_provider: '/provider/dashboard', hotel_owner: '/hotel/dashboard',
  }
  return map[auth.user?.role || ''] || '/'
})
const mobileOpen = ref(false)
watch(() => route.path, () => (mobileOpen.value = false))

const links = [
  { to: '/', label: 'Home' }, { to: '/about', label: 'About' }, { to: '/services', label: 'Services' },
  { to: '/properties', label: 'Properties' }, { to: '/hotels', label: 'Hotels' }, { to: '/marketplace', label: 'Marketplace' },
  { to: '/pricing', label: 'Pricing' }, { to: '/blog', label: 'Blog' }, { to: '/contact', label: 'Contact' },
]
</script>
