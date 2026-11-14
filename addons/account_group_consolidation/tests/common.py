"""Shared fixture: the Delta Group scenario, built once per test class."""

from datetime import date

from odoo.addons.account_group_consolidation.scenario.delta import DeltaScenario
from odoo.tests import TransactionCase

from . import expected_figures as expected


def month_bounds(month, year=2026):
    first = date(year, month, 1)
    following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first, date.fromordinal(following.toordinal() - 1)


class DeltaCase(TransactionCase):
    """Builds the same companies and documents as `make demo`."""

    expected = expected

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.scenario = DeltaScenario(cls.env).build()
        cls.companies = cls.scenario.companies
        cls.moves = cls.scenario.moves

    def assertFigures(self, actual, expected, label):
        """Compare dicts of report figures line by line, within the oracle's tolerance."""
        for code, value in expected.items():
            with self.subTest(figures=label, line=code):
                self.assertIn(code, actual, f"{label}: line {code} is missing")
                self.assertAlmostEqual(
                    actual[code],
                    value,
                    delta=self.expected.TOLERANCE,
                    msg=f"{label}: {code} is {actual[code]:,.2f}, expected {value:,.2f}",
                )
