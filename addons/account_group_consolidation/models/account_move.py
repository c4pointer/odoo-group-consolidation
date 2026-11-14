from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    consolidation_run_id = fields.Many2one(
        "account.consolidation.run",
        string="Consolidation run",
        readonly=True,
        copy=False,
        index="btree_not_null",
        ondelete="restrict",
        help="The consolidation run that created this elimination entry.",
    )
    consolidation_kind = fields.Selection(
        [("pl", "Profit and loss elimination"), ("bs", "Balance sheet elimination")],
        readonly=True,
        copy=False,
    )
