"""Group figures and elimination entries match the oracle.

The scenario's own books are proven in test_scenario_books; a failure here
points at the consolidation module. Runs for January, February and March are
created once per class, the way a controller closes the months in order.
"""

from datetime import date

from odoo import Command
from odoo.addons.account_group_consolidation.scenario import delta
from odoo.exceptions import AccessError, UserError
from odoo.tests import freeze_time, new_test_user, tagged

from .common import DeltaCase, month_bounds


@tagged("post_install", "-at_install")
class TestConsolidation(DeltaCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.scenario.consolidation_group
        cls.elim_company = cls.companies["group"]
        cls.members = cls.companies["us"] | cls.companies["ua"] | cls.companies["pl"]
        cls.runs = {month: cls._run(month) for month in (1, 2, 3)}

    @classmethod
    def _run(cls, month):
        first, _last = month_bounds(month)
        run = cls.env["account.consolidation.run"].create(
            {"group_id": cls.group.id, "date_from": first}
        )
        run.action_run()
        return run

    def _column(self, key):
        """Companies behind an oracle column name."""
        if key == "companies":
            return self.members
        if key == "eliminations":
            return self.elim_company
        if key == "group":
            return self.members | self.elim_company
        return self.companies[key]

    def _figures(self, month, column, **kwargs):
        return self.runs[month].get_figures(self._column(column), **kwargs)

    def _entries(self, run, kind, partners, on=None):
        """Elimination entries of `run` and `kind` for one pair of companies."""
        pair = {self.companies[key].partner_id for key in partners}
        moves = run.move_ids.filtered(
            lambda move: move.consolidation_kind == kind
            and (on is None or move.date == on)
            and set(move.line_ids.partner_id) <= pair
            and move.line_ids.partner_id
        )
        return moves.line_ids

    def _sum(self, lines, key=None, account_code=None, account_type=None):
        partner = self.companies[key].partner_id if key else None
        selected = lines.filtered(
            lambda line: (partner is None or line.partner_id == partner)
            and (
                account_code is None
                or line.account_id.with_company(line.company_id).code == account_code
            )
            and (account_type is None or line.account_id.account_type == account_type)
        )
        return sum(selected.mapped("balance"))

    # ---------------------------------------------------------- translation

    def test_translated_profit_by_month(self):
        for key, by_month in self.expected.TRANSLATED_PROFIT.items():
            for month, profit in by_month.items():
                with self.subTest(company=key, month=month):
                    actual = self._figures(month, key)["net_profit"]
                    self.assertAlmostEqual(actual, profit, delta=self.expected.TOLERANCE)

    def test_translated_profit_and_loss_ukraine_march(self):
        self.assertFigures(
            self._figures(3, "ua"), self.expected.TRANSLATED_PL_MARCH_UA, "ua P&L March, USD"
        )

    def test_translated_balance_sheet_march(self):
        for key, expected in self.expected.TRANSLATED_BS_MARCH.items():
            self.assertFigures(self._figures(3, key), expected, f"{key} balance sheet, USD")

    def test_company_columns_keep_own_currency_books(self):
        """The run's company columns, in local currency, equal each company's own books."""
        for key, expected in self.expected.STANDALONE_PL_MARCH.items():
            actual = self._figures(3, key, local=True)
            self.assertFigures(actual, expected, f"{key} P&L March, local")
        for key, expected in self.expected.STANDALONE_BS_MARCH.items():
            actual = self._figures(3, key, local=True)
            self.assertFigures(actual, expected, f"{key} balance sheet, local")

    # ---------------------------------------------------------- eliminations

    def test_profit_and_loss_eliminations(self):
        for (seller, buyer), by_month in self.expected.PL_ELIMINATIONS.items():
            for month, (revenue, cost, clearing) in by_month.items():
                with self.subTest(seller=seller, buyer=buyer, month=month):
                    lines = self._entries(self.runs[month], "pl", (seller, buyer))
                    # Revenue is removed with a debit, cost with a credit.
                    self.assertAlmostEqual(
                        self._sum(lines, seller, account_type="income"), revenue, delta=0.01
                    )
                    self.assertAlmostEqual(
                        -self._sum(lines, buyer, account_type="expense"), cost, delta=0.01
                    )
                    self.assertAlmostEqual(
                        -self._sum(lines, account_code=delta.ACC_IC_CLEARING), clearing, delta=0.01
                    )

    def test_balance_sheet_eliminations_march(self):
        _first, last = month_bounds(3)
        run = self.runs[3]
        codes = {
            "trade": (delta.ACC_RECEIVABLE, delta.ACC_PAYABLE),
            "loan": (delta.ACC_IC_LOAN_RECEIVABLE, delta.ACC_IC_LOAN_PAYABLE),
        }
        for (creditor, debtor, kind), expected in self.expected.BS_ELIMINATIONS_MARCH.items():
            receivable, payable, in_transit, clearing = expected
            lines = self._entries(run, "bs", (creditor, debtor), on=last)
            with self.subTest(creditor=creditor, debtor=debtor, kind=kind):
                receivable_code, payable_code = codes[kind]
                self.assertAlmostEqual(
                    -self._sum(lines, creditor, account_code=receivable_code),
                    receivable,
                    delta=0.01,
                )
                self.assertAlmostEqual(
                    self._sum(lines, debtor, account_code=payable_code), payable, delta=0.01
                )
                if kind == "trade":
                    self.assertAlmostEqual(
                        self._sum(lines, account_code=delta.ACC_CASH_IN_TRANSIT),
                        in_transit,
                        delta=0.01,
                    )
                    self.assertAlmostEqual(
                        self._sum(lines, account_code=delta.ACC_IC_CLEARING), clearing, delta=0.01
                    )

    def test_balance_sheet_eliminations_reverse_next_month(self):
        moves = self.runs[3].move_ids.filtered(lambda move: move.consolidation_kind == "bs")
        originals = moves.filtered(lambda move: move.date == date(2026, 3, 31))
        reversals = moves - originals
        self.assertTrue(originals)
        self.assertEqual(set(reversals.mapped("date")), {date(2026, 4, 1)})
        self.assertEqual(reversals.reversed_entry_id, originals)

    def test_profit_and_loss_eliminations_are_not_reversed(self):
        for run in self.runs.values():
            pl_moves = run.move_ids.filtered(lambda move: move.consolidation_kind == "pl")
            self.assertTrue(pl_moves)
            self.assertFalse(pl_moves.reversal_move_ids)
            self.assertEqual(set(pl_moves.mapped("date")), {run.date_to})

    def test_ic_clearing_nets_to_zero(self):
        for month, run in self.runs.items():
            with self.subTest(month=month):
                self.assertAlmostEqual(
                    run.clearing_balance, self.expected.IC_CLEARING_BALANCE, delta=0.01
                )
                self.assertAlmostEqual(
                    self._figures(month, "group")["ic_clearing"], 0.0, delta=0.01
                )

    def test_differences_explain_march(self):
        """The run tells the controller why each pair did not match."""
        differences = {
            frozenset(d.first_company_id | d.second_company_id): d
            for d in self.runs[3].difference_ids
        }
        ua_us = differences[frozenset(self.companies["ua"] | self.companies["us"])]
        pl_us = differences[frozenset(self.companies["pl"] | self.companies["us"])]
        self.assertAlmostEqual(ua_us.timing_difference, 50_000.0, delta=0.01)
        self.assertAlmostEqual(ua_us.cash_in_transit, 0.0, delta=0.01)
        self.assertAlmostEqual(pl_us.timing_difference, 0.0, delta=0.01)
        self.assertAlmostEqual(pl_us.cash_in_transit, 40_000.0, delta=0.01)

    # ---------------------------------------------------------- group results

    def test_group_profit_and_loss_by_month(self):
        for month, expected in self.expected.GROUP_PL.items():
            self.assertFigures(self._figures(month, "group"), expected, f"group P&L {month}")

    def test_group_profit_and_loss_year_to_date(self):
        self.assertFigures(
            self._figures(3, "group", ytd=True),
            self.expected.GROUP_PL_YTD_MARCH,
            "group P&L January-March",
        )

    def test_group_balance_sheet_march(self):
        for column, expected in self.expected.GROUP_BS_MARCH.items():
            self.assertFigures(self._figures(3, column), expected, f"balance sheet, {column}")

    # ---------------------------------------------------------- requirements

    def test_real_books_are_never_touched(self):
        """No elimination lands in Delta US, Ukraine or Poland."""
        moves = self.env["account.move"].search([("consolidation_run_id", "!=", False)])
        self.assertTrue(moves)
        self.assertEqual(moves.company_id, self.elim_company)
        self.assertEqual(moves.journal_id, self.group.journal_id)

    def test_elimination_entry_opens_for_auditor(self):
        """Every elimination is a posted entry that names its run and explains each line."""
        for run in self.runs.values():
            for move in run.move_ids:
                with self.subTest(move=move.name):
                    self.assertEqual(move.state, "posted")
                    self.assertEqual(move.consolidation_run_id, run)
                    self.assertTrue(move.ref)
                    self.assertTrue(all(move.line_ids.mapped("name")))

    # ---------------------------------------------------------- run behaviour

    def test_rerun_replaces_entries(self):
        run = self.runs[3]
        before = run.get_figures(self.members | self.elim_company)
        old_moves = run.move_ids
        run.action_run()
        self.assertFalse(old_moves.exists())
        self.assertEqual(len(run.move_ids), len(old_moves))
        self.assertFigures(run.get_figures(self.members | self.elim_company), before, "re-run")

    def test_locked_period_is_refused(self):
        self.elim_company.fiscalyear_lock_date = date(2026, 3, 31)
        with self.assertRaisesRegex(UserError, "locked"):
            self.runs[3].action_run()

    def test_months_close_in_order(self):
        run = self.env["account.consolidation.run"].create(
            {"group_id": self.group.id, "date_from": date(2026, 5, 1)}
        )
        with self.assertRaisesRegex(UserError, "April 2026"):
            run.action_run()

    def test_earlier_month_cannot_rerun_after_later_one(self):
        with self.assertRaisesRegex(UserError, "March 2026"):
            self.runs[2].action_run()

    def test_missing_rate_is_refused(self):
        self.group.rate_ids.filtered(
            lambda rate: rate.currency_id.name == "UAH" and rate.date.month == 4
        ).unlink()
        run = self.env["account.consolidation.run"].create(
            {"group_id": self.group.id, "date_from": date(2026, 4, 1)}
        )
        with self.assertRaisesRegex(UserError, "UAH"):
            run.action_run()

    def test_unmapped_account_is_refused(self):
        """A balance no report line reads stops the run instead of disappearing."""
        ukraine = self.companies["ua"]
        odd = (
            self.env["account.account"]
            .with_company(ukraine)
            .create({"code": "799000", "name": "Unexpected income", "account_type": "income_other"})
        )
        self.scenario._entry(
            ukraine,
            date(2026, 3, 20),
            "Unmapped income",
            [(odd, -1_000.0), (self.scenario._account(ukraine, delta.ACC_RECEIVABLE), 1_000.0)],
        )
        with self.assertRaisesRegex(UserError, "799000"):
            self.runs[3].action_run()

    def test_report_lines_are_configuration(self):
        """Moving rent to its own line is data, not code: the next run follows it."""
        self.env["account.consolidation.line"].create(
            {
                "name": "Office rent",
                "code": "rent",
                "section": "pl",
                "account_prefixes": "612",
                "partner_scope": "any",
                "sequence": 45,
            }
        )
        self.runs[3].action_run()
        ukraine = self._figures(3, "ua")
        self.assertAlmostEqual(ukraine["rent"], -5_000.0, delta=0.01)
        self.assertAlmostEqual(ukraine["other_costs"], 0.0, delta=0.01)
        self.assertAlmostEqual(ukraine["net_profit"], 25_000.0, delta=0.01)

    # ---------------------------------------------------------- April

    def test_april_unwinds_cut_off_and_transit(self):
        april = self._run(4)
        group = self.members | self.elim_company
        expected = self.expected.APRIL
        self.assertAlmostEqual(
            april.get_figures(group)["net_profit"], expected["group_net_profit"], delta=0.01
        )
        # IAS 21.45: the realised loss on an intercompany balance stays in the group.
        self.assertAlmostEqual(april.get_figures(group)["fx"], expected["pl_fx"], delta=0.01)
        self.assertAlmostEqual(
            april.get_figures(self.companies["pl"], local=True)["fx"],
            expected["pl_fx_local"],
            delta=0.01,
        )
        self.assertAlmostEqual(
            april.get_figures(self.companies["us"])["ic_cost"], expected["us_ic_cost"], delta=0.01
        )
        group_bs = april.get_figures(group)
        self.assertAlmostEqual(group_bs["cash_in_transit"], expected["cash_in_transit"], delta=0.01)
        self.assertAlmostEqual(april.clearing_balance, expected["ic_clearing"], delta=0.01)
        self.assertAlmostEqual(
            group_bs["total_assets"], group_bs["total_liabilities_equity"], delta=0.01
        )
        for (creditor, debtor), amount in expected["receivable_equals_payable"].items():
            lines = self._entries(april, "bs", (creditor, debtor), on=date(2026, 4, 30))
            with self.subTest(creditor=creditor, debtor=debtor):
                self.assertAlmostEqual(
                    -self._sum(lines, creditor, account_code=delta.ACC_RECEIVABLE),
                    amount,
                    delta=0.01,
                )
                self.assertAlmostEqual(
                    self._sum(lines, debtor, account_code=delta.ACC_PAYABLE), amount, delta=0.01
                )
                self.assertAlmostEqual(
                    self._sum(lines, account_code=delta.ACC_CASH_IN_TRANSIT), 0.0, delta=0.01
                )
        # Over January-April the Ukraine -> US timing difference has fully reversed.
        runs = (*self.runs.values(), april)
        revenue = cost = 0.0
        for run in runs:
            lines = self._entries(run, "pl", ("ua", "us"))
            revenue += self._sum(lines, "ua", account_type="income")
            cost -= self._sum(lines, "us", account_type="expense")
        self.assertAlmostEqual(revenue, expected["ua_us_ytd_revenue_and_cost"], delta=0.01)
        self.assertAlmostEqual(cost, expected["ua_us_ytd_revenue_and_cost"], delta=0.01)

    # ---------------------------------------------------------- review findings

    def test_changed_earlier_month_is_refused(self):
        """A February document posted after February closed must not slip into the group."""
        self.scenario._invoice(
            self.companies["us"],
            "in_invoice",
            "pl",
            date(2026, 2, 20),
            5_000.0,
            self.env.ref("base.USD"),
            delta.ACC_EXPENSE,
            "Late February design services",
        )
        with self.assertRaisesRegex(UserError, "February 2026"):
            self.runs[3].action_run()

    def test_full_offset_within_a_month_stays_exact(self):
        """Invoice and full credit note at different daily rates leave no USD behind.

        April: Ukraine has no other intercompany revenue, so the two documents are the
        only items of their kind and their USD amounts sum to zero.
        """
        uah, usd = self.env.ref("base.UAH"), self.env.ref("base.USD")
        self.env["res.currency.rate"].create(
            {"currency_id": uah.id, "name": date(2026, 4, 10), "rate": 43.5, "company_id": False}
        )
        ukraine = self.companies["ua"]
        invoice = self.scenario._invoice(
            ukraine,
            "out_invoice",
            "us",
            date(2026, 4, 5),
            10_000.0,
            usd,
            delta.ACC_REVENUE,
            "Invoice issued by mistake",
        )
        self.scenario._invoice(
            ukraine,
            "out_refund",
            "us",
            date(2026, 4, 20),
            10_000.0,
            usd,
            delta.ACC_REVENUE,
            "Full credit",
            reversed_entry=invoice,
        )
        april = self._run(4)
        self.assertAlmostEqual(april.get_figures(ukraine)["ic_revenue"], 0.0, delta=0.01)
        pair = april.difference_ids.filtered(
            lambda d: (d.first_company_id | d.second_company_id) == (ukraine | self.companies["us"])
        )
        self.assertAlmostEqual(pair.timing_difference, 0.0, delta=0.01)
        self.assertAlmostEqual(pair.cash_in_transit, 0.0, delta=0.01)

    def test_contact_of_a_group_company_is_intercompany(self):
        """A manual entry against a contact of Delta US is still intercompany."""
        contact = self.env["res.partner"].create(
            {"name": "Delta US, accounts payable", "parent_id": self.companies["us"].partner_id.id}
        )
        self.scenario.partners["us_contact"] = contact
        poland = self.companies["pl"]
        self.scenario._entry(
            poland,
            date(2026, 3, 25),
            "Extra design services",
            [
                (
                    self.scenario._account(poland, delta.ACC_RECEIVABLE),
                    4_000.0,
                    "us_contact",
                    1_000.0,
                ),
                (
                    self.scenario._account(poland, delta.ACC_REVENUE),
                    -4_000.0,
                    "us_contact",
                    -1_000.0,
                ),
            ],
        )
        self.runs[3].action_run()
        self.assertAlmostEqual(self._figures(3, "pl")["ic_revenue"], 24_000.0, delta=0.01)
        self.assertAlmostEqual(self._figures(3, "group")["ic_revenue"], 0.0, delta=0.01)

    def test_rate_date_is_month_end(self):
        rate = self.env["account.consolidation.rate"].create(
            {
                "group_id": self.group.id,
                "currency_id": self.env.ref("base.UAH").id,
                "date": date(2026, 5, 15),
                "average_rate": 44.0,
                "closing_rate": 45.0,
            }
        )
        self.assertEqual(rate.date, date(2026, 5, 31))

    def test_cron_closes_previous_month_once(self):
        with freeze_time("2026-04-02"):
            self.group.auto_run = True
            self.env["account.consolidation.group"]._cron_run_previous_month()
            april = self.group.run_ids.filtered(lambda r: r.date_from == date(2026, 3, 1))
            self.assertEqual(april, self.runs[3])
            moves = self.runs[3].move_ids
            self.env["account.consolidation.group"]._cron_run_previous_month()
            self.assertEqual(self.runs[3].move_ids, moves, "a closed month is not re-run")
        with freeze_time("2026-05-02"):
            self.env["account.consolidation.group"]._cron_run_previous_month()
            april = self.group.run_ids.filtered(lambda r: r.date_from == date(2026, 4, 1))
            self.assertEqual(april.state, "done")

    def test_members_need_the_configuring_user_access(self):
        # The scheduled action runs as superuser and skips the run's own access check,
        # so who may consolidate a company is decided when the group is configured:
        # Odoo refuses to link companies the user cannot read. Guards against a sudo()
        # creeping into the configuration path.
        user = new_test_user(
            self.env,
            "group_ledger_only",
            groups="account.group_account_manager",
            company_id=self.elim_company.id,
            company_ids=[Command.set(self.elim_company.ids)],
        )
        values = {
            "name": "Shadow group",
            "company_id": self.elim_company.id,
            "member_company_ids": [Command.set(self.members.ids)],
            "journal_id": self.group.journal_id.id,
            "clearing_account_id": self.group.clearing_account_id.id,
            "transit_account_id": self.group.transit_account_id.id,
            "start_date": date(2026, 1, 1),
            "auto_run": True,
        }
        with self.assertRaises(AccessError):
            self.env["account.consolidation.group"].with_user(user).create(values)
        self.group.auto_run = False
        other = self.env["res.company"].create({"name": "Unrelated Ltd", "currency_id": self.group.currency_id.id})
        user.company_ids = [Command.link(other.id)]
        user.company_ids = [Command.unlink(other.id)]
        with self.assertRaises(AccessError):
            self.group.with_user(user).write({"member_company_ids": [Command.link(other.id)]})
