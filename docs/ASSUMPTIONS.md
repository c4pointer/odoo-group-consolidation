# Assumptions

Where the task does not say, this is what was assumed. One line each.

## Group and periods

1. The year is 2026; demo data covers January to April, and the main check is March 2026.
2. The group is one level deep: Delta US owns 100% of Delta Ukraine and Delta Poland; there are no minority interests.
3. All companies start on 1 January 2026 with no opening balances.
4. Delta US is funded by USD 1,000,000 of share capital from external shareholders on 1 January; the subsidiaries have no share capital in the demo, so the investment-versus-equity elimination is out of scope.
5. Consolidation runs per calendar month; the group P&L is shown for a month and year to date, the balance sheet at month end.

## Currencies and translation

6. Group reporting currency is USD.
7. P&L lines are translated at the monthly average rate and balance sheet lines at the closing rate, the difference going to a translation reserve in equity; share capital is translated at closing, correct here only because Delta US alone has any, in USD.
8. Lines in USD are taken at their USD amount (`amount_currency`), not re-translated, so intercompany amounts stay exact; exchange differences have no USD amount and are translated from local currency.
9. Average and closing rates are entered per period in the consolidation module, separately from Odoo's daily transaction rates.
10. Demo rates are fictional round numbers, one per month end; Odoo 20 applies a rate from the day after its date, so each month-end rate books the next month's transactions and is that month's average.
11. No unrealised FX revaluation is booked in the demo (Community has no revaluation wizard); realised exchange differences, such as Poland's on 1 April, stay in the group P&L, as IAS 21.45 requires.
12. Amounts are rounded to 0.01 per report line; the translation reserve is the balancing figure.

## Intercompany

13. An intercompany line is any journal item whose partner, or its commercial partner (a contact of the company), is another group company's partner (`res.company.partner_id`).
14. All intercompany invoices, credit notes, payments and the loan are in USD.
15. Intercompany services carry no VAT (cross-border B2B services; tax is out of scope).
16. The loan of USD 200,000 is interest-free and is not repaid in the period; Delta Ukraine receives it on a USD bank account.
17. Both sides book the partial credit note on the same day (15 March): USD 2,000 on Poland's February invoice.
18. Delta US pays Delta Poland USD 40,000 on 31 March (January bill plus February bill net of the credit note); Delta US pays nothing to Delta Ukraine in the period.
19. Intercompany differences are told apart by cause: a document booked by one side only (cut-off, timing), a payment booked by one side only (cash in transit), and a document both sides booked at different amounts (a dispute). Only the dispute is an error; it is reported with its documents for the company in the wrong to correct, as consolidation tools do (an Oracle HFM plug account, an SAP reason code), and does not stop the run.
20. Two documents are the same transaction when one's Reference is the other's number, Odoo's convention for a vendor bill and what Odoo's inter-company rules write; linked documents are compared as one group (an invoice booked as several bills), matching is exact on the number, and an unmatched document counts as timing.

## Eliminations

21. Eliminations are posted in a separate company, Delta Group Consolidation (USD), which has no operations of its own; real companies' books are never touched.
22. P&L eliminations are posted per month and are not reversed; balance sheet eliminations are posted at month end and reversed on the 1st of the next month.
23. Payment timing differences are reclassified to Cash in transit, a group asset.
24. Document timing differences and disputed amounts pass through an intercompany clearing account, each on lines of its own, and the account must net to zero; a non-zero balance is reported as an unexplained difference. Both sides are always eliminated in full (IFRS 10 B86), so a dispute leaves the group result right and only one company's own books wrong.
25. Eliminations are exact in USD, so no tolerance threshold is applied.

## Books and reporting

26. Odoo Community has no Profit and Loss report; "the standard P&L shows a company's real books" is read as: anything filtered to a real company (journal items, standard analyses) never shows eliminations.
27. All companies use Odoo's generic chart; report lines map account code prefixes and a partner scope (any, external, group companies) to group lines, the longest prefix winning, as data a controller can edit.
28. To keep the demo small, payroll is accrued and not paid, and external invoices and bills stay unpaid.
29. Intercompany payments are bank entries reconciled with the invoices (Community creates no entry for a payment without an outstanding account); Odoo 20 then labels the February invoices "Reversed", not "Paid", with no effect on balances.

## Running

30. Months close in order: a month runs only when every earlier month since the group's start date has run, and an earlier month runs again only after the later months are reset.
31. Running a month again replaces its eliminations and results; a lock date in the consolidation company stops it, and the scheduled action never re-runs a finished month.
32. A journal item on an account that no report line reads stops the run with the account codes, rather than being left out of the group figures.
33. Who may consolidate is set when the group is configured (Odoo links only companies the user can read); whoever reads the consolidation company reads every member's column, so it is for group controllers only.
34. A company joins by being added to the group with rates for its currency, with no code change, from its first month of trading; an acquisition with earlier history (goodwill, minority interest) is out of scope.
35. An intercompany document in a third currency (EUR, Delta Germany to Delta US) is translated by both sides at the group rate for that currency, so it eliminates exactly; a company's own rate difference goes to its translation reserve.
36. Each run fingerprints the member books it read; a later month runs only if the books of the latest closed month are unchanged, otherwise it names the month to reset. Report lines are outside the fingerprint.
37. The rates of a consolidated month cannot be changed or deleted until its run is reset. Adding a rate for another currency is allowed, as it cannot change a finished run.

## Demo data

38. The demo module creates its companies and posted documents in code, so uninstalling it removes nothing, and Odoo never deletes posted entries anyway; to start over, recreate the database with `make demo`.
