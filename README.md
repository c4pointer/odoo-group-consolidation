# Group Consolidation for Odoo 20

An Odoo 20 Community module that shows group results for a multi-company,
multi-currency group as if it were one company. It eliminates intercompany
revenue, costs, balances and loans, translates each company into the group
currency, and shows a consolidated P&L and balance sheet for a chosen month
next to each company's own figures.

Two rules hold throughout:

- **Real books stay real.** Eliminations are posted only in a separate
  consolidation company. The books of the group companies are never written to,
  so their standard reports always show what they actually booked.
- **Every elimination is an ordinary journal entry.** An auditor opens it like
  any other entry: date, journal, accounts, partner and label.

The demo is Delta Group: Delta US Inc. (USD, parent, group currency), Delta
Ukraine LLC (UAH) and Delta Poland sp. z o.o. (PLN), January to April 2026.

## Install and run

### With Docker (recommended)

Requirements: Docker with the Compose plugin and GNU Make. Nothing else is
installed on the host; Odoo 20 Community and PostgreSQL 17 run from the official
images.

```bash
git clone https://github.com/c4pointer/odoo-group-consolidation.git
cd odoo-group-consolidation
make demo
```

`make demo` creates the database `delta`, installs the module with the Delta
Group demo data and starts Odoo. Open http://localhost:8020 and log in as
`admin` / `admin`. January and February are already consolidated; March is left
for you to run (see the five steps below). Run `make demo` again at any time to
start over from a clean database.

| Command | What it does |
|---|---|
| `make demo` | Recreate the demo database from scratch (one command) |
| `make bare` | Recreate an empty database, `delta_clean`, on port 8021 to install the module from Apps |
| `make demo-data DB=delta_clean` | Load the demo data into an existing database (one command) |
| `make tunnel` / `make tunnel-cf` | Share the demo publicly over SSH or a Cloudflare quick tunnel (see below) |
| `make test` | Install the module on a throw-away database and run its tests |
| `make up` / `make down` | Start / stop the containers (data is kept) |
| `make shell` | Odoo shell on the demo database |
| `make help` | List every target |

The ports can be changed: `ODOO_PORT=9000 ODOO_CLEAN_PORT=9001 make up`.

To install the module by hand and load the demo data separately:

