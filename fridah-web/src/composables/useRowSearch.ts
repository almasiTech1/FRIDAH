import { computed, ref } from 'vue'

/** Client-side search over already-loaded table rows + CSV export of what is currently shown. */
export function useRowSearch<T extends Record<string, any>>(source: () => T[], filename = 'export') {
  const q = ref('')
  const rows = computed(() => {
    const term = q.value.trim().toLowerCase()
    const all = source()
    if (!term) return all
    return all.filter((r) => Object.values(r).some((v) => (typeof v === 'string' || typeof v === 'number') && String(v).toLowerCase().includes(term)))
  })
  function exportCsv() {
    const list = rows.value
    if (!list.length) return
    const cols = Object.keys(list[0]).filter((k) => ['string', 'number', 'boolean'].includes(typeof list[0][k]))
    const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
    const csv = [cols.join(','), ...list.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    a.download = `${filename}-${new Date().toISOString().slice(0, 10)}.csv`
    a.click(); URL.revokeObjectURL(a.href)
  }
  return { q, rows, exportCsv }
}
