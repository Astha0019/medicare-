import io
from decimal import Decimal
from datetime import datetime
from config import Config
from utils.formatters import format_inr, format_date, format_datetime, number_to_words_inr

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_invoice_pdf(sale):
    """
    Generate professional A4 PDF invoice for Indian Pharmacy.
    Uses ReportLab if installed, otherwise uses pure Python PDF builder.
    """
    if REPORTLAB_AVAILABLE:
        try:
            return _generate_reportlab_pdf(sale)
        except Exception:
            return _generate_pure_pdf(sale)
    return _generate_pure_pdf(sale)


def _generate_reportlab_pdf(sale):


    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0b3b60'),
        alignment=1 # Center
    )
    tagline_style = ParagraphStyle(
        'TaglineStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0e9f85'),
        alignment=1
    )
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#333333'),
        alignment=1
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#222222')
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold'
    )
    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=table_cell,
        alignment=2 # Right
    )
    table_cell_right_bold = ParagraphStyle(
        'TableCellRightBold',
        parent=table_cell_bold,
        alignment=2 # Right
    )

    elements = []

    # Pharmacy Header
    elements.append(Paragraph(Config.PHARMACY_NAME, header_style))
    elements.append(Paragraph(Config.PHARMACY_TAGLINE, tagline_style))
    elements.append(Spacer(1, 1 * mm))
    elements.append(Paragraph(
        f"<b>Address:</b> {Config.PHARMACY_ADDRESS} &bull; <b>Phone:</b> {Config.PHARMACY_PHONE} &bull; <b>Email:</b> {Config.PHARMACY_EMAIL}",
        info_style
    ))
    elements.append(Paragraph(
        f"<b>GSTIN:</b> {Config.PHARMACY_GSTIN} &bull; <b>DL No:</b> {Config.PHARMACY_DL_NO} &bull; <b>FSSAI:</b> {Config.PHARMACY_FSSAI}",
        info_style
    ))
    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0b3b60'), spaceAfter=8))

    # Title & Invoice Details Table
    inv_title_data = [
        [
            Paragraph("<b>TAX INVOICE / RETAIL CASH MEMO</b>", ParagraphStyle('InvTitle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0b3b60'))),
            Paragraph(f"<b>Original Copy</b>", ParagraphStyle('InvCopy', fontName='Helvetica-Bold', fontSize=9, alignment=2, textColor=colors.HexColor('#666666')))
        ]
    ]
    t_title = Table(inv_title_data, colWidths=[100 * mm, 86 * mm])
    t_title.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_title)

    cust_info = [
        [
            Paragraph(f"<b>Invoice No:</b> {sale.invoice_number}", table_cell),
            Paragraph(f"<b>Customer Name:</b> {sale.customer_name}", table_cell)
        ],
        [
            Paragraph(f"<b>Date & Time:</b> {format_datetime(sale.sale_date)}", table_cell),
            Paragraph(f"<b>Customer Phone:</b> {sale.customer_phone or 'N/A'}", table_cell)
        ],
        [
            Paragraph(f"<b>Payment Mode:</b> {sale.payment_mode}", table_cell),
            Paragraph(f"<b>Prescribed Doctor:</b> {sale.doctor_name or 'Self / Walk-in'}", table_cell)
        ]
    ]
    t_cust = Table(cust_info, colWidths=[93 * mm, 93 * mm])
    t_cust.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafd')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_cust)
    elements.append(Spacer(1, 4 * mm))

    # Items Table Header
    items_header = [
        Paragraph("<b>#</b>", table_cell_bold),
        Paragraph("<b>Medicine Description</b>", table_cell_bold),
        Paragraph("<b>Batch</b>", table_cell_bold),
        Paragraph("<b>Exp</b>", table_cell_bold),
        Paragraph("<b>HSN</b>", table_cell_bold),
        Paragraph("<b>Qty</b>", table_cell_right_bold),
        Paragraph("<b>MRP</b>", table_cell_right_bold),
        Paragraph("<b>Rate</b>", table_cell_right_bold),
        Paragraph("<b>Disc%</b>", table_cell_right_bold),
        Paragraph("<b>GST%</b>", table_cell_right_bold),
        Paragraph("<b>Amount</b>", table_cell_right_bold),
    ]

    items_data = [items_header]
    col_widths = [7*mm, 52*mm, 18*mm, 16*mm, 14*mm, 10*mm, 15*mm, 15*mm, 11*mm, 11*mm, 17*mm]

    idx = 1
    for item in sale.items:
        med_name = item.medicine.name if item.medicine else "Medicine"
        strength = f" ({item.medicine.strength})" if (item.medicine and item.medicine.strength) else ""
        hsn = item.medicine.hsn_code if item.medicine else "3004"
        exp_str = format_date(item.expiry_date)
        
        row = [
            Paragraph(str(idx), table_cell),
            Paragraph(f"<b>{med_name}</b>{strength}", table_cell),
            Paragraph(item.batch_number, table_cell),
            Paragraph(exp_str, table_cell),
            Paragraph(hsn, table_cell),
            Paragraph(str(item.quantity), table_cell_right),
            Paragraph(f"{item.unit_mrp:.2f}", table_cell_right),
            Paragraph(f"{item.unit_selling_price:.2f}", table_cell_right),
            Paragraph(f"{item.discount_percent:.1f}%", table_cell_right),
            Paragraph(f"{item.gst_rate:.0f}%", table_cell_right),
            Paragraph(f"{item.line_total:.2f}", table_cell_right),
        ]
        items_data.append(row)
        idx += 1

    t_items = Table(items_data, colWidths=col_widths, repeatRows=1)
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b3b60')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    # Set header text color to white
    for i in range(len(items_header)):
        items_header[i].style.textColor = colors.white

    elements.append(t_items)
    elements.append(Spacer(1, 3 * mm))

    # Summary Section: Tax Breakdown (Left) and Billing Totals (Right)
    taxable_amount = sale.subtotal - sale.discount_amount
    cgst_val = sale.cgst_amount
    sgst_val = sale.sgst_amount

    tax_summary_data = [
        [Paragraph("<b>GST Breakdown</b>", table_cell_bold), Paragraph("<b>Rate</b>", table_cell_right_bold), Paragraph("<b>Tax Amount</b>", table_cell_right_bold)],
        [Paragraph("Central GST (CGST)", table_cell), Paragraph("6.00% avg", table_cell_right), Paragraph(f"Rs. {cgst_val:.2f}", table_cell_right)],
        [Paragraph("State GST (SGST)", table_cell), Paragraph("6.00% avg", table_cell_right), Paragraph(f"Rs. {sgst_val:.2f}", table_cell_right)],
        [Paragraph("<b>Total GST Tax</b>", table_cell_bold), Paragraph("", table_cell), Paragraph(f"<b>Rs. {sale.tax_amount:.2f}</b>", table_cell_right_bold)],
    ]
    t_tax_breakdown = Table(tax_summary_data, colWidths=[40*mm, 20*mm, 25*mm])
    t_tax_breakdown.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f4f8')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eeeeee')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    totals_data = [
        [Paragraph("Gross Subtotal:", table_cell), Paragraph(f"Rs. {sale.subtotal:.2f}", table_cell_right)],
        [Paragraph("Discount:", table_cell), Paragraph(f"-Rs. {sale.discount_amount:.2f}", table_cell_right)],
        [Paragraph("Tax (GST):", table_cell), Paragraph(f"+Rs. {sale.tax_amount:.2f}", table_cell_right)],
        [Paragraph("Round Off:", table_cell), Paragraph(f"Rs. {sale.round_off:.2f}", table_cell_right)],
        [Paragraph("<b>Net Total Payable:</b>", table_cell_bold), Paragraph(f"<b>Rs. {sale.total_amount:.2f}</b>", table_cell_right_bold)],
        [Paragraph("Amount Paid:", table_cell), Paragraph(f"Rs. {sale.amount_paid:.2f}", table_cell_right)],
        [Paragraph("Change Returned:", table_cell), Paragraph(f"Rs. {sale.change_returned:.2f}", table_cell_right)],
    ]
    t_totals = Table(totals_data, colWidths=[45*mm, 45*mm])
    t_totals.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#0b3b60')),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#e8f4f8')),
        ('LINEBELOW', (0,-1), (-1,-1), 1, colors.HexColor('#0b3b60')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))

    combined_summary = [
        [t_tax_breakdown, t_totals]
    ]
    t_summary_layout = Table(combined_summary, colWidths=[90*mm, 96*mm])
    t_summary_layout.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(t_summary_layout)
    elements.append(Spacer(1, 3 * mm))

    # Amount in Words
    words_str = number_to_words_inr(sale.total_amount)
    words_table = Table([[
        Paragraph(f"<b>Amount in Words:</b> <i>{words_str}</i>", table_cell)
    ]], colWidths=[186 * mm])
    words_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafafa')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(words_table)
    elements.append(Spacer(1, 4 * mm))

    # Terms & Conditions and Authorized Signatory
    terms_text = (
        "<b>Terms & Conditions:</b><br/>"
        "1. Goods once sold will only be accepted for return within 7 days with original tax invoice.<br/>"
        "2. Refrigerated & Schedule H/X drugs cannot be returned once delivered.<br/>"
        "3. Please check batch number, expiry date, and seal before leaving the counter.<br/>"
        "4. This is a computer generated invoice."
    )
    footer_data = [
        [
            Paragraph(terms_text, ParagraphStyle('Terms', fontName='Helvetica', fontSize=7, leading=9, textColor=colors.HexColor('#555555'))),
            Paragraph(
                f"<br/><br/><b>For {Config.PHARMACY_NAME}</b><br/><br/><br/>Authorized Pharmacist / Signatory",
                ParagraphStyle('Sign', fontName='Helvetica', fontSize=8, leading=11, alignment=1, textColor=colors.HexColor('#333333'))
            )
        ]
    ]
    t_footer = Table(footer_data, colWidths=[120 * mm, 66 * mm])
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _generate_pure_pdf(sale):
    """Fallback text-based pure PDF generator if ReportLab fails"""
    buffer = io.BytesIO()
    # Simple minimal valid PDF 1.4 stream
    content = []
    content.append(f"BT /F1 14 Tf 40 800 Td ({Config.PHARMACY_NAME}) Tj ET")
    content.append(f"BT /F2 9 Tf 40 785 Td (GSTIN: {Config.PHARMACY_GSTIN} | DL: {Config.PHARMACY_DL_NO}) Tj ET")
    content.append(f"BT /F2 10 Tf 40 765 Td (TAX INVOICE: {sale.invoice_number} | Date: {format_datetime(sale.sale_date)}) Tj ET")
    content.append(f"BT /F2 10 Tf 40 750 Td (Customer: {sale.customer_name} | Doctor: {sale.doctor_name or 'Self'}) Tj ET")
    content.append(f"0.5 w 40 740 m 555 740 l S")

    y = 720
    content.append(f"BT /F1 9 Tf 40 {y} Td (Medicine / Strength) Tj 220 {y} Td (Batch) Tj 300 {y} Td (Exp) Tj 360 {y} Td (Qty) Tj 420 {y} Td (Rate) Tj 490 {y} Td (Amount) Tj ET")
    y -= 15
    content.append(f"0.5 w 40 {y} m 555 {y} l S")
    y -= 15

    for item in sale.items:
        med_name = (item.medicine.name if item.medicine else 'Item')[:25]
        content.append(
            f"BT /F2 8 Tf 40 {y} Td ({med_name}) Tj 220 {y} Td ({item.batch_number}) Tj "
            f"300 {y} Td ({format_date(item.expiry_date)}) Tj 360 {y} Td ({item.quantity}) Tj "
            f"420 {y} Td (Rs.{item.unit_selling_price:.2f}) Tj 490 {y} Td (Rs.{item.line_total:.2f}) Tj ET"
        )
        y -= 16
        if y < 100:
            break

    y -= 10
    content.append(f"0.5 w 40 {y} m 555 {y} l S")
    y -= 18
    content.append(f"BT /F2 9 Tf 350 {y} Td (Subtotal: Rs.{sale.subtotal:.2f}) Tj ET")
    y -= 14
    content.append(f"BT /F2 9 Tf 350 {y} Td (Discount: Rs.{sale.discount_amount:.2f}) Tj ET")
    y -= 14
    content.append(f"BT /F2 9 Tf 350 {y} Td (GST Tax: Rs.{sale.tax_amount:.2f}) Tj ET")
    y -= 16
    content.append(f"BT /F1 11 Tf 350 {y} Td (TOTAL: Rs.{sale.total_amount:.2f}) Tj ET")

    stream_data = "\n".join(content).encode('latin-1', 'replace')
    stream_len = len(stream_data)

    pdf_parts = [
        b"%PDF-1.4\n",
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"6 0 obj << /Length {stream_len} >>\nstream\n".encode('ascii') + stream_data + b"\nendstream\nendobj\n",
    ]

    # Build xref
    pos = len(pdf_parts[0])
    offsets = [0]
    for part in pdf_parts[1:]:
        offsets.append(pos)
        pos += len(part)

    xref = f"xref\n0 7\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n"
    trailer = f"trailer << /Size 7 /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n"

    all_bytes = b"".join(pdf_parts) + xref.encode('ascii') + trailer.encode('ascii')
    return all_bytes

