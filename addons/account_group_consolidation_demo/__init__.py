from odoo.addons.account_group_consolidation.scenario.delta import DeltaScenario


def post_init_hook(env):
    """Create the Delta Group companies and documents when the demo module is installed."""
    DeltaScenario(env).build()
