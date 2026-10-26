from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func
from models import (
    db, Sale, SaleItem, Purchase, PurchaseItem, Medicine, MedicineBatch, 
    Supplier, MedicalRepresentative, Return, ReturnItem, StockMovement
)
from services.inventory_service import get_expiry_buckets

def get_dashboard_metrics():
    """
    Computes all live real-time dashboard figures directly from the database.
    """
    today = date.today()
    start_of_today = datetime.combine(today, datetime.min.time())
    end_of_today = datetime.combine(today, datetime.max.time())

    # 1. Total Medicines
    total_medicines = Medicine.query.filter_by(is_active=True).count()

    # 2. Total Stock Units
    active_batches = MedicineBatch.query.filter_by(is_active=True).all()
    total_stock_units = sum(b.quantity for b in active_batches if b.quantity > 0)

    # 3. Today's Sales & Invoices
    today_sales_records = Sale.query.filter(
        Sale.sale_date >= start_of_today,
        Sale.sale_date <= end_of_today,
        Sale.status != 'Cancelled'
    ).all()
    today_sales_amount = sum((s.total_amount for s in today_sales_records), Decimal('0.00'))
    today_invoices_count = len(today_sales_records)

    # 4. Inventory Valuation (Purchase cost vs MRP)
    total_valuation_cost = Decimal('0.00')
    total_valuation_mrp = Decimal('0.00')
    for b in active_batches:
        if b.quantity > 0:
            total_valuation_cost += (b.purchase_price * b.quantity)
            total_valuation_mrp += (b.mrp * b.quantity)

    # 5. Low stock medicines count
    all_active_meds = Medicine.query.filter_by(is_active=True).all()
    low_stock_medicines = [m for m in all_active_meds if m.is_low_stock]
    low_stock_count = len(low_stock_medicines)

    # 6. Expiry metrics
    expiry_data = get_expiry_buckets()
    expired_count = expiry_data['counts']['expired']
    expiring_soon_count = expiry_data['counts']['total_expiring_soon']
    expired_valuation = expiry_data['valuation']['expired_loss']

    # 7. Recent Sales (last 5)
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(5).all()

    # 8. Recent Purchases (last 5)
    recent_purchases = Purchase.query.order_by(Purchase.created_at.desc()).limit(5).all()

    # 9. Chart Data: Last 7 Days Sales
    chart_7_days_labels = []
    chart_7_days_values = []
    for i in range(6, -1, -1):
        day_d = today - timedelta(days=i)
        day_start = datetime.combine(day_d, datetime.min.time())
        day_end = datetime.combine(day_d, datetime.max.time())
        day_sales = Sale.query.filter(
            Sale.sale_date >= day_start,
            Sale.sale_date <= day_end,
            Sale.status != 'Cancelled'
        ).all()
        val = sum((s.total_amount for s in day_sales), Decimal('0.00'))
        chart_7_days_labels.append(day_d.strftime('%d %b'))
        chart_7_days_values.append(float(val))

    # 10. Chart Data: Last 30 Days Sales
    chart_30_days_labels = []
    chart_30_days_values = []
    for i in range(29, -1, -1):
        day_d = today - timedelta(days=i)
        day_start = datetime.combine(day_d, datetime.min.time())
        day_end = datetime.combine(day_d, datetime.max.time())
        day_sales = Sale.query.filter(
            Sale.sale_date >= day_start,
            Sale.sale_date <= day_end,
            Sale.status != 'Cancelled'
        ).all()
        val = sum((s.total_amount for s in day_sales), Decimal('0.00'))
        chart_30_days_labels.append(day_d.strftime('%d-%m'))
        chart_30_days_values.append(float(val))

    # 11. Top categories distribution
    category_counts = {}
    for m in all_active_meds:
        cat = m.category or 'General'
        category_counts[cat] = category_counts.get(cat, 0) + m.total_stock

    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:6]

    return {
        'total_medicines': total_medicines,
        'total_stock_units': total_stock_units,
        'today_sales_amount': today_sales_amount,
        'today_invoices_count': today_invoices_count,
        'low_stock_count': low_stock_count,
        'low_stock_medicines': low_stock_medicines[:5],
        'expired_count': expired_count,
        'expiring_soon_count': expiring_soon_count,
        'expired_valuation': expired_valuation,
        'total_valuation_cost': total_valuation_cost,
        'total_valuation_mrp': total_valuation_mrp,
        'recent_sales': recent_sales,
        'recent_purchases': recent_purchases,
        'chart_7_days': {
            'labels': chart_7_days_labels,
            'amounts': chart_7_days_values
        },
        'chart_30_days': {
            'labels': chart_30_days_labels,
            'amounts': chart_30_days_values
        },
        'category_chart': {
            'labels': [c[0] for c in top_categories],
            'counts': [c[1] for c in top_categories]
        }
    }


