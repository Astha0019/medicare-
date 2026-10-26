from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from flask import current_app
from models import db, Sale, SaleItem, Medicine, MedicineBatch, StockMovement, Return, ReturnItem, Payment, AuditLog

def generate_invoice_number():
    """Generates unique invoice number: INV-YYYYMMDD-XXXX"""
    today_str = datetime.now().strftime('%Y%m%d')
    prefix = f"INV-{today_str}-"
    
    # Find highest sequence for today
    last_sale = Sale.query.filter(Sale.invoice_number.like(f"{prefix}%")).order_by(Sale.id.desc()).first()
    if last_sale:
        try:
            last_seq = int(last_sale.invoice_number.split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1
        
    return f"{prefix}{new_seq:04d}"


def generate_return_number():
    """Generates unique return number: RET-YYYYMMDD-XXXX"""
    today_str = datetime.now().strftime('%Y%m%d')
    prefix = f"RET-{today_str}-"
    last_return = Return.query.filter(Return.return_number.like(f"{prefix}%")).order_by(Return.id.desc()).first()
    if last_return:
        try:
            last_seq = int(last_return.return_number.split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:04d}"


def create_sale(cashier_user, customer_name, customer_phone, doctor_name, payment_mode, 
                payment_reference, amount_paid, items_data, notes=None):
    """
    Creates an atomic sale transaction.
    items_data is a list of dicts:
    [{ 'medicine_id': 1, 'batch_id': 2, 'quantity': 2, 'discount_percent': 5.0 }]
    """
    if not items_data or len(items_data) == 0:
        raise ValueError("Cannot create sale with empty cart.")

    today = date.today()
    invoice_no = generate_invoice_number()

    sale = Sale(
        invoice_number=invoice_no,
        customer_name=(customer_name or 'Walk-in Customer').strip(),
        customer_phone=(customer_phone or '').strip(),
        doctor_name=(doctor_name or '').strip(),
        sale_date=datetime.now(),
        subtotal=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        cgst_amount=Decimal('0.00'),
        sgst_amount=Decimal('0.00'),
        round_off=Decimal('0.00'),
        total_amount=Decimal('0.00'),
        payment_mode=payment_mode or 'Cash',
        payment_reference=payment_reference,
        amount_paid=Decimal('0.00'),
        change_returned=Decimal('0.00'),
        status='Completed',
        notes=notes,
        created_by=cashier_user.id
    )

    db.session.add(sale)
    db.session.flush() # Flush to get sale.id

    subtotal_acc = Decimal('0.00')
    discount_acc = Decimal('0.00')
    tax_acc = Decimal('0.00')
    cgst_acc = Decimal('0.00')
    sgst_acc = Decimal('0.00')

    for item in items_data:
        med_id = int(item['medicine_id'])
        batch_id = int(item['batch_id'])
        qty = int(item['quantity'])
        disc_pct = Decimal(str(item.get('discount_percent', 0) or 0)).quantize(Decimal('0.01'))

        if qty <= 0:
            raise ValueError(f"Quantity must be greater than zero.")

        # Query batch with lock or fresh read
        batch = MedicineBatch.query.filter_by(id=batch_id, is_active=True).first()
        if not batch:
            raise ValueError(f"Batch ID {batch_id} not found or inactive.")
        if batch.medicine_id != med_id:
            raise ValueError(f"Batch {batch.batch_number} does not belong to selected medicine.")

        # Expiry check
        if batch.is_expired:
            raise ValueError(f"Batch {batch.batch_number} for medicine '{batch.medicine.name}' has EXPIRED ({batch.expiry_date.strftime('%d-%m-%Y')}) and cannot be sold.")

        # Stock availability check
        if batch.quantity < qty:
            raise ValueError(
                f"Insufficient stock for {batch.medicine.name} (Batch: {batch.batch_number}). "
                f"Available: {batch.quantity}, Requested: {qty}"
            )

        medicine = batch.medicine
        unit_mrp = Decimal(str(batch.mrp)).quantize(Decimal('0.01'))
        unit_sp = Decimal(str(batch.selling_price)).quantize(Decimal('0.01'))
        gst_rate = Decimal(str(medicine.gst_rate)).quantize(Decimal('0.01'))

        line_gross = (unit_sp * qty).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        line_discount = ((line_gross * disc_pct) / Decimal('100.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        line_net = line_gross - line_discount

        # Indian Pharmacy Tax: MRP / Selling Price is Tax-Inclusive
        # Taxable Value = Line Net / (1 + GST_Rate / 100)
        # Tax Amount = Line Net - Taxable Value
        one_plus_tax = Decimal('1.0') + (gst_rate / Decimal('100.0'))
        taxable_value = (line_net / one_plus_tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        line_tax = line_net - taxable_value
        line_cgst = (line_tax / Decimal('2.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        line_sgst = line_tax - line_cgst

        sale_item = SaleItem(
            sale_id=sale.id,
            medicine_id=med_id,
            batch_id=batch.id,
            batch_number=batch.batch_number,
            expiry_date=batch.expiry_date,
            quantity=qty,
            unit_mrp=unit_mrp,
            unit_selling_price=unit_sp,
            discount_percent=disc_pct,
            discount_amount=line_discount,
            gst_rate=gst_rate,
            tax_amount=line_tax,
            line_total=line_net
        )
        db.session.add(sale_item)

        # Update batch stock
        batch.quantity -= qty

        # Record stock movement
        movement = StockMovement(
            medicine_id=med_id,
            batch_id=batch.id,
            movement_type='Sale',
            quantity_change=-qty,
            current_stock_after=batch.quantity,
            reason=f"Sale Invoice #{invoice_no}",
            reference_id=invoice_no,
            created_by=cashier_user.id,
            created_at=datetime.now()
        )
        db.session.add(movement)

        # Accumulate totals
        subtotal_acc += line_gross
        discount_acc += line_discount
        tax_acc += line_tax
        cgst_acc += line_cgst
        sgst_acc += line_sgst

    raw_total = subtotal_acc - discount_acc
    # Round off to nearest Rupee
    rounded_total = raw_total.quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
    round_off = rounded_total - raw_total

    sale.subtotal = subtotal_acc
    sale.discount_amount = discount_acc
    sale.tax_amount = tax_acc
    sale.cgst_amount = cgst_acc
    sale.sgst_amount = sgst_acc
    sale.round_off = round_off
    sale.total_amount = rounded_total

    # Payment handling
    paid = Decimal(str(amount_paid or 0)).quantize(Decimal('0.01'))
    if paid == Decimal('0.00'):
        paid = rounded_total # Exact payment assumed if 0 entered
    sale.amount_paid = paid
    sale.change_returned = max(Decimal('0.00'), paid - rounded_total)

    payment = Payment(
        sale_id=sale.id,
        payment_type='Sale',
        amount=rounded_total,
        payment_mode=sale.payment_mode,
        reference_number=payment_reference,
        status='Success',
        notes=f"Payment for Invoice {invoice_no}"
    )
    db.session.add(payment)

    # Audit log
    audit = AuditLog(
        user_id=cashier_user.id,
        action='CREATE_SALE',
        module='Billing',
        details=f"Generated invoice {invoice_no} for ₹{rounded_total} ({len(items_data)} items). Mode: {sale.payment_mode}"
    )
    db.session.add(audit)

    db.session.commit()
    return sale


def process_sale_return(user, sale_id, return_items, reason):
    """
    Process customer return for a sale.
    return_items: [{'sale_item_id': 1, 'quantity': 1, 'action': 'Restock'|'WriteOff'}]
    """
    sale = Sale.query.get(sale_id)
    if not sale:
        raise ValueError("Sale not found.")
    if sale.status == 'Cancelled':
        raise ValueError("Cannot return items from a cancelled invoice.")

    ret_no = generate_return_number()
    ret_record = Return(
        return_number=ret_no,
        sale_id=sale.id,
        return_type='CustomerReturn',
        return_date=datetime.now(),
        total_amount=Decimal('0.00'),
        reason=reason or "Customer Return",
        status='Completed',
        created_by=user.id
    )
    db.session.add(ret_record)
    db.session.flush()

    total_refund = Decimal('0.00')

    for r_item in return_items:
        s_item_id = int(r_item['sale_item_id'])
        qty = int(r_item['quantity'])
        action = r_item.get('action', 'Restock')

        sale_item = SaleItem.query.get(s_item_id)
        if not sale_item or sale_item.sale_id != sale.id:
            raise ValueError(f"Sale item {s_item_id} invalid.")

        if qty <= 0 or qty > sale_item.quantity:
            raise ValueError(f"Invalid return quantity for {sale_item.medicine.name}. Max: {sale_item.quantity}")

        unit_effective_price = (sale_item.line_total / sale_item.quantity).quantize(Decimal('0.01'))
        refund_amount = (unit_effective_price * qty).quantize(Decimal('0.01'))
        total_refund += refund_amount

        batch = sale_item.batch

        if action == 'Restock':
            batch.quantity += qty
            movement = StockMovement(
                medicine_id=sale_item.medicine_id,
                batch_id=batch.id,
                movement_type='CustomerReturn',
                quantity_change=qty,
                current_stock_after=batch.quantity,
                reason=f"Customer Return #{ret_no} (Restocked)",
                reference_id=ret_no,
                created_by=user.id,
                created_at=datetime.now()
            )
            db.session.add(movement)
        else: # WriteOff
            movement = StockMovement(
                medicine_id=sale_item.medicine_id,
                batch_id=batch.id,
                movement_type='WriteOff',
                quantity_change=0,
                current_stock_after=batch.quantity,
                reason=f"Customer Return #{ret_no} (Damaged/Written-off: {qty} units)",
                reference_id=ret_no,
                created_by=user.id,
                created_at=datetime.now()
            )
            db.session.add(movement)

        ret_item = ReturnItem(
            return_id=ret_record.id,
            medicine_id=sale_item.medicine_id,
            batch_id=batch.id,
            quantity=qty,
            unit_price=unit_effective_price,
            total_amount=refund_amount,
            action_taken=action
        )
        db.session.add(ret_item)

    ret_record.total_amount = total_refund

    # Update sale status
    sale.status = 'Returned' if len(return_items) == len(sale.items) else 'Partially Returned'

    # Refund payment entry
    refund_payment = Payment(
        sale_id=sale.id,
        return_id=ret_record.id,
        payment_type='CustomerRefund',
        amount=total_refund,
        payment_mode=sale.payment_mode,
        status='Success',
        notes=f"Refund for return #{ret_no}"
    )
    db.session.add(refund_payment)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action='RETURN_SALE',
        module='Billing',
        details=f"Processed return #{ret_no} for Invoice #{sale.invoice_number}, refund ₹{total_refund} ({reason})"
    )
    db.session.add(audit)

    db.session.commit()
    return ret_record


def cancel_sale(user, sale_id, reason):
    """
    Cancels an entire sale, restores all batch stocks, and flags as Cancelled.
    """
    sale = Sale.query.get(sale_id)
    if not sale:
        raise ValueError("Sale not found.")
    if sale.status == 'Cancelled':
        raise ValueError("Sale is already cancelled.")

    for item in sale.items:
        batch = item.batch
        batch.quantity += item.quantity
        movement = StockMovement(
            medicine_id=item.medicine_id,
            batch_id=batch.id,
            movement_type='Adjustment',
            quantity_change=item.quantity,
            current_stock_after=batch.quantity,
            reason=f"Restored stock from cancelled invoice #{sale.invoice_number}",
            reference_id=sale.invoice_number,
            created_by=user.id,
            created_at=datetime.now()
        )
        db.session.add(movement)

    sale.status = 'Cancelled'
    sale.notes = f"{sale.notes or ''} [Cancelled by {user.full_name}: {reason}]"

    audit = AuditLog(
        user_id=user.id,
        action='CANCEL_SALE',
        module='Billing',
        details=f"Cancelled invoice #{sale.invoice_number} of ₹{sale.total_amount}. Reason: {reason}"
    )
    db.session.add(audit)

    db.session.commit()
    return sale
