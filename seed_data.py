import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from config import Config
from models import (
    db, User, Supplier, MedicalRepresentative, Medicine, MedicineBatch, 
    Purchase, PurchaseItem, Sale, SaleItem, Payment, StockMovement, AuditLog
)

def seed_database(app):
    with app.app_context():
        # Ensure instance folder exists
        os.makedirs(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance'), exist_ok=True)
        db.create_all()

        # Check if already seeded
        if User.query.first():
            print("Database already initialized with data.")
            return

        print("Seeding MediCare Pro database with authentic Indian pharmacy sample data...")

        # 1. Create Users
        admin = User(
            username='admin',
            email='admin@medicarepro.in',
            full_name='Dr. Ananya Sharma (Admin)',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')

        cashier = User(
            username='cashier',
            email='rajesh.cashier@medicarepro.in',
            full_name='Rajesh Kumar (Pharmacist)',
            role='cashier',
            is_active=True
        )
        cashier.set_password('cashier123')

        db.session.add_all([admin, cashier])
        db.session.flush()

        # 2. Create Suppliers
        sup1 = Supplier(
            name="Sri Venkateshwara Pharma Distributors",
            company_name="SVP Healthcare Ltd",
            contact_person="Venkatesh Rao",
            phone="080-26781234",
            email="sales@svppharma.com",
            address="Plot 45, Peenya Industrial Area, Bangalore, Karnataka - 560058",
            gstin="29AABCS1429B1Z1",
            drug_license_no="KA-BLR-20B-45892 / 21B-45893"
        )
        sup2 = Supplier(
            name="MedLife Wholesale & Healthcare Agency",
            company_name="MedLife Distribution India",
            contact_person="Pooja Hegde",
            phone="080-41228899",
            email="orders@medlifewholesale.in",
            address="Building 12, Koramangala 4th Block, Bangalore, Karnataka - 560034",
            gstin="29AAECM9102L1ZQ",
            drug_license_no="KA-BLR-20B-88741 / 21B-88742"
        )
        sup3 = Supplier(
            name="Apex Lifesciences Logistics",
            company_name="Apex Healthcare Ltd",
            contact_person="Manoj Swamy",
            phone="080-23447788",
            email="support@apexpharma.in",
            address="Shop 8, Rajajinagar 2nd Stage, Bangalore, Karnataka - 560010",
            gstin="29AAGCA8821M1ZX",
            drug_license_no="KA-BLR-20B-33120 / 21B-33121"
        )
        db.session.add_all([sup1, sup2, sup3])
        db.session.flush()

        # 3. Create Medical Representatives (MR)
        today = date.today()
        mr1 = MedicalRepresentative(
            name="Vikram Joshi",
            company_name="Cipla Limited",
            phone="+91 97412 34567",
            email="vikram.joshi@cipla.com",
            territory="Bangalore Central & M.G. Road",
            visit_notes="Discussed quarterly targets, syrup supply status, and new Montair-LC pediatric batches.",
            last_visit_date=today - timedelta(days=4)
        )
        mr2 = MedicalRepresentative(
            name="Neha Deshmukh",
            company_name="Sun Pharmaceutical Industries",
            phone="+91 98234 56789",
            email="neha.deshmukh@sunpharma.com",
            territory="Bangalore East & Indiranagar",
            visit_notes="Introduced Volini max gel festive scheme (10+1 free units) and Pantocid stock requirements.",
            last_visit_date=today - timedelta(days=7)
        )
        mr3 = MedicalRepresentative(
            name="Suresh Nambiar",
            company_name="Dr. Reddy's Laboratories",
            phone="+91 99805 54433",
            email="suresh.n@drreddys.com",
            territory="Bangalore North & Malleshwaram",
            visit_notes="Reviewed Omez-D availability and antibiotic seasonal promotions.",
            last_visit_date=today - timedelta(days=12)
        )
        mr4 = MedicalRepresentative(
            name="Amit Verma",
            company_name="Micro Labs Ltd",
            phone="+91 96112 88440",
            email="amit.verma@microlabs.in",
            territory="Bangalore South & Jayanagar",
            visit_notes="Verified Dolo 650 distribution, ensured continuous supply during monsoon fever surge.",
            last_visit_date=today - timedelta(days=2)
        )
        db.session.add_all([mr1, mr2, mr3, mr4])
        db.session.flush()

        # 4. Medicines and Batches (Clearly marked as Demo with Sample Prices in INR)
        demo_meds_data = [
            {
                'name': 'Dolo 650 (Demo)',
                'brand_name': 'Micro Labs Ltd',
                'manufacturer': 'Micro Labs Ltd',
                'generic': 'Paracetamol (650mg)',
                'dosage': 'Tablet',
                'strength': '650 mg',
                'category': 'Analgesic & Antipyretic',
                'sku': 'MED-DOLO-650',
                'barcode': '890123400101',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack A-01, Shelf 1',
                'min_stock': 20,
                'batches': [
                    {'batch': 'DL-2401', 'mfg': today - timedelta(days=120), 'exp': today + timedelta(days=450), 'qty': 120, 'pp': Decimal('24.00'), 'mrp': Decimal('33.60'), 'sp': Decimal('31.00'), 'supplier': sup1},
                    {'batch': 'DL-2309', 'mfg': today - timedelta(days=400), 'exp': today + timedelta(days=22), 'qty': 35, 'pp': Decimal('22.50'), 'mrp': Decimal('31.50'), 'sp': Decimal('29.00'), 'supplier': sup1}, # Expiring within 30 days
                ]
            },
            {
                'name': 'Augmentin 625 Duo (Demo)',
                'brand_name': 'GlaxoSmithKline (GSK)',
                'manufacturer': 'GlaxoSmithKline Pharmaceuticals',
                'generic': 'Amoxicillin (500mg) + Clavulanic Acid (125mg)',
                'dosage': 'Tablet',
                'strength': '625 mg',
                'category': 'Antibiotic',
                'sku': 'MED-AUG-625',
                'barcode': '890123400102',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack B-03, Shelf 2',
                'min_stock': 15,
                'batches': [
                    {'batch': 'AUG-771', 'mfg': today - timedelta(days=90), 'exp': today + timedelta(days=500), 'qty': 65, 'pp': Decimal('145.00'), 'mrp': Decimal('204.00'), 'sp': Decimal('190.00'), 'supplier': sup2},
                    {'batch': 'AUG-650', 'mfg': today - timedelta(days=365), 'exp': today + timedelta(days=48), 'qty': 20, 'pp': Decimal('140.00'), 'mrp': Decimal('198.00'), 'sp': Decimal('185.00'), 'supplier': sup2}, # Expiring within 60 days
                ]
            },
            {
                'name': 'Pan-D Capsule (Demo)',
                'brand_name': 'Alkem Laboratories',
                'manufacturer': 'Alkem Health Science',
                'generic': 'Pantoprazole (40mg) + Domperidone (30mg)',
                'dosage': 'Capsule',
                'strength': '40mg/30mg',
                'category': 'Gastrointestinal',
                'sku': 'MED-PAND-001',
                'barcode': '890123400103',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack A-02, Shelf 3',
                'min_stock': 25,
                'batches': [
                    {'batch': 'PND-901', 'mfg': today - timedelta(days=60), 'exp': today + timedelta(days=600), 'qty': 110, 'pp': Decimal('135.00'), 'mrp': Decimal('199.00'), 'sp': Decimal('180.00'), 'supplier': sup1},
                ]
            },
            {
                'name': 'Azithral 500 (Demo)',
                'brand_name': 'Alembic Pharmaceuticals',
                'manufacturer': 'Alembic Pharmaceuticals Ltd',
                'generic': 'Azithromycin (500mg)',
                'dosage': 'Tablet',
                'strength': '500 mg',
                'category': 'Antibiotic',
                'sku': 'MED-AZI-500',
                'barcode': '890123400104',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack B-01, Shelf 1',
                'min_stock': 20,
                'batches': [
                    {'batch': 'AZ-332', 'mfg': today - timedelta(days=80), 'exp': today + timedelta(days=400), 'qty': 50, 'pp': Decimal('82.00'), 'mrp': Decimal('119.50'), 'sp': Decimal('110.00'), 'supplier': sup2},
                    {'batch': 'AZ-110', 'mfg': today - timedelta(days=500), 'exp': today - timedelta(days=15), 'qty': 14, 'pp': Decimal('78.00'), 'mrp': Decimal('112.00'), 'sp': Decimal('105.00'), 'supplier': sup2}, # Expired batch!
                ]
            },
            {
                'name': 'Telma 40 (Demo)',
                'brand_name': 'Glenmark Pharmaceuticals',
                'manufacturer': 'Glenmark Pharma Ltd',
                'generic': 'Telmisartan (40mg)',
                'dosage': 'Tablet',
                'strength': '40 mg',
                'category': 'Cardiovascular',
                'sku': 'MED-TEL-040',
                'barcode': '890123400105',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack C-02, Shelf 2',
                'min_stock': 20,
                'batches': [
                    {'batch': 'TL-801', 'mfg': today - timedelta(days=100), 'exp': today + timedelta(days=550), 'qty': 80, 'pp': Decimal('142.00'), 'mrp': Decimal('220.00'), 'sp': Decimal('198.00'), 'supplier': sup3},
                ]
            },
            {
                'name': 'Glycomet-GP 2 (Demo)',
                'brand_name': 'USV Private Limited',
                'manufacturer': 'USV Pvt Ltd',
                'generic': 'Glimepiride (2mg) + Metformin Hydrochloride (500mg)',
                'dosage': 'Tablet',
                'strength': '2mg/500mg',
                'category': 'Antidiabetic',
                'sku': 'MED-GLY-GP2',
                'barcode': '890123400106',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack C-01, Shelf 3',
                'min_stock': 30,
                'batches': [
                    {'batch': 'GP-554', 'mfg': today - timedelta(days=110), 'exp': today + timedelta(days=480), 'qty': 125, 'pp': Decimal('118.00'), 'mrp': Decimal('175.00'), 'sp': Decimal('160.00'), 'supplier': sup3},
                ]
            },
            {
                'name': 'Ascoril-LS Syrup (Demo)',
                'brand_name': 'Glenmark Pharmaceuticals',
                'manufacturer': 'Glenmark Pharma Ltd',
                'generic': 'Levosalbutamol (1mg) + Ambroxol (30mg) + Guaifenesin (50mg)',
                'dosage': 'Syrup',
                'strength': '100 ml',
                'category': 'Respiratory',
                'sku': 'MED-ASC-100',
                'barcode': '890123400107',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack D-01, Shelf 1',
                'min_stock': 15,
                'batches': [
                    {'batch': 'AS-902', 'mfg': today - timedelta(days=70), 'exp': today + timedelta(days=420), 'qty': 45, 'pp': Decimal('78.00'), 'mrp': Decimal('118.00'), 'sp': Decimal('108.00'), 'supplier': sup1},
                ]
            },
            {
                'name': 'Becosules Z Capsules (Demo)',
                'brand_name': 'Pfizer India',
                'manufacturer': 'Pfizer Healthcare India',
                'generic': 'Vitamin B-Complex with Vitamin C & Zinc',
                'dosage': 'Capsule',
                'strength': 'Standard',
                'category': 'Vitamins & Supplements',
                'sku': 'MED-BEC-020',
                'barcode': '890123400108',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack E-01, Shelf 1',
                'min_stock': 25,
                'batches': [
                    {'batch': 'BC-441', 'mfg': today - timedelta(days=85), 'exp': today + timedelta(days=360), 'qty': 95, 'pp': Decimal('34.00'), 'mrp': Decimal('51.30'), 'sp': Decimal('47.00'), 'supplier': sup2},
                ]
            },
            {
                'name': 'Volini Pain Relief Gel (Demo)',
                'brand_name': 'Sun Pharmaceutical Industries',
                'manufacturer': 'Sun Pharma Laboratories',
                'generic': 'Diclofenac Diethylamine + Virgin Linseed Oil + Methyl Salicylate + Menthol',
                'dosage': 'Ointment',
                'strength': '50 g',
                'category': 'Topical Analgesic',
                'sku': 'MED-VOL-050',
                'barcode': '890123400109',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack E-02, Shelf 2',
                'min_stock': 15,
                'batches': [
                    {'batch': 'VOL-301', 'mfg': today - timedelta(days=50), 'exp': today + timedelta(days=520), 'qty': 40, 'pp': Decimal('110.00'), 'mrp': Decimal('165.00'), 'sp': Decimal('152.00'), 'supplier': sup2},
                ]
            },
            {
                'name': 'Montair-LC (Demo)',
                'brand_name': 'Cipla Limited',
                'manufacturer': 'Cipla Ltd',
                'generic': 'Montelukast (10mg) + Levocetirizine (5mg)',
                'dosage': 'Tablet',
                'strength': '10mg/5mg',
                'category': 'Antiallergic',
                'sku': 'MED-MNT-010',
                'barcode': '890123400110',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack B-02, Shelf 1',
                'min_stock': 20,
                'batches': [
                    {'batch': 'MN-780', 'mfg': today - timedelta(days=95), 'exp': today + timedelta(days=490), 'qty': 75, 'pp': Decimal('155.00'), 'mrp': Decimal('230.00'), 'sp': Decimal('210.00'), 'supplier': sup1},
                ]
            },
            {
                'name': 'Shelcal 500 (Demo)',
                'brand_name': 'Torrent Pharmaceuticals',
                'manufacturer': 'Torrent Pharma Ltd',
                'generic': 'Calcium (500mg) + Vitamin D3 (250 IU)',
                'dosage': 'Tablet',
                'strength': '500 mg',
                'category': 'Vitamins & Supplements',
                'sku': 'MED-SHL-500',
                'barcode': '890123400112',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack E-01, Shelf 3',
                'min_stock': 20,
                'batches': [
                    {'batch': 'SH-991', 'mfg': today - timedelta(days=280), 'exp': today + timedelta(days=75), 'qty': 28, 'pp': Decimal('88.00'), 'mrp': Decimal('131.00'), 'sp': Decimal('120.00'), 'supplier': sup3}, # Expiring in 90 days
                ]
            },
            {
                'name': 'Azithromycin 250 (Low Stock Demo)',
                'brand_name': 'Cipla Limited',
                'manufacturer': 'Cipla Ltd',
                'generic': 'Azithromycin (250mg)',
                'dosage': 'Tablet',
                'strength': '250 mg',
                'category': 'Antibiotic',
                'sku': 'MED-AZI-250',
                'barcode': '890123400116',
                'hsn': '3004',
                'gst': Decimal('12.00'),
                'rack': 'Rack B-01, Shelf 2',
                'min_stock': 25,
                'batches': [
                    {'batch': 'AZ2-99', 'mfg': today - timedelta(days=90), 'exp': today + timedelta(days=400), 'qty': 5, 'pp': Decimal('45.00'), 'mrp': Decimal('68.00'), 'sp': Decimal('62.00'), 'supplier': sup1}, # Low stock: 5 units <= 25
                ]
            }
        ]

        created_batches = []
        for m_data in demo_meds_data:
            med = Medicine(
                name=m_data['name'],
                brand_name=m_data['brand_name'],
                manufacturer=m_data['manufacturer'],
                generic_composition=m_data['generic'],
                dosage_form=m_data['dosage'],
                strength=m_data['strength'],
                category=m_data['category'],
                sku=m_data['sku'],
                barcode=m_data['barcode'],
                hsn_code=m_data['hsn'],
                gst_rate=m_data['gst'],
                rack_location=m_data['rack'],
                min_stock_level=m_data['min_stock'],
                is_demo=True,
                is_active=True
            )
            db.session.add(med)
            db.session.flush()

            for b_data in m_data['batches']:
                batch = MedicineBatch(
                    medicine_id=med.id,
                    supplier_id=b_data['supplier'].id,
                    batch_number=b_data['batch'],
                    mfg_date=b_data['mfg'],
                    expiry_date=b_data['exp'],
                    purchase_price=b_data['pp'],
                    mrp=b_data['mrp'],
                    selling_price=b_data['sp'],
                    quantity=b_data['qty'],
                    initial_quantity=b_data['qty'],
                    is_active=True
                )
                db.session.add(batch)
                db.session.flush()
                created_batches.append(batch)

                # Initial stock movement
                mov = StockMovement(
                    medicine_id=med.id,
                    batch_id=batch.id,
                    movement_type='Purchase',
                    quantity_change=b_data['qty'],
                    current_stock_after=b_data['qty'],
                    reason="Initial Stock Setup (Demo)",
                    reference_id="OPENING-STOCK",
                    created_by=admin.id
                )
                db.session.add(mov)

        # 5. Create Sample Historical Purchases linked to MRs
        pur1 = Purchase(
            invoice_number="SVP-INV-2026-9041",
            supplier_id=sup1.id,
            mr_id=mr4.id, # Micro Labs MR Amit Verma
            purchase_date=today - timedelta(days=15),
            subtotal=Decimal('12400.00'),
            tax_amount=Decimal('1488.00'),
            discount_amount=Decimal('400.00'),
            net_amount=Decimal('13488.00'),
            payment_status='Paid',
            payment_mode='Bank Transfer',
            notes='Monsoon fever stock replenishment',
            created_by=admin.id
        )
        pur2 = Purchase(
            invoice_number="MED-BLR-8812",
            supplier_id=sup2.id,
            mr_id=mr2.id, # Sun Pharma MR Neha Deshmukh
            purchase_date=today - timedelta(days=8),
            subtotal=Decimal('18600.00'),
            tax_amount=Decimal('2232.00'),
            discount_amount=Decimal('500.00'),
            net_amount=Decimal('20332.00'),
            payment_status='Paid',
            payment_mode='UPI',
            notes='Antibiotics & analgesics supply order',
            created_by=admin.id
        )
        pur3 = Purchase(
            invoice_number="APX-KA-4510",
            supplier_id=sup3.id,
            mr_id=mr1.id, # Cipla MR Vikram Joshi
            purchase_date=today - timedelta(days=3),
            subtotal=Decimal('9800.00'),
            tax_amount=Decimal('1176.00'),
            discount_amount=Decimal('250.00'),
            net_amount=Decimal('10726.00'),
            payment_status='Pending',
            payment_mode='Bank Transfer',
            notes='Hypertension & diabetic medicine orders',
            created_by=admin.id
        )
        db.session.add_all([pur1, pur2, pur3])
        db.session.flush()

        # 6. Create Historical Sales (last 7 days and today)
        sample_customers = [
            ("Kavita Nair", "9845011223", "Dr. R. K. Mehta"),
            ("Ramesh Chand", "9880199221", "Dr. Priya Shenoy"),
            ("Sunil Hegde", "9945122334", "Dr. Anand Rao"),
            ("Deepa Patel", "9740188776", "Walk-in"),
            ("Mohammed Farooq", "9663455112", "Dr. R. K. Mehta"),
            ("Asha Kulkarni", "9844099881", "Dr. Vijay Prasad"),
            ("Vikas Gowda", "9731244556", "Walk-in")
        ]

        inv_count = 1
        # Loop for past 6 days
        for i in range(6, 0, -1):
            sale_day = today - timedelta(days=i)
            day_time = datetime.combine(sale_day, datetime.min.time()) + timedelta(hours=11, minutes=20 * i)
            cust_name, cust_phone, doc_name = sample_customers[i % len(sample_customers)]

            # Pick 2 batches for this sale
            b1 = created_batches[0] # Dolo
            b2 = created_batches[3] # Pan-D

            inv_str = f"INV-{sale_day.strftime('%Y%m%d')}-{inv_count:04d}"
            inv_count += 1

            s_item1_sub = b1.selling_price * 2
            s_item2_sub = b2.selling_price * 1
            sale_sub = s_item1_sub + s_item2_sub
            sale_tax = (sale_sub * Decimal('0.12')).quantize(Decimal('0.01'))
            sale_cgst = (sale_tax / 2).quantize(Decimal('0.01'))
            sale_sgst = sale_tax - sale_cgst
            sale_total = sale_sub

            sale_rec = Sale(
                invoice_number=inv_str,
                customer_name=cust_name,
                customer_phone=cust_phone,
                doctor_name=doc_name,
                sale_date=day_time,
                subtotal=sale_sub,
                discount_amount=Decimal('0.00'),
                tax_amount=sale_tax,
                cgst_amount=sale_cgst,
                sgst_amount=sale_sgst,
                round_off=Decimal('0.00'),
                total_amount=sale_total,
                payment_mode='UPI' if i % 2 == 0 else 'Cash',
                payment_reference='UPI9872341' if i % 2 == 0 else None,
                amount_paid=sale_total,
                change_returned=Decimal('0.00'),
                status='Completed',
                created_by=cashier.id,
                created_at=day_time
            )
            db.session.add(sale_rec)
            db.session.flush()

            si1 = SaleItem(
                sale_id=sale_rec.id,
                medicine_id=b1.medicine_id,
                batch_id=b1.id,
                batch_number=b1.batch_number,
                expiry_date=b1.expiry_date,
                quantity=2,
                unit_mrp=b1.mrp,
                unit_selling_price=b1.selling_price,
                discount_percent=Decimal('0.00'),
                discount_amount=Decimal('0.00'),
                gst_rate=Decimal('12.00'),
                tax_amount=(s_item1_sub * Decimal('0.12')).quantize(Decimal('0.01')),
                line_total=s_item1_sub
            )
            si2 = SaleItem(
                sale_id=sale_rec.id,
                medicine_id=b2.medicine_id,
                batch_id=b2.id,
                batch_number=b2.batch_number,
                expiry_date=b2.expiry_date,
                quantity=1,
                unit_mrp=b2.mrp,
                unit_selling_price=b2.selling_price,
                discount_percent=Decimal('0.00'),
                discount_amount=Decimal('0.00'),
                gst_rate=Decimal('12.00'),
                tax_amount=(s_item2_sub * Decimal('0.12')).quantize(Decimal('0.01')),
                line_total=s_item2_sub
            )
            db.session.add_all([si1, si2])

        # Today's Sales (2 realistic invoices)
        today_inv1 = Sale(
            invoice_number=f"INV-{today.strftime('%Y%m%d')}-0001",
            customer_name="Sanjay Verma",
            customer_phone="9845033445",
            doctor_name="Dr. R. K. Mehta",
            sale_date=datetime.now() - timedelta(hours=3),
            subtotal=Decimal('370.00'),
            discount_amount=Decimal('10.00'),
            tax_amount=Decimal('38.57'),
            cgst_amount=Decimal('19.29'),
            sgst_amount=Decimal('19.28'),
            round_off=Decimal('0.00'),
            total_amount=Decimal('360.00'),
            payment_mode='Cash',
            amount_paid=Decimal('500.00'),
            change_returned=Decimal('140.00'),
            status='Completed',
            created_by=cashier.id
        )
        db.session.add(today_inv1)
        db.session.flush()

        ti1_item = SaleItem(
            sale_id=today_inv1.id,
            medicine_id=created_batches[0].medicine_id,
            batch_id=created_batches[0].id,
            batch_number=created_batches[0].batch_number,
            expiry_date=created_batches[0].expiry_date,
            quantity=2,
            unit_mrp=created_batches[0].mrp,
            unit_selling_price=created_batches[0].selling_price,
            discount_percent=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            gst_rate=Decimal('12.00'),
            tax_amount=Decimal('6.64'),
            line_total=Decimal('62.00')
        )
        ti2_item = SaleItem(
            sale_id=today_inv1.id,
            medicine_id=created_batches[3].medicine_id,
            batch_id=created_batches[3].id,
            batch_number=created_batches[3].batch_number,
            expiry_date=created_batches[3].expiry_date,
            quantity=1,
            unit_mrp=created_batches[3].mrp,
            unit_selling_price=created_batches[3].selling_price,
            discount_percent=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            gst_rate=Decimal('12.00'),
            tax_amount=Decimal('19.29'),
            line_total=Decimal('180.00')
        )
        db.session.add_all([ti1_item, ti2_item])

        today_inv2 = Sale(
            invoice_number=f"INV-{today.strftime('%Y%m%d')}-0002",
            customer_name="Lakshmi Narayanan",
            customer_phone="9988776655",
            doctor_name="Dr. Priya Shenoy",
            sale_date=datetime.now() - timedelta(hours=1),
            subtotal=Decimal('288.00'),
            discount_amount=Decimal('0.00'),
            tax_amount=Decimal('30.86'),
            cgst_amount=Decimal('15.43'),
            sgst_amount=Decimal('15.43'),
            round_off=Decimal('0.00'),
            total_amount=Decimal('288.00'),
            payment_mode='UPI',
            payment_reference='UPI-TXN-884129',
            amount_paid=Decimal('288.00'),
            change_returned=Decimal('0.00'),
            status='Completed',
            created_by=cashier.id
        )
        db.session.add(today_inv2)
        db.session.flush()

        # Audit initial seed
        audit = AuditLog(
            user_id=admin.id,
            action='SYSTEM_INIT',
            module='Setup',
            details='MediCare Pro initial database setup and demo sample data loaded successfully.'
        )
        db.session.add(audit)

        db.session.commit()
        print("MediCare Pro sample data seeded successfully!")
