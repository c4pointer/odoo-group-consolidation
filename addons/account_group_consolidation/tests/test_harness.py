from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHarness(TransactionCase):
    """Proves that `make test` discovers and runs this module's tests."""

    def test_module_installed(self):
        module = self.env["ir.module.module"].search([("name", "=", "account_group_consolidation")])
        self.assertEqual(module.state, "installed")
