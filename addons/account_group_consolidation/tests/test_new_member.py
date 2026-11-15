"""A company that joins the group needs configuration, not code.

Delta Germany GmbH (EUR) starts trading on 1 March 2026, after January and
February are closed. It sells to a German client in EUR and invoices Delta US
in USD; Delta US books the invoice the same day. The controller adds Germany to
the members and enters the EUR rates for March; nothing else changes.

Expected figures are worked out by hand from the oracle's March figures plus
Germany's two documents; the arithmetic is written next to each constant.
"""

from datetime import date

from odoo import Command
from odoo.addons.account_group_consolidation.scenario import delta
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import DeltaCase

# EUR per 1 USD in March: average for the P&L, closing for the balance sheet.
EUR_AVERAGE_MARCH = 0.92
EUR_CLOSING_MARCH = 0.90

# Delta Germany, March, in USD:
#   external sale      EUR 92,000 / 0.92 average = 100,000.00
#   sale to Delta US   USD 30,000, taken at its USD amount
#   receivable         EUR 92,000 / 0.90 closing = 102,222.22
#   translation reserve  132,222.22 assets - 130,000.00 profit = 2,222.22
GERMANY_MARCH = {
    "revenue": 100_000.00,
    "ic_revenue": 30_000.00,
    "net_profit": 130_000.00,
    "receivables": 102_222.22,
    "ic_receivables": 30_000.00,
    "total_assets": 132_222.22,
    "profit": 130_000.00,
    "cta": 2_222.22,
    "total_liabilities_equity": 132_222.22,
}

# Delta Germany, March, in its own books (EUR). Odoo converts the USD invoice at
# the 28 February rate, as it does for Ukraine and Poland: 30,000 x 0.92 = 27,600.
GERMANY_MARCH_LOCAL = {
    "revenue": 92_000.00,
    "ic_revenue": 27_600.00,
    "net_profit": 119_600.00,
    "receivables": 92_000.00,
    "ic_receivables": 27_600.00,
    "total_assets": 119_600.00,
}

# Group, March, in USD: the oracle's group figures plus Germany.
#   revenue        410,000.00 + 100,000.00 = 510,000.00 (the 30,000 to Delta US is eliminated)
#   net profit     227,500.00 + 100,000.00 = 327,500.00
#   receivables  1,152,450.80 + 102,222.22 = 1,254,673.02
#   total assets 2,152,450.80 + 132,222.22 - 30,000.00 = 2,254,673.02
#   profit (YTD)   602,500.00 + 130,000.00 - 30,000.00 (Delta US cost) = 702,500.00
#   reserve          3,680.67 + 2,222.22 = 5,902.89
GROUP_MARCH = {
    "revenue": 510_000.00,
    "ic_revenue": 0.00,
    "ic_cost": 0.00,
    "net_profit": 327_500.00,
    "receivables": 1_254_673.02,
    "ic_receivables": 0.00,
    "ic_payables": 0.00,
    "total_assets": 2_254_673.02,
    "profit": 702_500.00,
    "cta": 5_902.89,
    "total_liabilities_equity": 2_254_673.02,
}