1. `make bare` creates the empty database `delta_clean` (only `base`) and serves
   it on its own port. Open http://127.0.0.1:8021 and log in as `admin` /
   `admin`. (127.0.0.1 rather than localhost keeps its login apart from the demo's.)
2. Apps → remove the **Apps** filter → search "Consolidation" → install **Group
   Consolidation and Intercompany Eliminations**. No demo data is loaded.
3. `make demo-data DB=delta_clean` loads the Delta Group demo data with one
   command and restarts Odoo; reload the page. Installing **Group Consolidation:
   Delta Group demo data** from Apps does the same.

### Sharing it with a public link

`make tunnel` opens an SSH tunnel to [localhost.run](https://localhost.run) and
prints a public https address for the demo (`make tunnel TUNNEL_PORT=8021` for
the empty database). It needs only `ssh` and lives while the command runs; the
free address changes from time to time, so send the current one. Both Odoo
servers run with the database manager and database list turned off, so the
link exposes the application only; anyone with it can log in with the demo
login, so close the tunnel (Ctrl+C) when done.

`make tunnel-cf` does the same with a Cloudflare quick tunnel: its
`https://….trycloudflare.com` address does not change while the command runs.
It needs the `cloudflared` binary on the PATH (one file from
[github.com/cloudflare/cloudflared](https://github.com/cloudflare/cloudflared/releases),
no account).

### Into an existing Odoo 20

1. Copy `addons/account_group_consolidation` into a directory on the Odoo
   addons path. It depends only on `account`; nothing from Enterprise.
2. Apps → Update Apps List, then install **Group Consolidation and
   Intercompany Eliminations**.
3. Optional, on an empty database only: also copy
   `addons/account_group_consolidation_demo` and install **Group Consolidation:
   Delta Group demo data**. It creates the four Delta companies, their charts of
   accounts and all demo documents.

Without the demo, create a company for the eliminations (in the group currency,
with a general journal, a clearing account and a cash in transit account), then
a consolidation group under Invoicing → Configuration → Consolidation. The
controller needs **Show Full Accounting Features** (Settings → Users → the user →
Accounting) to see journal items; in Odoo 20 the accounting Administrator role
does not include it. The demo gives it to `admin`.

### Tests

`make test` installs the module on a fresh database and runs 56 tests; it exits
non-zero when any test fails. The tests compare balances and elimination amounts
with figures computed by hand in [`docs/expected_numbers.md`](docs/expected_numbers.md),
not screens. They cover the cut-off (31 March vs 2 April), the payment in
transit (31 March vs 1 April), the partial credit note, the USD loan to a UAH
company, the translation reserve, and the run's refusals (locked period, months
out of order, missing rate, unmapped account, a document changed in a closed month).
They also cover a fourth company (EUR) joining after two months are closed, an
intercompany invoice in a third currency, a payment moved out of a closed month,
and the rates of a closed month being locked.

## Standard Odoo mechanisms used, and what was added

**Used as they are:**

| Mechanism | How it is used |
|---|---|
| Multi-company, one database | Each Delta company keeps its own books, currency and chart; the consolidation company is one more company |
| Journal entries (`account.move`) | Eliminations are ordinary posted entries in a general journal of the consolidation company |
| Entry reversal | Balance sheet eliminations are reversed on the 1st of the next month with Odoo's own reversal, linked to the original |
| `amount_currency` on journal items | Intercompany documents are in USD, so their USD amount is eliminated exactly, with no rate rounding |
| Lock dates | A locked month in the consolidation company cannot be run or reset again |
| Access rights and multi-company record rules (`ir.access`) | Readers and managers come from the accounting groups; every record belongs to the consolidation company |
| Pivot and list views | The consolidated report is a pivot: report lines down, one column per company plus eliminations, the total is the group |
| Scheduled action (`ir.cron`) | Optionally consolidates the previous month on the 1st |
| Odoo test framework | `TransactionCase` tests against the hand-computed figures |

**Added on top:**

| Addition | What it does |
|---|---|
| Consolidation group | Member companies, the consolidation company, its journal, clearing and cash in transit accounts, the first month, and average and closing rates per month |
| Report lines | The mapping from accounts to report lines, as data: account code prefixes and a partner scope (external, group companies, any). A controller can add or change a line without code |
| Consolidation run | One month of one group: reads each company's books, translates them (P&L at the average rate, balance sheet at closing, USD items at their USD amount, translation reserve as the balancing figure), posts the eliminations per pair of companies and stores the results |
| Controls | Clearing balance (must be zero) and, per pair, the timing difference and cash in transit that explain why the two sides did not match. A month does not run if the books of the latest closed month changed after it closed, and the rates of a closed month are locked until it is reset |
| Link from entry to run | Each elimination entry shows the run and whether it is a P&L or balance sheet elimination |

How, when and where eliminations are created, and the options rejected, are in
[`docs/DECISION.md`](docs/DECISION.md).

## Checking the group results: five steps for a controller

Log in as `admin`. Odoo opens Delta US Inc.; in the company switcher at the top
right, also tick Delta Ukraine LLC, Delta Poland sp. z o.o. and Delta Group
Consolidation. The figures below are for the demo data, March 2026, in USD.

1. **Check the rates.** Invoicing → Configuration → Consolidation →
   Consolidation groups → Delta Group, tab **Rates**. Each month has an average
   rate (used for the P&L) and a closing rate (used for the balance sheet) for
   UAH and PLN, as units per 1 USD. For March: UAH 42.00 average and 43.00
   closing; PLN 4.00 average and 3.90 closing.

2. **Run the month.** Invoicing → Reporting → Consolidation → Consolidation
   runs → **New**. Choose Delta Group and March 2026, then press **Run
   consolidation**. Months close in order; if Odoo refuses, the message names
   the month to run or reset first. The status turns to Done.

3. **Read the controls on the run.** **Clearing balance** must be 0.00; anything
   else is an unexplained intercompany difference. The table below it explains
   each pair of companies: Delta US and Delta Ukraine differ by a 50,000.00
   timing difference (Ukraine's invoice of 31 March, booked by Delta US on
   2 April); Delta US and Delta Poland by 40,000.00 cash in transit (paid on
   31 March, received on 1 April).

4. **Read the group results.** Press **Report** on the run; Invoicing →
   Reporting → Consolidation → Consolidated report opens the same report for the
   latest closed month. Rows are grouped into Profit and loss, Assets, and
   Liabilities and equity, each with its
   subtotal; each column is a company in USD, the Delta Group Consolidation
   column shows the eliminations, and the last column (**Total**) is the group.
   Read the section subtotals, not the top Total row, which adds the sections
   together. Intercompany revenue, costs, receivables, payables and loans are
   0.00 in the group column. March group profit is 227,500.00, and assets and
   liabilities and equity are both 2,152,450.80. For the year to date, open
   Measures and add **Year to date**.

5. **Open an elimination as an auditor.** Press **Eliminations** on the run.
   Each entry is in the Delta Group Consolidation company, journal
   Eliminations; the label names the counterparty and the partner is the
   company whose balance is removed. Balance sheet eliminations are dated
   31 March and reversed on 1 April; P&L eliminations are not reversed. Then
   open Invoicing → Review → Control → Journal Items, filter on the journal
   Eliminations and group by company: only Delta Group Consolidation appears.
   The books of Delta US, Ukraine and Poland are untouched.

## Documents

| Document | What it holds |
|---|---|
| [`docs/DECISION.md`](docs/DECISION.md) | How, when and where eliminations are created; options rejected and why (one page) |
| [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) | Everything the task did not say, one line each |
| [`docs/expected_numbers.md`](docs/expected_numbers.md) | Expected figures computed by hand from the scenario; the tests' oracle |
| [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md) | How the AI harness works, which parts the AI did and how they were verified |

## Repository layout

```
addons/account_group_consolidation/        the module
  models/                                  group, rates, report lines, runs, results
  data/                                    default report lines, scheduled action
  scenario/delta.py                        the Delta Group scenario, shared by demo and tests
  tests/                                   tests against the hand-computed figures
addons/account_group_consolidation_demo/   one-command demo data
docs/                                      decision note, assumptions, oracle, AI workflow
.claude/                                   AI harness: hooks and settings
CLAUDE.md                                  instructions for the AI agent
```
