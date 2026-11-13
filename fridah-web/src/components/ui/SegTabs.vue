<template>
  <div class="fx-seg" role="tablist">
    <button v-for="o in options" :key="String(o.value)" role="tab" :aria-selected="o.value === modelValue" :class="{ on: o.value === modelValue }" @click="$emit('update:modelValue', o.value)">{{ o.label }}</button>
  </div>
</template>
<script setup lang="ts">
defineProps<{ modelValue: string | number; options: { label: string; value: string | number }[] }>()
defineEmits<{ 'update:modelValue': [v: any] }>()
</script>
