from datetime import date

from odoo.addons.account_group_consolidation.scenario.delta import DeltaScenario


def post_init_hook(env):
    scenario = DeltaScenario(env).build()
    # January and February are closed already; March is left for the controller to run.
    for month in (1, 2):
        run = env["account.consolidation.run"].create(
            {"group_id": scenario.consolidation_group.id, "date_from": date(2026, month, 1)}
        )
        run.action_run()
