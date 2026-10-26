from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # 'admin' or 'cashier'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('Sale', back_populates='cashier', foreign_keys='Sale.created_by')
    purchases = db.relationship('Purchase', back_populates='created_by_user', foreign_keys='Purchase.created_by')
    audit_logs = db.relationship('AuditLog', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active
        }


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    company_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    gstin = db.Column(db.String(20), nullable=True)
    drug_license_no = db.Column(db.String(80), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('Purchase', back_populates='supplier')
    batches = db.relationship('MedicineBatch', back_populates='supplier')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company_name': self.company_name,
            'contact_person': self.contact_person or '',
            'phone': self.phone,
            'email': self.email or '',
            'address': self.address or '',
            'gstin': self.gstin or '',
            'drug_license_no': self.drug_license_no or '',
            'is_active': self.is_active
        }


class MedicalRepresentative(db.Model):
    __tablename__ = 'medical_representatives'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    company_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    territory = db.Column(db.String(120), nullable=True)
    visit_notes = db.Column(db.Text, nullable=True)
    last_visit_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('Purchase', back_populates='mr')

    @property
    def total_purchases_count(self):
        return len(self.purchases)

    @property
    def total_purchase_amount(self):
        return sum([p.net_amount for p in self.purchases if p.net_amount]) or Decimal('0.00')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company_name': self.company_name,
            'phone': self.phone,
            'email': self.email or '',
            'territory': self.territory or '',
            'visit_notes': self.visit_notes or '',
            'last_visit_date': self.last_visit_date.strftime('%d-%m-%Y') if self.last_visit_date else '',
            'is_active': self.is_active,
            'total_purchase_amount': float(self.total_purchase_amount)
        }


class Medicine(db.Model):
    __tablename__ = 'medicines'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    brand_name = db.Column(db.String(150), nullable=True)
    manufacturer = db.Column(db.String(150), nullable=False)
    generic_composition = db.Column(db.String(255), nullable=False)
    dosage_form = db.Column(db.String(50), nullable=False, default='Tablet')  # Tablet, Capsule, Syrup, Injection, etc.
    strength = db.Column(db.String(50), nullable=False)  # 650mg, 500mg, etc.
    category = db.Column(db.String(80), nullable=False, default='General')  # Antibiotics, Analgesic, etc.
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(50), unique=True, nullable=True, index=True)
    hsn_code = db.Column(db.String(20), nullable=False, default='3004')
    gst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))  # 5, 12, 18
    rack_location = db.Column(db.String(60), nullable=True)  # e.g., 'Rack A-02'
    min_stock_level = db.Column(db.Integer, nullable=False, default=15)
    is_demo = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batches = db.relationship('MedicineBatch', back_populates='medicine', lazy='dynamic')
    sale_items = db.relationship('SaleItem', back_populates='medicine', lazy='dynamic')
    purchase_items = db.relationship('PurchaseItem', back_populates='medicine', lazy='dynamic')
    stock_movements = db.relationship('StockMovement', back_populates='medicine', lazy='dynamic')

    @property
    def total_stock(self):
        """Sum of all active batches with non-expired quantity"""
        active_batches = self.batches.filter_by(is_active=True).all()
        return sum(b.quantity for b in active_batches if b.quantity > 0)

    @property
    def active_sellable_stock(self):
        """Stock in batches that are active, not expired, and have quantity > 0"""
        today = date.today()
        batches = self.batches.filter(
            MedicineBatch.is_active == True,
            MedicineBatch.expiry_date >= today,
            MedicineBatch.quantity > 0
        ).all()
        return sum(b.quantity for b in batches)

    @property
    def is_low_stock(self):
        return self.total_stock <= self.min_stock_level

    @property
    def has_near_expiry(self):
        today = date.today()
        return any(
            0 <= (b.expiry_date - today).days <= 90 and b.quantity > 0
            for b in self.batches.filter_by(is_active=True).all()
        )

    @property
    def has_expired(self):
        today = date.today()
        return any(
            b.expiry_date < today and b.quantity > 0
            for b in self.batches.filter_by(is_active=True).all()
        )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand_name': self.brand_name or '',
            'manufacturer': self.manufacturer,
            'generic_composition': self.generic_composition,
            'dosage_form': self.dosage_form,
            'strength': self.strength,
            'category': self.category,
            'sku': self.sku,
            'barcode': self.barcode or '',
            'hsn_code': self.hsn_code,
            'gst_rate': float(self.gst_rate),
            'rack_location': self.rack_location or '',
            'min_stock_level': self.min_stock_level,
            'total_stock': self.total_stock,
            'sellable_stock': self.active_sellable_stock,
            'is_low_stock': self.is_low_stock,
            'is_demo': self.is_demo,
            'is_active': self.is_active
        }


class MedicineBatch(db.Model):
    __tablename__ = 'medicine_batches'

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    batch_number = db.Column(db.String(50), nullable=False, index=True)
    mfg_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    mrp = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    initial_quantity = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    medicine = db.relationship('Medicine', back_populates='batches')
    supplier = db.relationship('Supplier', back_populates='batches')
    sale_items = db.relationship('SaleItem', back_populates='batch')
    stock_movements = db.relationship('StockMovement', back_populates='batch')

    @property
    def is_expired(self):
        return self.expiry_date < date.today()

    @property
    def days_to_expiry(self):
        return (self.expiry_date - date.today()).days

    @property
    def expiry_status(self):
        days = self.days_to_expiry
        if days < 0:
            return 'expired'
        elif days <= 30:
            return 'critical'
        elif days <= 60:
            return 'warning'
        elif days <= 90:
            return 'attention'
        return 'good'

    @property
    def is_sellable(self):
        return self.is_active and not self.is_expired and self.quantity > 0

    def to_dict(self):
        return {
            'id': self.id,
            'medicine_id': self.medicine_id,
            'medicine_name': self.medicine.name if self.medicine else '',
            'batch_number': self.batch_number,
            'mfg_date': self.mfg_date.strftime('%d-%m-%Y') if self.mfg_date else '',
            'expiry_date': self.expiry_date.strftime('%d-%m-%Y'),
            'purchase_price': float(self.purchase_price),
            'mrp': float(self.mrp),
            'selling_price': float(self.selling_price),
            'quantity': self.quantity,
            'days_to_expiry': self.days_to_expiry,
            'is_expired': self.is_expired,
            'is_sellable': self.is_sellable,
            'supplier_name': self.supplier.name if self.supplier else 'N/A'
        }


