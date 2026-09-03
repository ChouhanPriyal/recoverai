let currentBucket = 'all';
let searchTimer = null;

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'High', label: 'High Value' },
  { key: 'Medium', label: 'High Recovery' },
  { key: 'recent', label: 'Recently Failed' },
];

function renderTabs(counts) {
  const tabsWrap = document.getElementById('tabs');
  if (!tabsWrap) return;
  tabsWrap.innerHTML = TABS.map(t => `
    <button data-key="${t.key}" class="tab-btn ${currentBucket === t.key ? 'active' : ''}">
      ${t.label} ${counts[t.key] !== undefined ? `(${counts[t.key]})` : ''}
    </button>
  `).join('');
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentBucket = btn.dataset.key;
      loadPayments();
    });
  });
}

function rowHtml(p) {
  const initial = initials(p.customer_name);
  const color = avatarColor(p.customer_name);
  return `
    <tr class="table-row">
      <td class="px-5 py-3.5">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold shadow-sm" style="background:${color}">${initial}</div>
          <div>
            <p class="font-semibold text-white">${p.customer_name}</p>
            <p class="text-[11.5px] text-slate-400">${p.email}</p>
          </div>
        </div>
      </td>
      <td class="px-5 py-3.5 text-slate-400 font-mono text-[12px]">${p.razorpay_payment_id}</td>
      <td class="px-5 py-3.5 font-bold text-white">${formatINR(p.amount)}</td>
      <td class="px-5 py-3.5 text-slate-300">${p.failure_reason}</td>
      <td class="px-5 py-3.5 text-slate-400">${p.attempts}</td>
      <td class="px-5 py-3.5 text-slate-400">${formatDate(p.failed_at)}</td>
      <td class="px-5 py-3.5 font-bold text-white">${p.recovery_score}%</td>
      <td class="px-5 py-3.5"><span class="badge ${scoreBucketClass(p.status)}">${p.status}</span></td>
      <td class="px-5 py-3.5">
        <button onclick="openDrawer(${p.id})" class="text-[#00E5FF] font-bold hover:underline">View</button>
      </td>
    </tr>
  `;
}

async function loadPayments() {
  const searchInput = document.getElementById('search-input');
  const search = searchInput ? searchInput.value : '';
  const params = new URLSearchParams({ search });
  if (currentBucket !== 'all') params.set('bucket', currentBucket);
  const rows = await apiGet('/api/failed-payments?' + params.toString());

  const counts = {
    all: rows.length,
    High: rows.filter(r => r.status === 'High').length,
    Medium: rows.filter(r => r.status === 'Medium').length,
    recent: rows.length,
  };
  renderTabs(counts);

  const tbody = document.getElementById('payments-tbody');
  if (tbody) {
    tbody.innerHTML = rows.length
      ? rows.map(rowHtml).join('')
      : `<tr><td colspan="9" class="text-center py-10 text-slate-400 text-sm">No failed payments match your search.</td></tr>`;
  }
  const countElem = document.getElementById('results-count');
  if (countElem) {
    countElem.textContent = `Showing 1 to ${rows.length} of ${rows.length} entries`;
  }
  if (window.lucide) lucide.createIcons();
}

async function openDrawer(id) {
  const p = await apiGet(`/api/failed-payments/${id}`);
  document.getElementById('drawer-content').innerHTML = `
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-bold text-white">Payment Details</h3>
      <button onclick="closeDrawer()" class="w-8 h-8 rounded-lg hover:bg-[#1E293B] text-slate-400 hover:text-white flex items-center justify-center transition-colors">
        <i data-lucide="x" class="w-4 h-4"></i>
      </button>
    </div>
    <div class="flex items-center gap-3 mb-6">
      <div class="w-11 h-11 rounded-full flex items-center justify-center text-white font-bold shadow-md" style="background:${avatarColor(p.customer_name)}">${initials(p.customer_name)}</div>
      <div>
        <p class="font-semibold text-white">${p.customer_name}</p>
        <p class="text-[12.5px] text-slate-400">${p.email}</p>
      </div>
      <span class="ml-auto badge ${scoreBucketClass(p.status)}">Score ${p.recovery_score}%</span>
    </div>
    <div class="grid grid-cols-2 gap-4 text-[13px] mb-6">
      <div><p class="text-slate-400 text-[11.5px]">Amount</p><p class="font-bold text-white">${formatINR(p.amount)}</p></div>
      <div><p class="text-slate-400 text-[11.5px]">Failure Reason</p><p class="font-semibold text-slate-200">${p.failure_reason}</p></div>
      <div><p class="text-slate-400 text-[11.5px]">Attempts</p><p class="font-semibold text-slate-200">${p.attempts}</p></div>
      <div><p class="text-slate-400 text-[11.5px]">Failed On</p><p class="font-semibold text-slate-300">${formatDate(p.failed_at)}</p></div>
      <div><p class="text-slate-400 text-[11.5px]">Payment ID</p><p class="font-semibold text-slate-200 font-mono text-[12px]">${p.razorpay_payment_id}</p></div>
      <div><p class="text-slate-400 text-[11.5px]">Status State</p><p class="font-bold text-[#00E5FF]">${p.recovery_state}</p></div>
    </div>
    <div class="flex gap-3">
      <a href="/recovery-agent#${p.id}" class="flex-1 text-center py-2.5 rounded-lg border border-[#26354D] bg-[#161F33] text-[13px] font-semibold text-slate-200 hover:bg-[#1E293B] transition-colors">Open in AI Agent</a>
      <button id="recover-btn" class="flex-1 py-2.5 rounded-lg bg-gradient-to-r from-[#00E5FF] to-[#00B4D8] text-[#090D16] text-[13px] font-extrabold shadow-[0_0_15px_rgba(0,229,255,0.3)] hover:brightness-110 transition-all">AI Recovery</button>
    </div>
  `;
  document.getElementById('recover-btn').addEventListener('click', async () => {
    await apiPost(`/api/failed-payments/${id}/recover`);
    showToast('Recovery workflow initiated for payment #' + id, 'success');
    document.getElementById('recover-btn').textContent = 'Recovery Started ✓';
    document.getElementById('recover-btn').disabled = true;
    loadPayments();
  });
  document.getElementById('detail-overlay').classList.remove('hidden');
  document.getElementById('detail-drawer').classList.remove('translate-x-full');
  if (window.lucide) lucide.createIcons();
}

function closeDrawer() {
  document.getElementById('detail-overlay').classList.add('hidden');
  document.getElementById('detail-drawer').classList.add('translate-x-full');
}

window.loadPayments = loadPayments;
window.openDrawer = openDrawer;
window.closeDrawer = closeDrawer;

const searchInputElem = document.getElementById('search-input');
if (searchInputElem) {
  searchInputElem.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadPayments, 250);
  });
}

loadPayments();
if (window.realtimeEngine) {
  window.realtimeEngine.subscribe(loadPayments);
}
