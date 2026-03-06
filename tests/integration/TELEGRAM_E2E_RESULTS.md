# ERPClaw Telegram E2E Test Results

**Date:** February 16, 2026
**Bot:** @MrStarkTheBot
**Server:** AWS Lightsail (44.230.107.142)
**Database:** Fresh init (167 tables, 445 indexes)
**Test Company:** Stark Industries (SI)

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 14 |
| Passed | 14 |
| Failed | 0 |
| Bugs Found & Fixed | 1 (Purchase Invoice SRNB) |

---

## Test Results

### T1: Company Setup (PASS)

**Action:** Set up Stark Industries with US GAAP chart of accounts.

| Component | Result |
|-----------|--------|
| Company | Stark Industries (SI) |
| Currency | USD |
| Chart of Accounts | US GAAP (94 accounts) |
| Fiscal Year | FY 2026 (Jan 1 - Dec 31) |
| Cost Center | Main |
| Warehouse | Main Warehouse |
| Naming Series | 38 document types |

**Skills tested:** erpclaw-setup

---

### T2: Master Data (PASS)

**Action:** Create items, customers, and suppliers.

| Entity | Details |
|--------|---------|
| Arc Reactor | Stock item, $5,000/ea |
| Consulting Services | Service item, $200/hr |
| Wayne Enterprises | Customer |
| Oscorp Industries | Supplier |

**Skills tested:** erpclaw-inventory, erpclaw-selling, erpclaw-buying

---

### T3: Procure-to-Pay (PASS)

**Action:** Full procurement cycle - PO, receipt, invoice.

| Document | Reference | Amount | Status |
|----------|-----------|--------|--------|
| Purchase Order | PO-2026-00001 | $60,000.00 | Submitted |
| Purchase Receipt | PR-2026-00001 | 20 units | SLE + GL posted |
| Purchase Invoice | PINV-2026-00001 | $60,000.00 | SRNB + AP posted |

**Result:** 20 Arc Reactors @ $3,000 each in stock. Oscorp owed $60,000.
**Skills tested:** erpclaw-buying

---

### T4: Order-to-Cash (PASS)

**Action:** Full sales cycle - SO, delivery, invoice.

| Document | Reference | Amount | Status |
|----------|-----------|--------|--------|
| Sales Order | SO-2026-00001 | $25,000.00 | Submitted |
| Delivery Note | DN-2026-00001 | 5 units | SLE + COGS posted |
| Sales Invoice | INV-2026-00001 | $25,000.00 | Revenue + AR posted |

**Result:** 15 Arc Reactors remaining. Wayne owes $25,000.
**Skills tested:** erpclaw-selling

---

### T5: Payments (PASS)

**Action:** Receive payment from customer, pay supplier.

| Payment | Reference | Amount | Status |
|---------|-----------|--------|--------|
| Wayne Enterprises (receive) | PAY-2026-00001 | $25,000.00 | Settled |
| Oscorp Industries (pay) | PAY-2026-00002 | $60,000.00 | Settled |

**Skills tested:** erpclaw-payments

---

### T6: Financial Reports (PASS)

**Action:** Trial balance, P&L, and balance sheet.

**Trial Balance:**
| Account | Debit | Credit |
|---------|-------|--------|
| Operating Checking | $25,000 | $60,000 |
| Trade Receivables | $25,000 | $25,000 |
| Raw Materials | $60,000 | $15,000 |
| Stock Received Not Billed | $60,000 | $60,000 |
| Trade Payables | $60,000 | $60,000 |
| Sales Revenue | - | $25,000 |
| COGS - Materials | $15,000 | - |
| **Totals** | **$245,000** | **$245,000** |

**P&L:** Revenue $25,000 | COGS $15,000 | Net Income $10,000 (40% margin)

**Skills tested:** erpclaw-reports, erpclaw-gl

---

### T7: HR - Department & Employees (PASS)

**Action:** Create HR department and add two employees with salary structures.

| Employee | Title | Start Date | Monthly Salary |
|----------|-------|------------|----------------|
| Tony Stark | CEO | Jan 1, 2026 | $15,000.00 |
| Pepper Potts | COO | Jan 1, 2026 | $12,000.00 |

**Also created:** Executive Management department, Executive Monthly salary structure.
**Skills tested:** erpclaw-hr

---

### T8: HR - Leave & Attendance (PASS)

**Action:** Submit leave request and mark attendance.

| HR Action | Details |
|-----------|---------|
| Leave Request | Pepper Potts, Feb 17-21 (5 days Paid Vacation), Approved |
| Attendance | Tony Stark, Feb 16, Present |
| Leave Balance | 15 of 20 days remaining |

**Skills tested:** erpclaw-hr

---

### T9: Manufacturing - BOM & Work Order (PASS)

**Action:** Create BOM and work order for Arc Reactor manufacturing.

**BOM (BOM-ARC-001):**
| Component | Qty per Unit | Rate | Amount |
|-----------|-------------|------|--------|
| Palladium Core | 2 | $500.00 | $1,000.00 |
| Vibranium Casing | 1 | $800.00 | $800.00 |
| **Total per unit** | | | **$1,800.00** |

