<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Property Approvals</h1>
      <p class="text-sm text-gray-500 mt-0.5">
        Properties an agency has submitted on your behalf. A property goes live only after both you
        and a Fridah administrator approve it. Any later change to key details sends it back for approval.
      </p>
    </div>
    <PropertyReviewList role="landlord" />
  </div>
</template>
<script setup lang="ts">
import PropertyReviewList from '@/components/common/PropertyReviewList.vue'
</script>
