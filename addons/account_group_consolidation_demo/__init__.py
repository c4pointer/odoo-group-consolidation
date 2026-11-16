"""Delta Group demo data, created in code on install (see README.rst).

The scenario itself is shared with the tests and lives in
account_group_consolidation/scenario/delta.py.
"""

from datetime import date

from odoo import Command
from odoo.addons.account_group_consolidation.scenario.delta import DeltaScenario


def post_init_hook(env):
    scenario = DeltaScenario(env).build()
    # The hook runs as the superuser; the person who logs in is admin, who needs the Delta
    # companies in the company switcher to follow the README.
    admin = env.ref("base.user_admin")
    admin.company_ids = [Command.link(company.id) for company in scenario.companies.values()]
    admin.company_id = scenario.companies["us"]
    # The auditor's step needs journal items: the accounting administrator group does not
    # include "Show Full Accounting Features" in Odoo 20.
    admin.group_ids = [Command.link(env.ref("account.group_account_user").id)]
    # January and February are closed already; March is left for the controller to run.
    for month in (1, 2):
        run = env["account.consolidation.run"].create(
            {"group_id": scenario.consolidation_group.id, "date_from": date(2026, month, 1)}
        )
        run.action_run()
