# CLAUDE.md — project instructions for the AI agent

## What this repository is

An Odoo 20 module, `account_group_consolidation`, built as a technical task.
Delta Group has three companies in one database, each with its own books and
currency: Delta US Inc. (USD, parent, group reporting currency), Delta Ukraine
LLC (UAH) and Delta Poland sp. z o.o. (PLN). Ukraine and Poland invoice Delta US
monthly in USD; Delta US lent Delta Ukraine USD 200,000 on 15 January.

The module produces group results in USD as if the group were one company:
it eliminates intercompany transactions and balances, and shows a consolidated
P&L and balance sheet for a chosen month next to each company's own results.

Non-negotiable business requirements:
- the standard P&L of each company always shows that company's real books,
  so eliminations are never posted into Delta US, Ukraine or Poland;
- every elimination is an ordinary journal entry an auditor can open.

## Hard rules

1. **Odoo 20 Community only.** The module depends on `account` and nothing
   from Enterprise. Reviewers must be able to install it from the README.
2. **English only** in everything committed: code, comments, docs, commit messages.
3. **The oracle is human-owned.** `docs/expected_numbers.md` and
   `addons/*/tests/expected_*.py` hold figures computed by hand from the
   scenario. A hook blocks edits to them. Never change a test's expected number
   to make it pass; if you believe the oracle is wrong, stop and explain why.
4. **Tests prove numbers, not screens.** Assert balances, totals and
   elimination amounts against the oracle. Cover the edge cases: cut-off
   (31 Mar vs 2 Apr), payment in transit (31 Mar vs 1 Apr), partial credit
   note, USD loan to a UAH company, translation difference.
5. **History is kept as it happened.** No squash, amend, rebase or force push.
   One small commit per logical step, only after `make lint` and `make test` pass
   (a deliberate red-test commit is allowed and must say so in the message).
6. **Configuration over hard-coding.** Intercompany partners, accounts and the
   consolidation company come from settings or data, never from literal ids or
   names in Python.

## Commands

| Command | What it does |
|---|---|
| `make up` / `make down` | Start / stop Odoo 20 + PostgreSQL 17 (http://localhost:8020) |
| `make demo` | Recreate database `delta` with the module and demo data |
| `make test` | Install the module on a fresh `delta_test` database and run its tests |
| `make harness` | Test the Claude Code hooks |
| `make lint` / `make fmt` | ruff check / auto-format |
| `make shell` | Odoo shell on `delta` |

`make test` exits non-zero when any test fails; trust its exit code.

## Workflow for every change

1. Plan first: state the goal, the files to touch and how it will be verified.
2. Write or update the assumption or decision in `docs/` when behaviour is not
   given by the task.
3. Write the test against the oracle and see it fail.
4. Implement until `make lint && make test` pass.
5. Ask for an independent review (a fresh subagent or `/code-review`), then
   the human reviews the diff before the commit.

## Domain glossary

- **Intercompany (IC)**: a transaction between two group companies; the
  counterpart partner is the other company's `res.company.partner_id`.
- **Elimination**: a consolidation entry that removes IC revenue/expense and
  IC receivable/payable (and the loan) from the group view.
- **Cut-off difference**: one side has booked a document, the other has not yet.
- **Cash in transit**: the payer has paid, the payee has not yet recorded it.
- **Translation**: balance sheet at the closing rate, P&L at the monthly
  average rate; the difference goes to a currency translation reserve (CTA).
- IC invoices are in USD, so `account.move.line.amount_currency` gives the
  exact USD amount to eliminate.

## Odoo 20 notes

- `account.account` is shared between companies (`company_ids` many2many).
- Demo data is not loaded by default: `--with-demo` on a new database, or
  `odoo module force-demo` on an existing one.
- Server source inside the container: `/usr/lib/python3/dist-packages/odoo`.
- Access rights and record rules are one model, `ir.access`, loaded from
  `security/ir.access.csv` (`id,name,model_id,group_id/id,operation,domain`):
  a row with a group grants `operation` (e.g. `r`, `crud`); a row without a group
  restricts with its domain. `ir.model.access` and `ir.rule` no longer exist.
- Account codes are company-dependent: read them with `account.with_company(company).code`.
- Model constraints are `models.Constraint("unique(...)", "message")` class attributes.
