<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Refunds</h1>
      <p class="text-sm text-gray-500 mt-0.5">Refund requests on payments made to you. Small refunds can be approved by you; larger ones and reversals need a FRIDAH administrator. Approving takes the matching amount back out of your wallet.</p>
    </div>
    <RefundsList role="landlord" />
  </div>
</template>
<script setup lang="ts">
import RefundsList from '@/components/common/RefundsList.vue'
</script>
