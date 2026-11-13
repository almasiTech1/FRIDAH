<template>
  <div class="space-y-5 max-w-2xl">
    <div>
      <h1 class="page-title">My Account</h1>
      <p class="text-sm text-gray-500 mt-0.5">Signed in as <strong>{{ auth.user?.first_name }} {{ auth.user?.last_name }}</strong> ({{ auth.user?.email }}) · Administrator</p>
    </div>
    <NotificationPreferences />
  </div>
</template>
<script setup lang="ts">
import NotificationPreferences from '@/components/common/NotificationPreferences.vue'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
</script>
