import io
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def generate_invoice_receipt(invoice):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>FRIDAH</b> — Payment Receipt", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Receipt for Invoice {invoice.invoice_number}", styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [
        ["Tenant", invoice.tenant.get_full_name() or invoice.tenant.username],
        ["Property", invoice.lease.unit.property.name],
        ["Unit", invoice.lease.unit.unit_number],
        ["Invoice Type", invoice.get_invoice_type_display()],
        ["Period", f"{invoice.period_start} to {invoice.period_end}"],
        ["Amount Due", f"KES {invoice.amount:,.2f}"],
        ["Amount Paid", f"KES {invoice.amount_paid:,.2f}"],
        ["Status", invoice.get_status_display()],
        ["Date Issued", invoice.created_at.strftime('%Y-%m-%d %H:%M')],
    ]
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Thank you for using FRIDAH.", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    invoice.pdf_receipt.save(f"{invoice.invoice_number}.pdf", ContentFile(buffer.read()), save=True)
    return invoice.pdf_receipt
