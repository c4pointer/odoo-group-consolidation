from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountConsolidationLine(models.Model):
    """One line of the group P&L or balance sheet, mapped from account codes.

    A journal item goes to the line with the longest matching account code
    prefix among the lines whose partner scope fits it. So "441" (exchange
    gains) wins over "4" (revenue) without any ordering rule, and a controller
    can add or change a line without touching code.
    """

    _name = "account.consolidation.line"
    _description = "Consolidation report line"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, help="Stable key used in exports and tests.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    section = fields.Selection(
        [
            ("pl", "Profit and loss"),
            ("asset", "Assets"),
            ("liability", "Liabilities and equity"),
        ],
        required=True,
    )
    kind = fields.Selection(
        [
            ("accounts", "Accounts"),
            ("profit", "Profit to date"),
            ("cta", "Translation reserve"),
        ],
        default="accounts",
        required=True,
        help="Accounts: journal items matched by prefix. Profit to date: the profit and loss "
        "accumulated in the balance sheet. Translation reserve: the balancing figure.",
    )
    account_prefixes = fields.Char(
        help="Comma-separated account code prefixes, for example 121 or 441,641."
    )
    partner_scope = fields.Selection(
        [
            ("any", "Any partner"),
            ("external", "External partners only"),
            ("intercompany", "Group companies only"),
        ],
        default="any",
        required=True,
    )

    _unique_code = models.Constraint("unique(code)", "Line codes must be unique.")

    @api.constrains("kind", "account_prefixes", "section")
    def _check_definition(self):
        for line in self:
            if line.kind == "accounts" and not line._prefixes():
                raise ValidationError(
                    self.env._("Line %(name)s needs account code prefixes.", name=line.name)
                )
            if line.kind != "accounts" and line.section != "liability":
                raise ValidationError(
                    self.env._("Profit and translation reserve lines belong to equity.")
                )

    def _prefixes(self):
        self.ensure_one()
        return [p.strip() for p in (self.account_prefixes or "").split(",") if p.strip()]

    def _classifier(self):
        """Return a function (account code, is intercompany) -> line or empty recordset."""
        rules = []
        for line in self.filtered(lambda r: r.kind == "accounts"):
            for prefix in line._prefixes():
                rules.append((prefix, line))
        # Longest prefix first; scoped lines before "any" on an equal prefix; then sequence.
        rules.sort(key=lambda r: (-len(r[0]), r[1].partner_scope == "any", r[1].sequence))
        cache = {}

        def classify(code, is_intercompany):
            key = (code, is_intercompany)
            if key not in cache:
                cache[key] = self.browse()
                for prefix, line in rules:
                    if not code.startswith(prefix):
                        continue
                    if line.partner_scope == "external" and is_intercompany:
                        continue
                    if line.partner_scope == "intercompany" and not is_intercompany:
                        continue
                    cache[key] = line
                    break
            return cache[key]

        return classify
