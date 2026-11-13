<template>
  <div class="relative">
    <button
      class="p-2.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-500 dark:hover:text-gray-200 dark:hover:bg-gray-800 rounded-xl transition-all duration-200 flex items-center gap-1"
      :title="$t('language.select')"
      @click="open = !open"
    >
      <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9l4.5-9 4.5 9m-8.25-2h7.5" />
      </svg>
      <span class="text-xs font-semibold uppercase">{{ locale }}</span>
    </button>

    <div v-if="open" class="absolute right-0 mt-1 w-36 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl shadow-lg py-1 z-30">
      <button
        v-for="opt in options" :key="opt.code"
        class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between"
        :class="locale === opt.code ? 'font-semibold text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-300'"
        @click="select(opt.code)"
      >
        {{ opt.label }}
        <span v-if="locale === opt.code">✓</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale } from '@/i18n'

const { t, locale } = useI18n()
const open = ref(false)
const options = computed(() => [
  { code: 'en' as const, label: t('language.english') },
  { code: 'sw' as const, label: t('language.swahili') },
])

function select(code: 'en' | 'sw') {
  setLocale(code)
  open.value = false
}
</script>

<style scoped>
.w-4\.5 { width: 1.125rem; }
.h-4\.5 { height: 1.125rem; }
</style>
