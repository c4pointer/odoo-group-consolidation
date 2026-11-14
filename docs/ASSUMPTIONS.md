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
7. P&L lines are translated at the monthly average rate, balance sheet lines at the month-end closing rate, share capital at the historical rate; the difference goes to a translation reserve (CTA) in equity.
8. Lines denominated in USD are taken at their USD amount (`amount_currency`) and not re-translated; for monetary items this equals closing-rate translation after remeasurement, and it keeps intercompany amounts exact. Exchange differences carry no USD amount, so they are translated from local currency.
9. Average and closing rates are entered per period in the consolidation module, separately from Odoo's daily transaction rates.
10. Demo rates are fictional round numbers chosen so a controller can check the figures by hand; Odoo holds one rate per month end, and because Odoo 20 applies a rate from the day after its date, each month-end rate is used for the next month's transactions and serves as that month's average.
11. Unrealised FX revaluation is not booked in the demo (Community has no revaluation wizard); realised exchange differences (Poland's receipt on 1 April) and any revaluation a company books stay in the group P&L, as IAS 21.45 requires for intercompany monetary items.
12. Amounts are rounded to 0.01 per report line; the translation reserve is the balancing figure.

## Intercompany

13. An intercompany line is any journal item whose partner is another group company's partner (`res.company.partner_id`).
14. All intercompany invoices, credit notes, payments and the loan are in USD.
15. Intercompany services carry no VAT (cross-border B2B services; tax is out of scope).
16. The loan of USD 200,000 is interest-free and is not repaid in the period; Delta Ukraine receives it on a USD bank account.
17. Both sides book the partial credit note on the same day (15 March): USD 2,000 on Poland's February invoice.
18. Delta US pays Delta Poland USD 40,000 on 31 March (January bill plus February bill net of the credit note); Delta US pays nothing to Delta Ukraine in the period.
19. A difference between the seller's and the buyer's documents (cut-off) and a payment booked by one side only (cash in transit) are the only expected kinds of intercompany difference.

## Eliminations

20. Eliminations are posted in a separate company, Delta Group Consolidation (USD), which has no operations of its own; real companies' books are never touched.
21. P&L eliminations are posted per month and are not reversed; balance sheet eliminations are posted at month end and reversed on the 1st of the next month.
22. Payment timing differences are reclassified to Cash in transit, a group asset.
23. Document timing differences pass through an intercompany clearing account that must net to zero; a non-zero balance is reported as an unexplained difference.
24. Eliminations are exact in USD, so no tolerance threshold is applied.

## Books and reporting

25. Odoo Community has no Profit and Loss report; "the standard P&L shows a company's real books" is read as: anything filtered to a real company (journal items, standard analyses) never shows eliminations.
26. All companies use Odoo's generic chart of accounts; report lines are derived from the account type plus the intercompany flag.
27. To keep the demo small, payroll is accrued and not paid, and external invoices and bills stay unpaid.
28. Intercompany payments are recorded as bank journal entries reconciled with the invoices (Community creates no entry for a payment without an outstanding account). Odoo 20 then labels the February invoices, settled by the credit note plus such an entry, as "Reversed" rather than "Paid"; balances and residual amounts are unaffected.