def get_sales_report(start_date=None, end_date=None):
    """
    Sales report filtered by date range with summary and line-item profitability.
    """
    query = Sale.query.filter(Sale.status != 'Cancelled')

    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Sale.sale_date >= start_date)

    if end_date:
        if isinstance(end_date, str):
            end_date = datetime.combine(datetime.strptime(end_date, '%Y-%m-%d').date(), datetime.max.time())
        query = query.filter(Sale.sale_date <= end_date)

    sales = query.order_by(Sale.sale_date.desc()).all()

    total_gross = sum((s.subtotal for s in sales), Decimal('0.00'))
    total_discount = sum((s.discount_amount for s in sales), Decimal('0.00'))
    total_tax = sum((s.tax_amount for s in sales), Decimal('0.00'))
    total_cgst = sum((s.cgst_amount for s in sales), Decimal('0.00'))
    total_sgst = sum((s.sgst_amount for s in sales), Decimal('0.00'))
    total_net = sum((s.total_amount for s in sales), Decimal('0.00'))

    # Calculate COGS (Cost of Goods Sold) and Gross Profit
    total_cogs = Decimal('0.00')
    for s in sales:
        for item in s.items:
            if item.batch:
                total_cogs += (item.batch.purchase_price * item.quantity)

    gross_profit = total_net - total_tax - total_cogs
    gross_margin_pct = ((gross_profit / (total_net - total_tax)) * Decimal('100.0')).quantize(Decimal('0.1')) if (total_net - total_tax) > 0 else Decimal('0.0')

    return {
        'sales': sales,
        'count': len(sales),
        'total_gross': total_gross,
        'total_discount': total_discount,
        'total_tax': total_tax,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'total_net': total_net,
        'total_cogs': total_cogs,
        'gross_profit': gross_profit,
        'gross_margin_pct': gross_margin_pct
    }


def get_purchase_report(start_date=None, end_date=None):
    """
    Purchase report filtered by date range.
    """
    query = Purchase.query

    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        query = query.filter(Purchase.purchase_date >= start_date)

    if end_date:
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        query = query.filter(Purchase.purchase_date <= end_date)

    purchases = query.order_by(Purchase.purchase_date.desc()).all()

    total_purchases = sum((p.net_amount for p in purchases), Decimal('0.00'))
    total_tax = sum((p.tax_amount for p in purchases), Decimal('0.00'))
    total_discount = sum((p.discount_amount for p in purchases), Decimal('0.00'))

    paid_amount = sum((p.net_amount for p in purchases if p.payment_status == 'Paid'), Decimal('0.00'))
    pending_amount = sum((p.net_amount for p in purchases if p.payment_status == 'Pending'), Decimal('0.00'))

    return {
        'purchases': purchases,
        'count': len(purchases),
        'total_purchases': total_purchases,
        'total_tax': total_tax,
        'total_discount': total_discount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount
    }


def get_top_selling_medicines(limit=10):
    """
    Identifies top-selling medicines by quantity sold and revenue generated.
    """
    results = db.session.query(
        Medicine.id,
        Medicine.name,
        Medicine.brand_name,
        Medicine.strength,
        Medicine.dosage_form,
        func.sum(SaleItem.quantity).label('total_qty_sold'),
        func.sum(SaleItem.line_total).label('total_revenue')
    ).join(SaleItem, Medicine.id == SaleItem.medicine_id)\
     .join(Sale, SaleItem.sale_id == Sale.id)\
     .filter(Sale.status != 'Cancelled')\
     .group_by(Medicine.id)\
     .order_by(func.sum(SaleItem.line_total).desc())\
     .limit(limit).all()

    top_items = []
    for r in results:
        top_items.append({
            'medicine_id': r.id,
            'name': r.name,
            'brand': r.brand_name or '',
            'form': f"{r.dosage_form} {r.strength}",
            'qty_sold': int(r.total_qty_sold or 0),
            'revenue': Decimal(str(r.total_revenue or 0)).quantize(Decimal('0.01'))
        })
    return top_items


def get_supplier_analytics():
    """
    Supplier-wise purchases and outstanding analysis.
    """
    suppliers = Supplier.query.filter_by(is_active=True).all()
    analytics = []
    for s in suppliers:
        total_spent = sum((p.net_amount for p in s.purchases), Decimal('0.00'))
        pending = sum((p.net_amount for p in s.purchases if p.payment_status == 'Pending'), Decimal('0.00'))
        analytics.append({
            'supplier': s,
            'purchases_count': len(s.purchases),
            'total_amount': total_spent,
            'pending_amount': pending
        })
    analytics.sort(key=lambda x: x['total_amount'], reverse=True)
    return analytics


def get_mr_analytics():
    """
    Medical Representative performance and facilitation analysis.
    """
    mrs = MedicalRepresentative.query.filter_by(is_active=True).all()
    analytics = []
    for mr in mrs:
        total_facilitated = sum((p.net_amount for p in mr.purchases), Decimal('0.00'))
        analytics.append({
            'mr': mr,
            'orders_count': len(mr.purchases),
            'total_amount': total_facilitated,
            'company': mr.company_name,
            'territory': mr.territory or 'N/A'
        })
    analytics.sort(key=lambda x: x['total_amount'], reverse=True)
    return analytics


def get_returns_analytics():
    """
    Returns, write-offs, and damages report.
    """
    returns = Return.query.order_by(Return.return_date.desc()).all()
    cust_returns = [r for r in returns if r.return_type == 'CustomerReturn']
    supp_returns = [r for r in returns if r.return_type == 'SupplierReturn']
    write_offs = [r for r in returns if r.return_type == 'ExpiryWriteOff']

    return {
        'all_returns': returns,
        'customer_returns_count': len(cust_returns),
        'customer_returns_amount': sum((r.total_amount for r in cust_returns), Decimal('0.00')),
        'supplier_returns_count': len(supp_returns),
        'supplier_returns_amount': sum((r.total_amount for r in supp_returns), Decimal('0.00')),
        'write_offs_count': len(write_offs),
        'write_offs_amount': sum((r.total_amount for r in write_offs), Decimal('0.00')),
    }
