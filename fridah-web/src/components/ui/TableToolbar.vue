<template>
  <div class="fx-toolbar">
    <label class="fx-tsearch"><Search :size="16" /><input :value="modelValue" type="search" :placeholder="placeholder" aria-label="Search rows" @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)" /></label>
    <span class="fx-chip neutral">{{ count }}<template v-if="total !== undefined && total !== count"> of {{ total }}</template> {{ count === 1 ? 'row' : 'rows' }}</span>
    <div class="fx-grow" />
    <slot />
    <ExportMenu v-if="exportable" label="Export" :disabled="!rows?.length" :handler="(f) => exportTable(f, { title }, rows || [])" />
  </div>
</template>
<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import ExportMenu from '@/components/ui/ExportMenu.vue'
import { exportTable } from '@/utils/exporters'
withDefaults(defineProps<{ modelValue: string; count: number; total?: number; placeholder?: string; exportable?: boolean; rows?: Record<string, any>[]; title?: string }>(), { placeholder: 'Search…', exportable: true, title: 'Report' })
defineEmits<{ 'update:modelValue': [v: string] }>()
</script>
