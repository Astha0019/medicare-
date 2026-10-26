import os
import csv
import io
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import (
    Flask, render_template, request, redirect, url_for, flash, 
    jsonify, Response, abort, send_file
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from functools import wraps

from config import Config
from models import (
    db, User, Supplier, MedicalRepresentative, Medicine, MedicineBatch, 
    Purchase, PurchaseItem, Sale, SaleItem, StockMovement, Return, ReturnItem, 
    Payment, AuditLog
)
from utils.formatters import format_inr, format_date, format_datetime, number_to_words_inr
from utils.invoice_pdf import generate_invoice_pdf
from services.billing_service import create_sale, process_sale_return, cancel_sale
from services.inventory_service import (
    record_purchase, write_off_expired_batch, return_batch_to_supplier, 
    adjust_batch_stock, get_expiry_buckets
)
from services.report_service import (
    get_dashboard_metrics, get_sales_report, get_purchase_report, 
    get_top_selling_medicines, get_supplier_analytics, get_mr_analytics, 
    get_returns_analytics
)
from seed_data import seed_database

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Initialize LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access MediCare Pro.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Template filters
    @app.template_filter('inr')
    def inr_filter(val, symbol=True):
        return format_inr(val, include_symbol=symbol)

    @app.template_filter('date_fmt')
    def date_filter(dt):
        return format_date(dt)

    @app.template_filter('datetime_fmt')
    def datetime_filter(dt):
        return format_datetime(dt)

    @app.template_filter('words_inr')
    def words_filter(val):
        return number_to_words_inr(val)

    # Context processors for all templates
    @app.context_processor
    def inject_global_data():
        low_count = 0
        expiry_count = 0
        if current_user.is_authenticated:
            try:
                # Fast count
                today = date.today()
                expiry_count = MedicineBatch.query.filter(
                    MedicineBatch.is_active == True,
                    MedicineBatch.expiry_date <= today + timedelta(days=90),
                    MedicineBatch.quantity > 0
                ).count()
            except Exception:
                pass
        return {
            'pharmacy_name': Config.PHARMACY_NAME,
            'currency_symbol': Config.CURRENCY_SYMBOL,
            'current_date': date.today().strftime('%d-%m-%Y'),
            'expiry_alert_count': expiry_count
        }

    # Role check decorator
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                flash('Access restricted to administrators only.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function

    # -------------------------------------------------------------
    # Authentication Routes
    # -------------------------------------------------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact admin.', 'danger')
                    return render_template('login.html')

                login_user(user)
                flash(f'Welcome back, {user.full_name}!', 'success')

                audit = AuditLog(
                    user_id=user.id,
                    action='LOGIN',
                    module='Auth',
                    details=f"User {user.username} logged in successfully.",
                    ip_address=request.remote_addr
                )
                db.session.add(audit)
                db.session.commit()

                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid username or password. Please try again.', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        audit = AuditLog(
            user_id=current_user.id,
            action='LOGOUT',
            module='Auth',
            details=f"User {current_user.username} logged out.",
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()

        logout_user()
        flash('You have been logged out safely.', 'info')
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # Dashboard Route
    # -------------------------------------------------------------
    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        metrics = get_dashboard_metrics()
        return render_template('dashboard.html', m=metrics)

    # -------------------------------------------------------------
    # Medicine Inventory Routes
    # -------------------------------------------------------------
    @app.route('/inventory')
    @login_required
    def inventory():
        search_query = request.args.get('q', '').strip()
        category_filter = request.args.get('category', '').strip()
        brand_filter = request.args.get('brand', '').strip()
        stock_filter = request.args.get('stock', '').strip()

        query = Medicine.query.filter_by(is_active=True)

        if search_query:
            query = query.filter(
                (Medicine.name.ilike(f'%{search_query}%')) |
                (Medicine.generic_composition.ilike(f'%{search_query}%')) |
                (Medicine.sku.ilike(f'%{search_query}%')) |
                (Medicine.barcode.ilike(f'%{search_query}%')) |
                (Medicine.brand_name.ilike(f'%{search_query}%'))
            )

        if category_filter:
            query = query.filter_by(category=category_filter)

        if brand_filter:
            query = query.filter_by(brand_name=brand_filter)

        medicines = query.order_by(Medicine.name.asc()).all()

        if stock_filter == 'low':
            medicines = [m for m in medicines if m.is_low_stock]
        elif stock_filter == 'out':
            medicines = [m for m in medicines if m.total_stock == 0]
        elif stock_filter == 'near_expiry':
            medicines = [m for m in medicines if m.has_near_expiry]
        elif stock_filter == 'expired':
            medicines = [m for m in medicines if m.has_expired]

        # Extract distinct categories and brands for filter dropdowns
        categories = sorted(list(set(m.category for m in Medicine.query.filter_by(is_active=True).all() if m.category)))
        brands = sorted(list(set(m.brand_name for m in Medicine.query.filter_by(is_active=True).all() if m.brand_name)))

        return render_template(
            'inventory.html', 
            medicines=medicines, 
            categories=categories, 
            brands=brands,
            search_query=search_query,
            selected_category=category_filter,
            selected_brand=brand_filter,
            selected_stock=stock_filter
        )

    @app.route('/inventory/add', methods=['GET', 'POST'])
    @login_required
    def add_medicine():
        suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()

        if request.method == 'POST':
            try:
                name = request.form.get('name', '').strip()
                brand_name = request.form.get('brand_name', '').strip()
                manufacturer = request.form.get('manufacturer', '').strip()
                generic_comp = request.form.get('generic_composition', '').strip()
                dosage_form = request.form.get('dosage_form', 'Tablet').strip()
                strength = request.form.get('strength', '').strip()
                category = request.form.get('category', 'General').strip()
                sku = request.form.get('sku', '').strip().upper()
                barcode = request.form.get('barcode', '').strip() or None
                hsn_code = request.form.get('hsn_code', '3004').strip()
                gst_rate = Decimal(request.form.get('gst_rate', '12.00'))
                rack_location = request.form.get('rack_location', '').strip()
                min_stock = int(request.form.get('min_stock_level', 15))

                if not name or not manufacturer or not generic_comp or not sku:
                    flash('Please fill in all required fields.', 'danger')
                    return render_template('medicine_form.html', suppliers=suppliers, mode='add')

                # Check unique SKU
                if Medicine.query.filter_by(sku=sku).first():
                    flash(f'SKU "{sku}" already exists. Please provide a unique SKU.', 'danger')
                    return render_template('medicine_form.html', suppliers=suppliers, mode='add')

                if barcode and Medicine.query.filter_by(barcode=barcode).first():
                    flash(f'Barcode "{barcode}" already exists.', 'danger')
                    return render_template('medicine_form.html', suppliers=suppliers, mode='add')

                medicine = Medicine(
                    name=name,
                    brand_name=brand_name,
                    manufacturer=manufacturer,
                    generic_composition=generic_comp,
                    dosage_form=dosage_form,
                    strength=strength,
                    category=category,
                    sku=sku,
                    barcode=barcode,
                    hsn_code=hsn_code,
                    gst_rate=gst_rate,
                    rack_location=rack_location,
                    min_stock_level=min_stock,
                    is_demo=False,
                    is_active=True
                )
                db.session.add(medicine)
                db.session.flush()

                # Optional initial batch creation if provided
                batch_number = request.form.get('initial_batch_number', '').strip().upper()
                if batch_number:
                    exp_date = datetime.strptime(request.form.get('initial_expiry_date'), '%Y-%m-%d').date()
                    mfg_raw = request.form.get('initial_mfg_date')
                    mfg_date = datetime.strptime(mfg_raw, '%Y-%m-%d').date() if mfg_raw else None
                    qty = int(request.form.get('initial_quantity', 0))
                    p_price = Decimal(request.form.get('initial_purchase_price', '0.00'))
                    mrp = Decimal(request.form.get('initial_mrp', '0.00'))
                    s_price = Decimal(request.form.get('initial_selling_price', '0.00') or mrp)
                    supplier_id = int(request.form.get('initial_supplier_id')) if request.form.get('initial_supplier_id') else None

                    batch = MedicineBatch(
                        medicine_id=medicine.id,
                        supplier_id=supplier_id,
                        batch_number=batch_number,
                        mfg_date=mfg_date,
                        expiry_date=exp_date,
                        purchase_price=p_price,
                        mrp=mrp,
                        selling_price=s_price,
                        quantity=qty,
                        initial_quantity=qty,
                        is_active=True
                    )
                    db.session.add(batch)
                    db.session.flush()

                    if qty > 0:
                        mov = StockMovement(
                            medicine_id=medicine.id,
                            batch_id=batch.id,
                            movement_type='Purchase',
                            quantity_change=qty,
                            current_stock_after=qty,
                            reason="Opening Stock Setup",
                            reference_id="OPENING-STOCK",
                            created_by=current_user.id
                        )
                        db.session.add(mov)

                audit = AuditLog(
                    user_id=current_user.id,
                    action='ADD_MEDICINE',
                    module='Inventory',
                    details=f"Added new medicine {medicine.name} (SKU: {medicine.sku})"
                )
                db.session.add(audit)
                db.session.commit()

                flash(f'Medicine "{medicine.name}" created successfully.', 'success')
                return redirect(url_for('inventory'))

            except Exception as e:
                db.session.rollback()
                flash(f'Error adding medicine: {str(e)}', 'danger')

        return render_template('medicine_form.html', suppliers=suppliers, mode='add', medicine=None)

    @app.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_medicine(id):
        medicine = Medicine.query.get_or_404(id)
        suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()

        if request.method == 'POST':
            try:
                medicine.name = request.form.get('name', '').strip()
                medicine.brand_name = request.form.get('brand_name', '').strip()
                medicine.manufacturer = request.form.get('manufacturer', '').strip()
                medicine.generic_composition = request.form.get('generic_composition', '').strip()
                medicine.dosage_form = request.form.get('dosage_form', 'Tablet').strip()
                medicine.strength = request.form.get('strength', '').strip()
                medicine.category = request.form.get('category', 'General').strip()
                medicine.barcode = request.form.get('barcode', '').strip() or None
                medicine.hsn_code = request.form.get('hsn_code', '3004').strip()
                medicine.gst_rate = Decimal(request.form.get('gst_rate', '12.00'))
                medicine.rack_location = request.form.get('rack_location', '').strip()
                medicine.min_stock_level = int(request.form.get('min_stock_level', 15))

                audit = AuditLog(
                    user_id=current_user.id,
                    action='EDIT_MEDICINE',
                    module='Inventory',
                    details=f"Updated details for medicine {medicine.name} (SKU: {medicine.sku})"
                )
                db.session.add(audit)
                db.session.commit()

                flash(f'Medicine "{medicine.name}" updated successfully.', 'success')
                return redirect(url_for('view_medicine', id=medicine.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Error updating medicine: {str(e)}', 'danger')

        return render_template('medicine_form.html', suppliers=suppliers, mode='edit', medicine=medicine)

    @app.route('/inventory/view/<int:id>')
    @login_required
    def view_medicine(id):
        medicine = Medicine.query.get_or_404(id)
        batches = medicine.batches.order_by(MedicineBatch.expiry_date.asc()).all()
        movements = medicine.stock_movements.order_by(StockMovement.created_at.desc()).limit(20).all()
        suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()
        return render_template(
            'medicine_view.html', 
            medicine=medicine, 
            batches=batches, 
            movements=movements,
            suppliers=suppliers
        )

    @app.route('/inventory/batch/add/<int:medicine_id>', methods=['POST'])
    @login_required
    def add_batch(medicine_id):
        medicine = Medicine.query.get_or_404(medicine_id)
        try:
            batch_no = request.form.get('batch_number', '').strip().upper()
            exp_date = datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date()
            mfg_raw = request.form.get('mfg_date')
            mfg_date = datetime.strptime(mfg_raw, '%Y-%m-%d').date() if mfg_raw else None
            qty = int(request.form.get('quantity', 0))
            p_price = Decimal(request.form.get('purchase_price', '0.00'))
            mrp = Decimal(request.form.get('mrp', '0.00'))
            s_price = Decimal(request.form.get('selling_price', '0.00') or mrp)
            supplier_id = int(request.form.get('supplier_id')) if request.form.get('supplier_id') else None

            if not batch_no:
                flash('Batch number is required.', 'danger')
                return redirect(url_for('view_medicine', id=medicine.id))

            # Check if batch exists
            existing_batch = MedicineBatch.query.filter_by(medicine_id=medicine.id, batch_number=batch_no).first()
            if existing_batch:
                flash(f'Batch "{batch_no}" already exists for this medicine. Please update stock instead.', 'warning')
                return redirect(url_for('view_medicine', id=medicine.id))

            batch = MedicineBatch(
                medicine_id=medicine.id,
                supplier_id=supplier_id,
                batch_number=batch_no,
                mfg_date=mfg_date,
                expiry_date=exp_date,
                purchase_price=p_price,
                mrp=mrp,
                selling_price=s_price,
                quantity=qty,
                initial_quantity=qty,
                is_active=True
            )
            db.session.add(batch)
            db.session.flush()

            if qty > 0:
                mov = StockMovement(
                    medicine_id=medicine.id,
                    batch_id=batch.id,
                    movement_type='Purchase',
                    quantity_change=qty,
                    current_stock_after=qty,
                    reason="Manual Batch Creation",
                    reference_id=f"BATCH-{batch.batch_number}",
                    created_by=current_user.id
                )
                db.session.add(mov)

            db.session.commit()
            flash(f'Batch {batch_no} added successfully.', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding batch: {str(e)}', 'danger')

        return redirect(url_for('view_medicine', id=medicine.id))

    @app.route('/inventory/batch/adjust', methods=['POST'])
    @login_required
    def adjust_stock():
        try:
            batch_id = int(request.form.get('batch_id'))
            new_qty = int(request.form.get('new_quantity'))
            reason = request.form.get('reason', 'Audit Discrepancy Correction').strip()

            batch = adjust_batch_stock(current_user, batch_id, new_qty, reason)
            flash(f'Stock for Batch {batch.batch_number} updated to {new_qty} units.', 'success')
            return redirect(url_for('view_medicine', id=batch.medicine_id))
        except Exception as e:
            flash(f'Error adjusting stock: {str(e)}', 'danger')
            return redirect(url_for('inventory'))

    @app.route('/inventory/api/search')
    @login_required
    def api_search_medicines():
        """
        Fast JSON search endpoint for Point of Sale billing.
        Returns medicine details and active, sellable (non-expired, stock > 0) batches.
        """
        q = request.args.get('term', '').strip()
        if not q or len(q) < 2:
            return jsonify([])

        medicines = Medicine.query.filter(
            Medicine.is_active == True,
            (
                (Medicine.name.ilike(f'%{q}%')) |
                (Medicine.brand_name.ilike(f'%{q}%')) |
                (Medicine.sku.ilike(f'%{q}%')) |
                (Medicine.barcode == q)
            )
        ).limit(15).all()

        today = date.today()
        results = []
        for m in medicines:
            # Only include non-expired batches with positive stock
            batches = m.batches.filter(
                MedicineBatch.is_active == True,
                MedicineBatch.expiry_date >= today,
                MedicineBatch.quantity > 0
            ).order_by(MedicineBatch.expiry_date.asc()).all()

            if not batches:
                continue

            batches_data = []
            for b in batches:
                batches_data.append({
                    'id': b.id,
                    'batch_number': b.batch_number,
                    'expiry_date': b.expiry_date.strftime('%d-%m-%Y'),
                    'mrp': float(b.mrp),
                    'selling_price': float(b.selling_price),
                    'quantity': b.quantity,
                    'days_to_expiry': (b.expiry_date - today).days
                })

            results.append({
                'id': m.id,
                'name': m.name,
                'brand_name': m.brand_name or '',
                'generic': m.generic_composition,
                'dosage_form': m.dosage_form,
                'strength': m.strength,
                'hsn_code': m.hsn_code,
                'gst_rate': float(m.gst_rate),
                'rack_location': m.rack_location or 'N/A',
                'batches': batches_data
            })

        return jsonify(results)

    # -------------------------------------------------------------
    # Billing / Point of Sale (POS) Routes
    # -------------------------------------------------------------
    @app.route('/billing')
    @login_required
    def billing():
        return render_template('billing.html')

    @app.route('/billing/checkout', methods=['POST'])
    @login_required
    def checkout():
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'success': False, 'message': 'No transaction data received.'}), 400

            customer_name = data.get('customer_name')
            customer_phone = data.get('customer_phone')
            doctor_name = data.get('doctor_name')
            payment_mode = data.get('payment_mode', 'Cash')
            payment_reference = data.get('payment_reference')
            amount_paid = data.get('amount_paid', 0)
            items = data.get('items', [])
            notes = data.get('notes')

            if not items:
                return jsonify({'success': False, 'message': 'Cart is empty. Please add items.'}), 400

            sale = create_sale(
                cashier_user=current_user,
                customer_name=customer_name,
                customer_phone=customer_phone,
                doctor_name=doctor_name,
                payment_mode=payment_mode,
                payment_reference=payment_reference,
                amount_paid=amount_paid,
                items_data=items,
                notes=notes
            )

            return jsonify({
                'success': True,
                'message': f'Invoice {sale.invoice_number} generated successfully.',
                'invoice_id': sale.id,
                'invoice_number': sale.invoice_number,
                'total_amount': float(sale.total_amount),
                'amount_paid': float(sale.amount_paid),
                'change_returned': float(sale.change_returned)
            })

        except ValueError as ve:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(ve)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Billing error: {str(e)}'}), 500

    @app.route('/invoices')
    @login_required
    def invoices():
        search_query = request.args.get('q', '').strip()
        status_filter = request.args.get('status', '').strip()
        date_from = request.args.get('from', '').strip()
        date_to = request.args.get('to', '').strip()

        query = Sale.query

        if search_query:
            query = query.filter(
                (Sale.invoice_number.ilike(f'%{search_query}%')) |
                (Sale.customer_name.ilike(f'%{search_query}%')) |
                (Sale.customer_phone.ilike(f'%{search_query}%')) |
                (Sale.doctor_name.ilike(f'%{search_query}%'))
            )

        if status_filter:
            query = query.filter_by(status=status_filter)

        if date_from:
            d_start = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Sale.sale_date >= d_start)

        if date_to:
            d_end = datetime.combine(datetime.strptime(date_to, '%Y-%m-%d').date(), datetime.max.time())
            query = query.filter(Sale.sale_date <= d_end)

        invoices_list = query.order_by(Sale.sale_date.desc()).limit(100).all()

        return render_template(
            'invoices.html', 
            invoices=invoices_list,
            search_query=search_query,
            selected_status=status_filter,
            date_from=date_from,
            date_to=date_to
        )

    @app.route('/invoices/view/<int:id>')
    @login_required
    def view_invoice(id):
        sale = Sale.query.get_or_404(id)
        return render_template('invoice_detail.html', sale=sale)

    @app.route('/invoices/pdf/<int:id>')
    @login_required
    def download_invoice_pdf(id):
        sale = Sale.query.get_or_404(id)
        pdf_bytes = generate_invoice_pdf(sale)
        if not pdf_bytes:
            flash('PDF generation is temporarily unavailable. You can use the browser print option.', 'warning')
            return redirect(url_for('view_invoice', id=sale.id))

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=Invoice_{sale.invoice_number}.pdf'}
        )

    @app.route('/invoices/cancel/<int:id>', methods=['POST'])
    @login_required
    def cancel_invoice_route(id):
        reason = request.form.get('reason', 'Customer cancellation').strip()
        try:
            sale = cancel_sale(current_user, id, reason)
            flash(f'Invoice {sale.invoice_number} cancelled and batch stock restored.', 'success')
        except Exception as e:
            flash(f'Error cancelling invoice: {str(e)}', 'danger')
        return redirect(url_for('view_invoice', id=id))

    @app.route('/invoices/return/<int:id>', methods=['GET', 'POST'])
    @login_required
    def return_invoice_route(id):
        sale = Sale.query.get_or_404(id)
        if request.method == 'POST':
            try:
                reason = request.form.get('reason', 'Customer Return').strip()
                return_items = []
                for item in sale.items:
                    qty_key = f"return_qty_{item.id}"
                    action_key = f"return_action_{item.id}"
                    qty = int(request.form.get(qty_key, 0))
                    action = request.form.get(action_key, 'Restock')
                    if qty > 0:
                        return_items.append({
                            'sale_item_id': item.id,
                            'quantity': qty,
                            'action': action
                        })

                if not return_items:
                    flash('Please select at least one item and quantity to return.', 'warning')
                    return render_template('invoice_return.html', sale=sale)

                ret_rec = process_sale_return(current_user, sale.id, return_items, reason)
                flash(f'Return #{ret_rec.return_number} processed. Refund amount: ₹{ret_rec.total_amount}', 'success')
                return redirect(url_for('view_invoice', id=sale.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Error processing return: {str(e)}', 'danger')

        return render_template('invoice_return.html', sale=sale)

    # -------------------------------------------------------------
    # Expiry Management Routes
    # -------------------------------------------------------------
    @app.route('/expiry')
    @login_required
    def expiry():
        expiry_info = get_expiry_buckets()
        return render_template('expiry.html', exp=expiry_info)

    @app.route('/expiry/write-off', methods=['POST'])
    @login_required
    def write_off_batch():
        try:
            batch_id = int(request.form.get('batch_id'))
            qty = int(request.form.get('quantity'))
            reason = request.form.get('reason', 'Expired stock write-off').strip()

            write_off_expired_batch(current_user, batch_id, qty, reason)
            flash(f'Successfully written off {qty} units of expired stock.', 'success')
        except Exception as e:
            flash(f'Error writing off batch: {str(e)}', 'danger')
        return redirect(url_for('expiry'))

    @app.route('/expiry/return-to-supplier', methods=['POST'])
    @login_required
    def return_to_supplier():
        try:
            batch_id = int(request.form.get('batch_id'))
            qty = int(request.form.get('quantity'))
            reason = request.form.get('reason', 'Near expiry return to distributor').strip()

            return_batch_to_supplier(current_user, batch_id, qty, reason)
            flash(f'Successfully returned {qty} units to supplier.', 'success')
        except Exception as e:
            flash(f'Error returning to supplier: {str(e)}', 'danger')
        return redirect(url_for('expiry'))

    # -------------------------------------------------------------
    # Purchases and Suppliers Routes
    # -------------------------------------------------------------
    @app.route('/purchases')
    @login_required
    def purchases():
        purchases_list = Purchase.query.order_by(Purchase.purchase_date.desc()).all()
        return render_template('purchases.html', purchases=purchases_list)

    @app.route('/purchases/new', methods=['GET', 'POST'])
    @login_required
    def new_purchase():
        suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()
        mrs = MedicalRepresentative.query.filter_by(is_active=True).order_by(MedicalRepresentative.name.asc()).all()
        medicines = Medicine.query.filter_by(is_active=True).order_by(Medicine.name.asc()).all()

        if request.method == 'POST':
            try:
                supplier_id = int(request.form.get('supplier_id'))
                invoice_number = request.form.get('invoice_number', '').strip().upper()
                purchase_date = request.form.get('purchase_date')
                mr_id = request.form.get('mr_id') or None
                payment_status = request.form.get('payment_status', 'Paid')
                payment_mode = request.form.get('payment_mode', 'Bank Transfer')
                notes = request.form.get('notes', '').strip()

                # Process multi-line items
                item_med_ids = request.form.getlist('item_medicine_id[]')
                item_batches = request.form.getlist('item_batch_number[]')
                item_mfgs = request.form.getlist('item_mfg_date[]')
                item_exps = request.form.getlist('item_expiry_date[]')
                item_qtys = request.form.getlist('item_quantity[]')
                item_frees = request.form.getlist('item_free_quantity[]')
                item_pps = request.form.getlist('item_purchase_price[]')
                item_mrps = request.form.getlist('item_mrp[]')
                item_sps = request.form.getlist('item_selling_price[]')
                item_gsts = request.form.getlist('item_gst_rate[]')
                item_discs = request.form.getlist('item_discount_percent[]')

                if not item_med_ids:
                    flash('Please add at least one medicine item to the purchase invoice.', 'danger')
                    return render_template('purchase_form.html', suppliers=suppliers, mrs=mrs, medicines=medicines)

                items_data = []
                for i in range(len(item_med_ids)):
                    if not item_med_ids[i] or not item_batches[i] or not item_exps[i]:
                        continue
                    items_data.append({
                        'medicine_id': int(item_med_ids[i]),
                        'batch_number': item_batches[i].strip().upper(),
                        'mfg_date': item_mfgs[i] if (i < len(item_mfgs) and item_mfgs[i]) else None,
                        'expiry_date': item_exps[i],
                        'quantity': int(item_qtys[i]),
                        'free_quantity': int(item_frees[i]) if (i < len(item_frees) and item_frees[i]) else 0,
                        'purchase_price': Decimal(item_pps[i]),
                        'mrp': Decimal(item_mrps[i]),
                        'selling_price': Decimal(item_sps[i] or item_mrps[i]),
                        'gst_rate': Decimal(item_gsts[i] if i < len(item_gsts) and item_gsts[i] else 12.0),
                        'discount_percent': Decimal(item_discs[i] if i < len(item_discs) and item_discs[i] else 0.0)
                    })

                purchase_data = {
                    'supplier_id': supplier_id,
                    'invoice_number': invoice_number,
                    'purchase_date': purchase_date,
                    'mr_id': mr_id,
                    'payment_status': payment_status,
                    'payment_mode': payment_mode,
                    'notes': notes
                }

                pur = record_purchase(current_user, purchase_data, items_data)
                flash(f'Purchase invoice #{pur.invoice_number} recorded successfully and stock updated.', 'success')
                return redirect(url_for('view_purchase', id=pur.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Error recording purchase: {str(e)}', 'danger')

        return render_template('purchase_form.html', suppliers=suppliers, mrs=mrs, medicines=medicines)

    @app.route('/purchases/view/<int:id>')
    @login_required
    def view_purchase(id):
        purchase = Purchase.query.get_or_404(id)
        return render_template('purchase_detail.html', purchase=purchase)

    @app.route('/suppliers', methods=['GET', 'POST'])
    @login_required
    def suppliers():
        if request.method == 'POST':
            try:
                name = request.form.get('name', '').strip()
                company_name = request.form.get('company_name', '').strip()
                contact_person = request.form.get('contact_person', '').strip()
                phone = request.form.get('phone', '').strip()
                email = request.form.get('email', '').strip()
                address = request.form.get('address', '').strip()
                gstin = request.form.get('gstin', '').strip().upper()
                drug_license_no = request.form.get('drug_license_no', '').strip()

                supplier = Supplier(
                    name=name,
                    company_name=company_name,
                    contact_person=contact_person,
                    phone=phone,
                    email=email,
                    address=address,
                    gstin=gstin,
                    drug_license_no=drug_license_no,
                    is_active=True
                )
                db.session.add(supplier)
                db.session.commit()
                flash(f'Supplier "{supplier.name}" added successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding supplier: {str(e)}', 'danger')
            return redirect(url_for('suppliers'))

        suppliers_analytics = get_supplier_analytics()
        return render_template('suppliers.html', suppliers=suppliers_analytics)

    # -------------------------------------------------------------
    # Medical Representative (MR) Tracking Routes
    # -------------------------------------------------------------
    @app.route('/representatives', methods=['GET', 'POST'])
    @login_required
    def representatives():
        if request.method == 'POST':
            try:
                name = request.form.get('name', '').strip()
                company_name = request.form.get('company_name', '').strip()
                phone = request.form.get('phone', '').strip()
                email = request.form.get('email', '').strip()
                territory = request.form.get('territory', '').strip()
                visit_notes = request.form.get('visit_notes', '').strip()
                v_date_raw = request.form.get('last_visit_date')
                last_visit = datetime.strptime(v_date_raw, '%Y-%m-%d').date() if v_date_raw else date.today()

                mr = MedicalRepresentative(
                    name=name,
                    company_name=company_name,
                    phone=phone,
                    email=email,
                    territory=territory,
                    visit_notes=visit_notes,
                    last_visit_date=last_visit,
                    is_active=True
                )
                db.session.add(mr)
                db.session.commit()
                flash(f'Medical Representative "{mr.name}" registered.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding representative: {str(e)}', 'danger')
            return redirect(url_for('representatives'))

        mr_list = get_mr_analytics()
        return render_template('representatives.html', mrs=mr_list)

    @app.route('/representatives/log-visit/<int:id>', methods=['POST'])
    @login_required
    def log_mr_visit(id):
        mr = MedicalRepresentative.query.get_or_404(id)
        try:
            notes = request.form.get('visit_notes', '').strip()
            v_date_raw = request.form.get('visit_date')
            mr.last_visit_date = datetime.strptime(v_date_raw, '%Y-%m-%d').date() if v_date_raw else date.today()
            if notes:
                existing_notes = mr.visit_notes or ''
                new_entry = f"[{mr.last_visit_date.strftime('%d-%m-%Y')}]: {notes}"
                mr.visit_notes = f"{new_entry}\n{existing_notes}" if existing_notes else new_entry

            db.session.commit()
            flash(f'Visit logged for MR {mr.name}.', 'success')
        except Exception as e:
            flash(f'Error logging visit: {str(e)}', 'danger')
        return redirect(url_for('representatives'))

    # -------------------------------------------------------------
    # Comprehensive Reports Routes
    # -------------------------------------------------------------
    @app.route('/reports')
    @login_required
    def reports():
        report_type = request.args.get('type', 'sales')
        date_from = request.args.get('from', '')
        date_to = request.args.get('to', '')

        # Defaults: current month if not provided
        today = date.today()
        first_of_month = today.replace(day=1).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')

        if not date_from:
            date_from = first_of_month
        if not date_to:
            date_to = today_str

        sales_data = get_sales_report(date_from, date_to)
        purchase_data = get_purchase_report(date_from, date_to)
        top_medicines = get_top_selling_medicines(limit=10)
        supplier_data = get_supplier_analytics()
        mr_data = get_mr_analytics()
        returns_data = get_returns_analytics()
        expiry_data = get_expiry_buckets()

        # Stock valuation
        active_batches = MedicineBatch.query.filter_by(is_active=True).all()
        stock_valuation_cost = sum((b.purchase_price * b.quantity for b in active_batches if b.quantity > 0), Decimal('0.00'))
        stock_valuation_mrp = sum((b.mrp * b.quantity for b in active_batches if b.quantity > 0), Decimal('0.00'))

        # Low stock medicines
        low_stock_list = [m for m in Medicine.query.filter_by(is_active=True).all() if m.is_low_stock]

        return render_template(
            'reports.html',
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            sales_data=sales_data,
            purchase_data=purchase_data,
            top_medicines=top_medicines,
            supplier_data=supplier_data,
            mr_data=mr_data,
            returns_data=returns_data,
            expiry_data=expiry_data,
            valuation_cost=stock_valuation_cost,
            valuation_mrp=stock_valuation_mrp,
            low_stock_list=low_stock_list
        )

    @app.route('/reports/export/csv')
    @login_required
    def export_report_csv():
        report_type = request.args.get('type', 'sales')
        date_from = request.args.get('from', '')
        date_to = request.args.get('to', '')

        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == 'sales':
            sales_data = get_sales_report(date_from, date_to)
            writer.writerow(['Invoice No', 'Date', 'Customer Name', 'Customer Phone', 'Doctor', 'Payment Mode', 'Gross (INR)', 'Discount (INR)', 'Tax/GST (INR)', 'Net Total (INR)', 'Status'])
            for s in sales_data['sales']:
                writer.writerow([
                    s.invoice_number,
                    s.sale_date.strftime('%d-%m-%Y %H:%M'),
                    s.customer_name,
                    s.customer_phone or '',
                    s.doctor_name or '',
                    s.payment_mode,
                    f"{s.subtotal:.2f}",
                    f"{s.discount_amount:.2f}",
                    f"{s.tax_amount:.2f}",
                    f"{s.total_amount:.2f}",
                    s.status
                ])
            filename = f"Medicare_Sales_Report_{date_from}_to_{date_to}.csv"

        elif report_type == 'purchases':
            purchase_data = get_purchase_report(date_from, date_to)
            writer.writerow(['Invoice No', 'Date', 'Supplier', 'MR', 'Subtotal (INR)', 'Tax (INR)', 'Discount (INR)', 'Net Amount (INR)', 'Payment Status'])
            for p in purchase_data['purchases']:
                writer.writerow([
                    p.invoice_number,
                    p.purchase_date.strftime('%d-%m-%Y'),
                    p.supplier.name,
                    p.mr.name if p.mr else 'Direct',
                    f"{p.subtotal:.2f}",
                    f"{p.tax_amount:.2f}",
                    f"{p.discount_amount:.2f}",
                    f"{p.net_amount:.2f}",
                    p.payment_status
                ])
            filename = f"Medicare_Purchase_Report_{date_from}_to_{date_to}.csv"

        elif report_type == 'stock':
            medicines = Medicine.query.filter_by(is_active=True).order_by(Medicine.name.asc()).all()
            writer.writerow(['Medicine Name', 'Brand', 'Category', 'Form', 'Strength', 'SKU', 'Rack', 'Available Stock Units', 'Min Level', 'Status'])
            for m in medicines:
                writer.writerow([
                    m.name,
                    m.brand_name or '',
                    m.category,
                    m.dosage_form,
                    m.strength,
                    m.sku,
                    m.rack_location or '',
                    m.total_stock,
                    m.min_stock_level,
                    'LOW STOCK' if m.is_low_stock else 'Normal'
                ])
            filename = f"Medicare_Stock_Report_{date.today().strftime('%d-%m-%Y')}.csv"

        else: # Expiry
            expiry_info = get_expiry_buckets()
            writer.writerow(['Category', 'Medicine Name', 'Batch No', 'Expiry Date', 'Available Qty', 'Purchase Price (INR)', 'Total Cost Loss/Risk (INR)'])
            for item in expiry_info['buckets']['expired']:
                writer.writerow(['EXPIRED', item['medicine'].name, item['batch'].batch_number, item['batch'].expiry_date.strftime('%d-%m-%Y'), item['batch'].quantity, f"{item['batch'].purchase_price:.2f}", f"{item['purchase_value']:.2f}"])
            for item in expiry_info['buckets']['within_30']:
                writer.writerow(['Expiring < 30 Days', item['medicine'].name, item['batch'].batch_number, item['batch'].expiry_date.strftime('%d-%m-%Y'), item['batch'].quantity, f"{item['batch'].purchase_price:.2f}", f"{item['purchase_value']:.2f}"])
            for item in expiry_info['buckets']['within_60']:
                writer.writerow(['Expiring 30-60 Days', item['medicine'].name, item['batch'].batch_number, item['batch'].expiry_date.strftime('%d-%m-%Y'), item['batch'].quantity, f"{item['batch'].purchase_price:.2f}", f"{item['purchase_value']:.2f}"])
            filename = f"Medicare_Expiry_Risk_Report_{date.today().strftime('%d-%m-%Y')}.csv"

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    # -------------------------------------------------------------
    # Audit Logs (Admin only)
    # -------------------------------------------------------------
    @app.route('/audit-logs')
    @login_required
    @admin_required
    def audit_logs():
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(150).all()
        return render_template('audit_logs.html', logs=logs)

    # CLI command to seed database
    @app.cli.command("init-db")
    def init_db_command():
        """Initialize database with demo Indian pharmacy dataset"""
        seed_database(app)
        print("Database initialized and seeded.")

    return app

app = create_app()

# Auto-initialize and seed database on startup (for both Gunicorn and local development)
with app.app_context():
    try:
        db.create_all()
        seed_database(app)
    except Exception as e:
        app.logger.warning(f"Database auto-seed check: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
