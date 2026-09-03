let currentTab = 'all';
const TABS = [
  { key: 'all', label: 'All Campaigns' },
  { key: 'running', label: 'Running' },
  { key: 'completed', label: 'Completed' },
  { key: 'draft', label: 'Drafts' },
];

function renderTabs() {
  const tabsWrap = document.getElementById('tabs');
  if (!tabsWrap) return;
  tabsWrap.innerHTML = TABS.map(t => `
    <button data-key="${t.key}" class="tab-btn ${currentTab === t.key ? 'active' : ''}">${t.label}</button>
  `).join('');
  document.querySelectorAll('#tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      currentTab = btn.dataset.key;
      renderTabs();
      loadCampaigns();
    });
  });
}

function rowHtml(c) {
  const pct = c.potential_revenue > 0 ? Math.min(100, Math.round((c.recovered_revenue / c.potential_revenue) * 100)) : 0;
  const isRunning = c.status === 'Running';
  const isCompleted = c.status === 'Completed';

  return `
    <tr class="table-row">
      <td class="px-5 py-3.5 font-bold text-white">${c.name}</td>
      <td class="px-5 py-3.5 text-slate-400">${c.target_audience || '—'}</td>
      <td class="px-5 py-3.5"><span class="badge badge-completed">${c.strategy || '—'}</span></td>
      <td class="px-5 py-3.5 text-slate-300">${(c.customer_count || 0).toLocaleString('en-IN')}</td>
      <td class="px-5 py-3.5 font-bold text-white">${formatINR(c.potential_revenue)}</td>
      <td class="px-5 py-3.5">
        <div class="flex items-center gap-2">
          <span class="font-bold text-emerald-400">${formatINR(c.recovered_revenue)}</span>
          <div class="w-16 h-1.5 rounded-full bg-[#161F33] overflow-hidden border border-[#26354D]"><div class="h-full bg-[#00E5FF] shadow-[0_0_8px_rgba(0,229,255,0.8)]" style="width:${pct}%"></div></div>
        </div>
      </td>
      <td class="px-5 py-3.5"><span class="badge ${statusBadgeClass(c.status)}">${c.status}</span></td>
      <td class="px-5 py-3.5">
        <div class="flex items-center gap-2">
          ${!isCompleted ? `
            <button onclick="toggleCampaignStatus(${c.id}, '${isRunning ? 'Paused' : 'Running'}')" class="text-xs font-bold px-2.5 py-1 rounded border ${isRunning ? 'border-amber-500/30 text-amber-400 hover:bg-amber-500/10' : 'border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10'} transition-colors">
              ${isRunning ? 'Pause' : 'Launch'}
            </button>
          ` : ''}
          <button onclick="deleteCampaign(${c.id})" class="text-xs font-bold px-2 py-1 rounded text-rose-400 hover:bg-rose-500/10 transition-colors" title="Delete Campaign">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </td>
    </tr>
  `;
}

async function loadCampaigns() {
  try {
    const data = await apiGet('/api/campaigns?status=' + currentTab);
    const tbody = document.getElementById('campaigns-tbody');
    if (tbody) {
      tbody.innerHTML = data.campaigns.length
        ? data.campaigns.map(rowHtml).join('')
        : `<tr><td colspan="8" class="text-center py-10 text-slate-400 text-sm">No campaigns found in this view.</td></tr>`;
    }

    const s = data.summary || {};
    const rate = s.potential_revenue > 0 ? Math.round((s.recovered_revenue / s.potential_revenue) * 100) : 0;
    const cardsWrap = document.getElementById('summary-cards');
    if (cardsWrap) {
      cardsWrap.className = 'grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4';
      cardsWrap.innerHTML = `
        <div class="card p-4"><p class="text-[12px] text-slate-400 mb-1">Total Campaigns</p><p class="text-xl font-extrabold text-white">${s.total_campaigns || 0}</p></div>
        <div class="card p-4"><p class="text-[12px] text-slate-400 mb-1">Running</p><p class="text-xl font-extrabold text-emerald-400">${s.running || 0}</p></div>
        <div class="card p-4"><p class="text-[12px] text-slate-400 mb-1">Total Audience</p><p class="text-xl font-extrabold text-white">${(s.total_customers || 0).toLocaleString('en-IN')}</p></div>
        <div class="card p-4"><p class="text-[12px] text-slate-400 mb-1">Potential Rev.</p><p class="text-xl font-extrabold text-white">${formatINR(s.potential_revenue, { compact: true })}</p></div>
        <div class="card p-4"><p class="text-[12px] text-slate-400 mb-1">Recovered Rev.</p><p class="text-xl font-extrabold text-[#00E5FF]">${formatINR(s.recovered_revenue, { compact: true })}</p></div>
        <div class="card p-4"><p class="text-[12px] text-slate-400 mb-1">Recovery Rate</p><p class="text-xl font-extrabold text-amber-400">${rate}%</p></div>
      `;
    }
    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error('Error loading campaigns:', e);
  }
}

async function toggleCampaignStatus(id, newStatus) {
  try {
    await apiPost(`/api/campaigns/${id}/status`, { status: newStatus });
    showToast(`Campaign status updated to ${newStatus}`, 'success');
    loadCampaigns();
  } catch (e) {
    showToast('Failed to update status: ' + e.message, 'warning');
  }
}

async function deleteCampaign(id) {
  if (!confirm('Are you sure you want to delete this campaign?')) return;
  try {
    const res = await fetch(`/api/campaigns/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Campaign deleted', 'info');
      loadCampaigns();
    }
  } catch (e) {
    showToast('Failed to delete campaign', 'warning');
  }
}

function openModal() {
  const modal = document.getElementById('modal-overlay');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
}

function closeModal() {
  const modal = document.getElementById('modal-overlay');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

window.loadCampaigns = loadCampaigns;
window.openModal = openModal;
window.closeModal = closeModal;
window.toggleCampaignStatus = toggleCampaignStatus;
window.deleteCampaign = deleteCampaign;

const newBtn = document.getElementById('new-campaign-btn');
if (newBtn) {
  newBtn.addEventListener('click', openModal);
}

const modalOverlay = document.getElementById('modal-overlay');
if (modalOverlay) {
  modalOverlay.addEventListener('click', e => {
    if (e.target.id === 'modal-overlay') closeModal();
  });
}

const formElem = document.getElementById('campaign-form');
if (formElem) {
  formElem.addEventListener('submit', async e => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    
    try {
      const res = await apiPost('/api/campaigns', payload);
      if (res.ok) {
        showToast(`🎉 Campaign "${payload.name}" created successfully!`, 'success');
        closeModal();
        e.target.reset();
        loadCampaigns();
      }
    } catch (err) {
      showToast('Error creating campaign: ' + err.message, 'warning');
    }
  });
}

renderTabs();
loadCampaigns();
if (window.realtimeEngine) {
  window.realtimeEngine.subscribe(loadCampaigns);
}
