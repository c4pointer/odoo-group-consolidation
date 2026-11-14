# Expected numbers — the test oracle

Computed by hand from the scenario below, before any module code exists.
Automated tests compare the module's output with these figures. This file is
human-owned: the AI agent is blocked from editing it.

Precision: every figure is rounded to 0.01 per report line; tests allow
±0.01 per line. The translation reserve is the balancing figure, so the
balance sheet always balances to the cent.

## 1. Exchange rates (fictional, round numbers chosen for hand-checking)

Units of local currency per 1 USD.

| Period | UAH average | UAH closing | PLN average | PLN closing |
|---|---:|---:|---:|---:|
| Jan 2026 | 40.00 | 41.00 | 4.00 | 4.00 |
| Feb 2026 | 41.00 | 42.00 | 4.00 | 4.00 |
| Mar 2026 | 42.00 | 43.00 | 4.00 | 3.90 |
| Apr 2026 | 43.00 | 44.00 | 3.90 | 3.90 |

Rates in Odoo: one rate per month end (31 Dec 2025: UAH 40.00, PLN 4.00;
then each closing rate above). Odoo 20 applies a rate from the day after its
date, so every transaction in a month, including one dated the last day, is
booked at the previous month-end rate. That rate is also the month's average.

## 2. Transactions

### Delta US Inc. (USD)

| Date | Document | Amount USD |
|---|---|---:|
| 01 Jan | Share capital from external shareholders, to bank | 1,000,000.00 |
| 15 Jan | Loan to Delta Ukraine, from bank | 200,000.00 |
| 25 Jan / 25 Feb / 25 Mar | External customer invoices | 300,000.00 / 320,000.00 / 350,000.00 |
| 25 Jan / 25 Feb / 25 Mar | External vendor bills | 20,000.00 each |
| 31 Jan / 28 Feb / 31 Mar | Payroll accrual | 80,000.00 each |
| 31 Jan / 28 Feb | Vendor bills from Delta Ukraine | 40,000.00 / 45,000.00 |
| **02 Apr** | Vendor bill from Delta Ukraine (UA invoice of 31 Mar) | 50,000.00 |
| 31 Jan / 28 Feb / 31 Mar | Vendor bills from Delta Poland | 20,000.00 / 22,000.00 / 25,000.00 |
| 15 Mar | Vendor credit note from Delta Poland on the February bill | 2,000.00 |
| **31 Mar** | Payment to Delta Poland (January bill + February bill net of credit note) | 40,000.00 |

### Delta Ukraine LLC (UAH)

| Date | Document | USD | UAH |
|---|---|---:|---:|
| 15 Jan | Loan from Delta US, received on the USD bank account (rate 40.00) | 200,000.00 | 8,000,000.00 |
| 15 Jan / 15 Feb / 15 Mar | External customer invoices | | 400,000.00 / 410,000.00 / 420,000.00 |
| 15 Jan / 15 Feb / 15 Mar | External vendor bills (office rent) | | 200,000.00 / 205,000.00 / 210,000.00 |
| 31 Jan / 28 Feb / 31 Mar | Payroll accrual | | 1,200,000.00 / 1,230,000.00 / 1,260,000.00 |
| 31 Jan | Invoice to Delta US (rate 40.00) | 40,000.00 | 1,600,000.00 |
| 28 Feb | Invoice to Delta US (rate 41.00) | 45,000.00 | 1,845,000.00 |
| **31 Mar** | Invoice to Delta US (rate 42.00) | 50,000.00 | 2,100,000.00 |

### Delta Poland sp. z o.o. (PLN)

| Date | Document | USD | PLN |
|---|---|---:|---:|
| 15 Jan / 15 Feb / 15 Mar | External customer invoices | | 200,000.00 each |
| 15 Jan / 15 Feb / 15 Mar | External vendor bills | | 40,000.00 each |
| 31 Jan / 28 Feb / 31 Mar | Payroll accrual | | 150,000.00 each |
| 31 Jan | Invoice to Delta US (rate 4.00) | 20,000.00 | 80,000.00 |
| 28 Feb | Invoice to Delta US (rate 4.00) | 22,000.00 | 88,000.00 |
| 15 Mar | Credit note to Delta US on the February invoice (rate 4.00) | 2,000.00 | 8,000.00 |
| 31 Mar | Invoice to Delta US (rate 4.00) | 25,000.00 | 100,000.00 |
| **01 Apr** | Receipt from Delta US on the USD bank account (rate 3.90), matched to January and February | 40,000.00 | 156,000.00 |

The receipt of 01 Apr settles invoices booked at 80,000 + 88,000 − 8,000 =
160,000 PLN with 156,000 PLN, so Odoo books a **realised exchange loss of
PLN 4,000** in April (two exchange difference entries of PLN 2,000).

