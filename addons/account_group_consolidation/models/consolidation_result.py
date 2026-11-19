from odoo import fields, models


class AccountConsolidationResult(models.Model):
    """One report line of one column (a company or the eliminations) for one run.

    Stored rather than computed live, so the figures a controller signed off
    do not move afterwards. Read in the pivot view; the pivot total is the group.
    """

    _name = "account.consolidation.result"
    _description = "Consolidation result"
    _order = "run_id, sequence, column_company_id"

    run_id = fields.Many2one(
        "account.consolidation.run", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="run_id.company_id", store=True)
    date_to = fields.Date(related="run_id.date_to", store=True, string="Month end")
    line_id = fields.Many2one("account.consolidation.line", required=True, ondelete="cascade")
    code = fields.Char(related="line_id.code", store=True)
    section = fields.Selection(related="line_id.section", store=True)
    sequence = fields.Integer(related="line_id.sequence", store=True)
    column_company_id = fields.Many2one("res.company", string="Column", required=True)
    is_elimination = fields.Boolean(string="Eliminations")
    currency_id = fields.Many2one(related="column_company_id.currency_id", string="Currency")
    group_currency_id = fields.Many2one(related="run_id.currency_id", string="Group currency")
    local_amount = fields.Monetary(
        currency_field="currency_id",
        help="Own currency: the month for profit and loss, month end for the balance sheet.",
    )
    local_amount_ytd = fields.Monetary(currency_field="currency_id", string="Local, year to date")
    amount = fields.Monetary(
        currency_field="group_currency_id",
        string="Amount",
        help="Group currency: the month for profit and loss, month end for the balance sheet.",
    )
    amount_ytd = fields.Monetary(currency_field="group_currency_id", string="Year to date")


class AccountConsolidationDifference(models.Model):
    """Why a pair of companies did not match at month end."""

    _name = "account.consolidation.difference"
    _description = "Intercompany difference"
    _order = "run_id, first_company_id, second_company_id"

    run_id = fields.Many2one(
        "account.consolidation.run", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="run_id.company_id", store=True)
    currency_id = fields.Many2one(related="run_id.currency_id")
    first_company_id = fields.Many2one("res.company", required=True)
    second_company_id = fields.Many2one("res.company", required=True)
    timing_difference = fields.Monetary(
        help="Documents booked by one side only (cut-off), taken to the clearing account. "
        "Not an error: it reverses when the other side books the document.",
    )
    amount_difference = fields.Monetary(
        help="Documents booked by both sides at different amounts, matched by the buyer's "
        "reference being the seller's document number. Positive: the seller booked more. "
        "An error in one company's books, to be corrected there; it does not reverse by itself.",
    )
    disputed_documents = fields.Text(
        help="The matched documents whose amounts disagree, with each side's amount.",
    )
    cash_in_transit = fields.Monetary(
        help="Payments recorded by the payer and not yet by the payee.",
    )