class Purchase(db.Model):
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), nullable=False, unique=True, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    mr_id = db.Column(db.Integer, db.ForeignKey('medical_representatives.id'), nullable=True)
    purchase_date = db.Column(db.Date, nullable=False, default=date.today)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    net_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    payment_status = db.Column(db.String(20), nullable=False, default='Paid')  # Paid, Pending, Partial
    payment_mode = db.Column(db.String(30), nullable=False, default='Bank Transfer')
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplier = db.relationship('Supplier', back_populates='purchases')
    mr = db.relationship('MedicalRepresentative', back_populates='purchases')
    created_by_user = db.relationship('User', back_populates='purchases', foreign_keys=[created_by])
    items = db.relationship('PurchaseItem', back_populates='purchase', cascade='all, delete-orphan')


class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('medicine_batches.id'), nullable=True)
    batch_number = db.Column(db.String(50), nullable=False)
    mfg_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    free_quantity = db.Column(db.Integer, nullable=False, default=0)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    mrp = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    gst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    purchase = db.relationship('Purchase', back_populates='items')
    medicine = db.relationship('Medicine', back_populates='purchase_items')
    batch = db.relationship('MedicineBatch')


class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False, default='Walk-in Customer')
    customer_phone = db.Column(db.String(20), nullable=True)
    doctor_name = db.Column(db.String(120), nullable=True)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)  # Sum of item selling price * qty
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    tax_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    cgst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    sgst_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    round_off = db.Column(db.Numeric(6, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Card, Mixed
    payment_reference = db.Column(db.String(100), nullable=True)
    amount_paid = db.Column(db.Numeric(12, 2), nullable=False)
    change_returned = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    status = db.Column(db.String(25), nullable=False, default='Completed')  # Completed, Returned, Cancelled
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cashier = db.relationship('User', back_populates='sales', foreign_keys=[created_by])
    items = db.relationship('SaleItem', back_populates='sale', cascade='all, delete-orphan')
    returns = db.relationship('Return', back_populates='sale')

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone or '',
            'doctor_name': self.doctor_name or '',
            'sale_date': self.sale_date.strftime('%d-%m-%Y %I:%M %p'),
            'subtotal': float(self.subtotal),
            'discount_amount': float(self.discount_amount),
            'tax_amount': float(self.tax_amount),
            'cgst_amount': float(self.cgst_amount),
            'sgst_amount': float(self.sgst_amount),
            'round_off': float(self.round_off),
            'total_amount': float(self.total_amount),
            'payment_mode': self.payment_mode,
            'status': self.status,
            'cashier_name': self.cashier.full_name if self.cashier else 'System',
            'items_count': len(self.items)
        }


class SaleItem(db.Model):
    __tablename__ = 'sale_items'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('medicine_batches.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_mrp = db.Column(db.Numeric(10, 2), nullable=False)
    unit_selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    gst_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    sale = db.relationship('Sale', back_populates='items')
    medicine = db.relationship('Medicine', back_populates='sale_items')
    batch = db.relationship('MedicineBatch', back_populates='sale_items')


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('medicine_batches.id'), nullable=True)
    movement_type = db.Column(db.String(30), nullable=False)  # Purchase, Sale, CustomerReturn, SupplierReturn, WriteOff, Adjustment
    quantity_change = db.Column(db.Integer, nullable=False)  # +qty or -qty
    current_stock_after = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    reference_id = db.Column(db.String(100), nullable=True)  # Invoice number, purchase invoice no, return id
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    medicine = db.relationship('Medicine', back_populates='stock_movements')
    batch = db.relationship('MedicineBatch', back_populates='stock_movements')
    user = db.relationship('User')


class Return(db.Model):
    __tablename__ = 'returns'

    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    return_type = db.Column(db.String(30), nullable=False)  # CustomerReturn, SupplierReturn, ExpiryWriteOff
    return_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Completed')  # Completed, Cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sale = db.relationship('Sale', back_populates='returns')
    supplier = db.relationship('Supplier')
    user = db.relationship('User')
    items = db.relationship('ReturnItem', back_populates='return_record', cascade='all, delete-orphan')


class ReturnItem(db.Model):
    __tablename__ = 'return_items'

    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('returns.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('medicine_batches.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    action_taken = db.Column(db.String(30), nullable=False, default='Restocked')  # Restocked, WrittenOff, ReturnedToSupplier

    return_record = db.relationship('Return', back_populates='items')
    medicine = db.relationship('Medicine')
    batch = db.relationship('MedicineBatch')


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=True)
    return_id = db.Column(db.Integer, db.ForeignKey('returns.id'), nullable=True)
    payment_type = db.Column(db.String(30), nullable=False)  # Sale, Purchase, Refund
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_mode = db.Column(db.String(30), nullable=False)  # Cash, UPI, Card, Bank Transfer, Cheque
    reference_number = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Success')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(60), nullable=False, index=True)
    module = db.Column(db.String(50), nullable=False, index=True)
    details = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', back_populates='audit_logs')
