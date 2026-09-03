/**
 * RecoverAI — Shared Javascript Utilities & Real-Time Engine (Dark Futuristic AI Theme)
 */

async function apiGet(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${url}`);
  return await res.json();
}

async function apiPost(url, body = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} posting ${url}`);
  return await res.json();
}

function formatINR(amount, options = {}) {
  const val = Number(amount) || 0;
  if (options.compact && val >= 100000) {
    return '₹' + (val / 100000).toFixed(1) + 'L';
  }
  if (options.compact && val >= 1000) {
    return '₹' + (val / 1000).toFixed(1) + 'k';
  }
  return '₹' + val.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function initials(name) {
  if (!name) return '??';
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.substring(0, 2).toUpperCase();
}

function avatarColor(name) {
  const colors = [
    '#00B4D8', '#0284C7', '#059669', '#D97706', '#E11D48',
    '#0891B2', '#00E5FF', '#2563EB', '#D946EF', '#4F46E5'
  ];
  let hash = 0;
  for (let i = 0; i < (name || '').length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function scoreBucketClass(status) {
  if (status === 'High') return 'badge-high';
  if (status === 'Medium') return 'badge-medium';
  return 'badge-low';
}

function statusBadgeClass(status) {
  const s = (status || '').toLowerCase();
  if (s === 'running') return 'badge-running';
  if (s === 'completed') return 'badge-completed';
  if (s === 'paused') return 'badge-paused';
  return 'badge-draft';
}

// Dark Futuristic Toast notification helper
function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  const border = type === 'success' ? 'border-emerald-500/50 text-emerald-300' : type === 'warning' ? 'border-amber-500/50 text-amber-300' : 'border-[#00E5FF]/50 text-[#00E5FF]';
  toast.className = `bg-[#111726]/95 backdrop-blur-md border ${border} px-4 py-3 rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.8)] text-[13px] font-semibold flex items-center gap-2.5 transition-all transform translate-y-2 opacity-0 pointer-events-auto max-w-md`;
  toast.innerHTML = `<i data-lucide="${type === 'success' ? 'check-circle-2' : type === 'warning' ? 'alert-triangle' : 'sparkles'}" class="w-4 h-4 shrink-0"></i><span>${message}</span>`;
  
  toastContainer.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Global Real-Time Live Polling Engine
class RealtimeEngine {
  constructor() {
    this.intervalId = null;
    this.listeners = [];
    this.active = true;
    this.interval = 4000;
  }

  subscribe(callback) {
    this.listeners.push(callback);
    if (!this.intervalId && this.active) {
      this.start();
    }
  }

  start() {
    this.active = true;
    if (this.intervalId) clearInterval(this.intervalId);
    this.intervalId = setInterval(() => {
      if (this.active) {
        this.listeners.forEach(fn => fn());
      }
    }, this.interval);
  }

  stop() {
    this.active = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

window.realtimeEngine = new RealtimeEngine();
