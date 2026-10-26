import os
from decimal import Decimal

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'medicare-pro-super-secret-key-inr-2026')
    
    # Database URL configuration (Render PostgreSQL uses postgres:// which SQLAlchemy 1.4+ requires as postgresql://)
    _db_url = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "medicare_pro.db")}'
    )
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pharmacy Details for Invoices & Receipts
    PHARMACY_NAME = "MediCare Pro Pharmacy"
    PHARMACY_TAGLINE = "Healthcare with Trust & Care"
    PHARMACY_ADDRESS = "Shop No. 12-14, Health Plaza, M.G. Road, Bangalore, Karnataka - 560001"
    PHARMACY_PHONE = "+91 98765 43210"
    PHARMACY_EMAIL = "contact@medicarepro.in"
    PHARMACY_GSTIN = "29AABCU9603R1ZX"
    PHARMACY_DL_NO = "KA-BLR-20B-112233 / 21B-112234"
    PHARMACY_FSSAI = "11221334000543"

    # Localization
    CURRENCY_CODE = "INR"
    CURRENCY_SYMBOL = "₹"
    TIMEZONE = "Asia/Kolkata"
    DATE_FORMAT = "%d-%m-%Y"
    DATETIME_FORMAT = "%d-%m-%Y %I:%M %p"

    # Default Tax Rates in India (GST)
    GST_RATES = [Decimal('0.0'), Decimal('5.0'), Decimal('12.0'), Decimal('18.0'), Decimal('28.0')]
    DEFAULT_GST_RATE = Decimal('12.0')

    # Expiry alert thresholds in days
    EXPIRY_NEAR_DAYS = 90
    EXPIRY_CRITICAL_DAYS = 30
    LOW_STOCK_THRESHOLD = 15
