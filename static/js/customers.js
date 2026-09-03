let searchTimer = null;

const SUMMARY_DEFS = [
  { key: 'total',             label: 'Total Customers',     icon: 'users',        tint: 'bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20' },
  { key: 'high_value',        label: 'High Value Customers', icon: 'gem',         tint: 'bg-amber-500/10 text-amber-400 border border-amber-500/20' },
  { key: 'at_risk',           label: 'At Risk Customers',   icon: 'shield-alert', tint: 'bg-rose-500/10 text-rose-400 border border-rose-500/20' },
  { key: 'repeat_customers',  label: 'Repeat Customers',    icon: 'repeat',       tint: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' },
];

function riskClass(level) {
  return { Low: 'badge-high', Medium: 'badge-medium', High: 'badge-low' }[level] || 'badge-low';
}

async function loadSummary() {
  const elem = document.getElementById('summary-cards');
  if (!elem) return;
  const s = await apiGet('/api/customers/summary');
  elem.innerHTML = SUMMARY_DEFS.map(def => `
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <span class="text-[13px] text-slate-400 font-medium">${def.label}</span>
        <span class="w-8 h-8 rounded-lg ${def.tint} flex items-center justify-center"><i data-lucide="${def.icon}" class="w-4 h-4"></i></span>
      </div>
      <p class="text-2xl font-extrabold text-white">${(s[def.key] || 0).toLocaleString('en-IN')}</p>
    </div>
  `).join('');
  if (window.lucide) lucide.createIcons();
}

function rowHtml(c) {
  return `
    <tr class="table-row">
      <td class="px-5 py-3.5">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold shadow-sm" style="background:${avatarColor(c.name)}">${initials(c.name)}</div>
          <div>
            <p class="font-semibold text-white">${c.name}</p>
            <p class="text-[11.5px] text-slate-400">${c.email}</p>
          </div>
        </div>
      </td>
      <td class="px-5 py-3.5 font-bold text-white">${formatINR(c.total_spent)}</td>
      <td class="px-5 py-3.5 text-emerald-400 font-bold">${c.successful_payments}</td>
      <td class="px-5 py-3.5 text-rose-400 font-bold">${c.failed_payments}</td>
      <td class="px-5 py-3.5 text-slate-300">${formatINR(c.avg_order)}</td>
      <td class="px-5 py-3.5 text-slate-400">${formatDate(c.last_payment_at)}</td>
      <td class="px-5 py-3.5"><span class="badge ${riskClass(c.risk_level)}">${c.risk_level}</span></td>
      <td class="px-5 py-3.5"><button onclick="openDrawer(${c.id})" class="text-[#00E5FF] font-bold hover:underline">View</button></td>
    </tr>
  `;
}

async function loadCustomers() {
  const searchInput = document.getElementById('search-input');
  const search = searchInput ? searchInput.value : '';
  const rows = await apiGet('/api/customers?' + new URLSearchParams({ search }));
  const tbody = document.getElementById('customers-tbody');
  if (tbody) {
    tbody.innerHTML = rows.length
      ? rows.map(rowHtml).join('')
      : `<tr><td colspan="8" class="text-center py-10 text-slate-400 text-sm">No customers match your search.</td></tr>`;
  }
  const countElem = document.getElementById('results-count');
  if (countElem) {
    countElem.textContent = `Showing 1 to ${rows.length} of ${rows.length} entries`;
  }
}

async function openDrawer(id) {
  const c = await apiGet(`/api/customers/${id}`);
  const recoverable = (c.payment_history || [])
    .filter(p => p.recovery_state === 'Pending')
    .reduce((sum, p) => sum + Number(p.amount), 0);

  document.getElementById('drawer-content').innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-bold text-white">Customer Profile</h3>
      <button onclick="closeDrawer()" class="w-8 h-8 rounded-lg hover:bg-[#1E293B] text-slate-400 hover:text-white flex items-center justify-center transition-colors"><i data-lucide="x" class="w-4 h-4"></i></button>
    </div>
    <div class="flex items-center gap-3 mb-6">
      <div class="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-md" style="background:${avatarColor(c.name)}">${initials(c.name)}</div>
      <div>
        <p class="font-semibold text-white">${c.name}</p>
        <p class="text-[12.5px] text-slate-400">${c.email} · ${c.phone || '—'}</p>
      </div>
      <span class="ml-auto badge ${riskClass(c.risk_level)}">${c.risk_level} Risk</span>
    </div>
    <div class="grid grid-cols-2 gap-3 mb-6">
      <div class="card p-3.5"><p class="text-[11px] text-slate-400">Total Spent</p><p class="font-bold text-white text-[15px]">${formatINR(c.total_spent)}</p></div>
      <div class="card p-3.5"><p class="text-[11px] text-slate-400">Recoverable Now</p><p class="font-bold text-[#00E5FF] text-[15px]">${formatINR(recoverable)}</p></div>
      <div class="card p-3.5"><p class="text-[11px] text-slate-400">Successful Payments</p><p class="font-bold text-emerald-400 text-[15px]">${c.successful_payments}</p></div>
      <div class="card p-3.5"><p class="text-[11px] text-slate-400">Failed Payments</p><p class="font-bold text-rose-400 text-[15px]">${c.failed_payments}</p></div>
    </div>
    <h4 class="text-[13px] font-bold text-slate-200 mb-3 uppercase tracking-wider">Payment History</h4>
    <div class="space-y-2">
      ${(c.payment_history || []).map(p => `
        <div class="flex items-center justify-between p-3 rounded-lg border border-[#1E293B] bg-[#161F33]/40">
          <div>
            <p class="text-[13px] font-medium text-white">${formatINR(p.amount)} · ${p.failure_reason}</p>
            <p class="text-[11.5px] text-slate-400">${formatDate(p.failed_at)}</p>
          </div>
          <span class="badge ${scoreBucketClass(p.status)}">${p.status}</span>
        </div>
      `).join('') || `<p class="text-[13px] text-slate-400">No payment history yet.</p>`}
    </div>
  `;
  document.getElementById('detail-overlay').classList.remove('hidden');
  document.getElementById('detail-drawer').classList.remove('translate-x-full');
  if (window.lucide) lucide.createIcons();
}

function closeDrawer() {
  document.getElementById('detail-overlay').classList.add('hidden');
  document.getElementById('detail-drawer').classList.add('translate-x-full');
}

window.loadCustomersData = function() {
  loadSummary();
  loadCustomers();
};
window.openDrawer = openDrawer;
window.closeDrawer = closeDrawer;

const searchInputElem = document.getElementById('search-input');
if (searchInputElem) {
  searchInputElem.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadCustomers, 250);
  });
}

window.loadCustomersData();
if (window.realtimeEngine) {
  window.realtimeEngine.subscribe(window.loadCustomersData);
}
