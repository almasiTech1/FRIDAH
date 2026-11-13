<template>
  <div ref="root" class="fx-pop-wrap" style="display:inline-block">
    <button class="fx-btn" :class="{ compact }" :style="compact ? 'height:32px;padding:0 12px;font-size:12px' : 'height:38px'" :disabled="disabled || busy" :aria-expanded="open" @click.stop="open = !open">
      <span v-if="busy" class="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" /><Download v-else />
      {{ label }}<ChevronDown :size="13" />
    </button>
    <div v-if="open" class="fx-pop" style="width:220px;padding:6px">
      <button v-for="f in formats" :key="f" class="fx-pop-item" @click.stop="pick(f)">
        <span class="fx-ico"><component :is="ICON[f]" /></span><span><b class="block font-semibold">{{ NAME[f] }}</b><small>{{ HINT[f] }}</small></span>
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { Download, ChevronDown, FileText, FileType2, Sheet, FileSpreadsheet } from 'lucide-vue-next'
import { useToastStore } from '@/stores/toasts'
import type { ExportFormat } from '@/utils/exporters'

const props = withDefaults(defineProps<{ handler: (f: ExportFormat) => Promise<unknown>; formats?: ExportFormat[]; label?: string; compact?: boolean; disabled?: boolean }>(),
  { formats: () => ['pdf', 'docx', 'xlsx', 'csv'], label: 'Export' })
const toast = useToastStore()
const open = ref(false); const busy = ref(false); const root = ref<HTMLElement>()
onClickOutside(root, () => (open.value = false))
const ICON = { pdf: FileText, docx: FileType2, xlsx: Sheet, csv: FileSpreadsheet } as const
const NAME = { pdf: 'PDF document', docx: 'Word document', xlsx: 'Excel spreadsheet', csv: 'CSV file' } as const
const HINT = { pdf: 'Print-ready', docx: 'Editable .docx', xlsx: 'Formatted .xlsx', csv: 'Plain data' } as const
async function pick(f: ExportFormat) {
  open.value = false; busy.value = true
  try { await props.handler(f); toast.push(`${NAME[f]} ready`, { body: 'Check your downloads folder.' }) }
  catch (e: any) { toast.push('Could not create the file', { body: e?.message || 'Please try again.', tone: 'error' }) }
  finally { busy.value = false }
}
</script>
