import { it, expect, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

it('invoice PDFs carry the configured company name, tax PIN and payment details', async () => {
  vi.stubEnv('VITE_COMPANY_NAME', 'Prime Estates Ltd'); vi.stubEnv('VITE_COMPANY_KRA_PIN', 'P051234567Z'); vi.stubEnv('VITE_COMPANY_PAYBILL', '123456')
  vi.resetModules(); setActivePinia(createPinia())
  const { exportInvoice } = await import('@/utils/exporters')
  let last: Blob; const got: Blob[] = []
  ;(URL as any).createObjectURL = (b: Blob) => { last = b; return 'blob:x' }; (URL as any).revokeObjectURL = () => {}
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { got.push(last) })
  await exportInvoice('pdf', { invoice_number: 'INV-9', tenant_name: 'Test', amount: 1000, amount_paid: 0, balance: 1000, status: 'pending' })
  const txt = await new Promise<string>((res) => { const fr = new FileReader(); fr.onload = () => res(Buffer.from(fr.result as ArrayBuffer).toString('latin1')); fr.readAsArrayBuffer(got[0]) })
  expect(txt).toContain('Prime Estates Ltd'); expect(txt).toContain('P051234567Z'); expect(txt).toContain('Paybill: 123456')
})
