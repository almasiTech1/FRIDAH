<template>
  <div class="fx-public fx-auth">
    <div class="fx-ambient" :class="{ 'has-wall': !!skin.wallpaper }"><i class="fx-blob a" /><i class="fx-blob b" /></div>
    <div class="fx-auth-body">
      <div class="fx-auth-top">
        <BackButton fallback="/" />
        <div class="fx-grow" />
        <SkinSwitcher />
        <button class="fx-icon-btn" :aria-label="skin.isDark ? 'Light look' : 'Dark look'" @click="skin.toggleMode()"><Sun v-if="skin.isDark" /><Moon v-else /></button>
        <LanguageSwitcher />
      </div>

      <div class="fx-auth-grid">
        <aside class="fx-auth-hero fx-panel">
          <div class="flex items-center gap-3"><div class="fx-logo">F</div><b class="tracking-wide">FRIDAH</b></div>
          <h2>Property, hotels &amp; rentals — <span style="color:var(--link)">one smart platform</span></h2>
          <p>Collect rent by M-Pesa, manage units and bookings, and keep every statement in one place.</p>
          <div class="fx-auth-cards">
            <div class="fx-kpi float a"><div class="fx-kpi-top"><span class="fx-kpi-icon"><TrendingUp /></span><span class="fx-chip">▲ 15%</span></div><p class="fx-kpi-val">KES 428K</p><p class="fx-kpi-label">Rent collected</p></div>
            <div class="fx-kpi accent float b"><div class="fx-kpi-top"><span class="fx-kpi-icon"><KeyRound /></span></div><p class="fx-kpi-val">92%</p><p class="fx-kpi-label">Occupancy</p></div>
          </div>
          <ul class="fx-auth-points">
            <li><ShieldCheck /> Bank-grade security and role-based access</li>
            <li><Smartphone /> M-Pesa STK push and automatic reconciliation</li>
            <li><BarChart3 /> Live dashboards for owners, agencies and hotels</li>
          </ul>
        </aside>

        <section class="fx-panel fx-auth-card">
          <div class="text-center mb-6">
            <div class="fx-logo mx-auto mb-3" style="width:52px;height:52px;border-radius:18px;font-size:20px">F</div>
            <h1>{{ title }}</h1><p>{{ subtitle }}</p>
          </div>
          <slot />
        </section>
      </div>
    </div>
    <ToastHost />
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount } from 'vue'
import { Sun, Moon, TrendingUp, KeyRound, ShieldCheck, Smartphone, BarChart3 } from 'lucide-vue-next'
import BackButton from '@/components/ui/BackButton.vue'
import SkinSwitcher from '@/components/ui/SkinSwitcher.vue'
import ToastHost from '@/components/ui/ToastHost.vue'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import { useSkinStore } from '@/stores/skin'
import { useThemeStore } from '@/stores/theme'

defineProps<{ title: string; subtitle: string }>()
const skin = useSkinStore(); const theme = useThemeStore()
skin.setPortalDefault('public'); skin.apply()
onBeforeUnmount(() => setTimeout(() => { if (!document.querySelector('.fx-shell, .fx-public')) { skin.release(); theme.apply() } }, 0))
</script>
