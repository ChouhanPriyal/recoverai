let queue = [];
let activeId = null;

function queueItemHtml(p) {
  const active = p.id === activeId;
  return `
    <button data-id="${p.id}" class="queue-item w-full text-left p-3 rounded-xl border transition-all duration-150
      ${active ? 'border-[#00E5FF]/60 bg-[#00E5FF]/10 text-white shadow-[0_0_12px_rgba(0,229,255,0.15)]' : 'border-transparent hover:bg-[#161F33] text-slate-300'}">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-bold shrink-0 shadow-sm" style="background:${avatarColor(p.customer_name)}">${initials(p.customer_name)}</div>
        <div class="min-w-0 flex-1">
          <p class="text-[13px] font-semibold truncate ${active ? 'text-[#00E5FF]' : 'text-slate-200'}">${p.customer_name}</p>
          <p class="text-[11px] text-slate-400 truncate">Failed ${formatDate(p.failed_at)}</p>
        </div>
        <span class="text-[11px] font-extrabold ${p.status === 'High' ? 'text-emerald-400' : p.status === 'Medium' ? 'text-amber-400' : 'text-rose-400'}">Score ${p.recovery_score}%</span>
      </div>
    </button>
  `;
}

function renderQueue(filter = '') {
  const elem = document.getElementById('queue-list');
  if (!elem) return;
  const filtered = queue.filter(p =>
    p.customer_name.toLowerCase().includes(filter.toLowerCase()) ||
    (p.email || '').toLowerCase().includes(filter.toLowerCase())
  );
  elem.innerHTML = filtered.map(queueItemHtml).join('') ||
    `<p class="text-[12.5px] text-slate-400 px-2 py-4 text-center">No pending payments in queue.</p>`;
  document.querySelectorAll('.queue-item').forEach(btn => {
    btn.addEventListener('click', () => selectPayment(Number(btn.dataset.id)));
  });
}

const ACTIVITY_ICON = { analysis: 'brain-circuit', decision: 'git-branch', action: 'zap', message: 'message-circle' };

