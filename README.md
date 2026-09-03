# RecoverAI — AI Revenue Recovery Agent

A 7-page SaaS dashboard (HTML + Tailwind CSS + vanilla JS, Flask + MySQL backend) that turns
Razorpay payment failures into recovered revenue.

```
Razorpay Payment Failure → AI Analysis → Recovery Score → AI Decision → Recovery Action → Revenue Recovered
```

## Pages

| # | Page | Route |
|---|------|-------|
| 1 | Dashboard | `/dashboard` |
| 2 | Failed Payments | `/failed-payments` |
| 3 | Customers | `/customers` |
| 4 | AI Recovery Agent | `/recovery-agent` |
| 5 | Recovery Campaigns | `/campaigns` |
| 6 | Analytics | `/analytics` |
| 7 | Settings | `/settings` |

All 7 share one sidebar (`templates/base.html`) that highlights the active page. Each page is a
thin server-rendered shell that hydrates itself from the JSON API (`/api/...`) using its own
script in `static/js/`.

## Stack

- **Frontend:** HTML + Tailwind CSS (CDN) + vanilla JS + Chart.js + Lucide icons — no build step.
- **Backend:** Flask (`app.py`) exposing page routes and a JSON API.
- **Database:** MySQL (`schema.sql` for tables, `seed.sql` for demo data matching the mockups).
- **Integrations (stubbed, ready to wire up):** Razorpay webhook endpoint (`/api/webhooks/razorpay`)
  and a Gemini-ready `score_payment()` function that currently uses a heuristic scorer — swap it
  for a real Gemini call once you add `GEMINI_API_KEY`.

## Setup

1. **Create the database**
   ```bash
   mysql -u root -p < schema.sql
   mysql -u root -p < seed.sql   # optional demo data
   ```

2. **Install dependencies**
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure connection** — either edit `config.py` defaults or export env vars:
   ```bash
   export MYSQL_HOST=localhost
   export MYSQL_USER=root
   export MYSQL_PASSWORD=yourpassword
   export MYSQL_DB=recoverai
   export RAZORPAY_KEY_ID=...
   export RAZORPAY_KEY_SECRET=...
   export RAZORPAY_WEBHOOK_SECRET=...
   export GEMINI_API_KEY=...
   ```

4. **Run**
   ```bash
   python3 app.py
   # http://localhost:5000
   ```

## API surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/dashboard` | Stat cards, 7-day trend, AI insights |
| GET | `/api/failed-payments` | Search/filter failed payments |
| GET | `/api/failed-payments/<id>` | Payment detail |
| POST | `/api/failed-payments/<id>/recover` | Trigger manual recovery |
| GET | `/api/customers` | Customer list + search |
| GET | `/api/customers/summary` | KPI cards |
| GET | `/api/customers/<id>` | Profile + payment history |
| GET | `/api/recovery-agent/queue` | Pending payments ranked by recovery score |
| GET | `/api/recovery-agent/<payment_id>` | Score, reasoning, strategy, activity timeline |
| POST | `/api/recovery-agent/<payment_id>/recover` | "Let AI Recover Now" |
| GET/POST | `/api/campaigns` | List / create campaigns |
| GET | `/api/analytics` | Funnel, trend, breakdowns, ROI |
| GET/POST | `/api/settings` | Recovery rules, notifications, integrations |
| POST | `/api/webhooks/razorpay` | Razorpay `payment.failed` webhook entry point |

## Wiring real Razorpay + Gemini

- Point your Razorpay webhook at `/api/webhooks/razorpay` (verify the signature with
  `RAZORPAY_WEBHOOK_SECRET` before trusting the payload — a TODO is left in `app.py`).
- Replace `score_payment()` in `app.py` with a call to the Gemini API using `GEMINI_API_KEY`,
  feeding it the customer history + failure context and asking for a score, strategy, and
  a drafted recovery message (JSON-structured output works well here).
