<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">My Refunds</h1>
      <p class="text-sm text-gray-500 mt-0.5">Refund requests you made or that affect your payments.</p>
    </div>
    <RefundsList role="tenant" />
  </div>
</template>
<script setup lang="ts">
import RefundsList from '@/components/common/RefundsList.vue'
</script>
