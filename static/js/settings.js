const TABS = [
  { key: 'rules', label: 'Recovery Rules' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'integrations', label: 'Integrations' },
  { key: 'general', label: 'General' },
];

const RULE_TOGGLES = [
  { key: 'auto_analyze_failed_payments', title: 'Automatically analyze failed payments', sub: 'AI will analyze every failed payment automatically' },
  { key: 'prioritize_high_value', title: 'Prioritize high-value customers', sub: 'Focus recovery efforts on customers with higher lifetime value' },
  { key: 'automated_reminders', title: 'Automatically send reminders', sub: 'Send automated reminders to customers' },
  { key: 'automated_recovery_actions', title: 'Automatically create recovery actions', sub: 'Let AI create and execute recovery actions' },
];

const NOTIFICATION_TOGGLES = [
  { key: 'notify_email', title: 'Email notifications', sub: 'Get notified by email about recovery activity' },
  { key: 'notify_sms', title: 'SMS notifications', sub: 'Get a text when a high-value recovery succeeds' },
  { key: 'notify_slack', title: 'Slack notifications', sub: 'Post recovery updates to a Slack channel' },
];

let settings = {};

function renderTabs() {
  const tabsWrap = document.getElementById('tabs');
  if (!tabsWrap) return;
  tabsWrap.innerHTML = TABS.map((t, i) => `
    <button data-key="${t.key}" class="tab-btn ${i === 0 ? 'active' : ''}">${t.label}</button>
  `).join('');
  document.querySelectorAll('#tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#tabs .tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('[data-panel]').forEach(p => p.classList.add('hidden'));
      const targetPanel = document.querySelector(`[data-panel="${btn.dataset.key}"]`);
      if (targetPanel) targetPanel.classList.remove('hidden');
    });
  });
}

function toggleRow(def) {
  const isOn = settings[def.key] === 'true';
  return `
    <div class="flex items-center justify-between py-2">
      <div>
        <p class="text-[13px] font-semibold text-slate-200">${def.title}</p>
        <p class="text-[11.5px] text-slate-400">${def.sub}</p>
      </div>
      <div class="toggle ${isOn ? 'on' : ''}" data-key="${def.key}" onclick="toggleEl(this)"><div class="knob"></div></div>
    </div>
  `;
}

function toggleEl(el) {
  el.classList.toggle('on');
}
window.toggleEl = toggleEl;

const TEXT_SETTING_KEYS = [
  'minimum_payment_amount', 'maximum_recovery_attempts', 'recovery_score_threshold', 'retry_after_hours',
  'razorpay_key_id', 'razorpay_key_secret', 'razorpay_webhook_secret', 'gemini_api_key',
  'business_name', 'admin_email', 'cost_per_recovery_attempt',
];

function fillInputs() {
  TEXT_SETTING_KEYS.forEach(key => {
    const el = document.getElementById(key);
    if (el && settings[key] !== undefined) el.value = settings[key];
  });
}

async function loadSettings() {
  settings = await apiGet('/api/settings');
  const rulesElem = document.getElementById('toggle-rules');
  if (rulesElem) rulesElem.innerHTML = RULE_TOGGLES.map(toggleRow).join('');
  const notifElem = document.getElementById('toggle-notifications');
  if (notifElem) notifElem.innerHTML = NOTIFICATION_TOGGLES.map(toggleRow).join('');
  fillInputs();
  if (window.lucide) lucide.createIcons();
}

const saveBtn = document.getElementById('save-btn');
if (saveBtn) {
  saveBtn.addEventListener('click', async () => {
    const payload = {};
    document.querySelectorAll('.toggle[data-key]').forEach(t => {
      payload[t.dataset.key] = t.classList.contains('on') ? 'true' : 'false';
    });
    TEXT_SETTING_KEYS.forEach(key => {
      const el = document.getElementById(key);
      if (el) payload[key] = el.value;
    });
    const original = saveBtn.textContent;
    saveBtn.textContent = 'Saving...';
    try {
      await apiPost('/api/settings', payload);
      showToast('Settings saved successfully', 'success');
      saveBtn.textContent = 'Saved ✓';
    } catch(e) {
      showToast('Failed to save settings: ' + e.message, 'warning');
    } finally {
      setTimeout(() => (saveBtn.textContent = original), 1500);
    }
  });
}

renderTabs();
loadSettings();
