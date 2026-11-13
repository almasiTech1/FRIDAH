<template>
  <Transition
    enter-active-class="transition duration-500 ease-out"
    enter-from-class="translate-y-full opacity-0"
    leave-active-class="transition duration-300 ease-in"
    leave-to-class="translate-y-full opacity-0"
  >
    <div v-if="visible" class="fixed bottom-0 inset-x-0 z-50 p-4">
      <div class="max-w-4xl mx-auto glass-card p-5 flex flex-col sm:flex-row items-center gap-4">
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">
          We use cookies to improve your experience and analyze site traffic. By continuing, you agree to our
          <RouterLink to="/privacy" class="text-brand-600 dark:text-brand-400 font-medium hover:underline">Privacy Policy</RouterLink>.
        </p>
        <div class="flex gap-2 flex-shrink-0">
          <button class="btn-outline text-sm py-2 px-4" @click="decline">Decline</button>
          <button class="btn-primary bg-brand-600 hover:bg-brand-700 text-sm py-2 px-4" @click="accept">Accept</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const STORAGE_KEY = 'fridah-cookie-consent'
const visible = ref(false)

onMounted(() => {
  if (!localStorage.getItem(STORAGE_KEY)) visible.value = true
})

function accept() {
  localStorage.setItem(STORAGE_KEY, 'accepted')
  visible.value = false
}
function decline() {
  localStorage.setItem(STORAGE_KEY, 'declined')
  visible.value = false
}
</script>
