/**
 * MediCare Pro - Core Frontend JavaScript
 * Handles POS Billing, Dynamic Calculations, Typeahead Search, and Hotkeys
 */

// Global state for Point of Sale
let posCart = [];
let searchDebounceTimer = null;

document.addEventListener('DOMContentLoaded', function () {
  initPOS();
  initPurchaseForm();
  initGlobalShortcuts();
});

// -----------------------------------------------------------------
// Point of Sale (POS) Billing Logic
// -----------------------------------------------------------------
function initPOS() {
  const searchInput = document.getElementById('posMedicineSearch');
  const resultsBox = document.getElementById('posSearchResults');
  const checkoutBtn = document.getElementById('posBtnCheckout');
  const amountPaidInput = document.getElementById('posAmountPaid');
  const paymentModeSelect = document.getElementById('posPaymentMode');

  if (!searchInput) return;

  // Search input typing listener with debounce
  searchInput.addEventListener('input', function () {
    clearTimeout(searchDebounceTimer);
    const query = this.value.trim();

    if (query.length < 2) {
      resultsBox.style.display = 'none';
      resultsBox.innerHTML = '';
      return;
    }

    searchDebounceTimer = setTimeout(() => {
      fetch(`/inventory/api/search?term=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
          renderSearchResults(data, resultsBox);
        })
        .catch(err => console.error('Search error:', err));
    }, 250);
  });

  // Close search results on outside click
  document.addEventListener('click', function (e) {
    if (!searchInput.contains(e.target) && !resultsBox.contains(e.target)) {
      resultsBox.style.display = 'none';
    }
  });

  // Calculate change when amount paid is entered
  if (amountPaidInput) {
    amountPaidInput.addEventListener('input', updatePOSSummary);
  }

  // Payment mode toggle
  if (paymentModeSelect) {
    paymentModeSelect.addEventListener('change', function () {
      const refField = document.getElementById('posPaymentRefContainer');
      if (refField) {
        refField.style.display = (this.value === 'UPI' || this.value === 'Card') ? 'block' : 'none';
      }
    });
  }

  // Checkout submission
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', submitPOSCheckout);
  }
}

function renderSearchResults(medicines, container) {
  container.innerHTML = '';
  if (!medicines || medicines.length === 0) {
    container.innerHTML = '<div class="p-3 text-muted text-center"><i class="bi bi-info-circle me-1"></i> No matching medicines with available sellable stock.</div>';
    container.style.display = 'block';
    return;
  }

  medicines.forEach(med => {
    med.batches.forEach(batch => {
      const div = document.createElement('div');
      div.className = 'pos-search-item';
      div.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <strong>${med.name}</strong> <span class="badge bg-light text-dark border ms-1">${med.dosage_form} ${med.strength}</span>
            <div class="small text-muted">${med.generic} &bull; <span class="text-primary">Rack: ${med.rack_location}</span></div>
          </div>
          <div class="text-end">
            <span class="badge bg-primary">₹${batch.selling_price.toFixed(2)}</span>
            <div class="small text-muted">Batch: <strong>${batch.batch_number}</strong> (Exp: ${batch.expiry_date})</div>
            <div class="small ${batch.quantity <= 10 ? 'text-danger font-monospace' : 'text-success'}">Stock: ${batch.quantity} units</div>
          </div>
        </div>
      `;
      div.addEventListener('click', () => {
        addItemToPOSCart(med, batch);
        container.style.display = 'none';
        document.getElementById('posMedicineSearch').value = '';
        document.getElementById('posMedicineSearch').focus();
      });
      container.appendChild(div);
    });
  });

  container.style.display = 'block';
}

function addItemToPOSCart(medicine, batch) {
  // Check if item/batch already in cart
  const existing = posCart.find(item => item.batch_id === batch.id);
  if (existing) {
    if (existing.quantity + 1 > batch.quantity) {
      alert(`Cannot add more. Available stock for batch ${batch.batch_number} is ${batch.quantity}.`);
      return;
    }
    existing.quantity += 1;
  } else {
    posCart.push({
      medicine_id: medicine.id,
      medicine_name: medicine.name,
      dosage: `${medicine.dosage_form} ${medicine.strength}`,
      batch_id: batch.id,
      batch_number: batch.batch_number,
      expiry_date: batch.expiry_date,
      available_stock: batch.quantity,
      mrp: batch.mrp,
      selling_price: batch.selling_price,
      gst_rate: medicine.gst_rate,
      quantity: 1,
      discount_percent: 0.0
    });
  }

  renderPOSCartTable();
}

function renderPOSCartTable() {
  const tbody = document.getElementById('posCartTableBody');
  const emptyRow = document.getElementById('posCartEmptyRow');
  if (!tbody) return;

  if (posCart.length === 0) {
    tbody.innerHTML = `
      <tr id="posCartEmptyRow">
        <td colspan="9" class="text-center py-4 text-muted">
          <i class="bi bi-cart-x fs-3 d-block mb-1"></i>
          Cart is empty. Search and select medicines above or press F2.
        </td>
      </tr>
    `;
    updatePOSSummary();
    return;
  }

  tbody.innerHTML = '';
  posCart.forEach((item, index) => {
    const gross = item.selling_price * item.quantity;
    const discount = (gross * (item.discount_percent / 100));
    const lineTotal = gross - discount;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${index + 1}</td>
      <td>
        <strong>${item.medicine_name}</strong>
        <div class="small text-muted">${item.dosage}</div>
      </td>
      <td><span class="badge bg-light text-dark border">${item.batch_number}</span></td>
      <td><small class="text-muted">${item.expiry_date}</small></td>
      <td style="width: 100px;">
        <input type="number" class="form-control form-control-sm text-center fw-bold" 
               min="1" max="${item.available_stock}" value="${item.quantity}" 
               onchange="updateCartItemQty(${index}, this.value)">
      </td>
      <td class="text-end">₹${item.selling_price.toFixed(2)}</td>
      <td style="width: 90px;">
        <input type="number" class="form-control form-control-sm text-center" 
               min="0" max="100" step="0.5" value="${item.discount_percent}" 
               onchange="updateCartItemDisc(${index}, this.value)">
      </td>
      <td class="text-end fw-bold text-primary">₹${lineTotal.toFixed(2)}</td>
      <td class="text-center">
        <button class="btn btn-sm btn-outline-danger" onclick="removeCartItem(${index})" title="Remove item">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  updatePOSSummary();
}

function updateCartItemQty(index, newQty) {
  const qty = parseInt(newQty, 10);
  if (isNaN(qty) || qty <= 0) {
    posCart[index].quantity = 1;
  } else if (qty > posCart[index].available_stock) {
    alert(`Only ${posCart[index].available_stock} units available in stock.`);
    posCart[index].quantity = posCart[index].available_stock;
  } else {
    posCart[index].quantity = qty;
  }
  renderPOSCartTable();
}

function updateCartItemDisc(index, newDisc) {
  const disc = parseFloat(newDisc);
  posCart[index].discount_percent = isNaN(disc) || disc < 0 ? 0.0 : Math.min(disc, 100.0);
  renderPOSCartTable();
}

function removeCartItem(index) {
  posCart.splice(index, 1);
  renderPOSCartTable();
}

function updatePOSSummary() {
  let subtotal = 0;
  let totalDiscount = 0;
  let totalTax = 0;

  posCart.forEach(item => {
    const gross = item.selling_price * item.quantity;
    const disc = (gross * (item.discount_percent / 100));
    const net = gross - disc;

    // GST inclusive calculation:
    // Taxable = Net / (1 + GST/100)
    const tax = net - (net / (1 + (item.gst_rate / 100)));

    subtotal += gross;
    totalDiscount += disc;
    totalTax += tax;
  });

  const rawNet = subtotal - totalDiscount;
  const grandTotal = Math.round(rawNet);
  const roundOff = grandTotal - rawNet;

  // Update UI Elements
  const elSub = document.getElementById('posSummarySubtotal');
  const elDisc = document.getElementById('posSummaryDiscount');
  const elTax = document.getElementById('posSummaryTax');
  const elRound = document.getElementById('posSummaryRoundOff');
  const elGrand = document.getElementById('posSummaryGrandTotal');
  const elItemsCount = document.getElementById('posCartItemsCount');

  if (elSub) elSub.textContent = `₹${subtotal.toFixed(2)}`;
  if (elDisc) elDisc.textContent = `-₹${totalDiscount.toFixed(2)}`;
  if (elTax) elTax.textContent = `₹${totalTax.toFixed(2)}`;
  if (elRound) elRound.textContent = `₹${roundOff.toFixed(2)}`;
  if (elGrand) elGrand.textContent = `₹${grandTotal.toFixed(2)}`;
  if (elItemsCount) elItemsCount.textContent = posCart.length;

  // Change calculator
  const amountPaidInput = document.getElementById('posAmountPaid');
  const changeDisplay = document.getElementById('posChangeReturned');
  if (amountPaidInput && changeDisplay) {
    const paid = parseFloat(amountPaidInput.value) || 0;
    const change = Math.max(0, paid - grandTotal);
    changeDisplay.textContent = `₹${change.toFixed(2)}`;
  }
}

function submitPOSCheckout() {
  if (posCart.length === 0) {
    alert('Please add medicines to cart before checking out.');
    return;
  }

  const custName = document.getElementById('posCustomerName').value.trim() || 'Walk-in Customer';
  const custPhone = document.getElementById('posCustomerPhone').value.trim();
  const doctorName = document.getElementById('posDoctorName').value.trim();
  const paymentMode = document.getElementById('posPaymentMode').value;
  const paymentRef = document.getElementById('posPaymentRef') ? document.getElementById('posPaymentRef').value.trim() : '';
  const amountPaid = parseFloat(document.getElementById('posAmountPaid').value) || 0;

  const checkoutBtn = document.getElementById('posBtnCheckout');
  checkoutBtn.disabled = true;
  checkoutBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Processing...';

  const payload = {
    customer_name: custName,
    customer_phone: custPhone,
    doctor_name: doctorName,
    payment_mode: paymentMode,
    payment_reference: paymentRef,
    amount_paid: amountPaid,
    items: posCart.map(item => ({
      medicine_id: item.medicine_id,
      batch_id: item.batch_id,
      quantity: item.quantity,
      discount_percent: item.discount_percent
    }))
  };

  fetch('/billing/checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      checkoutBtn.disabled = false;
      checkoutBtn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Complete & Print Bill';

      if (data.success) {
        // Show success modal with links
        showCheckoutSuccessModal(data);
        // Clear cart
        posCart = [];
        renderPOSCartTable();
        // Clear customer fields
        document.getElementById('posCustomerName').value = '';
        document.getElementById('posCustomerPhone').value = '';
        document.getElementById('posDoctorName').value = '';
        document.getElementById('posAmountPaid').value = '';
      } else {
        alert(data.message || 'Error completing billing transaction.');
      }
    })
    .catch(err => {
      checkoutBtn.disabled = false;
      checkoutBtn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Complete & Print Bill';
      console.error('Checkout error:', err);
      alert('Network or server error during checkout.');
    });
}

function showCheckoutSuccessModal(data) {
  const modalEl = document.getElementById('posSuccessModal');
  if (!modalEl) {
    alert(`Success! Invoice ${data.invoice_number} created.`);
    window.location.href = `/invoices/view/${data.invoice_id}`;
    return;
  }

  document.getElementById('posSuccessInvoiceNo').textContent = data.invoice_number;
  document.getElementById('posSuccessTotal').textContent = `₹${data.total_amount.toFixed(2)}`;
  document.getElementById('posSuccessChange').textContent = `₹${data.change_returned.toFixed(2)}`;
  document.getElementById('posSuccessViewBtn').href = `/invoices/view/${data.invoice_id}`;
  document.getElementById('posSuccessPdfBtn').href = `/invoices/pdf/${data.invoice_id}`;

  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

// -----------------------------------------------------------------
// Purchase Form Dynamic Multi-Row Item Management
// -----------------------------------------------------------------
function initPurchaseForm() {
  const addRowBtn = document.getElementById('btnAddPurchaseRow');
  const tbody = document.getElementById('purchaseItemsTableBody');
  if (!addRowBtn || !tbody) return;

  addRowBtn.addEventListener('click', () => {
    addPurchaseItemRow(tbody);
  });
}

function addPurchaseItemRow(tbody) {
  const medicineSelectTemplate = document.getElementById('purchaseMedicineOptionsTemplate');
  if (!medicineSelectTemplate) return;

  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>
      <select name="item_medicine_id[]" class="form-select form-select-sm" required onchange="onPurchaseMedChange(this)">
        ${medicineSelectTemplate.innerHTML}
      </select>
    </td>
    <td><input type="text" name="item_batch_number[]" class="form-control form-control-sm text-uppercase" placeholder="Batch No" required></td>
    <td><input type="date" name="item_mfg_date[]" class="form-control form-control-sm"></td>
    <td><input type="date" name="item_expiry_date[]" class="form-control form-control-sm" required></td>
    <td><input type="number" name="item_quantity[]" class="form-control form-control-sm text-center" min="1" value="1" required oninput="calcPurchaseRow(this)"></td>
    <td><input type="number" name="item_free_quantity[]" class="form-control form-control-sm text-center" min="0" value="0"></td>
    <td><input type="number" name="item_purchase_price[]" class="form-control form-control-sm text-end" step="0.01" min="0" value="0.00" required oninput="calcPurchaseRow(this)"></td>
    <td><input type="number" name="item_mrp[]" class="form-control form-control-sm text-end" step="0.01" min="0" value="0.00" required></td>
    <td><input type="number" name="item_selling_price[]" class="form-control form-control-sm text-end" step="0.01" min="0" value="0.00"></td>
    <td><input type="number" name="item_gst_rate[]" class="form-control form-control-sm text-center" step="0.5" value="12.0" oninput="calcPurchaseRow(this)"></td>
    <td><input type="number" name="item_discount_percent[]" class="form-control form-control-sm text-center" step="0.5" value="0.0" oninput="calcPurchaseRow(this)"></td>
    <td class="text-end fw-bold text-primary purchase-row-total">₹0.00</td>
    <td class="text-center">
      <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('tr').remove(); updatePurchaseSummary();">
        <i class="bi bi-trash"></i>
      </button>
    </td>
  `;
  tbody.appendChild(tr);
}

function calcPurchaseRow(input) {
  const tr = input.closest('tr');
  const qty = parseFloat(tr.querySelector('[name="item_quantity[]"]').value) || 0;
  const price = parseFloat(tr.querySelector('[name="item_purchase_price[]"]').value) || 0;
  const gst = parseFloat(tr.querySelector('[name="item_gst_rate[]"]').value) || 0;
  const disc = parseFloat(tr.querySelector('[name="item_discount_percent[]"]').value) || 0;

  const gross = qty * price;
  const discountVal = gross * (disc / 100);
  const taxable = gross - discountVal;
  const tax = taxable * (gst / 100);
  const net = taxable + tax;

  tr.querySelector('.purchase-row-total').textContent = `₹${net.toFixed(2)}`;
  updatePurchaseSummary();
}

function updatePurchaseSummary() {
  const rows = document.querySelectorAll('#purchaseItemsTableBody tr');
  let subtotal = 0;
  let totalTax = 0;
  let totalDisc = 0;

  rows.forEach(tr => {
    const qty = parseFloat(tr.querySelector('[name="item_quantity[]"]')?.value) || 0;
    const price = parseFloat(tr.querySelector('[name="item_purchase_price[]"]')?.value) || 0;
    const gst = parseFloat(tr.querySelector('[name="item_gst_rate[]"]')?.value) || 0;
    const disc = parseFloat(tr.querySelector('[name="item_discount_percent[]"]')?.value) || 0;

    const gross = qty * price;
    const discountVal = gross * (disc / 100);
    const taxable = gross - discountVal;
    const tax = taxable * (gst / 100);

    subtotal += gross;
    totalDisc += discountVal;
    totalTax += tax;
  });

  const net = subtotal - totalDisc + totalTax;

  const elSub = document.getElementById('purchaseSummarySubtotal');
  const elTax = document.getElementById('purchaseSummaryTax');
  const elDisc = document.getElementById('purchaseSummaryDiscount');
  const elNet = document.getElementById('purchaseSummaryNet');

  if (elSub) elSub.textContent = `₹${subtotal.toFixed(2)}`;
  if (elTax) elTax.textContent = `₹${totalTax.toFixed(2)}`;
  if (elDisc) elDisc.textContent = `-₹${totalDisc.toFixed(2)}`;
  if (elNet) elNet.textContent = `₹${net.toFixed(2)}`;
}

// -----------------------------------------------------------------
// Global Keyboard Shortcuts
// -----------------------------------------------------------------
function initGlobalShortcuts() {
  window.addEventListener('keydown', function (e) {
    // F2: Jump to Billing
    if (e.key === 'F2') {
      e.preventDefault();
      const searchBox = document.getElementById('posMedicineSearch');
      if (searchBox) {
        searchBox.focus();
        searchBox.select();
      } else {
        window.location.href = '/billing';
      }
    }
  });
}
