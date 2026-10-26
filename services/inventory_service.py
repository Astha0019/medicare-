from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from models import (
    db, Medicine, MedicineBatch, Purchase, PurchaseItem, Supplier, 
    MedicalRepresentative, StockMovement, Return, ReturnItem, Payment, AuditLog
)

def record_purchase(user, purchase_data, items_data):
    """
    Records an incoming purchase invoice and automatically updates or creates batches and stock.
    purchase_data: {supplier_id, mr_id, invoice_number, purchase_date, payment_mode, payment_status, notes}
    items_data: list of dicts with medicine_id, batch_number, mfg_date, expiry_date, quantity, 
                free_quantity, purchase_price, mrp, selling_price, gst_rate, discount_percent
    """
    supplier_id = int(purchase_data['supplier_id'])
    invoice_no = str(purchase_data['invoice_number']).strip()
    mr_id = int(purchase_data['mr_id']) if purchase_data.get('mr_id') else None

    # Duplicate supplier invoice prevention
    existing = Purchase.query.filter_by(supplier_id=supplier_id, invoice_number=invoice_no).first()
    if existing:
        raise ValueError(f"Supplier invoice '{invoice_no}' has already been recorded for this supplier.")

    p_date = purchase_data.get('purchase_date')
    if isinstance(p_date, str):
        p_date = datetime.strptime(p_date, '%Y-%m-%d').date()
    elif not p_date:
        p_date = date.today()

    purchase = Purchase(
        invoice_number=invoice_no,
        supplier_id=supplier_id,
        mr_id=mr_id,
        purchase_date=p_date,
        subtotal=Decimal('0.00'),
        tax_amount=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        net_amount=Decimal('0.00'),
        payment_status=purchase_data.get('payment_status', 'Paid'),
        payment_mode=purchase_data.get('payment_mode', 'Bank Transfer'),
        notes=purchase_data.get('notes', ''),
        created_by=user.id
    )
    db.session.add(purchase)
    db.session.flush()

    subtotal_acc = Decimal('0.00')
    tax_acc = Decimal('0.00')
    discount_acc = Decimal('0.00')

    for item in items_data:
        med_id = int(item['medicine_id'])
        batch_no = str(item['batch_number']).strip().upper()
        qty = int(item['quantity'])
        free_qty = int(item.get('free_quantity', 0) or 0)
        p_price = Decimal(str(item['purchase_price'])).quantize(Decimal('0.01'))
        mrp = Decimal(str(item['mrp'])).quantize(Decimal('0.01'))
        s_price = Decimal(str(item.get('selling_price') or mrp)).quantize(Decimal('0.01'))
        gst_rate = Decimal(str(item.get('gst_rate', 12.0))).quantize(Decimal('0.01'))
        disc_pct = Decimal(str(item.get('discount_percent', 0.0))).quantize(Decimal('0.01'))

        # Dates
        exp_date_raw = item['expiry_date']
        if isinstance(exp_date_raw, str):
            exp_date = datetime.strptime(exp_date_raw, '%Y-%m-%d').date()
        else:
            exp_date = exp_date_raw

        mfg_date_raw = item.get('mfg_date')
        if mfg_date_raw and isinstance(mfg_date_raw, str):
            mfg_date = datetime.strptime(mfg_date_raw, '%Y-%m-%d').date()
        elif isinstance(mfg_date_raw, date):
            mfg_date = mfg_date_raw
        else:
            mfg_date = None

        total_received_units = qty + free_qty

        # Line calculation:
        # Billed amount = qty * purchase_price
        gross_line = (p_price * qty).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        disc_line = ((gross_line * disc_pct) / Decimal('100.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        taxable_line = gross_line - disc_line
        tax_line = ((taxable_line * gst_rate) / Decimal('100.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net_line = taxable_line + tax_line

        # Find or create MedicineBatch
        batch = MedicineBatch.query.filter_by(
            medicine_id=med_id,
            batch_number=batch_no
        ).first()

        if batch:
            batch.quantity += total_received_units
            batch.purchase_price = p_price
            batch.mrp = mrp
            batch.selling_price = s_price
            batch.expiry_date = exp_date
            if mfg_date:
                batch.mfg_date = mfg_date
            batch.supplier_id = supplier_id
            batch.is_active = True
        else:
            batch = MedicineBatch(
                medicine_id=med_id,
                supplier_id=supplier_id,
                batch_number=batch_no,
                mfg_date=mfg_date,
                expiry_date=exp_date,
                purchase_price=p_price,
                mrp=mrp,
                selling_price=s_price,
                quantity=total_received_units,
                initial_quantity=total_received_units,
                is_active=True
            )
            db.session.add(batch)
            db.session.flush()

        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            medicine_id=med_id,
            batch_id=batch.id,
            batch_number=batch_no,
            mfg_date=mfg_date,
            expiry_date=exp_date,
            quantity=qty,
            free_quantity=free_qty,
            purchase_price=p_price,
            mrp=mrp,
            selling_price=s_price,
            gst_rate=gst_rate,
            discount_percent=disc_pct,
            tax_amount=tax_line,
            total_amount=net_line
        )
        db.session.add(purchase_item)

        # Stock movement record
        movement = StockMovement(
            medicine_id=med_id,
            batch_id=batch.id,
            movement_type='Purchase',
            quantity_change=total_received_units,
            current_stock_after=batch.quantity,
            reason=f"Purchase from {purchase.supplier.name} (Inv: {invoice_no})",
            reference_id=invoice_no,
            created_by=user.id,
            created_at=datetime.now()
        )
        db.session.add(movement)

        subtotal_acc += gross_line
        discount_acc += disc_line
        tax_acc += tax_line

    net_purchase_amount = (subtotal_acc - discount_acc + tax_acc).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    purchase.subtotal = subtotal_acc
    purchase.discount_amount = discount_acc
    purchase.tax_amount = tax_acc
    purchase.net_amount = net_purchase_amount

    # Add payment entry
    if purchase.payment_status in ['Paid', 'Partial']:
        pmt = Payment(
            purchase_id=purchase.id,
            payment_type='Purchase',
            amount=net_purchase_amount if purchase.payment_status == 'Paid' else (net_purchase_amount / 2),
            payment_mode=purchase.payment_mode,
            status='Success',
            notes=f"Purchase payment for Supplier Inv #{invoice_no}"
        )
        db.session.add(pmt)

    audit = AuditLog(
        user_id=user.id,
        action='ADD_PURCHASE',
        module='Purchases',
        details=f"Recorded Purchase #{invoice_no} from {purchase.supplier.name} for ₹{net_purchase_amount}"
    )
    db.session.add(audit)

    db.session.commit()
    return purchase


def write_off_expired_batch(user, batch_id, quantity, reason):
    """
    Write off expired or damaged medicine batch stock.
    """
    batch = MedicineBatch.query.get(batch_id)
    if not batch:
        raise ValueError("Batch not found.")
    if quantity <= 0 or quantity > batch.quantity:
        raise ValueError(f"Invalid write-off quantity: {quantity}. Available: {batch.quantity}")

    today_str = datetime.now().strftime('%Y%m%d')
    ret_no = f"WO-{today_str}-{batch.id}"

    cost_val = (batch.purchase_price * quantity).quantize(Decimal('0.01'))

    ret_record = Return(
        return_number=ret_no,
        supplier_id=batch.supplier_id,
        return_type='ExpiryWriteOff',
        return_date=datetime.now(),
        total_amount=cost_val,
        reason=reason or f"Expired Stock Write-off ({quantity} units)",
        status='Completed',
        created_by=user.id
    )
    db.session.add(ret_record)
    db.session.flush()

    ret_item = ReturnItem(
        return_id=ret_record.id,
        medicine_id=batch.medicine_id,
        batch_id=batch.id,
        quantity=quantity,
        unit_price=batch.purchase_price,
        total_amount=cost_val,
        action_taken='WrittenOff'
    )
    db.session.add(ret_item)

    batch.quantity -= quantity

    movement = StockMovement(
        medicine_id=batch.medicine_id,
        batch_id=batch.id,
        movement_type='WriteOff',
        quantity_change=-quantity,
        current_stock_after=batch.quantity,
        reason=f"Write-off: {reason} ({ret_no})",
        reference_id=ret_no,
        created_by=user.id,
        created_at=datetime.now()
    )
    db.session.add(movement)

    audit = AuditLog(
        user_id=user.id,
        action='WRITE_OFF_BATCH',
        module='Expiry',
        details=f"Wrote off {quantity} units of {batch.medicine.name} (Batch: {batch.batch_number}). Cost: ₹{cost_val}"
    )
    db.session.add(audit)

    db.session.commit()
    return ret_record


def return_batch_to_supplier(user, batch_id, quantity, reason):
    """
    Return near-expiry or defective batch stock to supplier.
    """
    batch = MedicineBatch.query.get(batch_id)
    if not batch:
        raise ValueError("Batch not found.")
    if not batch.supplier_id:
        raise ValueError("Batch has no supplier assigned. Please assign a supplier before returning.")
    if quantity <= 0 or quantity > batch.quantity:
        raise ValueError(f"Invalid return quantity: {quantity}. Available: {batch.quantity}")

    today_str = datetime.now().strftime('%Y%m%d')
    ret_no = f"SRET-{today_str}-{batch.id}"
    credit_amount = (batch.purchase_price * quantity).quantize(Decimal('0.01'))

    ret_record = Return(
        return_number=ret_no,
        supplier_id=batch.supplier_id,
        return_type='SupplierReturn',
        return_date=datetime.now(),
        total_amount=credit_amount,
        reason=reason or f"Returned to supplier ({quantity} units)",
        status='Completed',
        created_by=user.id
    )
    db.session.add(ret_record)
    db.session.flush()

    ret_item = ReturnItem(
        return_id=ret_record.id,
        medicine_id=batch.medicine_id,
        batch_id=batch.id,
        quantity=quantity,
        unit_price=batch.purchase_price,
        total_amount=credit_amount,
        action_taken='ReturnedToSupplier'
    )
    db.session.add(ret_item)

    batch.quantity -= quantity

    movement = StockMovement(
        medicine_id=batch.medicine_id,
        batch_id=batch.id,
        movement_type='SupplierReturn',
        quantity_change=-quantity,
        current_stock_after=batch.quantity,
        reason=f"Returned to supplier {batch.supplier.name} ({ret_no}): {reason}",
        reference_id=ret_no,
        created_by=user.id,
        created_at=datetime.now()
    )
    db.session.add(movement)

    audit = AuditLog(
        user_id=user.id,
        action='RETURN_TO_SUPPLIER',
        module='Expiry',
        details=f"Returned {quantity} units of {batch.medicine.name} (Batch: {batch.batch_number}) to supplier {batch.supplier.name}. Credit: ₹{credit_amount}"
    )
    db.session.add(audit)

    db.session.commit()
    return ret_record


def adjust_batch_stock(user, batch_id, new_quantity, reason):
    """
    Manually adjust batch stock to fix physical audit discrepancies.
    """
    batch = MedicineBatch.query.get(batch_id)
    if not batch:
        raise ValueError("Batch not found.")
    if new_quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    delta = new_quantity - batch.quantity
    if delta == 0:
        return batch

    batch.quantity = new_quantity

    movement = StockMovement(
        medicine_id=batch.medicine_id,
        batch_id=batch.id,
        movement_type='Adjustment',
        quantity_change=delta,
        current_stock_after=batch.quantity,
        reason=f"Manual Stock Audit Discrepancy Adjustment: {reason}",
        reference_id=f"ADJ-{batch.id}",
        created_by=user.id,
        created_at=datetime.now()
    )
    db.session.add(movement)

    audit = AuditLog(
        user_id=user.id,
        action='ADJUST_STOCK',
        module='Inventory',
        details=f"Adjusted stock for {batch.medicine.name} (Batch {batch.batch_number}) by {delta:+d} to {new_quantity}. Reason: {reason}"
    )
    db.session.add(audit)

    db.session.commit()
    return batch


def get_expiry_buckets():
    """
    Categorizes all batches with stock > 0 into:
    - Expired (< 0 days)
    - Expiring in 30 days (0-30 days)
    - Expiring in 60 days (31-60 days)
    - Expiring in 90 days (61-90 days)
    - Good (> 90 days)
    """
    today = date.today()
    batches = MedicineBatch.query.filter(
        MedicineBatch.is_active == True,
        MedicineBatch.quantity > 0
    ).order_by(MedicineBatch.expiry_date.asc()).all()

    buckets = {
        'expired': [],
        'within_30': [],
        'within_60': [],
        'within_90': [],
        'good': []
    }

    total_loss_expired = Decimal('0.00')
    total_at_risk_30 = Decimal('0.00')
    total_at_risk_60 = Decimal('0.00')
    total_at_risk_90 = Decimal('0.00')

    for b in batches:
        days = (b.expiry_date - today).days
        val = (b.purchase_price * b.quantity).quantize(Decimal('0.01'))
        mrp_val = (b.mrp * b.quantity).quantize(Decimal('0.01'))

        item_info = {
            'batch': b,
            'medicine': b.medicine,
            'days': days,
            'purchase_value': val,
            'mrp_value': mrp_val
        }

        if days < 0:
            buckets['expired'].append(item_info)
            total_loss_expired += val
        elif days <= 30:
            buckets['within_30'].append(item_info)
            total_at_risk_30 += val
        elif days <= 60:
            buckets['within_60'].append(item_info)
            total_at_risk_60 += val
        elif days <= 90:
            buckets['within_90'].append(item_info)
            total_at_risk_90 += val
        else:
            buckets['good'].append(item_info)

    return {
        'buckets': buckets,
        'counts': {
            'expired': len(buckets['expired']),
            'within_30': len(buckets['within_30']),
            'within_60': len(buckets['within_60']),
            'within_90': len(buckets['within_90']),
            'good': len(buckets['good']),
            'total_expiring_soon': len(buckets['within_30']) + len(buckets['within_60']) + len(buckets['within_90'])
        },
        'valuation': {
            'expired_loss': total_loss_expired,
            'risk_30': total_at_risk_30,
            'risk_60': total_at_risk_60,
            'risk_90': total_at_risk_90
        }
    }
