"""The monthly consolidation run.

One run per group and month. Running it:

1. checks the month can be closed (not locked, previous month closed, no later
   month closed, the user sees every company);
2. reads each member company's posted journal items up to month end and
   translates them to the group currency;
3. posts, in the consolidation company only, one profit and loss elimination
   and one balance sheet elimination (reversed on the 1st) per pair of companies;
4. stores the report: every company in its own currency and in group currency,
   the eliminations, and the controls.

Running a month again replaces its entries and results.
"""

import hashlib
from collections import defaultdict
from datetime import timedelta
from itertools import combinations

from dateutil.relativedelta import relativedelta
from odoo import Command, api, fields, models
from odoo.exceptions import UserError

# Report sign per section: revenue and gains positive, costs negative; assets
# positive; liabilities and equity positive.
SIGN = {"pl": -1.0, "asset": 1.0, "liability": -1.0}


class AccountConsolidationRun(models.Model):
    _name = "account.consolidation.run"
    _description = "Consolidation run"
    _order = "date_from desc, id desc"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    group_id = fields.Many2one(
        "account.consolidation.group", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="group_id.company_id", store=True)
    currency_id = fields.Many2one(related="group_id.currency_id")
    date_from = fields.Date(string="Month", required=True)
    date_to = fields.Date(compute="_compute_date_to", store=True)
    state = fields.Selection(
        [("draft", "Not run"), ("done", "Done")], default="draft", required=True, readonly=True
    )
    run_at = fields.Datetime(string="Last run", readonly=True)
    move_ids = fields.One2many("account.move", "consolidation_run_id", string="Elimination entries")
    move_count = fields.Integer(compute="_compute_move_count")
    result_ids = fields.One2many("account.consolidation.result", "run_id", readonly=True)
    difference_ids = fields.One2many("account.consolidation.difference", "run_id", readonly=True)
    clearing_balance = fields.Monetary(
        string="Clearing balance",
        readonly=True,
        help="Balance of the intercompany clearing account at month end. Must be zero; "
        "anything else is an unexplained intercompany difference.",
    )
    books_fingerprint = fields.Char(
        readonly=True,
        copy=False,
        help="Digest of the member books this run read. A later month runs only while the "
        "books of the latest closed month still give the same digest.",
    )

    _unique_month = models.Constraint(
        "unique(group_id, date_from)", "There is already a run for this group and month."
    )

    # ------------------------------------------------------------------ fields

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalise_month(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalise_month(vals)
        return super().write(vals)

    @api.model
    def _normalise_month(self, vals):
        if vals.get("date_from"):
            vals["date_from"] = fields.Date.to_date(vals["date_from"]).replace(day=1)

    @api.depends("date_from")
    def _compute_date_to(self):
        for run in self:
            run.date_to = run.date_from and run.date_from + relativedelta(day=31)

    @api.depends("group_id.name", "date_from")
    def _compute_name(self):
        for run in self:
            month = f"{run.date_from:%B %Y}" if run.date_from else ""
            run.name = f"{run.group_id.name or ''} - {month}"

    def _compute_move_count(self):
        for run in self:
            run.move_count = len(run.move_ids)

    # ------------------------------------------------------------------ actions

    def action_run(self):
        for run in self.sorted("date_from"):
            run._check_can_run()
            run._clear()
            run._consolidate()
        return True

    def action_reset(self):
        for run in self:
            run._check_no_later_run()
            run._check_not_locked()
            run._clear()
        return True

    def action_view_results(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_group_consolidation.action_consolidation_result"
        )
        action["name"] = self.env._("Consolidated report: %(run)s", run=self.name)
        action["domain"] = [("run_id", "=", self.id)]
        # No search grouping: the pivot's own rows (section, then line) give a subtotal per
        # section, so profit, assets and liabilities are never added together.
        action["context"] = {}
        return action

    @api.model
    def action_open_latest_report(self):
        """The menu entry: the report of the latest closed month, as its Report button opens it.

        A pivot over every run would add balance sheets of different months together, so
        when no run is visible the menu says what to do instead of showing one.
        """
        # Server actions run as superuser: search as the user, in the companies they selected.
        run = self.sudo(False).search(
            [("state", "=", "done"), ("company_id", "in", self.env.companies.ids)], limit=1
        )  # ordered latest month first
        if run:
            return run.action_view_results()
        hidden = self.sudo().search(
            [("state", "=", "done"), ("company_id", "in", self.env.user.company_ids.ids)],
            limit=1,
        )
        if hidden:
            raise UserError(
                self.env._(
                    "Select %(company)s in the company switcher to see the consolidated report.",
                    company=hidden.company_id.name,
                )
            )
        raise UserError(
            self.env._("No month is consolidated yet. Run one under Consolidation runs first.")
        )

    def action_view_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Elimination entries"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("consolidation_run_id", "=", self.id)],
            "context": {"create": False},
        }

    def get_figures(self, companies, ytd=False, local=False):
        """Report figures of the given column companies, by line code, with totals.

        `companies` are member companies and/or the consolidation company (the
        elimination column); all of them together give the group. `local` reads
        the company's own currency and only makes sense for one company.
        """
        self.ensure_one()
        field = ("local_" if local else "") + ("amount_ytd" if ytd else "amount")
        figures = defaultdict(float)
        totals = {
            "pl": "net_profit",
            "asset": "total_assets",
            "liability": "total_liabilities_equity",
        }
        for row in self.result_ids.filtered(lambda r: r.column_company_id in companies):
            figures[row.code] += row[field]
            figures[totals[row.section]] += row[field]
        return dict(figures)

    # ------------------------------------------------------------------ checks

    def _check_can_run(self):
        self.ensure_one()
        group = self.group_id
        if self.date_from < group.start_date.replace(day=1):
            raise UserError(
                self.env._(
                    "%(group)s starts in %(month)s.",
                    group=group.name,
                    month=f"{group.start_date:%B %Y}",
                )
            )
        self._check_not_locked()
        self._check_no_later_run()
        missing = []
        month = group.start_date.replace(day=1)
        done = set(group.run_ids.filtered(lambda r: r.state == "done").mapped("date_from"))
        while month < self.date_from:
            if month not in done:
                missing.append(f"{month:%B %Y}")
            month += relativedelta(months=1)
        if missing:
            raise UserError(
                self.env._("Close the earlier months first: %(months)s.", months=", ".join(missing))
            )
        companies = group.member_company_ids | group.company_id
        if not self.env.su and companies - self.env.user.company_ids:
            raise UserError(
                self.env._(
                    "You need access to every company of the group to consolidate it: "
                    "%(companies)s.",
                    companies=", ".join((companies - self.env.user.company_ids).mapped("name")),
                )
            )
        self._check_closed_books_unchanged()

    def _check_closed_books_unchanged(self):
        """The months already closed must still read the books they were closed on.

        Books are cumulative, so the latest closed month covers every change dated in it
        or before; earlier months are read only to name the first one that changed.
        """
        closed = self.group_id.run_ids.filtered(
            lambda r: r.state == "done" and r.date_from < self.date_from and r.books_fingerprint
        ).sorted("date_from", reverse=True)
        changed = self.browse()
        for run in closed:
            if run._read_fingerprint() == run.books_fingerprint:
                break
            changed = run
        if changed:
            raise UserError(
                self.env._(
                    "The books of %(month)s changed after it was consolidated. Reset the runs "
                    "from %(month)s onwards and run them again.",
                    month=f"{changed.date_from:%B %Y}",
                )
            )

    def _check_not_locked(self):
        company = self.group_id.company_id
        lock = company._get_user_fiscal_lock_date(self.group_id.journal_id, ignore_exceptions=True)
        if lock and lock >= self.date_from:
            raise UserError(
                self.env._(
                    "%(company)s is locked up to %(lock)s; %(month)s cannot be consolidated "
                    "again.",
                    company=company.name,
                    lock=lock,
                    month=f"{self.date_from:%B %Y}",
                )
            )

    def _check_no_later_run(self):
        later = self.group_id.run_ids.filtered(
            lambda r: r.state == "done" and r.date_from > self.date_from
        )
        if later:
            raise UserError(
                self.env._(
                    "Reset the later months first, from the latest: %(months)s.",
                    months=", ".join(f"{d:%B %Y}" for d in sorted(later.mapped("date_from"))),
                )
            )

    def _clear(self):
        moves = self.move_ids
        moves.filtered(lambda m: m.state == "posted").button_draft()
        moves.unlink()
        self.result_ids.unlink()
        self.difference_ids.unlink()
        self.write(
            {"state": "draft", "clearing_balance": 0.0, "run_at": False, "books_fingerprint": False}
        )

    # ------------------------------------------------------------------ reading books

    def _read_book(self, company, classify, member_by_partner):
        """Translated balances of one company up to month end.

        Returns {(line, account code, counterpart company, month): [local, group]}
        where amounts are signed debit-positive, the counterpart is the member
        company on the item's partner (empty for external items), and month is
        the first day of the month the item was booked in.
        """
        book = defaultdict(lambda: [0.0, 0.0])
        unmapped = set()
        items = self.env["account.move.line"].with_company(company)
        base_domain = [
            ("company_id", "=", company.id),
            ("parent_state", "=", "posted"),
            ("date", "<=", self.date_to),
        ]
        no_company = self.env["res.company"]
        # Items in group currency with a zero group amount (exchange differences) are
        # read separately, because profit and loss items translate them from local currency.
        for operator in ("=", "!="):
            rows = items._read_group(
                [*base_domain, ("amount_currency", operator, 0.0)],
                ["account_id", "partner_id", "currency_id", "date:month"],
                ["balance:sum", "amount_currency:sum"],
            )
            for account, partner, currency, month, balance, amount_currency in rows:
                if company.currency_id.is_zero(balance) and currency.is_zero(amount_currency):
                    continue
                code = account.with_company(company).code
                counterpart = member_by_partner.get(partner.commercial_partner_id, no_company)
                if counterpart == company:
                    counterpart = no_company
                line = classify(code, bool(counterpart))
                if not line:
                    unmapped.add(code)
                    continue
                translated = self._translate(
                    company,
                    line.section,
                    currency,
                    month,
                    balance,
                    amount_currency,
                    has_document_amount=operator == "!=",
                    intercompany=bool(counterpart),
                )
                key = (line, code, counterpart, month)
                book[key][0] += balance
                book[key][1] += translated
        if unmapped:
            raise UserError(
                self.env._(
                    "No consolidation line reads these accounts of %(company)s: %(codes)s. "
                    "Add their code prefix to a line before running.",
                    company=company.name,
                    codes=", ".join(sorted(unmapped)),
                )
            )
        return book

    def _read_fingerprint(self):
        """Fingerprint of the member books as they read today for this run's month."""
        classify = self.env["account.consolidation.line"].search([])._classifier()
        member_by_partner = self.group_id._member_by_partner()
        members = self.group_id.member_company_ids
        return self._fingerprint(
            {c: self._read_book(c, classify, member_by_partner) for c in members}
        )

    @staticmethod
    def _fingerprint(books):
        """Digest of local and translated amounts by company, account, counterpart and month.

        Report lines are left out, so adding or moving a line does not reopen closed months.
        """
        rows = defaultdict(lambda: [0.0, 0.0])
        for company, book in books.items():
            for (_line, code, counterpart, month), (local, amount) in book.items():
                row = rows[(company.id, code, counterpart.id or 0, month.isoformat())]
                row[0] += local
                row[1] += amount
        # Adding 0.0 turns -0.0 into 0.0, so a sign of zero never changes the digest.
        payload = sorted(
            (key, round(local, 2) + 0.0, round(amount, 2) + 0.0)
            for key, (local, amount) in rows.items()
            if round(local, 2) or round(amount, 2)
        )
        return hashlib.sha256(repr(payload).encode()).hexdigest()

    def _translate(
        self,
        company,
        section,
        currency,
        month,
        balance,
        amount_currency,
        has_document_amount,
        intercompany=False,
    ):
        """Translate a group of items to the group currency.

        `has_document_amount` tells whether every item of the group carries a non-zero
        document-currency amount: it is decided per item when reading, because an invoice
        and its full credit note sum to zero in USD and must still be taken at their USD
        amount.
        """
        group_currency = self.currency_id
        use_document = section != "pl" or has_document_amount
        if intercompany and use_document and currency not in (company.currency_id, group_currency):
            # An intercompany document in a third currency: both sides translate its document
            # amount at the group's rate for that currency, so they eliminate exactly.
            if section == "pl":
                average, _closing = self.group_id._rate(currency, month)
                return amount_currency / average
            _average, closing = self.group_id._rate(currency, self.date_to)
            return amount_currency / closing
        if company.currency_id == group_currency:
            return balance
        if currency == group_currency and use_document:
            # Denominated in group currency: the document amount is exact.
            return amount_currency
        if section == "pl":
            average, _closing = self.group_id._rate(company.currency_id, month)
            return balance / average
        _average, closing = self.group_id._rate(company.currency_id, self.date_to)
        return balance / closing

    # ------------------------------------------------------------------ consolidating

    def _consolidate(self):
        group = self.group_id
        lines = self.env["account.consolidation.line"].search([])
        classify = lines._classifier()
        member_by_partner = group._member_by_partner()
        members = group.member_company_ids.sorted("id")
        books = {c: self._read_book(c, classify, member_by_partner) for c in members}
        fingerprint = self._fingerprint(books)

        differences = []
        for first, second in combinations(members, 2):
            differences.append(self._eliminate_pair(books, first, second))
        self.env["account.consolidation.difference"].create(differences)

        books[group.company_id] = self._read_book(group.company_id, classify, member_by_partner)
        self._check_earlier_months_eliminated(books)
        self._store_results(books, lines)
        self.write(
            {
                "state": "done",
                "run_at": fields.Datetime.now(),
                "clearing_balance": self._clearing_balance(),
                "books_fingerprint": fingerprint,
            }
        )

    def _check_earlier_months_eliminated(self, books):
        """Each month's intercompany P&L, books plus eliminations, must net to zero.

        A document dated in a month that was already consolidated would otherwise stay in
        the group P&L and show up as a clearing balance with no explanation.
        """
        group_currency = self.currency_id
        start = self.group_id.start_date.replace(day=1)
        net = defaultdict(float)
        for company, book in books.items():
            per_key = defaultdict(float)
            for (line, code, counterpart, month), (_local, amount) in book.items():
                if line.section == "pl" and counterpart and line.partner_scope == "intercompany":
                    per_key[(company, counterpart, code, month)] += amount
            for (_company, _counterpart, _code, month), amount in per_key.items():
                # Rounded per company, counterpart and account, as the eliminations are.
                net[month] += group_currency.round(amount)
        changed = sorted(
            month
            for month, amount in net.items()
            if month >= start and not group_currency.is_zero(amount)
        )
        if changed:
            raise UserError(
                self.env._(
                    "Intercompany documents changed after these months were consolidated: "
                    "%(months)s. Reset the runs from %(first)s onwards and run them again.",
                    months=", ".join(f"{m:%B %Y}" for m in changed),
                    first=f"{changed[0]:%B %Y}",
                )
            )

    def _pair_rows(self, books, first, second):
        """Eliminable rows of a pair: intercompany lines of each side towards the other."""
        for company, other in ((first, second), (second, first)):
            for (line, code, counterpart, month), (_local, amount) in books[company].items():
                if counterpart == other and line.partner_scope == "intercompany":
                    yield company, other, line, code, month, amount

    def _eliminate_pair(self, books, first, second):
        group_currency = self.currency_id
        pl_month = defaultdict(float)
        pl_by_month = defaultdict(float)
        balance_sheet = defaultdict(float)
        labels = {}
        for company, other, line, code, month, amount in self._pair_rows(books, first, second):
            key = (company, other, code)
            labels[key] = line.name
            if line.section == "pl":
                pl_by_month[(key, month)] += amount
                if month == self.date_from:
                    pl_month[key] += amount
            else:
                balance_sheet[key] += amount

        rounded_pl = {k: group_currency.round(v) for k, v in pl_month.items()}
        pl_lines = self._elimination_lines(rounded_pl, labels)
        timing_today = -sum(rounded_pl.values())
        if pl_lines:
            if not group_currency.is_zero(timing_today):
                pl_lines.append(
                    self._clearing_line(
                        -timing_today,
                        self.env._(
                            "Booked by one side only in %(month)s: %(first)s / %(second)s",
                            month=f"{self.date_from:%B %Y}",
                            first=first.name,
                            second=second.name,
                        ),
                    )
                )
            self._post(
                pl_lines,
                "pl",
                self.date_to,
                self.env._(
                    "Intercompany P&L elimination %(month)s: %(first)s / %(second)s",
                    month=f"{self.date_from:%B %Y}",
                    first=first.name,
                    second=second.name,
                ),
            )

        # Documents booked by one side only, since the start: the sum of every month's
        # P&L elimination residual, rounded the same way, so the clearing account nets to zero.
        timing = -sum(group_currency.round(v) for v in pl_by_month.values())
        rounded_bs = {k: group_currency.round(v) for k, v in balance_sheet.items()}
        net = sum(rounded_bs.values())
        in_transit = group_currency.round(net - timing)
        bs_lines = self._elimination_lines(rounded_bs, labels)
        if bs_lines:
            if not group_currency.is_zero(timing):
                bs_lines.append(
                    self._clearing_line(
                        timing,
                        self.env._(
                            "Documents booked by one side only: %(first)s / %(second)s",
                            first=first.name,
                            second=second.name,
                        ),
                    )
                )
            if not group_currency.is_zero(in_transit):
                bs_lines.append(
                    {
                        "name": self.env._(
                            "Cash in transit: %(first)s / %(second)s",
                            first=first.name,
                            second=second.name,
                        ),
                        "account_id": self.group_id.transit_account_id.id,
                        "debit": max(in_transit, 0.0),
                        "credit": max(-in_transit, 0.0),
                    }
                )
            ref = self.env._(
                "Intercompany balance elimination %(day)s: %(first)s / %(second)s",
                day=self.date_to,
                first=first.name,
                second=second.name,
            )
            move = self._post(bs_lines, "bs", self.date_to, ref)
            reversal = move._reverse_moves(
                [
                    {
                        "date": self.date_to + timedelta(days=1),
                        "ref": self.env._("Reversal of %(ref)s", ref=ref),
                        "consolidation_run_id": self.id,
                        "consolidation_kind": "bs",
                    }
                ]
            )
            reversal.action_post()

        return {
            "run_id": self.id,
            "first_company_id": first.id,
            "second_company_id": second.id,
            "timing_difference": timing,
            "cash_in_transit": in_transit,
        }

    def _elimination_lines(self, amounts, labels):
        """One line per company and account, taking the balance out of the group."""
        lines = []
        for (company, other, code), amount in sorted(
            amounts.items(), key=lambda item: (item[0][0].id, item[0][2])
        ):
            if self.currency_id.is_zero(amount):
                continue
            lines.append(
                {
                    "name": self.env._(
                        "%(company)s: %(line)s with %(other)s",
                        company=company.name,
                        line=labels[(company, other, code)],
                        other=other.name,
                    ),
                    "account_id": self._group_account(code).id,
                    "partner_id": company.partner_id.id,
                    "debit": max(-amount, 0.0),
                    "credit": max(amount, 0.0),
                }
            )
        return lines

    def _clearing_line(self, amount, label):
        """`amount` is the debit-positive balance put on the clearing account."""
        return {
            "name": label,
            "account_id": self.group_id.clearing_account_id.id,
            "debit": max(amount, 0.0),
            "credit": max(-amount, 0.0),
        }

    def _group_account(self, code):
        company = self.group_id.company_id
        account = (
            self.env["account.account"]
            .with_company(company)
            .search([("code", "=", code), ("company_ids", "in", company.id)], limit=1)
        )
        if not account:
            raise UserError(
                self.env._(
                    "Account %(code)s is missing in %(company)s; eliminations are posted on "
                    "the same account codes as the member companies use.",
                    code=code,
                    company=company.name,
                )
            )
        return account

    def _post(self, lines, kind, day, ref):
        company = self.group_id.company_id
        move = (
            self.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": "entry",
                    "company_id": company.id,
                    "journal_id": self.group_id.journal_id.id,
                    "date": day,
                    "ref": ref,
                    "consolidation_run_id": self.id,
                    "consolidation_kind": kind,
                    "line_ids": [Command.create(vals) for vals in lines],
                }
            )
        )
        move.action_post()
        return move

    def _clearing_balance(self):
        account = self.group_id.clearing_account_id
        rows = self.env["account.move.line"]._read_group(
            [
                ("company_id", "=", self.group_id.company_id.id),
                ("account_id", "=", account.id),
                ("parent_state", "=", "posted"),
                ("date", "<=", self.date_to),
            ],
            [],
            ["balance:sum"],
        )
        return self.currency_id.round(rows[0][0] or 0.0)

    # ------------------------------------------------------------------ results

    def _store_results(self, books, lines):
        year_start = self.date_from.replace(month=1)
        group_currency = self.currency_id
        consolidation_company = self.group_id.company_id
        values = []
        for company, book in books.items():
            local_currency = company.currency_id
            figures = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # local, local ytd, group, ytd
            profit = [0.0, 0.0]
            for (line, _code, _counterpart, month), (local, amount) in book.items():
                sign = SIGN[line.section]
                if line.section == "pl":
                    profit[0] += sign * local
                    profit[1] += sign * amount
                    if month < year_start:
                        continue
                    target = figures[line]
                    target[1] += sign * local
                    target[3] += sign * amount
                    if month == self.date_from:
                        target[0] += sign * local
                        target[2] += sign * amount
                else:
                    target = figures[line]
                    for index, value in ((0, local), (1, local), (2, amount), (3, amount)):
                        target[index] += sign * value

            rows = {}
            for line in lines:
                if line.kind == "accounts":
                    local, local_ytd, amount, amount_ytd = figures.get(line, [0.0] * 4)
                elif line.kind == "profit":
                    local = local_ytd = profit[0]
                    amount = amount_ytd = profit[1]
                else:
                    continue
                rows[line] = [
                    local_currency.round(local),
                    local_currency.round(local_ytd),
                    group_currency.round(amount),
                    group_currency.round(amount_ytd),
                ]
            for line in lines.filtered(lambda r: r.kind == "cta"):
                balancing = []
                for index, currency in enumerate(
                    (local_currency, local_currency, group_currency, group_currency)
                ):
                    assets = sum(v[index] for k, v in rows.items() if k.section == "asset")
                    equity = sum(v[index] for k, v in rows.items() if k.section == "liability")
                    balancing.append(currency.round(assets - equity))
                rows[line] = balancing

            for line, (local, local_ytd, amount, amount_ytd) in rows.items():
                values.append(
                    {
                        "run_id": self.id,
                        "line_id": line.id,
                        "column_company_id": company.id,
                        "is_elimination": company == consolidation_company,
                        "local_amount": local,
                        "local_amount_ytd": local_ytd,
                        "amount": amount,
                        "amount_ytd": amount_ytd,
                    }
                )
        self.env["account.consolidation.result"].create(values)
