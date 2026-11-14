# Decision note: how, when and where eliminations are created

## Decision

**Where.** Eliminations are ordinary posted journal entries in a separate
company, *Delta Group Consolidation* (USD), in a journal called Eliminations.
This company has no operations; it exists to hold the group adjustments.
The real companies' books are never touched, so every standard view filtered
to Delta US, Ukraine or Poland shows only their own transactions. The auditor
opens an elimination like any other entry: each line's partner is the company
whose balance it removes, its label names the counterparty, and the entry links
to the consolidation run that created it.

**When.** At period end, per month, when the controller clicks *Run
consolidation* (a monthly scheduled action can do the same). A run is
idempotent: running March again replaces March's eliminations instead of
adding to them, and the run refuses to proceed if the period is locked.

**How.** For each pair of group companies the run reads the intercompany
journal items (partner = the other company's partner), in USD:

1. *P&L elimination for the month*: seller's intercompany revenue against the
   buyer's intercompany cost. A document booked by one side only (Ukraine's
   31 March invoice, booked by Delta US on 2 April) goes to an intercompany
   clearing account.
2. *Balance sheet elimination at month end*, reversed on the 1st of the next
   month: seller's receivable against buyer's payable, and the loan against
   the borrowing. A payment booked by one side only (Delta US paid Poland on
   31 March, Poland recorded it on 1 April) is reclassified to *Cash in
   transit*; the document difference goes to the clearing account.
3. *Controls*: the clearing account must net to zero (shown on the run), and
   every earlier month's intercompany P&L must still be fully eliminated: a
   document dated in a month already consolidated stops the run and names the
   month to re-run. The translation reserve is the balancing figure, so the
   group balance sheet balances by construction; it is not a control.

Intercompany amounts are taken in USD from the documents themselves
(`amount_currency`), so eliminations are exact and need no tolerance.
Everything else is translated at average (P&L) and closing (balance sheet)
rates per period, with the difference in a translation reserve.

The group P&L and balance sheet are stored as a result of each run: one row
per report line and per column (each company in its own currency and in USD,
eliminations, group). Finance reads them in a pivot view and exports them
with standard Odoo export. Report lines map account codes to group lines, as
data the controller can change.

## Options rejected

| Option | Why rejected |
|---|---|
| Post eliminations in Delta US's books | Delta US's P&L would no longer show its real books, which breaks an explicit requirement. |
| Eliminate only inside the report (filter intercompany lines out of a query) | Nothing for the auditor to open; the adjustment is invisible and cannot be reviewed or reversed. |
| Eliminate in real time, when each intercompany invoice is posted | Cut-off, partial credit notes and payments in transit only make sense at period end; a per-document entry would be wrong at every month end where the two sides disagree. |
| Odoo Enterprise inter-company rules (auto-create the mirror bill) | Requires Enterprise; it also makes both sides book on the same date, hiding the 31 March / 2 April cut-off that Finance has to see. |
| Translate everything at the average rate and absorb the FX noise in eliminations | Intercompany amounts would differ by a few hundred dollars every month for purely technical reasons; using the USD document amount removes the noise. |
| A live SQL view as the group report | Always current, but the reported numbers could change after the controller signed them off; a stored result per run is reproducible and auditable. |
