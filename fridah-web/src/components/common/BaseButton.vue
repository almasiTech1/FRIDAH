<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[variantClass, sizeClass, 'btn']"
    v-bind="$attrs"
  >
    <span v-if="loading" class="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
    <slot v-else-if="$slots.icon" name="icon" />
    <span v-if="$slots.default"><slot /></span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  color?: string
}>(), { variant: 'primary', size: 'md', loading: false, disabled: false, type: 'button' })

const variantClass = computed(() => ({
  primary: `btn-primary ${props.color || 'bg-gray-900 hover:bg-gray-700'}`,
  outline: 'btn-outline border-gray-200',
  ghost: 'btn-ghost',
  danger: 'btn-primary bg-red-600 hover:bg-red-700',
}[props.variant]))

const sizeClass = computed(() => ({
  sm: 'text-xs px-3 py-1.5',
  md: 'text-sm px-4 py-2',
  lg: 'text-base px-5 py-2.5',
}[props.size]))
</script>