## 3. Translation rule

- P&L lines: monthly average rate of the month in which they were booked.
- Balance sheet lines: closing rate of the reporting month.
- Share capital: historical rate (Delta US only, already USD).
- **Lines denominated in USD (the group currency) are taken at their USD
  amount**, not re-translated. This keeps every intercompany amount exact,
  and equals closing-rate translation after remeasurement. Balance sheet
  lines in USD always use the USD amount, even when it is zero (an exchange
  difference does not change what is owed in USD). P&L lines use it only
  when it is not zero; exchange differences carry no USD amount, so they are
  translated from local currency at the average rate.
- Translation reserve (CTA) = translated net assets − translated equity.

## 4. Standalone results, own currency

### Profit and loss, March 2026

| Line | Delta US (USD) | Delta Ukraine (UAH) | Delta Poland (PLN) |
|---|---:|---:|---:|
| External revenue | 350,000.00 | 420,000.00 | 200,000.00 |
| Intercompany revenue | 0.00 | 2,100,000.00 | 92,000.00 |
| Intercompany services cost | −23,000.00 | 0.00 | 0.00 |
| Payroll | −80,000.00 | −1,260,000.00 | −150,000.00 |
| Other external costs | −20,000.00 | −210,000.00 | −40,000.00 |
| **Net profit** | **227,000.00** | **1,050,000.00** | **102,000.00** |

Poland's March intercompany revenue: 100,000 invoice − 8,000 credit note.
Delta US's March intercompany cost: 25,000 from Poland − 2,000 credit note;
nothing from Ukraine, because Delta US books Ukraine's March invoice on 2 April.

### Balance sheet, 31 March 2026

| Line | Delta US (USD) | Delta Ukraine (UAH) | Delta Poland (PLN) |
|---|---:|---:|---:|
| Bank | 760,000.00 | 8,000,000.00 | 0.00 |
| External trade receivables | 970,000.00 | 1,230,000.00 | 600,000.00 |
| Intercompany receivables | 0.00 | 5,545,000.00 | 260,000.00 |
| Intercompany loan receivable | 200,000.00 | 0.00 | 0.00 |
| **Total assets** | **1,930,000.00** | **14,775,000.00** | **860,000.00** |
| External trade payables | 60,000.00 | 615,000.00 | 120,000.00 |
| Salaries payable | 240,000.00 | 3,690,000.00 | 450,000.00 |
| Intercompany payables | 110,000.00 | 0.00 | 0.00 |
| Intercompany loan payable | 0.00 | 8,000,000.00 | 0.00 |
| Share capital | 1,000,000.00 | 0.00 | 0.00 |
| Profit, January–March | 520,000.00 | 2,470,000.00 | 290,000.00 |
| **Total liabilities and equity** | **1,930,000.00** | **14,775,000.00** | **860,000.00** |

Delta US intercompany payables: 85,000 to Ukraine (January + February) and
25,000 to Poland (65,000 billed net − 40,000 paid).

## 5. Translated to USD

### Profit and loss in USD, by month

| | Jan | Feb | Mar | Jan–Mar |
|---|---:|---:|---:|---:|
| Delta US | 140,000.00 | 153,000.00 | 227,000.00 | 520,000.00 |
| Delta Ukraine | 15,000.00 | 20,000.00 | 25,000.00 | 60,000.00 |
| Delta Poland | 22,500.00 | 24,500.00 | 25,500.00 | 72,500.00 |
| **Sum of companies** | **177,500.00** | **197,500.00** | **277,500.00** | **652,500.00** |

Delta Ukraine, March: external revenue 420,000 / 42 = 10,000; intercompany
revenue 50,000 (USD amount); payroll 1,260,000 / 42 = 30,000; rent
210,000 / 42 = 5,000; net 25,000.

### Balance sheet in USD, 31 March 2026 (closing rates 43.00 and 3.90)

| Line | Delta Ukraine | Delta Poland |
|---|---:|---:|
| Bank (USD account, USD amount) | 200,000.00 | 0.00 |
| External trade receivables | 28,604.65 | 153,846.15 |
| Intercompany receivables (USD amount) | 135,000.00 | 65,000.00 |
| External trade payables | 14,302.33 | 30,769.23 |
| Salaries payable | 85,813.95 | 115,384.62 |
| Intercompany loan payable (USD amount) | 200,000.00 | 0.00 |
| Net assets | 63,488.37 | 72,692.30 |
| Profit, January–March, at average rates | 60,000.00 | 72,500.00 |
| **Translation reserve** | **3,488.37** | **192.30** |

## 6. Eliminations

### Profit and loss eliminations (posted per month, never reversed)

