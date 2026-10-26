# MediCare Pro — Indian Medical Shop Management System
https://medicare-sw4t.onrender.com/login?next=%2F

**MediCare Pro** is a comprehensive, production-grade Medical Shop & Pharmacy Management System built with Python, Flask, SQLite with SQLAlchemy ORM, Bootstrap 5, Chart.js, and ReportLab. It is specifically tailored for the Indian retail pharmacy sector with native support for Indian Rupees (**₹, INR**), Indian date formatting (**DD-MM-YYYY**), Indian standard time (**Asia/Kolkata**), GST compliance (CGST/SGST), Drug License & HSN classification, and multi-batch inventory tracking.

---

## 🌟 Key Features

### 1. Hospital-Inspired Dashboard
- **Live Database Calculations:** Real-time KPI cards for Total Medicines, Total Stock Units, Today's Sales in ₹, and Today's Invoices Count.
- **Financial & Risk Overview:** Real-time Inventory Valuation (at Purchase Cost and MRP), Low-Stock count, Near-Expiry count (< 90 days), and Expired batch loss in ₹.
- **Interactive Chart.js Visualizations:**
  - 7-Day & 30-Day Sales Volume and Revenue trends.
  - Therapeutic Category Stock distribution donut chart.
- **Recent Activities:** Live tables of the latest sales receipts and incoming supplier shipments.

### 2. Multi-Batch Medicine Inventory
- **Full Medicine Profile:** Product name, brand, manufacturer, generic composition, dosage form, strength, category, SKU, barcode, HSN code, GST rate, shelf/rack location, and minimum stock level.
- **Multiple Batches:** Track multiple distinct batches for the same medicine with individual batch numbers, manufacturing dates, expiry dates, purchase costs, MRPs, selling prices, and available units.
- **Demo Medicine Tagging:** Clearly marked sample demo medicines and pricing rules.
- **Stock Protection:** Absolute prevention of negative stock and automatic exclusion of expired batches from sales.
- **Stock Movements Audit Trail:** Every inward purchase, counter sale, customer return, supplier return, write-off, and manual stock adjustment is permanently recorded in the `stock_movements` ledger.

### 3. Point of Sale (POS) & Billing
- **Instant Live Typeahead Search:** Fast search by medicine name, generic salt, SKU, or barcode.
- **Keyboard Shortcuts:** Press <kbd>F2</kbd> anywhere to start a new sale or focus the search box.
- **Smart Batch Selection:** Displays live available stock, expiry dates, and rates for non-expired batches.
- **Indian Pharmacy Tax Computation:** MRP and selling price are treated as tax-inclusive by Indian retail standard; automatically computes taxable value, CGST (50%), and SGST (50%) splits.
- **Payment Modes:** Cash, UPI (GooglePay, PhonePe, Paytm), Card, and Mixed payments.
- **Cash Change Calculator:** Enter amount received to instantly compute change returned.
- **Downloadable PDF Invoices:** Built-in PDF generation powered by **ReportLab** producing official A4 Indian Tax Invoices with pharmacy header, DL numbers, GSTIN, doctor name, and amount in words.
- **In-Browser Thermal/Slip Printing:** Print-friendly CSS optimized for POS thermal receipt printers and A4 sheets (<kbd>Ctrl + P</kbd>).
- **Customer Returns & Cancellations:** Authorized return interface supporting item-by-item quantity selection and restock or write-off actions.

### 4. Proactive Expiry Management
- **Dedicated Expiry Dashboard:** Categorized into 4 actionable buckets:
  - Already Expired (Unsold stock loss in ₹).
  - Critical (< 30 days remaining).
  - Warning (31 to 60 days remaining).
  - Attention (61 to 90 days remaining).
- **Automatic Sales Lock:** Expired batches automatically become ineligible for sale at POS counters.
- **One-Click Actions:**
  - **Write-Off:** Mark expired units for biomedical disposal with audit logging.
  - **Supplier Return:** Return near-expiry stock to distributors for credit notes.

