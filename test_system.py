import os
import sys
from decimal import Decimal
from datetime import datetime, date

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import app
from models import db, User, Medicine, MedicineBatch, Sale, Purchase, StockMovement
from seed_data import seed_database
from services.billing_service import create_sale, process_sale_return
from utils.invoice_pdf import generate_invoice_pdf

def test_all():
    print("=" * 60)
    print("MediCare Pro System Comprehensive Verification")
    print("=" * 60)

    with app.app_context():
        # 1. Seed database
        seed_database(app)

        # 2. Check counts
        user_count = User.query.count()
        med_count = Medicine.query.count()
        batch_count = MedicineBatch.query.count()
        sale_count = Sale.query.count()
        pur_count = Purchase.query.count()

        print(f"[OK] Users seeded: {user_count}")
        print(f"[OK] Medicines seeded: {med_count}")
        print(f"[OK] Batches seeded: {batch_count}")
        print(f"[OK] Historical Sales seeded: {sale_count}")
        print(f"[OK] Purchases seeded: {pur_count}")

        assert user_count >= 2, "Expected at least 2 users (admin, cashier)"
        assert med_count >= 10, "Expected at least 10 demo medicines"

        # 3. Test POS Billing Transaction
        admin = User.query.filter_by(username='admin').first()
        dolo = Medicine.query.filter(Medicine.name.like('%Dolo%')).first()
        assert dolo is not None, "Dolo 650 should exist in database"

        # Find valid non-expired batch for Dolo
        today = date.today()
        valid_batch = MedicineBatch.query.filter(
            MedicineBatch.medicine_id == dolo.id,
            MedicineBatch.expiry_date > today,
            MedicineBatch.quantity > 5
        ).first()
        assert valid_batch is not None, "Should have an active valid batch for Dolo"

        initial_qty = valid_batch.quantity
        print(f"[INFO] Initial stock for batch {valid_batch.batch_number}: {initial_qty} units")

        # Create test sale for 2 units
        items = [{
            'medicine_id': dolo.id,
            'batch_id': valid_batch.id,
            'quantity': 2,
            'discount_percent': 5.0
        }]

        new_sale = create_sale(
            cashier_user=admin,
            customer_name="Test Customer Verma",
            customer_phone="9876543210",
            doctor_name="Dr. Test Rao",
            payment_mode="UPI",
            payment_reference="UPI-TEST-1234",
            amount_paid=Decimal('60.00'),
            items_data=items,
            notes="Automated verification test bill"
        )

        db.session.refresh(valid_batch)
        print(f"[OK] Sale created: Invoice #{new_sale.invoice_number}")
        print(f"[OK] Total Sale Amount: ₹{new_sale.total_amount}")
        print(f"[OK] New batch stock after sale: {valid_batch.quantity} (Decremented by 2: {initial_qty - 2 == valid_batch.quantity})")
        assert valid_batch.quantity == initial_qty - 2, "Stock should be decremented by exactly 2"

        # 4. Test PDF Generation
        pdf_bytes = generate_invoice_pdf(new_sale)
        assert pdf_bytes is not None and len(pdf_bytes) > 500, "PDF bytes should be generated"
        print(f"[OK] PDF Invoice generated successfully! File size: {len(pdf_bytes)} bytes")

        # Save test pdf
        test_pdf_path = os.path.join(os.path.dirname(__file__), 'instance', 'test_invoice.pdf')
        with open(test_pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        print(f"[OK] Test PDF written to: {test_pdf_path}")

        # 5. Test Expiry Blocking
        expired_batch = MedicineBatch.query.filter(
            MedicineBatch.expiry_date < today
        ).first()
        if expired_batch:
            print(f"[INFO] Testing sale rejection on expired batch: {expired_batch.batch_number}")
            try:
                create_sale(
                    cashier_user=admin,
                    customer_name="Expired Test",
                    customer_phone="9999999999",
                    doctor_name="",
                    payment_mode="Cash",
                    payment_reference=None,
                    amount_paid=Decimal('100.00'),
                    items_data=[{
                        'medicine_id': expired_batch.medicine_id,
                        'batch_id': expired_batch.id,
                        'quantity': 1,
                        'discount_percent': 0.0
                    }]
                )
                assert False, "Should have raised ValueError on expired batch sale!"
            except ValueError as ve:
                print(f"[PASS] Successfully blocked expired batch sale! Reason: {ve}")

        # 6. Test Insufficient Stock Blocking
        try:
            create_sale(
                cashier_user=admin,
                customer_name="Overstock Test",
                customer_phone="9999999999",
                doctor_name="",
                payment_mode="Cash",
                payment_reference=None,
                amount_paid=Decimal('100.00'),
                items_data=[{
                    'medicine_id': valid_batch.medicine_id,
                    'batch_id': valid_batch.id,
                    'quantity': valid_batch.quantity + 9999,
                    'discount_percent': 0.0
                }]
            )
            assert False, "Should have raised ValueError on excess quantity sale!"
        except ValueError as ve:
            print(f"[PASS] Successfully prevented selling more than available stock! Reason: {ve}")

        # 7. Test Customer Return
        sale_item = new_sale.items[0]
        ret_result = process_sale_return(
            user=admin,
            sale_id=new_sale.id,
            return_items=[{
                'sale_item_id': sale_item.id,
                'quantity': 1,
                'action': 'Restock'
            }],
            reason="Customer test return 1 unit"
        )
        db.session.refresh(valid_batch)
        print(f"[PASS] Processed Return #{ret_result.return_number}. Refund: ₹{ret_result.total_amount}. Stock restored to: {valid_batch.quantity}")

    print("=" * 60)
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    test_all()