function detailHtml(p) {
  const rec = p.recommendation || {};
  const isRecovered = p.recovery_state === 'Recovered';
  const isInProgress = p.recovery_state === 'In Progress';

  return `
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <!-- Payment details -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-[12px] font-bold text-slate-400 uppercase tracking-wider">Payment Details</p>
          <span class="badge ${isRecovered ? 'badge-high' : isInProgress ? 'badge-medium' : 'badge-draft'}">${p.recovery_state}</span>
        </div>
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shadow-md" style="background:${avatarColor(p.customer_name)}">${initials(p.customer_name)}</div>
          <div>
            <p class="font-semibold text-white text-[14px]">${p.customer_name}</p>
            <p class="text-[11.5px] text-slate-400">${p.email}</p>
          </div>
        </div>
        <div class="space-y-3 text-[13px] mb-5">
          <div class="flex justify-between"><span class="text-slate-400">Amount</span><span class="font-bold text-white">${formatINR(p.amount)}</span></div>
          <div class="flex justify-between"><span class="text-slate-400">Failure Reason</span><span class="font-medium text-slate-200">${p.failure_reason}</span></div>
          <div class="flex justify-between"><span class="text-slate-400">Failed On</span><span class="font-medium text-slate-300">${formatDate(p.failed_at)}</span></div>
          <div class="flex justify-between"><span class="text-slate-400">Attempts</span><span class="font-medium text-slate-300">${p.attempts}</span></div>
        </div>
        <div class="rounded-xl bg-[#00E5FF]/10 border border-[#00E5FF]/30 p-4 text-center shadow-[0_0_15px_rgba(0,229,255,0.1)]">
          <p class="text-[11px] text-[#00E5FF] font-bold uppercase tracking-wider mb-1">AI Recovery Score</p>
          <p class="text-3xl font-extrabold text-white drop-shadow-[0_0_10px_rgba(0,229,255,0.5)]">${rec.confidence || p.recovery_score}%</p>
          <p class="text-[11.5px] text-[#00E5FF] font-semibold mt-1">High Probability</p>
        </div>
      </div>

      <!-- Activity timeline -->
      <div class="card p-5">
        <p class="text-[12px] font-bold text-slate-400 uppercase tracking-wider mb-4">AI Agent Timeline</p>
        <div class="space-y-4">
          ${(p.activity || []).map((a, idx) => `
            <div class="flex gap-3">
              <div class="flex flex-col items-center">
                <span class="w-7 h-7 rounded-full bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/30 flex items-center justify-center shrink-0">
                  <i data-lucide="${ACTIVITY_ICON[a.activity_type] || 'circle'}" class="w-3.5 h-3.5"></i>
                </span>
                ${idx < p.activity.length - 1 ? '<span class="w-px flex-1 bg-[#1E293B] my-1"></span>' : ''}
              </div>
              <div class="pb-3">
                <p class="text-[12.5px] font-medium text-slate-200">${a.activity}</p>
                <p class="text-[11px] text-slate-400">${formatDate(a.created_at)}</p>
              </div>
            </div>
          `).join('') || `<p class="text-[12.5px] text-slate-400">No activity logged yet — trigger recovery to begin.</p>`}
        </div>
      </div>

      <!-- Recommendation -->
      <div class="card p-5 flex flex-col">
        <p class="text-[12px] font-bold text-slate-400 uppercase tracking-wider mb-4">Gemini AI Strategy</p>
        <div class="flex items-center gap-3 mb-4">
          <span class="w-9 h-9 rounded-xl bg-gradient-to-br from-[#00E5FF] to-[#00B4D8] text-[#090D16] flex items-center justify-center shadow-[0_0_12px_rgba(0,229,255,0.4)]">
            <i data-lucide="wand-2" class="w-4 h-4"></i>
          </span>
          <div>
            <p class="text-[11px] text-slate-400">Recommended Strategy</p>
            <p class="font-extrabold text-white text-[14px]">${rec.strategy || 'Payment Retry'}</p>
          </div>
        </div>
        <p class="text-[11.5px] font-bold text-slate-300 mb-1.5">AI Assessment & Reasoning</p>
        <p class="text-[12.5px] text-slate-400 leading-relaxed mb-4">${rec.reasoning || 'AI evaluation complete.'}</p>
        ${rec.message_draft ? `
        <p class="text-[11.5px] font-bold text-slate-300 mb-1.5">Personalized Outreach Draft</p>
        <p class="text-[12.5px] text-slate-300 leading-relaxed bg-[#161F33] border border-[#26354D] rounded-lg p-3 mb-4 italic">"${rec.message_draft}"</p>
        ` : ''}

        ${isRecovered ? `
          <div class="mt-auto p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-center">
            <p class="text-emerald-400 text-[13px] font-extrabold">✓ Revenue Recovered</p>
          </div>
        ` : `
          <button id="recover-now-btn" class="mt-auto w-full py-3 rounded-xl bg-gradient-to-r from-[#00E5FF] to-[#00B4D8] text-[#090D16] text-[13.5px] font-extrabold flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(0,229,255,0.35)] hover:brightness-110 transition-all">
            <i data-lucide="zap" class="w-4 h-4"></i> ${isInProgress ? 'Re-Trigger AI Outreach' : 'Let AI Recover Now'}
          </button>
        `}
      </div>
    </div>
  `;
}

async function selectPayment(id) {
  activeId = id;
  const searchInput = document.getElementById('queue-search');
  renderQueue(searchInput ? searchInput.value : '');
  const p = await apiGet(`/api/recovery-agent/${id}`);
  const detailElem = document.getElementById('agent-detail');
  if (detailElem) {
    detailElem.innerHTML = detailHtml(p);
    if (window.lucide) lucide.createIcons();

    const btn = document.getElementById('recover-now-btn');
    if (btn) {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Dispatching AI Agent...`;
        if (window.lucide) lucide.createIcons();
        await apiPost(`/api/recovery-agent/${id}/recover`);
        showToast('🚀 AI Recovery workflow dispatched for ' + p.customer_name, 'success');
        await selectPayment(id);
        await loadQueue();
      });
    }
  }
}

async function loadQueue() {
  queue = await apiGet('/api/recovery-agent/queue');
  const searchInput = document.getElementById('queue-search');
  renderQueue(searchInput ? searchInput.value : '');
  if (queue.length) {
    if (!activeId || !queue.find(q => q.id === activeId)) {
      const hash = Number(window.location.hash.replace('#', ''));
      activeId = (hash && queue.find(q => q.id === hash)) ? hash : queue[0].id;
    }
    selectPayment(activeId);
  }
}

window.loadQueue = loadQueue;
const searchInput = document.getElementById('queue-search');
if (searchInput) {
  searchInput.addEventListener('input', e => renderQueue(e.target.value));
}

loadQueue();
if (window.realtimeEngine) {
  window.realtimeEngine.subscribe(loadQueue);
}
