<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="text-center">
      <p class="text-7xl font-bold text-gray-200">404</p>
      <h1 class="mt-4 text-xl font-semibold text-gray-800">Page not found</h1>
      <p class="mt-2 text-gray-500 text-sm">The page you're looking for doesn't exist.</p>
      <RouterLink to="/" class="mt-6 btn-primary bg-gray-900 hover:bg-gray-700 inline-flex">Go home</RouterLink>
    </div>
  </div>
</template>
<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
