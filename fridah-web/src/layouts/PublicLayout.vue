<template>
  <div class="fx-public">
    <div class="fx-ambient" :class="{ 'has-wall': !!skin.wallpaper }"><i class="fx-blob a" /><i class="fx-blob b" /></div>
    <div class="fx-public-body">
      <PublicNavbar />
      <div v-if="route.path !== '/'" class="fx-subbar"><BackButton fallback="/" /></div>
      <main class="flex-1">
        <RouterView v-slot="{ Component }">
          <Transition name="pub" mode="out-in"><component :is="Component" /></Transition>
        </RouterView>
      </main>
      <PublicFooter />
    </div>
    <WhatsAppButton />
    <CookieConsent />
    <ToastHost />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import PublicNavbar from '@/components/public/PublicNavbar.vue'
import PublicFooter from '@/components/public/PublicFooter.vue'
import WhatsAppButton from '@/components/public/WhatsAppButton.vue'
import CookieConsent from '@/components/public/CookieConsent.vue'
import ToastHost from '@/components/ui/ToastHost.vue'
import BackButton from '@/components/ui/BackButton.vue'
import { useSkinStore } from '@/stores/skin'
import { useThemeStore } from '@/stores/theme'

const route = useRoute(); const skin = useSkinStore(); const theme = useThemeStore()
skin.setPortalDefault('public')
skin.apply()
onBeforeUnmount(() => {
  setTimeout(() => { if (!document.querySelector('.fx-shell, .fx-public')) { skin.release(); theme.apply() } }, 0)
})
</script>

<style scoped>
.pub-enter-active, .pub-leave-active { transition: opacity .2s ease, transform .2s ease; }
.pub-enter-from { opacity: 0; transform: translateY(8px); }
.pub-leave-to { opacity: 0; }
</style>
