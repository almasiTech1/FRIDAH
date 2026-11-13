import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { autoColumns, exportTable, exportInvoice, exportSummary } from '@/utils/exporters'

let saved: { name: string; blob: Blob }[] = []
beforeEach(() => {
  setActivePinia(createPinia()); saved = []
  ;(URL as any).createObjectURL = vi.fn((b: Blob) => { (saved as any).lastBlob = b; return 'blob:x' }); (URL as any).revokeObjectURL = vi.fn()
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) { saved.push({ name: this.download, blob: (saved as any).lastBlob }) })
})
const rows = [{ id: 'u1', invoice_number: 'INV-001', tenant_name: 'Wanjiru', amount: 25000, balance: 0, due_date: '2026-11-05', status: 'paid' }]
const head = (b: Blob, n = 4) => new Promise<Uint8Array>((res, rej) => {
  const fr = new FileReader()
  fr.onload = () => res(new Uint8Array(fr.result as ArrayBuffer).slice(0, n)); fr.onerror = () => rej(fr.error)
  fr.readAsArrayBuffer(b)
})

describe('document exports', () => {
  it('auto columns hide ids and format money and dates', () => {
    const cols = autoColumns(rows)
    expect(cols.map((c) => c.key)).not.toContain('id')
    expect(cols.find((c) => c.key === 'amount')!.format!(25000, {})).toMatch(/25,000/)
    expect(cols.find((c) => c.key === 'due_date')!.format!('2026-11-05', {})).not.toBe('2026-11-05')
  })
  it('creates a CSV with a header row', async () => {
    await exportTable('csv', { title: 'Invoices' }, rows)
    expect(saved[0].name).toMatch(/^invoices-\d{4}-\d{2}-\d{2}\.csv$/)
    expect(await saved[0].blob.text()).toContain('Invoice Number')
  })
  it('creates real PDF, Word and Excel files', async () => {
    await exportTable('pdf', { title: 'Invoices' }, rows)
    expect(String.fromCharCode(...(await head(saved[0].blob)))).toBe('%PDF')
    await exportTable('docx', { title: 'Invoices' }, rows)
    expect(Array.from(await head(saved[1].blob, 2))).toEqual([0x50, 0x4b]) // zip container
    await exportTable('xlsx', { title: 'Invoices' }, rows)
    expect(Array.from(await head(saved[2].blob, 2))).toEqual([0x50, 0x4b])
    expect(saved.map((s) => s.name.split('.').pop())).toEqual(['pdf', 'docx', 'xlsx'])
  })
  it('creates invoice PDF and Word documents', async () => {
    const inv = { invoice_number: 'INV-2026-0042', tenant_name: 'Wanjiru Kamau', invoice_type: 'rent', amount: 25000, amount_paid: 10000, balance: 15000, due_date: '2026-11-05', period_start: '2026-11-01', period_end: '2026-11-30', status: 'partially_paid' }
    await exportInvoice('pdf', inv); await exportInvoice('docx', inv)
    expect(saved.map((s) => s.name)).toEqual(['invoice-inv-2026-0042.pdf', 'invoice-inv-2026-0042.docx'])
    expect(String.fromCharCode(...(await head(saved[0].blob)))).toBe('%PDF')
  })
  it('refuses to export nothing', async () => {
    await expect(exportTable('pdf', { title: 'x' }, [])).rejects.toThrow(/nothing to export/i)
    await expect(exportSummary('csv', { title: 'x' }, [])).rejects.toThrow()
  })
})
