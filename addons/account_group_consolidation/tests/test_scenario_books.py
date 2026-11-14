"""Each company's own books match the oracle, read straight from journal items.

These tests use no consolidation code: they sum posted journal items by account
code, account type and partner. They prove the scenario is the one the oracle
was computed from, so a later failure in the group figures points at the module.
"""

from datetime import date

from odoo.tests import tagged

from .common import DeltaCase, month_bounds

# Test-side reading of the generic chart: line -> (account codes, partner filter).
PL_LINES = {
    "revenue": (("400000",), "external"),
    "ic_revenue": (("400000",), "intercompany"),
    "ic_cost": (("600000",), "intercompany"),
    "payroll": (("630000",), "any"),
    "other_costs": (("600000", "612000"), "external"),
    "fx": (("441000", "641000"), "any"),
}
BS_LINES = {
    "receivables": (("121000",), "external"),
    "ic_receivables": (("121000",), "intercompany"),
    "ic_loan_receivable": (("192000",), "any"),
    "payables": (("211000",), "external"),
    "salaries_payable": (("230000",), "any"),
    "ic_payables": (("211000",), "intercompany"),
    "ic_loan_payable": (("292000",), "any"),
    "share_capital": (("301000",), "any"),
}
ASSET_TYPES = ("asset_cash", "asset_receivable", "asset_current", "asset_non_current")
PL_TYPES = ("income", "income_other", "expense", "expense_direct_cost", "expense_depreciation")


