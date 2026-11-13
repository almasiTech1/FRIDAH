/**
 * Company details printed on invoices and reports.
 * Set the VITE_COMPANY_* variables in .env (see .env.example) — anything left empty is simply not printed.
 */
const env = import.meta.env as Record<string, string | undefined>
const v = (k: string, d = '') => (env[k] ?? d).trim()

export const company = {
  name: v('VITE_COMPANY_NAME', 'FRIDAH'),
  tagline: v('VITE_COMPANY_TAGLINE', 'Property management platform'),
  address: v('VITE_COMPANY_ADDRESS'),
  phone: v('VITE_COMPANY_PHONE'),
  email: v('VITE_COMPANY_EMAIL'),
  kraPin: v('VITE_COMPANY_KRA_PIN'),
  vatNo: v('VITE_COMPANY_VAT_NO'),
  paybill: v('VITE_COMPANY_PAYBILL'),
  bankDetails: v('VITE_COMPANY_BANK_DETAILS'),
  /** URL or data: URI of a PNG/JPG logo. Must be same-origin or allow CORS. */
  logoUrl: v('VITE_COMPANY_LOGO_URL'),
  invoiceFooter: v('VITE_COMPANY_INVOICE_FOOTER'),
}

/** Lines shown under the company name (address, contact, tax numbers), skipping empty ones. */
export function companyLines(): string[] {
  return [
    company.address,
    [company.phone, company.email].filter(Boolean).join('  |  '),
    [company.kraPin && `KRA PIN: ${company.kraPin}`, company.vatNo && `VAT No: ${company.vatNo}`].filter(Boolean).join('  |  '),
  ].filter(Boolean)
}

/** Payment instructions for the foot of an invoice. */
export function paymentLines(): string[] {
  return [company.paybill && `M-Pesa Paybill: ${company.paybill} (account = invoice number)`, company.bankDetails && `Bank: ${company.bankDetails}`].filter(Boolean) as string[]
}

/** Loads the configured logo as a data URL (null if not set or it fails to load). */
export async function loadLogo(): Promise<{ data: string; type: 'PNG' | 'JPEG' } | null> {
  if (!company.logoUrl) return null
  try {
    let data = company.logoUrl
    if (!data.startsWith('data:')) {
      const blob = await (await fetch(company.logoUrl)).blob()
      data = await new Promise<string>((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result)); r.onerror = () => rej(r.error); r.readAsDataURL(blob) })
    }
    return { data, type: /^data:image\/png/.test(data) ? 'PNG' : 'JPEG' }
  } catch { return null }
}
