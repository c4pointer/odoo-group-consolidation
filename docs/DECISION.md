# Decision note: how, when and where eliminations are created

## Decision

**Where.** Eliminations are ordinary posted journal entries in a separate
company, *Delta Group Consolidation* (USD), journal Eliminations. The real
companies' books are never touched, so their standard reports show only what
they booked. An auditor opens an elimination like any other entry: each line's
partner is the company whose balance it removes, the label names the
counterparty, and the entry links to the run that created it.

**When.** Per month, at period end, when the controller presses *Run
consolidation* (a scheduled action can do it on the 1st). Months close in
order. Running a month again replaces its eliminations instead of adding to
them; a lock date stops it.

**How.** For each pair of group companies the run reads their intercompany
journal items (partner = the other company), in USD:

1. *P&L, per month, never reversed*: the seller's revenue against the buyer's
   cost. A document booked by one side only (Ukraine's 31 March invoice, booked
   by Delta US on 2 April) goes to an intercompany clearing account.
2. *Balance sheet, at month end, reversed on the 1st*: receivable against
   payable, the loan against the borrowing. A payment booked by one side only
   (paid by Delta US on 31 March, received by Poland on 1 April) becomes
   *Cash in transit*.
3. *Controls*: the clearing account must net to zero, and a month runs only
   if the books of the latest closed month have not changed since it closed.

Intercompany amounts come from the documents' USD amount (`amount_currency`),
so they eliminate exactly. Everything else is translated at the average rate
(P&L) and the closing rate (balance sheet); the difference is the translation
reserve.

Each run stores the group P&L and balance sheet: one row per report line and
column (each company, eliminations). Finance reads them in a pivot and exports
them with standard Odoo export. Report lines map account codes to group lines
as data a controller can change.

## Options rejected

| Option | Why rejected |
|---|---|
| Post eliminations in Delta US's books | Delta US's P&L would stop showing its real books, an explicit requirement. |
| Eliminate only inside the report query | Nothing for the auditor to open, review or reverse. |
| Eliminate when each intercompany invoice is posted | Cut-off, credit notes and cash in transit only make sense at period end. |
| Enterprise inter-company rules (mirror bills) | Needs Enterprise, and books both sides on one date, hiding the 31 March / 2 April cut-off. |
| Translate intercompany items at the average rate | Both sides would differ by a few hundred dollars each month for technical reasons. |
| A live SQL view as the group report | Signed-off figures could change later; a stored result per run is reproducible. |