**Work Order (WO-2026-00001):** 5 units, Feb 17-21, materials needed: 10 Palladium Cores + 5 Vibranium Casings.
**Skills tested:** erpclaw-manufacturing

---

### T10: Projects (PASS)

**Action:** Create project with tasks, assignments, and milestones.

**Project: Avengers Tower Construction (PROJ-2026-00001)**
| Field | Details |
|-------|---------|
| Timeline | Mar 1 - Jun 30, 2026 |
| Budget | $500,000.00 |
| Tasks | Foundation Work ($150K), Structural Assembly ($250K) |
| Assignment | Tony Stark → Foundation Work |
| Dependencies | Structural Assembly depends on Foundation Work |
| Milestones | Foundation Complete (Mar 31), Structure Complete (May 31) |

**Skills tested:** erpclaw-projects

---

### T11: Assets (PASS)

**Action:** Register fixed asset with depreciation schedule.

**Asset: CNC Milling Machine (ASSET-2026-00001)**
| Field | Details |
|-------|---------|
| Gross Value | $120,000.00 |
| Useful Life | 10 years |
| Method | Straight-Line |
| Monthly Depreciation | $1,000.00 |
| GL Accounts | Asset (1250), Expense (5260), Accumulated (1251) |
| Schedule | 120 months through Feb 2036 |

**Skills tested:** erpclaw-assets

---

### T12: Quality (PASS)

**Action:** Create inspection template and run quality inspection.

**Template: Arc Reactor QC**
| Parameter | Type | Criteria |
|-----------|------|----------|
| Power Output | Numeric | Minimum 1,000 Watts |
| Casing Integrity | Pass/Fail | Must pass |

**Inspection (QI-2026-00001):** 20 units inspected, 18 passed, 2 failed (casing defects).
**Skills tested:** erpclaw-quality

---

### T13: Journal Entry (PASS)

**Action:** Manual adjusting journal entry for office supplies.

| Account | Debit | Credit |
|---------|-------|--------|
| 5240 - Office Supplies | $5,000.00 | - |
| 1112 - Operating Checking | - | $5,000.00 |

**Skills tested:** erpclaw-journals

---

### T14: Balance Sheet Verification (PASS)

**Action:** Full balance sheet after all transactions.

Assets = Liabilities + Equity. All accounts balanced.
**Skills tested:** erpclaw-reports

---

## Bug Found & Fixed

### Purchase Invoice GL: COGS vs SRNB

**Problem:** When a purchase invoice was created from a PO that had an associated purchase receipt, the invoice's GL posting debited the expense/COGS account instead of Stock Received Not Billed (SRNB). This caused COGS to be overstated by the full purchase amount ($60K), inflating expenses.

**Root Cause:** Two issues in `erpclaw-buying/scripts/db_query.py`:
1. The `create-purchase-invoice` action, when creating from a PO with submitted receipts, set `update_stock=0` but did not link the `purchase_receipt_id` on the invoice.
2. The `submit-purchase-invoice` action always debited the expense account regardless of whether a receipt existed.

**Fix:**
1. In `create_purchase_invoice()`: When creating from PO, auto-detect submitted receipts and set `purchase_receipt_id`.
2. In `submit_purchase_invoice()`: Check if invoice has a linked receipt; if so, debit SRNB instead of expense.

**Verification:** After fix, COGS correctly shows $15,000 (5 units x $3,000) instead of $75,000. SRNB fully cleared ($60K in from receipt, $60K out from invoice). P&L shows correct 40% gross margin.

---

## Skills Tested (14 of 14 deployed)

| Skill | Actions Tested | Status |
|-------|---------------|--------|
| erpclaw-setup | initialize-database, setup-company, add-chart-of-accounts, add-fiscal-year, add-cost-center, add-warehouse, add-naming-series | PASS |
| erpclaw-gl | GL posting (via other skills), period queries | PASS |
| erpclaw-journals | add-journal-entry, submit-journal-entry | PASS |
| erpclaw-payments | add-payment-entry, submit-payment-entry | PASS |
| erpclaw-tax | Tax template application (via invoices) | PASS |
| erpclaw-reports | trial-balance, profit-and-loss, balance-sheet | PASS |
| erpclaw-inventory | add-item, stock queries | PASS |
| erpclaw-selling | add-sales-order, submit-sales-order, add-delivery-note, submit-delivery-note, add-sales-invoice, submit-sales-invoice | PASS |
| erpclaw-buying | add-purchase-order, submit-purchase-order, create-purchase-receipt, submit-purchase-receipt, create-purchase-invoice, submit-purchase-invoice | PASS |
| erpclaw-manufacturing | add-bom, add-work-order | PASS |
| erpclaw-hr | add-department, add-employee, add-salary-structure, add-leave-request, mark-attendance | PASS |
| erpclaw-projects | add-project, add-task, add-milestone | PASS |
| erpclaw-assets | add-asset, add-depreciation-schedule | PASS |
| erpclaw-quality | add-inspection-template, add-quality-inspection | PASS |

## Test Environment

- **604 Part A (pytest) tests:** All green
- **14 Telegram E2E tests:** All green
- **40 integration tests:** All green
- **Total automated + E2E:** 658 tests passing
