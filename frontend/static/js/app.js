
const API = 'http://localhost:8000/api';
let token = localStorage.getItem('po_token');
let currentUser = JSON.parse(localStorage.getItem('po_user') || 'null');
let allProducts = [];
let allVendors = [];

/* ── Auth ──────────────────────────────────────────────────────────────── */

async function loginDemo() {
  try {
    const res = await fetch(`${API}/auth/demo-login`, { method: 'POST' });
    const data = await res.json();
    token = data.access_token;
    currentUser = data.user;
    localStorage.setItem('po_token', token);
    localStorage.setItem('po_user', JSON.stringify(currentUser));
    initApp();
  } catch (e) {
    toast('Failed to login. Is the backend running?', 'error');
  }
}

function logout() {
  localStorage.removeItem('po_token');
  localStorage.removeItem('po_user');
  token = null;
  document.getElementById('app').style.display = 'none';
  document.getElementById('loginOverlay').style.display = 'flex';
}

async function apiGet(path) {
  const res = await fetch(`${API}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function apiPatch(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/* ── Init ──────────────────────────────────────────────────────────────── */

function initApp() {
  document.getElementById('loginOverlay').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  if (currentUser) {
    document.getElementById('sidebarUser').innerHTML = `
      <strong>${currentUser.name || 'User'}</strong>
      ${currentUser.email || ''}
    `;
  }
  loadDashboard();
}

window.onload = () => {
  if (token) {
    initApp();
  }
};

/* ── View Router ───────────────────────────────────────────────────────── */

function showView(view, el) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`view-${view}`).classList.add('active');
  el.classList.add('active');
  const titles = { dashboard: 'Dashboard', orders: 'Purchase Orders', vendors: 'Vendors', products: 'Products' };
  document.getElementById('pageTitle').textContent = titles[view] || view;

  if (view === 'dashboard') loadDashboard();
  else if (view === 'orders')   loadOrders();
  else if (view === 'vendors')  loadVendors();
  else if (view === 'products') loadProducts();
  return false;
}

/* ── Dashboard ─────────────────────────────────────────────────────────── */

async function loadDashboard() {
  try {
    const orders = await apiGet('/purchase-orders/?limit=100');
    // Stats
    document.getElementById('statTotal').textContent = orders.length;
    const totalVal = orders.reduce((s, o) => s + o.total_amount, 0);
    document.getElementById('statValue').textContent = fmt(totalVal);
    document.getElementById('statPending').textContent = orders.filter(o => o.status === 'pending').length;
    document.getElementById('statApproved').textContent = orders.filter(o => o.status === 'approved').length;
    // Recent 5
    const recent = orders.slice(0, 5);
    document.getElementById('dashboardOrders').innerHTML = renderOrdersTable(recent);
  } catch(e) {
    document.getElementById('dashboardOrders').innerHTML = `<div class="empty"><div class="empty-icon">⚠️</div><p>Could not load data. Make sure the backend is running.</p></div>`;
  }
}

/* ── Orders ────────────────────────────────────────────────────────────── */

async function loadOrders() {
  const status = document.getElementById('statusFilter')?.value || '';
  const url = `/purchase-orders/?limit=100${status ? '&status='+status : ''}`;
  try {
    const orders = await apiGet(url);
    document.getElementById('ordersTable').innerHTML = orders.length
      ? renderOrdersTable(orders, true)
      : `<div class="empty"><div class="empty-icon">📋</div><p>No orders found.</p></div>`;
  } catch(e) { toast('Failed to load orders', 'error'); }
}

function renderOrdersTable(orders, withActions = false) {
  if (!orders.length) return `<div class="empty"><div class="empty-icon">📋</div><p>No orders yet.</p></div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Vendor</th>
            <th>Items</th>
            <th>Subtotal</th>
            <th>Tax (5%)</th>
            <th>Total</th>
            <th>Status</th>
            <th>Date</th>
            ${withActions ? '<th>Actions</th>' : ''}
          </tr>
        </thead>
        <tbody>
          ${orders.map(o => `
            <tr>
              <td><strong>${o.reference_no}</strong></td>
              <td>${o.vendor?.name || '—'}</td>
              <td>${o.items?.length || 0}</td>
              <td>${fmt(o.subtotal)}</td>
              <td>${fmt(o.tax_amount)}</td>
              <td style="font-family:var(--font-head);font-weight:700;color:var(--accent)">${fmt(o.total_amount)}</td>
              <td><span class="badge badge-${o.status}">${o.status}</span></td>
              <td>${new Date(o.created_at).toLocaleDateString('en-IN')}</td>
              ${withActions ? `<td>
                <select class="status-select" onchange="updateStatus(${o.id}, this.value)">
                  ${['draft','pending','approved','rejected','completed'].map(s =>
                    `<option value="${s}" ${s===o.status?'selected':''}>${s}</option>`
                  ).join('')}
                </select>
              </td>` : ''}
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
}

async function updateStatus(id, status) {
  try {
    await apiPatch(`/purchase-orders/${id}/status`, { status });
    toast(`Status updated to ${status}`, 'success');
  } catch(e) { toast('Failed to update status', 'error'); }
}

/* ── Vendors ───────────────────────────────────────────────────────────── */

async function loadVendors() {
  try {
    allVendors = await apiGet('/vendors/');
    document.getElementById('vendorsGrid').innerHTML = allVendors.length
      ? `<div class="cards-grid">${allVendors.map(v => `
          <div class="card">
            <div class="card-title">${v.name}</div>
            <div class="card-sub">${v.contact} · ${v.email}</div>
            <div class="stars">${'★'.repeat(Math.round(v.rating))}${'☆'.repeat(5-Math.round(v.rating))}</div>
            <div class="card-meta">
              <span class="card-tag">${v.phone || 'No phone'}</span>
              <span class="card-tag">Rating: ${v.rating}</span>
            </div>
          </div>`).join('')}
        </div>`
      : `<div class="empty"><div class="empty-icon">🏢</div><p>No vendors yet. Add one!</p></div>`;
  } catch(e) { toast('Failed to load vendors', 'error'); }
}

function openVendorModal() {
  ['vName','vContact','vEmail','vPhone'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('vRating').value = '0';
  document.getElementById('vendorModal').style.display = 'flex';
}

async function submitVendor() {
  const body = {
    name: val('vName'), contact: val('vContact'),
    email: val('vEmail'), phone: val('vPhone'),
    rating: parseFloat(val('vRating')) || 0
  };
  if (!body.name || !body.contact || !body.email) { toast('Name, contact and email are required', 'error'); return; }
  try {
    await apiPost('/vendors/', body);
    toast('Vendor added!', 'success');
    closeModal('vendorModal');
    loadVendors();
  } catch(e) { toast(e.message, 'error'); }
}

/* ── Products ──────────────────────────────────────────────────────────── */

async function loadProducts() {
  try {
    allProducts = await apiGet('/products/');
    document.getElementById('productsGrid').innerHTML = allProducts.length
      ? `<div class="cards-grid">${allProducts.map(p => `
          <div class="card">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:.5rem">
              <div>
                <div class="card-title">${p.name}</div>
                <div class="card-sub">SKU: ${p.sku}</div>
              </div>
              <button class="btn-ai" onclick="generateAI(${p.id}, '${p.name.replace(/'/g,"\\'")}')">✨ Auto-Desc</button>
            </div>
            <div style="margin:.5rem 0;font-family:var(--font-head);font-size:1.1rem;font-weight:700;color:var(--accent)">${fmt(p.unit_price)}</div>
            ${p.ai_description ? `<p style="font-size:.8rem;color:var(--text2);margin-top:.5rem;font-style:italic">${p.ai_description}</p>` : ''}
            <div class="card-meta">
              <span class="card-tag">${p.category || 'Uncategorized'}</span>
              <span class="card-tag">Stock: ${p.stock_level}</span>
            </div>
          </div>`).join('')}
        </div>`
      : `<div class="empty"><div class="empty-icon">📦</div><p>No products yet. Add one!</p></div>`;
  } catch(e) { toast('Failed to load products', 'error'); }
}

function openProductModal() {
  ['pName','pSku','pCategory','pPrice'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('pStock').value = '0';
  document.getElementById('productModal').style.display = 'flex';
}

async function submitProduct() {
  const body = {
    name: val('pName'), sku: val('pSku'),
    category: val('pCategory') || null,
    unit_price: parseFloat(val('pPrice')),
    stock_level: parseInt(val('pStock')) || 0
  };
  if (!body.name || !body.sku || !body.unit_price) { toast('Name, SKU and price are required', 'error'); return; }
  try {
    await apiPost('/products/', body);
    toast('Product added!', 'success');
    closeModal('productModal');
    loadProducts();
  } catch(e) { toast(e.message, 'error'); }
}

/* ── AI Description ────────────────────────────────────────────────────── */

async function generateAI(productId, productName) {
  document.getElementById('aiProductName').textContent = productName;
  document.getElementById('aiResult').innerHTML = `<div class="ai-loading">Generating description…<span class="spinner"></span></div>`;
  document.getElementById('aiModal').style.display = 'flex';

  try {
    const res = await fetch(`${API}/products/${productId}/generate-description`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    });
    const data = await res.json();
    document.getElementById('aiResult').innerHTML = `<p>${data.ai_description}</p>`;
    // Refresh products to show saved description
    loadProducts();
  } catch(e) {
    document.getElementById('aiResult').innerHTML = `<p style="color:var(--danger)">Generation failed. Check your GEMINI_API_KEY.</p>`;
  }
}

/* ── Create PO Modal ───────────────────────────────────────────────────── */

let poRowCount = 0;

async function openCreatePOModal() {
  // Load vendors + products
  try {
    [allVendors, allProducts] = await Promise.all([
      apiGet('/vendors/'),
      apiGet('/products/')
    ]);
  } catch(e) {
    toast('Failed to load vendors/products', 'error'); return;
  }

  // Populate vendor dropdown
  const vSel = document.getElementById('poVendor');
  vSel.innerHTML = allVendors.length
    ? allVendors.map(v => `<option value="${v.id}">${v.name}</option>`).join('')
    : '<option value="">No vendors — add one first</option>';

  document.getElementById('poNotes').value = '';
  document.getElementById('poItemsBody').innerHTML = '';
  poRowCount = 0;
  resetTotals();
  addProductRow();
  document.getElementById('poModal').style.display = 'flex';
}

function addProductRow() {
  const id = poRowCount++;
  const options = allProducts.map(p =>
    `<option value="${p.id}" data-price="${p.unit_price}">${p.name} (${fmt(p.unit_price)})</option>`
  ).join('');

  const row = document.createElement('tr');
  row.id = `row-${id}`;
  row.innerHTML = `
    <td>
      <select onchange="rowChanged(${id})" id="rProd-${id}">
        ${options}
      </select>
    </td>
    <td id="rPrice-${id}" style="color:var(--text2);font-family:var(--font-head)">
      ${allProducts[0] ? fmt(allProducts[0].unit_price) : '—'}
    </td>
    <td>
      <input type="number" id="rQty-${id}" value="1" min="1" style="width:65px"
             oninput="rowChanged(${id})"/>
    </td>
    <td class="line-total" id="rTotal-${id}">
      ${allProducts[0] ? fmt(allProducts[0].unit_price) : '—'}
    </td>
    <td>
      <button class="btn-icon" onclick="removeRow(${id})" title="Remove">✕</button>
    </td>`;
  document.getElementById('poItemsBody').appendChild(row);
  recalcTotals();
}

function removeRow(id) {
  const row = document.getElementById(`row-${id}`);
  if (row) row.remove();
  recalcTotals();
}

function rowChanged(id) {
  const sel = document.getElementById(`rProd-${id}`);
  const qty = parseInt(document.getElementById(`rQty-${id}`).value) || 1;
  const price = parseFloat(sel.selectedOptions[0]?.dataset.price) || 0;
  const lineTotal = price * qty;
  document.getElementById(`rPrice-${id}`).textContent = fmt(price);
  document.getElementById(`rTotal-${id}`).textContent = fmt(lineTotal);
  recalcTotals();
}

function recalcTotals() {
  let subtotal = 0;
  document.querySelectorAll('[id^="rTotal-"]').forEach(el => {
    subtotal += parseFloat(el.textContent.replace(/[^0-9.]/g,'')) || 0;
  });
  const tax = subtotal * 0.05;
  const total = subtotal + tax;
  document.getElementById('poSubtotal').textContent = fmt(subtotal);
  document.getElementById('poTax').textContent = fmt(tax);
  document.getElementById('poTotal').textContent = fmt(total);
}

function resetTotals() {
  document.getElementById('poSubtotal').textContent = '₹0.00';
  document.getElementById('poTax').textContent = '₹0.00';
  document.getElementById('poTotal').textContent = '₹0.00';
}

async function submitPO() {
  const vendorId = parseInt(document.getElementById('poVendor').value);
  const notes = document.getElementById('poNotes').value;
  if (!vendorId) { toast('Please select a vendor', 'error'); return; }

  // Collect rows
  const items = [];
  let valid = true;
  document.querySelectorAll('#poItemsBody tr').forEach(row => {
    const idMatch = row.id.match(/row-(\d+)/);
    if (!idMatch) return;
    const rid = idMatch[1];
    const sel = document.getElementById(`rProd-${rid}`);
    const qty = parseInt(document.getElementById(`rQty-${rid}`).value) || 0;
    if (!sel || !qty) { valid = false; return; }
    items.push({ product_id: parseInt(sel.value), quantity: qty });
  });

  if (!valid || items.length === 0) { toast('Add at least one product with a valid quantity', 'error'); return; }

  try {
    await apiPost('/purchase-orders/', { vendor_id: vendorId, items, notes });
    toast('Purchase Order created! 🎉', 'success');
    closeModal('poModal');
    loadDashboard();
  } catch(e) { toast(e.message, 'error'); }
}

/* ── Utilities ─────────────────────────────────────────────────────────── */

function fmt(n) {
  return '₹' + (n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function val(id) { return document.getElementById(id)?.value?.trim() || ''; }

function closeModal(id) { document.getElementById(id).style.display = 'none'; }

let toastTimer;
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.className = 'toast', 3000);
}

// Close modals on overlay click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.style.display = 'none';
  }
});
