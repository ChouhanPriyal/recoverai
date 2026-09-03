let trendChartInstance = null;
let donutChartInstance = null;

const STAT_DEFS = [
  { key: 'failed_payments',      label: 'Failed Payments',           icon: 'circle-x',   tint: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',    fmt: v => (v || 0).toLocaleString('en-IN') },
  { key: 'lost_revenue',         label: 'Lost Revenue',              icon: 'trending-down', tint: 'bg-amber-500/10 text-amber-400 border border-amber-500/20', fmt: v => formatINR(v, { compact: true }) },
  { key: 'recovered_revenue',    label: 'Recovered Revenue',         icon: 'shield-check', tint: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', fmt: v => formatINR(v, { compact: true }) },
  { key: 'recovery_rate',        label: 'Recovery Rate',             icon: 'gauge',      tint: 'bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20 shadow-[0_0_10px_rgba(0,229,255,0.15)]', fmt: v => (v || 0) + '%' },
  { key: 'potential_recoverable',label: 'Potentially Recoverable',   icon: 'wallet',     tint: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',    fmt: v => formatINR(v, { compact: true }) },
];

function renderStatCards(data) {
  const wrap = document.getElementById('stat-cards');
  if (!wrap) return;
  wrap.innerHTML = STAT_DEFS.map(def => `
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <span class="text-[13px] text-slate-400 font-medium">${def.label}</span>
        <span class="w-8 h-8 rounded-lg ${def.tint} flex items-center justify-center">
          <i data-lucide="${def.icon}" class="w-4 h-4"></i>
        </span>
      </div>
      <p class="text-2xl font-extrabold text-white">${def.fmt(data[def.key])}</p>
      <p class="text-[11.5px] text-emerald-400 font-medium mt-1.5 flex items-center gap-1">
        <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i> vs last 7 days
      </p>
    </div>
  `).join('');
  if (window.lucide) lucide.createIcons();
}

function renderTrendChart(trend) {
  const canvas = document.getElementById('trendChart');
  if (!canvas) return;
  const labels = trend.map(t => new Date(t.day).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
  const values = trend.map(t => Number(t.recovered));

  if (trendChartInstance) {
    trendChartInstance.data.labels = labels;
    trendChartInstance.data.datasets[0].data = values;
    trendChartInstance.update();
    return;
  }

  trendChartInstance = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Recovered Revenue',
        data: values,
        borderColor: '#00E5FF',
        backgroundColor: 'rgba(0, 229, 255, 0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#00E5FF',
        pointHoverRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          ticks: { color: '#94A3B8', callback: v => formatINR(v, { compact: true }) },
          grid: { color: 'rgba(255, 255, 255, 0.06)' },
        },
        x: {
          ticks: { color: '#94A3B8' },
          grid: { display: false },
        },
      },
    },
  });
}

function renderDonut(recovered, lost) {
  const canvas = document.getElementById('rateDonut');
  if (!canvas) return;
  const unrecovered = Math.max(lost - recovered, 0);

  if (donutChartInstance) {
    donutChartInstance.data.datasets[0].data = [recovered, unrecovered];
    donutChartInstance.update();
  } else {
    donutChartInstance = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Recovered', 'Unrecovered'],
        datasets: [{ data: [recovered, unrecovered], backgroundColor: ['#00E5FF', '#1E293B'], borderWidth: 0 }],
      },
      options: { cutout: '72%', plugins: { legend: { display: false } } },
    });
  }

  document.getElementById('legend-recovered').textContent = formatINR(recovered, { compact: true });
  document.getElementById('legend-unrecovered').textContent = formatINR(unrecovered, { compact: true });
  document.getElementById('legend-lost').textContent = formatINR(lost, { compact: true });
}

const INSIGHT_ICON = { opportunity: 'trending-up', warning: 'alert-triangle', success: 'check-circle-2', info: 'lightbulb' };
const INSIGHT_TINT = {
  opportunity: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  warning: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  success: 'bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20',
  info: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
};

function renderInsights(insights) {
  const wrap = document.getElementById('insights-list');
  if (!wrap) return;
  wrap.innerHTML = insights.map(i => `
    <div class="flex items-start gap-3 p-3.5 rounded-xl border border-[#1E293B] bg-[#161F33]/60">
      <span class="w-8 h-8 rounded-lg ${INSIGHT_TINT[i.type]} flex items-center justify-center shrink-0">
        <i data-lucide="${INSIGHT_ICON[i.type]}" class="w-4 h-4"></i>
      </span>
      <p class="text-[13px] text-slate-300 leading-snug">${i.text}</p>
    </div>
  `).join('');
  if (window.lucide) lucide.createIcons();
}

async function loadDashboardData() {
  try {
    const data = await apiGet('/api/dashboard');
    renderStatCards(data);
    renderTrendChart(data.trend);
    renderDonut(data.recovered_revenue, data.lost_revenue);
    renderInsights(data.insights);
  } catch (e) {
    console.error(e);
  }
}

window.loadDashboardData = loadDashboardData;
loadDashboardData();
if (window.realtimeEngine) {
  window.realtimeEngine.subscribe(loadDashboardData);
}