@tagged("post_install", "-at_install")
class TestScenarioBooks(DeltaCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = ("us", "ua", "pl")
        cls.group_partners = {cls.companies[k].partner_id for k in group}

    def _balances(self, company, date_from, date_to):
        """Return {(account code, account type, partner): balance} in company currency."""
        domain = [
            ("company_id", "=", company.id),
            ("parent_state", "=", "posted"),
            ("date", "<=", date_to),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        rows = self.env["account.move.line"]._read_group(
            domain, ["account_id", "partner_id"], ["balance:sum"]
        )
        result = {}
        for account, partner, balance in rows:
            account = account.with_company(company)
            key = (account.code, account.account_type, partner)
            result[key] = result.get(key, 0.0) + balance
        return result

    def _is_ic(self, company, partner):
        return partner in self.group_partners and partner != company.partner_id

    def _sum(self, company, balances, codes, partners):
        total = 0.0
        for (code, _type, partner), balance in balances.items():
            if code not in codes:
                continue
            is_ic = self._is_ic(company, partner)
            if partners == "any" or (partners == "intercompany") == is_ic:
                total += balance
        return total

    def _profit_and_loss(self, company, date_from, date_to):
        balances = self._balances(company, date_from, date_to)
        figures = {
            line: -self._sum(company, balances, codes, partners)
            for line, (codes, partners) in PL_LINES.items()
        }
        figures["net_profit"] = -sum(
            balance for (_c, kind, _p), balance in balances.items() if kind in PL_TYPES
        )
        return figures

    def _balance_sheet(self, company, at):
        balances = self._balances(company, None, at)
        figures = {
            line: (1 if line.endswith("receivable") or line.endswith("receivables") else -1)
            * self._sum(company, balances, codes, partners)
            for line, (codes, partners) in BS_LINES.items()
        }
        figures["bank"] = sum(
            balance for (_c, kind, _p), balance in balances.items() if kind == "asset_cash"
        )
        figures["profit"] = -sum(
            balance for (_c, kind, _p), balance in balances.items() if kind in PL_TYPES
        )
        figures["total_assets"] = sum(
            balance for (_c, kind, _p), balance in balances.items() if kind in ASSET_TYPES
        )
        figures["total_liabilities_equity"] = -sum(
            balance for (_c, kind, _p), balance in balances.items() if kind not in ASSET_TYPES
        )
        return figures

    # ------------------------------------------------------------------ tests

    def test_profit_and_loss_march(self):
        first, last = month_bounds(3)
        for key, expected in self.expected.STANDALONE_PL_MARCH.items():
            actual = self._profit_and_loss(self.companies[key], first, last)
            self.assertFigures(actual, expected, f"{key} P&L March")

    def test_balance_sheet_31_march(self):
        _first, last = month_bounds(3)
        for key, expected in self.expected.STANDALONE_BS_MARCH.items():
            actual = self._balance_sheet(self.companies[key], last)
            self.assertFigures(actual, expected, f"{key} balance sheet 31 March")

    def test_every_account_is_read(self):
        """Lines above plus bank and P&L types cover every balance: nothing is left unread."""
        _first, last = month_bounds(3)
        known_codes = {
            code for codes, _p in (*PL_LINES.values(), *BS_LINES.values()) for code in codes
        }
        for key in ("us", "ua", "pl"):
            balances = self._balances(self.companies[key], None, last)
            unread = {
                code
                for (code, kind, _p), balance in balances.items()
                if code not in known_codes and kind != "asset_cash" and balance
            }
            self.assertFalse(unread, f"{key} has balances on accounts no line reads: {unread}")

    def test_cut_off_ukraine_march_invoice(self):
        """Ukraine invoices on 31 March; Delta US books the bill on 2 April."""
        invoice = self.moves["ua_inv_3"]
        bill = self.moves["us_bill_ua_3"]
        self.assertEqual(invoice.date, date(2026, 3, 31))
        self.assertEqual(bill.invoice_date, date(2026, 3, 31))
        self.assertEqual(bill.date, date(2026, 4, 2))
        self.assertEqual(bill.amount_total, invoice.amount_total)

    def test_partial_credit_note(self):
        """USD 2,000 credit on Poland's February invoice, linked to it on both sides."""
        refund = self.moves["pl_refund"]
        self.assertEqual(refund.move_type, "out_refund")
        self.assertEqual(refund.reversed_entry_id, self.moves["pl_inv_2"])
        self.assertEqual(refund.amount_total, 2_000.0)
        self.assertEqual(self.moves["us_refund_pl"].reversed_entry_id, self.moves["us_bill_pl_2"])

    def test_payment_in_transit(self):
        """Delta US has paid on 31 March; Delta Poland still shows the receivable that day."""
        for key in ("us_bill_pl_1", "us_bill_pl_2"):
            self.assertTrue(self.moves[key].currency_id.is_zero(self.moves[key].amount_residual))
        _first, last = month_bounds(3)
        poland, delta_us = self.companies["pl"], self.companies["us"]
        # PLN 260,000 still open at Poland is USD 65,000; Delta US owes Poland only USD 25,000.
        poland_open = self.env["account.move.line"].search(
            [
                ("company_id", "=", poland.id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("partner_id", "=", delta_us.partner_id.id),
                ("parent_state", "=", "posted"),
                ("date", "<=", last),
            ]
        )
        self.assertAlmostEqual(sum(poland_open.mapped("amount_currency")), 65_000.0)
        us_payable = self.env["account.move.line"].search(
            [
                ("company_id", "=", delta_us.id),
                ("account_id.account_type", "=", "liability_payable"),
                ("partner_id", "=", poland.partner_id.id),
                ("parent_state", "=", "posted"),
                ("date", "<=", last),
            ]
        )
        self.assertAlmostEqual(-sum(us_payable.mapped("balance")), 25_000.0)

    def test_realised_exchange_loss_in_april(self):
        """The 1 April receipt at 3.90 settles invoices booked at 4.00: PLN 4,000 loss."""
        poland = self.companies["pl"]
        first, last = month_bounds(4)
        april = self._profit_and_loss(poland, first, last)
        self.assertAlmostEqual(april["fx"], self.expected.APRIL["pl_fx_local"], delta=0.01)
        for key in ("pl_inv_1", "pl_inv_2"):
            self.assertTrue(self.moves[key].currency_id.is_zero(self.moves[key].amount_residual))

    def test_loan_is_usd_on_both_sides(self):
        """USD 200,000: Delta Ukraine owes exactly USD 200,000 whatever the UAH rate."""
        ukraine = self.companies["ua"]
        loan_account = self.scenario._account(ukraine, "292000")
        loan_lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", ukraine.id),
                ("account_id", "=", loan_account.id),
                ("parent_state", "=", "posted"),
            ]
        )
        self.assertTrue(loan_lines)
        self.assertEqual(loan_lines.currency_id, self.env.ref("base.USD"))
        self.assertAlmostEqual(sum(loan_lines.mapped("amount_currency")), -200_000.0)
        self.assertEqual(loan_lines.partner_id, self.companies["us"].partner_id)
