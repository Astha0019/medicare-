import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import app
from models import User

def test_routes():
    print("Testing HTTP routes with Flask test client...")
    client = app.test_client()

    with app.app_context():
        # Login as admin
        admin = User.query.filter_by(username='admin').first()

    with client:
        # 1. Test Login Page (unauthenticated)
        res = client.get('/login')
        assert res.status_code == 200, f"/login failed: {res.status_code}"
        print("[PASS] GET /login -> 200")

        # 2. Login as admin
        res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        assert res.status_code == 200, f"Login post failed: {res.status_code}"
        print("[PASS] POST /login -> authenticated")

        # 3. Test Dashboard
        res = client.get('/dashboard')
        assert res.status_code == 200, f"/dashboard failed: {res.status_code}"
        print("[PASS] GET /dashboard -> 200")

        # 4. Test Inventory
        res = client.get('/inventory')
        assert res.status_code == 200, f"/inventory failed: {res.status_code}"
        print("[PASS] GET /inventory -> 200")

        # 5. Test Add Medicine page
        res = client.get('/inventory/add')
        assert res.status_code == 200, f"/inventory/add failed: {res.status_code}"
        print("[PASS] GET /inventory/add -> 200")

        # 6. Test View Medicine
        res = client.get('/inventory/view/1')
        assert res.status_code == 200, f"/inventory/view/1 failed: {res.status_code}"
        print("[PASS] GET /inventory/view/1 -> 200")

        # 7. Test Billing (POS)
        res = client.get('/billing')
        assert res.status_code == 200, f"/billing failed: {res.status_code}"
        print("[PASS] GET /billing -> 200")

        # 8. Test Search API
        res = client.get('/inventory/api/search?term=dolo')
        assert res.status_code == 200, f"Search API failed: {res.status_code}"
        data = res.get_json()
        assert len(data) > 0, "Expected search results for dolo"
        print(f"[PASS] GET /inventory/api/search?term=dolo -> 200 ({len(data)} items returned)")

        # 9. Test Invoices List
        res = client.get('/invoices')
        assert res.status_code == 200, f"/invoices failed: {res.status_code}"
        print("[PASS] GET /invoices -> 200")

        # 10. Test Invoice Detail
        res = client.get('/invoices/view/1')
        assert res.status_code == 200, f"/invoices/view/1 failed: {res.status_code}"
        print("[PASS] GET /invoices/view/1 -> 200")

        # 11. Test Invoice PDF Download
        res = client.get('/invoices/pdf/1')
        assert res.status_code == 200, f"/invoices/pdf/1 failed: {res.status_code}"
        assert res.mimetype == 'application/pdf', f"Expected PDF mimetype, got {res.mimetype}"
        print(f"[PASS] GET /invoices/pdf/1 -> 200 (PDF mime verified, length: {len(res.data)})")

        # 12. Test Expiry Dashboard
        res = client.get('/expiry')
        assert res.status_code == 200, f"/expiry failed: {res.status_code}"
        print("[PASS] GET /expiry -> 200")

        # 13. Test Purchases List
        res = client.get('/purchases')
        assert res.status_code == 200, f"/purchases failed: {res.status_code}"
        print("[PASS] GET /purchases -> 200")

        # 14. Test New Purchase Page
        res = client.get('/purchases/new')
        assert res.status_code == 200, f"/purchases/new failed: {res.status_code}"
        print("[PASS] GET /purchases/new -> 200")

        # 15. Test View Purchase
        res = client.get('/purchases/view/1')
        assert res.status_code == 200, f"/purchases/view/1 failed: {res.status_code}"
        print("[PASS] GET /purchases/view/1 -> 200")

        # 16. Test Suppliers
        res = client.get('/suppliers')
        assert res.status_code == 200, f"/suppliers failed: {res.status_code}"
        print("[PASS] GET /suppliers -> 200")

        # 17. Test Medical Representatives
        res = client.get('/representatives')
        assert res.status_code == 200, f"/representatives failed: {res.status_code}"
        print("[PASS] GET /representatives -> 200")

        # 18. Test Reports (Sales, Purchases, Valuation, Low Stock, etc.)
        for r_type in ['sales', 'purchases', 'valuation', 'lowstock', 'topmeds', 'suppliers', 'mrs', 'returns']:
            res = client.get(f'/reports?type={r_type}')
            assert res.status_code == 200, f"/reports?type={r_type} failed: {res.status_code}"
        print("[PASS] GET /reports (all 8 tabs) -> 200")

        # 19. Test CSV Export
        for c_type in ['sales', 'purchases', 'stock', 'expiry']:
            res = client.get(f'/reports/export/csv?type={c_type}')
            assert res.status_code == 200, f"CSV export {c_type} failed: {res.status_code}"
            assert res.mimetype == 'text/csv'
        print("[PASS] GET /reports/export/csv (all formats) -> 200")

        # 20. Test Audit Logs
        res = client.get('/audit-logs')
        assert res.status_code == 200, f"/audit-logs failed: {res.status_code}"
        print("[PASS] GET /audit-logs -> 200")

    print("=" * 60)
    print("ALL 20 ROUTE TESTS PASSED WITH 200 OK!")
    print("=" * 60)

if __name__ == '__main__':
    test_routes()
