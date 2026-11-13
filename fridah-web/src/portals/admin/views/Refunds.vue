<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Refunds & Reversals</h1>
      <p class="text-sm text-gray-500 mt-0.5">Approve or reject requests, then record the M-Pesa payout to the customer. You cannot approve a request you made yourself.</p>
    </div>
    <RefundPolicyCard />
    <RefundsList role="admin" />
  </div>
</template>
<script setup lang="ts">
import RefundsList from '@/components/common/RefundsList.vue'
import RefundPolicyCard from '@/components/common/RefundPolicyCard.vue'
</script>