class GermanyCase(DeltaCase):
    """January and February closed, then Delta Germany joins and March is run.

    Subclasses post Germany's March documents in `_post_march`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.scenario.consolidation_group
        cls.closed = {month: cls._run(date(2026, month, 1)) for month in (1, 2)}
        cls.germany = cls._add_germany()
        cls._post_march()
        cls.march = cls._run(date(2026, 3, 1))

    @classmethod
    def _post_march(cls):
        raise NotImplementedError

    @classmethod
    def _run(cls, first):
        run = cls.env["account.consolidation.run"].create(
            {"group_id": cls.group.id, "date_from": first}
        )
        run.action_run()
        return run

    @classmethod
    def _add_germany(cls):
        scenario = cls.scenario
        eur = cls.env.ref("base.EUR")
        eur.active = True
        # Odoo converts at the latest rate dated on or before the document: 28 February's here.
        odoo_rates = (
            (date(2026, 2, 28), EUR_AVERAGE_MARCH),
            (date(2026, 3, 31), EUR_CLOSING_MARCH),
        )
        for day, rate in odoo_rates:
            cls.env["res.currency.rate"].create(
                {"currency_id": eur.id, "name": day, "rate": rate, "company_id": False}
            )
        germany = scenario.add_company("de", "Delta Germany GmbH", eur, "base.de")
        scenario.partners["de_client"] = cls.env["res.partner"].create(
            {"name": "Elbe Maschinenbau (German client)", "is_company": True}
        )

        # The whole change a controller makes: one more member and its rates.
        cls.group.write(
            {
                "member_company_ids": [Command.link(germany.id)],
                "rate_ids": [
                    Command.create(
                        {
                            "currency_id": eur.id,
                            "date": date(2026, 3, 31),
                            "average_rate": EUR_AVERAGE_MARCH,
                            "closing_rate": EUR_CLOSING_MARCH,
                        }
                    )
                ],
            }
        )

        return germany

    def _group_columns(self):
        return self.group.member_company_ids | self.group.company_id


@tagged("post_install", "-at_install")
class TestNewMember(GermanyCase):
    @classmethod
    def _post_march(cls):
        scenario = cls.scenario
        eur = cls.env.ref("base.EUR")
        scenario._invoice(
            cls.germany,
            "out_invoice",
            "de_client",
            date(2026, 3, 15),
            92_000.0,
            eur,
            delta.ACC_REVENUE,
            "Engineering services to German client",
        )
        invoice = scenario._invoice(
            cls.germany,
            "out_invoice",
            "us",
            date(2026, 3, 20),
            30_000.0,
            scenario.usd,
            delta.ACC_REVENUE,
            "Engineering services for client projects",
        )
        scenario._invoice(
            cls.companies["us"],
            "in_invoice",
            "de",
            date(2026, 3, 20),
            30_000.0,
            scenario.usd,
            delta.ACC_EXPENSE,
            "Engineering services from Delta Germany",
            ref=invoice.name,
        )

    def test_germany_is_translated(self):
        self.assertFigures(self.march.get_figures(self.germany), GERMANY_MARCH, "Germany USD")
        self.assertFigures(
            self.march.get_figures(self.germany, local=True), GERMANY_MARCH_LOCAL, "Germany EUR"
        )

    def test_group_figures_march(self):
        self.assertEqual(self.march.state, "done")
        self.assertFigures(self.march.get_figures(self._group_columns()), GROUP_MARCH, "Group")

    def test_pair_with_germany_is_eliminated(self):
        us = self.companies["us"]
        pair = (us | self.germany).partner_id
        moves = self.march.move_ids.filtered(
            lambda move: move.line_ids.partner_id and move.line_ids.partner_id <= pair
        )
        profit_and_loss = moves.filtered(lambda move: move.consolidation_kind == "pl")
        balance_sheet = moves.filtered(lambda move: move.consolidation_kind == "bs")
        self.assertEqual(len(profit_and_loss), 1)
        self.assertEqual(
            sorted(balance_sheet.mapped("date")), [date(2026, 3, 31), date(2026, 4, 1)]
        )

        def removed(move, company):
            return sum(
                move.line_ids.filtered(lambda line: line.partner_id == company.partner_id).mapped(
                    "balance"
                )
            )

        # Germany's revenue and Delta US's cost leave the group, exactly, in USD.
        self.assertAlmostEqual(removed(profit_and_loss, self.germany), 30_000.00, places=2)
        self.assertAlmostEqual(removed(profit_and_loss, us), -30_000.00, places=2)
        month_end = balance_sheet.filtered(lambda move: move.date == date(2026, 3, 31))
        self.assertAlmostEqual(removed(month_end, self.germany), -30_000.00, places=2)
        self.assertAlmostEqual(removed(month_end, us), 30_000.00, places=2)

        difference = self.march.difference_ids.filtered(
            lambda row: {row.first_company_id, row.second_company_id} == {us, self.germany}
        )
        self.assertEqual(len(difference), 1)
        self.assertAlmostEqual(difference.timing_difference, 0.0, places=2)
        self.assertAlmostEqual(difference.cash_in_transit, 0.0, places=2)
        self.assertAlmostEqual(self.march.clearing_balance, 0.0, places=2)

    def test_germany_books_are_not_touched(self):
        self.assertEqual(self.march.move_ids.company_id, self.group.company_id)
        self.assertFalse(
            self.env["account.move"].search_count(
                [("company_id", "=", self.germany.id), ("consolidation_run_id", "!=", False)]
            )
        )

    def test_closed_months_keep_their_figures(self):
        for month, run in self.closed.items():
            with self.subTest(month=month):
                self.assertEqual(run.state, "done")
                self.assertAlmostEqual(
                    run.get_figures(run.group_id.member_company_ids | run.group_id.company_id)[
                        "net_profit"
                    ],
                    self.expected.GROUP_PL[month]["net_profit"],
                    delta=self.expected.TOLERANCE,
                )

    def test_joining_with_history_in_a_closed_month_is_refused(self):
        """A February pair booked by both sides nets to zero; the books check still sees it."""
        eur, usd = self.env.ref("base.EUR"), self.scenario.usd
        self.group.rate_ids = [
            Command.create(
                {
                    "currency_id": eur.id,
                    "date": date(2026, 2, 28),
                    "average_rate": EUR_AVERAGE_MARCH,
                    "closing_rate": EUR_AVERAGE_MARCH,
                }
            )
        ]
        invoice = self.scenario._invoice(
            self.germany,
            "out_invoice",
            "us",
            date(2026, 2, 20),
            10_000.0,
            usd,
            delta.ACC_REVENUE,
            "February services",
        )
        self.scenario._invoice(
            self.companies["us"],
            "in_invoice",
            "de",
            date(2026, 2, 20),
            10_000.0,
            usd,
            delta.ACC_EXPENSE,
            "February services from Delta Germany",
            ref=invoice.name,
        )
        with self.assertRaisesRegex(UserError, "February 2026"):
            self.march.action_run()


@tagged("post_install", "-at_install")
class TestThirdCurrencyIntercompany(GermanyCase):
    """Germany invoices Delta US in EUR, neither the group's currency nor Delta US's.

    By hand, in USD: EUR 27,600 / 0.92 average = 30,000.00 revenue and cost;
    EUR 27,600 / 0.90 closing = 30,666.67 receivable and payable at 31 March.
    Delta US booked the bill at 30,000.00; the 666.67 goes to its translation
    reserve and the opposite 666.67 to Germany's, so the group is the oracle's March.
    """

    @classmethod
    def _post_march(cls):
        eur = cls.env.ref("base.EUR")
        invoice = cls.scenario._invoice(
            cls.germany,
            "out_invoice",
            "us",
            date(2026, 3, 20),
            27_600.0,
            eur,
            delta.ACC_REVENUE,
            "Engineering services, invoiced in EUR",
        )
        cls.scenario._invoice(
            cls.companies["us"],
            "in_invoice",
            "de",
            date(2026, 3, 20),
            27_600.0,
            eur,
            delta.ACC_EXPENSE,
            "Engineering services from Delta Germany, in EUR",
            ref=invoice.name,
        )

    def test_both_sides_at_the_group_rate(self):
        germany = self.march.get_figures(self.germany)
        us = self.march.get_figures(self.companies["us"])
        self.assertAlmostEqual(germany["ic_revenue"], 30_000.00, delta=0.01)
        self.assertAlmostEqual(germany["ic_receivables"], 30_666.67, delta=0.01)
        self.assertAlmostEqual(germany["cta"], 666.67, delta=0.01)
        # 110,000.00 owed to Ukraine and Poland, plus 30,666.67 owed to Germany.
        self.assertAlmostEqual(us["ic_payables"], 140_666.67, delta=0.01)
        self.assertAlmostEqual(us["cta"], -666.67, delta=0.01)

    def test_pair_eliminates_with_no_difference(self):
        us = self.companies["us"]
        pair = self.march.difference_ids.filtered(
            lambda row: {row.first_company_id, row.second_company_id} == {us, self.germany}
        )
        self.assertAlmostEqual(pair.timing_difference, 0.0, delta=0.01)
        self.assertAlmostEqual(pair.cash_in_transit, 0.0, delta=0.01)
        self.assertAlmostEqual(self.march.clearing_balance, 0.0, delta=0.01)

    def test_group_is_the_oracle_march(self):
        figures = self.march.get_figures(self._group_columns())
        self.assertFigures(figures, self.expected.GROUP_PL[3], "Group P&L")
        self.assertFigures(figures, self.expected.GROUP_BS_MARCH["group"], "Group balance sheet")