### 5. Supply Chain & Supplier Management
- **Inward Purchase Orders:** Record incoming shipments with supplier invoice numbers, purchase dates, batch numbers, manufacturing dates, expiry dates, billed units, free bonus units, purchase rates, MRPs, GST, discounts, and payment status (Paid, Pending, Partial).
- **Duplicate Prevention:** Prevents duplicate supplier invoice recording.
- **Distributor Profiles:** Track phone numbers, email, physical addresses, GSTIN, and Drug License (20B/21B) numbers.

### 6. Medical Representative (MR) Tracking
- **Separate MR & Supplier Records:** Distinct entities acknowledging that an MR facilitates orders while distributors supply the stock.
- **MR Profiles:** Name, pharmaceutical company, contact phone, territory, last visit date, and visit notes.
- **Order Facilitation History:** Automatically links purchase orders to facilitating MRs and calculates cumulative purchase values facilitated.
- **Field Visit Logger:** Record ongoing visits, promotional schemes, and territory feedback.

### 7. Comprehensive Financial Reports & Analytics
- **Sales & Profitability Report:** Filter by custom date ranges or quick presets (Today, 7 Days, This Month). Displays Gross Sales, Discounts, GST Tax, Net Sales, Cost of Goods Sold (COGS), Gross Profit in ₹, and Gross Margin %.
- **Purchase Reports:** Tracks total inward procurement, settled amounts, and outstanding distributor credit balances.
- **Stock Valuation Report:** Compares inventory purchase cost valuation with retail MRP valuation.
- **Low Stock Reorder Report:** Lists all medicines below reorder thresholds with suggested reorder quantities.
- **Best-Selling Medicines:** Identifies top pharmaceutical products by units sold and revenue.
- **Supplier & MR Analytics:** Performance and volume metrics.
- **Returns & Write-Offs Log:** Financial impact of customer refunds, supplier credits, and expired waste.
- **One-Click CSV Export:** Export Sales, Purchases, Stock, and Expiry reports directly to `.csv` format.

### 8. Security & Compliance
- **Authentication & Authorization:** Secure session management with role-based access control (`admin` and `cashier`).
- **Password Hashing:** Passwords hashed using Werkzeug (`scrypt`/`pbkdf2`).
- **Comprehensive Audit Log:** Admin-accessible log recording user logins, sales creation, cancellations, returns, write-offs, and stock adjustments with timestamps and IP addresses.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+ / Python 3.13, Flask 3.1+ |
| **Database** | SQLite with SQLAlchemy 2.0+ ORM |
| **Authentication** | Flask-Login with secure password hashing |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3.3 |
| **Icons** | Bootstrap Icons 1.11.3 |
| **Charts** | Chart.js 4.4.2 |
| **PDF Engine** | ReportLab 5.1+ (with pure-Python vector fallback) |
| **Currency** | Indian Rupee (₹, INR) with Indian numbering format |
| **Timezone** | Asia/Kolkata (IST) |
| **Date Format** | DD-MM-YYYY |

---

## 🚀 Setup & Run Instructions for PyCharm

### Method 1: Opening in PyCharm

1. **Launch PyCharm** and select **Open**.
2. Navigate to and open the project directory:
   ```text
   D:\medicare_pro
   ```
3. **Configure Python Interpreter:**
   - In PyCharm, go to **File** &rarr; **Settings** (or <kbd>Ctrl + Alt + S</kbd>).
   - Under **Project: medicare_pro**, click **Python Interpreter**.
   - Select your existing Python 3.10+ interpreter (e.g. Python 3.13) or create a new Virtual Environment (`venv`).
4. **Install Dependencies:**
   - Open PyCharm's built-in **Terminal** (<kbd>Alt + F12</kbd>).
   - Run:
     ```powershell
     pip install -r requirements.txt
     ```
5. **Run the Application:**
   - In the PyCharm Project tool window, right-click `app.py` and select **Run 'app'**.
   - Alternatively, in the PyCharm terminal, run:
     ```powershell
     python app.py
     ```
6. **Open in Browser:**
   - Open your browser and navigate to:
     ```text
     http://127.0.0.1:5000/
     ```

---

## 🔑 Default Login Credentials

The system comes pre-initialized with sample Indian pharmacy data and two ready-to-use user accounts:

