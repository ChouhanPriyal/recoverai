const DONUT_COLORS = ['#00E5FF', '#38BDF8', '#F59E0B', '#10B981', '#F43F5E', '#A855F7'];

let analyticsTrendChart = null;
let analyticsReasonDonut = null;
let analyticsStrategyDonut = null;

function renderStatCards(d) {
  const elem = document.getElementById('stat-cards');
  if (!elem) return;
  const defs = [
    { label: 'Recovery Rate', value: (d.recovery_rate || 0) + '%', icon: 'gauge', tint: 'bg-[#00E5FF]/10 text-[#00E5FF] border border-[#00E5FF]/20 shadow-[0_0_10px_rgba(0,229,255,0.15)]' },
    { label: 'Recovered Revenue', value: formatINR(d.recovered_revenue, { compact: true }), icon: 'shield-check', tint: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' },
    { label: 'Average Recovery Time', value: (d.avg_recovery_hours || 0) + ' hrs', icon: 'clock', tint: 'bg-sky-500/10 text-sky-400 border border-sky-500/20' },
    { label: 'ROI from Recovery', value: (d.roi_percent || 0) + '%', icon: 'trending-up', tint: 'bg-amber-500/10 text-amber-400 border border-amber-500/20' },
  ];
  elem.innerHTML = defs.map(def => `
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <span class="text-[13px] text-slate-400 font-medium">${def.label}</span>
        <span class="w-8 h-8 rounded-lg ${def.tint} flex items-center justify-center"><i data-lucide="${def.icon}" class="w-4 h-4"></i></span>
      </div>
      <p class="text-2xl font-extrabold text-white">${def.value}</p>
    </div>
  `).join('');
  if (window.lucide) lucide.createIcons();
}

function renderFunnel(f) {
  const elem = document.getElementById('funnel');
  if (!elem) return;
  const stages = [
    { label: 'Failed Payments', value: f.failed || 0 },
    { label: 'Analyzed by AI', value: f.analyzed || 0 },
    { label: 'Recovery Attempted', value: f.attempted || 0 },
    { label: 'Recovered', value: f.recovered || 0 },
  ];
  const max = stages[0].value || 1;
  elem.innerHTML = stages.map((s, i) => {
    const pct = Math.max(8, Math.round((s.value / max) * 100));
    return `
      <div>
        <div class="flex justify-between text-[12.5px] mb-1.5">
          <span class="text-slate-400">${s.label}</span>
          <span class="font-bold text-white">${s.value.toLocaleString('en-IN')} <span class="text-slate-400 font-normal">(${Math.round((s.value / max) * 100)}%)</span></span>
        </div>
        <div class="h-3 rounded-full bg-[#161F33] overflow-hidden border border-[#26354D]">
          <div class="h-full rounded-full transition-all duration-300" style="width:${pct}%; background:${DONUT_COLORS[i % DONUT_COLORS.length]}"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderTrend(trend) {
  const canvas = document.getElementById('trendChart');
  if (!canvas) return;
  const labels = trend.map(t => new Date(t.day).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
  const lostData = trend.map(t => Number(t.lost));
  const recoveredData = trend.map(t => Number(t.recovered));

  if (analyticsTrendChart) {
    analyticsTrendChart.data.labels = labels;
    analyticsTrendChart.data.datasets[0].data = lostData;
    analyticsTrendChart.data.datasets[1].data = recoveredData;
    analyticsTrendChart.update();
  } else {
    analyticsTrendChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Lost', data: lostData, borderColor: '#F43F5E', backgroundColor: 'transparent', tension: 0.4, pointRadius: 3 },
          { label: 'Recovered', data: recoveredData, borderColor: '#00E5FF', backgroundColor: 'rgba(0,229,255,0.08)', fill: true, tension: 0.4, pointRadius: 3 },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11.5 }, color: '#94A3B8' } } },
        scales: {
          y: { ticks: { color: '#94A3B8', callback: v => formatINR(v, { compact: true }) }, grid: { color: 'rgba(255, 255, 255, 0.06)' } },
          x: { ticks: { color: '#94A3B8' }, grid: { display: false } }
        },
      },
    });
  }
}

function renderDonutChart(chartRef, canvasId, legendId, rows, labelKey, valueKey) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  const total = rows.reduce((s, r) => s + Number(r[valueKey]), 0) || 1;
  const labels = rows.map(r => r[labelKey]);
  const data = rows.map(r => r[valueKey]);

  let instance = chartRef;
  if (instance) {
    instance.data.labels = labels;
    instance.data.datasets[0].data = data;
    instance.update();
  } else {
    instance = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{ data, backgroundColor: DONUT_COLORS, borderWidth: 0 }],
      },
      options: { cutout: '65%', plugins: { legend: { display: false } } },
    });
  }

  const legendElem = document.getElementById(legendId);
  if (legendElem) {
    legendElem.innerHTML = rows.map((r, i) => `
      <div class="flex items-center justify-between">
        <span class="flex items-center gap-2 text-slate-400"><span class="w-2.5 h-2.5 rounded-full" style="background:${DONUT_COLORS[i % DONUT_COLORS.length]}"></span>${r[labelKey]}</span>
        <span class="font-bold text-white">${Math.round((r[valueKey] / total) * 100)}%</span>
      </div>
    `).join('');
  }
  return instance;
}

async function loadAnalyticsData() {
  try {
    const d = await apiGet('/api/analytics');
    renderStatCards(d);
    renderFunnel(d.funnel || {});
    renderTrend(d.trend || []);
    analyticsReasonDonut = renderDonutChart(analyticsReasonDonut, 'reasonDonut', 'reason-legend', d.by_reason || [], 'failure_reason', 'cnt');
    analyticsStrategyDonut = renderDonutChart(analyticsStrategyDonut, 'strategyDonut', 'strategy-legend', d.by_strategy || [], 'strategy', 'cnt');
  } catch (e) {
    console.error(e);
  }
}

window.loadAnalyticsData = loadAnalyticsData;
loadAnalyticsData();
if (window.realtimeEngine) {
  window.realtimeEngine.subscribe(loadAnalyticsData);
}
