import logging

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountConsolidationGroup(models.Model):
    """Who is consolidated, where eliminations go, and at which rates."""

    _name = "account.consolidation.group"
    _description = "Consolidation group"
    _check_company_auto = True

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Consolidation company",
        required=True,
        help="Company that holds the elimination entries. It has no operations of its own; "
        "its currency is the group reporting currency.",
    )
    currency_id = fields.Many2one(related="company_id.currency_id", string="Group currency")
    member_company_ids = fields.Many2many(
        "res.company",
        string="Member companies",
        required=True,
        help="Companies whose books are consolidated. Intercompany lines are journal items "
        "whose partner is another member company.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Elimination journal",
        required=True,
        check_company=True,
        domain="[('type', '=', 'general')]",
    )
    clearing_account_id = fields.Many2one(
        "account.account",
        string="Intercompany clearing account",
        required=True,
        check_company=True,
        help="Takes the documents booked by one side only. Nets to zero at every month end.",
    )
    transit_account_id = fields.Many2one(
        "account.account",
        string="Cash in transit account",
        required=True,
        check_company=True,
        help="Takes payments recorded by the payer and not yet by the payee.",
    )
    start_date = fields.Date(
        required=True,
        help="First month consolidated. Each later month needs the previous one closed.",
    )
    auto_run = fields.Boolean(
        string="Run monthly",
        help="The scheduled action consolidates the previous month on the 1st.",
    )
    rate_ids = fields.One2many("account.consolidation.rate", "group_id", string="Rates")
    run_ids = fields.One2many("account.consolidation.run", "group_id", string="Runs")

    @api.constrains("company_id", "member_company_ids")
    def _check_companies(self):
        for group in self:
            if group.company_id in group.member_company_ids:
                raise ValidationError(
                    self.env._("The consolidation company cannot be a member company.")
                )

    def _member_by_partner(self):
        """Member company by its commercial partner; look items up by commercial partner too."""
        return {
            company.partner_id.commercial_partner_id: company for company in self.member_company_ids
        }

    def _rate(self, currency, day):
        """Return (average, closing) units of `currency` per group currency for day's month."""
        self.ensure_one()
        first = day.replace(day=1)
        rate = self.rate_ids.filtered(
            lambda r: r.currency_id == currency and r.date.replace(day=1) == first
        )
        if not rate:
            raise UserError(
                self.env._(
                    "There is no consolidation rate for %(currency)s in %(month)s. "
                    "Add it on the consolidation group before running.",
                    currency=currency.name,
                    month=f"{first:%B %Y}",
                )
            )
        return rate.average_rate, rate.closing_rate

    @api.model
    def _cron_run_previous_month(self):
        first = fields.Date.context_today(self).replace(day=1) - relativedelta(months=1)
        for group in self.search([("auto_run", "=", True)]):
            run = group.run_ids.filtered(lambda r: r.date_from == first)
            if run.state == "done":
                continue  # signed-off figures are never re-run by the scheduler
            try:
                with self.env.cr.savepoint():
                    run = run or self.env["account.consolidation.run"].create(
                        {"group_id": group.id, "date_from": first}
                    )
                    run.action_run()
            except UserError as error:
                # One group's problem (a lock, a missing rate) must not stop the others.
                _logger.warning(
                    "Consolidation of %s for %s was not run: %s", group.name, first, error
                )


class AccountConsolidationRate(models.Model):
    """Average and closing rate of one currency for one month."""

    _name = "account.consolidation.rate"
    _description = "Consolidation rate"
    _order = "date desc, currency_id"

    group_id = fields.Many2one("account.consolidation.group", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="group_id.company_id", store=True)
    currency_id = fields.Many2one("res.currency", required=True)
    date = fields.Date(string="Month end", required=True)
    average_rate = fields.Float(
        digits=(12, 6),
        required=True,
        help="Units of this currency per one unit of group currency, average for the month. "
        "Used for profit and loss.",
    )
    closing_rate = fields.Float(
        digits=(12, 6),
        required=True,
        help="Units of this currency per one unit of group currency at month end. "
        "Used for the balance sheet.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalise_date(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalise_date(vals)
        return super().write(vals)

    @api.model
    def _normalise_date(self, vals):
        # One rate per month: whatever day is entered, the rate belongs to its month end.
        if vals.get("date"):
            vals["date"] = fields.Date.to_date(vals["date"]) + relativedelta(day=31)

    _unique_month = models.Constraint(
        "unique(group_id, currency_id, date)",
        "One rate per currency and month.",
    )
    _positive = models.Constraint(
        "CHECK(average_rate > 0 AND closing_rate > 0)",
        "Rates must be positive.",
    )