| Role | Username | Password | Full Name | Access Level |
|---|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Dr. Ananya Sharma | Full access (Billing, Inventory, Purchases, Suppliers, MRs, Reports, Audit Logs) |
| **Cashier / Pharmacist** | `cashier` | `cashier123` | Rajesh Kumar | Counter POS billing, customer search, and view invoices |

*(The login page includes quick-fill buttons to populate these credentials with a single click.)*

---

## 📁 Project Directory Structure

```text
medicare_pro/
├── app.py                      # Main Flask application, routes, and context processors
├── config.py                   # Pharmacy details, GST rates, localization & database configuration
├── models.py                   # SQLAlchemy ORM models (User, Medicine, Batch, Sale, Purchase, etc.)
├── requirements.txt            # Project dependencies
├── seed_data.py                # Database seeder with realistic Indian medicine catalog & sample sales
├── test_system.py              # Automated system test suite for billing, stock, and PDF generation
├── test_routes.py              # Test suite verifying all 20 HTTP endpoints return 200 OK
├── instance/
│   ├── medicare_pro.db         # SQLite persistent database file
│   └── test_invoice.pdf        # Verified sample generated PDF tax invoice
├── services/
│   ├── billing_service.py      # Cart calculations, atomic transactions, returns, and invoice numbering
│   ├── inventory_service.py    # Purchase inwards, batch stock increment, write-offs, and expiry buckets
│   └── report_service.py       # Metrics, gross profit, stock valuation, COGS, and top-selling analytics
├── utils/
│   ├── formatters.py           # Indian Rupee (₹) numbering, DD-MM-YYYY dates, and amount in words
│   └── invoice_pdf.py          # ReportLab PDF invoice generator with Indian GST tax tables
├── static/
│   ├── css/
│   │   └── style.css           # Premium hospital-inspired styling (Deep Navy, Clinical Teal, Ice Blue)
│   └── js/
│       └── app.js              # POS cart engine, typeahead search, hotkeys (F2), and change calculator
└── templates/
    ├── base.html               # Master layout with hospital sidebar, live date, and notification badges
    ├── login.html              # Hospital login screen with one-click demo credentials
    ├── dashboard.html          # Operational dashboard with real-time stats and Chart.js graphs
    ├── inventory.html          # Medicine catalog with category, brand, and stock filters
    ├── medicine_form.html      # Add & edit medicine specifications and Indian pricing rules
    ├── medicine_view.html      # Medicine profile, multi-batch ledger, and stock movement log
    ├── billing.html            # Fast Point of Sale (POS) counter billing interface
    ├── invoices.html           # Sales invoices history with search and status filters
    ├── invoice_detail.html     # Official Indian Tax Invoice view and printable slip
    ├── invoice_return.html     # Customer return and stock restock/write-off processing
    ├── expiry.html             # Dedicated expiry dashboard with 30/60/90 days tabs and actions
    ├── purchases.html          # Supplier purchase orders list
    ├── purchase_form.html      # Multi-item purchase receiving form with real-time totals
    ├── purchase_detail.html    # Detailed purchase invoice view with batch records
    ├── suppliers.html          # Supplier & distributor directory with GSTIN and DL details
    ├── representatives.html    # Medical Representative (MR) directory with visit logger
    ├── reports.html            # Financial analytics, valuation, COGS, profit, and CSV exports
    └── audit_logs.html         # Admin audit trail for financial and stock changes
```

---

## 🧪 Verification & Testing

To run the verification test suites at any time from PyCharm terminal:

```powershell
# Run core system logic test (billing, stock locks, PDF engine, returns):
python test_system.py

# Run all 20 web route tests:
python test_routes.py
```

Both test suites will execute and verify database persistence, stock deduction integrity, expired batch rejection, and PDF generation.

---

## ⚖️ Indian Regulatory & Compliance Information

- **Drug License Numbers:** DL-20B (Allopathic drugs) & DL-21B (Specific Schedule C & C1 drugs).
- **Goods and Services Tax (GST):** Formatted for Indian retail chemists; invoice displays separate 50% Central GST (CGST) and 50% State GST (SGST) breakdowns.
- **HSN Codes:** Standard Chapter 3004 medicaments classification.
- **Maximum Retail Price (MRP):** Complies with the Legal Metrology Act and DPCO guidelines; all demo medicine prices are editable by the administrator.
