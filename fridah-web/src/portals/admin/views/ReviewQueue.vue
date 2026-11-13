<template>
  <div class="space-y-5">
    <div>
      <h1 class="page-title">Property Review Queue</h1>
      <p class="text-sm text-gray-500 mt-0.5">
        Oldest first. Agency-submitted properties also need the landlord's approval - your approval alone will not publish them.
      </p>
    </div>
    <PropertyReviewList role="admin" />
  </div>
</template>
<script setup lang="ts">
import PropertyReviewList from '@/components/common/PropertyReviewList.vue'
</script>
