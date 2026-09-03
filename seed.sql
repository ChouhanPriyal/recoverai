USE recoverai;

-- ---------------------------------------------------------------------
-- Customers
-- ---------------------------------------------------------------------
INSERT INTO customers (name, email, phone, total_spent, successful_payments, failed_payments, avg_order, risk_level, repeat_customer, last_payment_at) VALUES
('Priya Sharma', 'priya@email.com', '+91 90000 10001', 42500, 14, 2, 3035, 'Low',    TRUE,  '2026-08-19 10:42:00'),
('Rahul Verma',  'rahul@email.com', '+91 90000 10002', 38160, 12, 3, 3180, 'Medium', TRUE,  '2026-08-19 09:15:00'),
('Aman Singh',   'aman@email.com',  '+91 90000 10003', 12990,  8, 3, 1623, 'High',   FALSE, '2026-08-18 08:50:00'),
('Sneha Patel',  'sneha@email.com', '+91 90000 10004', 65230, 16, 1, 4077, 'Low',    TRUE,  '2026-08-18 11:32:00'),
('Karan Mehta',  'karan@email.com', '+91 90000 10005', 21450, 10, 2, 2145, 'Medium', FALSE, '2026-08-18 07:45:00'),
('Neha Gupta',   'neha@email.com',  '+91 90000 10006', 18300,  7, 2, 2614, 'Medium', FALSE, '2026-08-18 06:20:00'),
('Vikram Raj',   'vikram@email.com','+91 90000 10007', 27650,  9, 3, 3072, 'High',   FALSE, '2026-08-18 05:05:00');

-- ---------------------------------------------------------------------
-- Failed payments
-- ---------------------------------------------------------------------
INSERT INTO payments (razorpay_payment_id, customer_id, amount, failure_reason, attempts, recovery_score, status, recovery_state, failed_at) VALUES
('pay_Qw12ErX9', 1, 2999, 'Bank Declined',          1, 91, 'High',   'Pending', '2026-08-19 10:42:00'),
('pay_Lk34PoY8', 2, 5499, 'Network Error',          2, 76, 'Medium', 'Pending', '2026-08-19 09:15:00'),
('pay_Zx56MnB2', 3, 1299, 'Authentication Failed',  3, 32, 'Low',    'Pending', '2026-08-18 08:50:00'),
('pay_Po98LmN3', 4, 8999, 'Bank Declined',          1, 94, 'High',   'Pending', '2026-08-18 11:32:00'),
('pay_Ax9OQpQ7', 5, 4499, 'Insufficient Funds',     2, 66, 'Medium', 'Pending', '2026-08-18 07:45:00'),
('pay_Bn23QwE1', 6, 2249, 'Bank Declined',          1, 89, 'High',   'Pending', '2026-08-18 06:20:00'),
('pay_Xc76UlM4', 7, 6499, 'Network Error',          2, 58, 'Medium', 'Pending', '2026-08-18 05:05:00');

-- ---------------------------------------------------------------------
-- AI Recovery Agent activity timeline (payment #1 — Priya Sharma)
-- ---------------------------------------------------------------------
INSERT INTO agent_activity (payment_id, activity, activity_type, created_at) VALUES
(1, 'Payment failed received from Razorpay', 'analysis', '2026-08-19 10:42:00'),
(1, 'Customer history analyzed',              'analysis', '2026-08-19 10:43:00'),
(1, 'Recovery probability calculated (91%)',   'analysis', '2026-08-19 10:43:30'),
(1, 'Best strategy selected: Payment Retry',   'decision', '2026-08-19 10:44:00'),
(1, 'Personalized message generated',          'action',   '2026-08-19 10:44:30'),
(1, 'Recovery action initiated',               'action',   '2026-08-19 10:45:00'),
(1, 'Waiting for customer payment...',         'message',  '2026-08-19 10:45:30');

-- ---------------------------------------------------------------------
-- AI recommendation for payment #1
-- ---------------------------------------------------------------------
INSERT INTO ai_recommendations (payment_id, strategy, reasoning, message_draft, confidence) VALUES
(1, 'Payment Retry',
 'Customer has strong payment history (14 successful out of 16). Only 1 previous failed attempt. High lifetime value customer. Failure reason is temporary (Bank Declined). 91% probability of successful recovery.',
 'Hi Priya, we noticed your last payment of ₹2,999 did not go through. Please retry using a different card or UPI — it only takes a minute.',
 91);

-- ---------------------------------------------------------------------
-- Campaigns
-- ---------------------------------------------------------------------
INSERT INTO campaigns (name, target_audience, strategy, customer_count, potential_revenue, recovered_revenue, status) VALUES
('High Value Recovery',   'Payments above ₹5,000', 'Payment Retry',    127, 812000, 306000, 'Running'),
('24h Reminder Campaign', 'Payments made < 24h',   'Smart Reminder',   249, 213000,  88000, 'Running'),
('Weekend Recovery',      'Weekend Failures',      'Reminder + Offer', 358, 154000,  54000, 'Completed'),
('Low Value Recovery',    'Payments under ₹1,000', 'Smart Reminder',   358, 268000,  42000, 'Running'),
('New Customer Recovery', 'First-time Failures',   'Personalized Retry',156, 126000,      0, 'Draft');