| Month | Pair | Seller revenue | Buyer cost | Difference to IC clearing |
|---|---|---:|---:|---:|
| Jan | Ukraine → US | 40,000.00 | 40,000.00 | 0.00 |
| Jan | Poland → US | 20,000.00 | 20,000.00 | 0.00 |
| Feb | Ukraine → US | 45,000.00 | 45,000.00 | 0.00 |
| Feb | Poland → US | 22,000.00 | 22,000.00 | 0.00 |
| **Mar** | **Ukraine → US** | **50,000.00** | **0.00** | **50,000.00** |
| Mar | Poland → US | 23,000.00 | 23,000.00 | 0.00 |

### Balance sheet eliminations at 31 March (reversed on 1 April)

| Pair | Seller receivable | Buyer payable | Cash in transit | IC clearing |
|---|---:|---:|---:|---:|
| Ukraine → US, trade | 135,000.00 | 85,000.00 | 0.00 | 50,000.00 |
| Poland → US, trade | 65,000.00 | 25,000.00 | **40,000.00** | 0.00 |
| US → Ukraine, loan | 200,000.00 | 200,000.00 | 0.00 | 0.00 |

Cash in transit = (seller documents − buyer documents) − (seller receivable −
buyer payable). For Poland: (65,000 − 65,000) − (65,000 − 25,000) = −40,000,
i.e. 40,000 has left Delta US and has not yet reached Delta Poland.

**Control: the IC clearing account nets to zero.** P&L eliminations put
50,000 in (credit); the balance-sheet elimination takes 50,000 out (debit).
A non-zero clearing balance means an unexplained intercompany difference.

## 7. Group results in USD

### Group profit and loss

| | Jan | Feb | **Mar** | Jan–Mar |
|---|---:|---:|---:|---:|
| External revenue | 360,000.00 | 380,000.00 | **410,000.00** | 1,150,000.00 |
| Intercompany revenue | 0.00 | 0.00 | **0.00** | 0.00 |
| Intercompany services cost | 0.00 | 0.00 | **0.00** | 0.00 |
| Payroll | −147,500.00 | −147,500.00 | **−147,500.00** | −442,500.00 |
| Other external costs | −35,000.00 | −35,000.00 | **−35,000.00** | −105,000.00 |
| **Net profit** | **177,500.00** | **197,500.00** | **227,500.00** | **602,500.00** |

March check: sum of companies 277,500 − Ukraine's March invoice 50,000 =
227,500 = external revenue 410,000 − external costs 182,500.

### Group balance sheet, 31 March 2026

| Line | Sum of companies | Eliminations | **Group** |
|---|---:|---:|---:|
| Bank | 960,000.00 | 0.00 | **960,000.00** |
| Cash in transit | 0.00 | 40,000.00 | **40,000.00** |
| External trade receivables | 1,152,450.80 | 0.00 | **1,152,450.80** |
| Intercompany receivables | 200,000.00 | −200,000.00 | **0.00** |
| Intercompany loan receivable | 200,000.00 | −200,000.00 | **0.00** |
| **Total assets** | **2,512,450.80** | **−360,000.00** | **2,152,450.80** |
| External trade payables | 105,071.56 | 0.00 | **105,071.56** |
| Salaries payable | 441,198.57 | 0.00 | **441,198.57** |
| Intercompany payables | 110,000.00 | −110,000.00 | **0.00** |
| Intercompany loan payable | 200,000.00 | −200,000.00 | **0.00** |
| Share capital | 1,000,000.00 | 0.00 | **1,000,000.00** |
| Profit, January–March | 652,500.00 | −50,000.00 | **602,500.00** |
| Translation reserve | 3,680.67 | 0.00 | **3,680.67** |
| **Total liabilities and equity** | **2,512,450.80** | **−360,000.00** | **2,152,450.80** |

Control: bank + cash in transit = 1,000,000 = the share capital, the only
cash that entered the group from outside. The loan and the payment only
moved cash between group companies.

## 8. April (cut-off and in-transit items unwind)

- Delta US books Ukraine's March invoice on 2 April: April P&L elimination
  removes 50,000 of intercompany cost.
- Delta Poland books the 40,000 receipt on 1 April at 3.90 and a realised
  exchange loss of PLN 4,000, translated at 3.90 = USD 1,025.64. Under
  IAS 21.45 an exchange difference on an intercompany monetary item is
  **not** eliminated: it stays in the group P&L, and the translation reserve
  absorbs the other side.
- Group April profit = −50,000 (Delta US) + 50,000 (elimination) −
  1,025.64 (Delta Poland) = **−1,025.64** (no other April activity in the demo).
- At 30 April cash in transit is 0.00, and every intercompany receivable
  equals its payable in USD: Ukraine → US 135,000; Poland → US 25,000.
- Over January–April the Ukraine → US eliminations are 135,000 of revenue
  and 135,000 of cost; the timing difference has fully reversed.
