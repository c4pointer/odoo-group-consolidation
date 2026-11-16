==========================================
Group Consolidation: Delta Group demo data
==========================================

Installing this module loads the Delta Group demo data with one step. It has
no data files on purpose: the data is created in code by ``post_init_hook``
in ``__init__.py``.

Where the data comes from
=========================

The hook calls ``DeltaScenario(env).build()`` from
``account_group_consolidation/scenario/delta.py``. The scenario creates:

- Delta US Inc. (USD), Delta Ukraine LLC (UAH), Delta Poland sp. z o.o. (PLN)
  and the consolidation company, each with Odoo's generic chart of accounts;
- the UAH and PLN exchange rates for December 2025 to April 2026;
- each company's own posted documents, the intercompany invoices, the partial
  credit note, the USD 200,000 loan and the payments, January to April 2026;
- the Eliminations journal and the consolidation group with its members and
  monthly average and closing rates.

The report lines come from the main module's own data, not from this module.

The hook then gives ``admin`` access to the Delta companies and runs the
January and February consolidation, leaving March for the controller.

Why the scenario lives in the main module
=========================================

The module's tests build the same scenario, so the demo a controller clicks
through is exactly the data the tests prove. ``make test`` installs only
``account_group_consolidation``, which cannot depend on this module, so the
shared code sits in the main module. The main module never imports it on
install: installing ``account_group_consolidation`` alone loads no demo data.

The data is built with the ORM, not XML records, because it needs companies
with a loaded chart of accounts, posted invoices and reconciled payments.

Loading and reloading
=====================

- ``make demo`` recreates the database ``delta`` with this module installed.
- ``make demo-data DB=<name>`` installs it on an existing database.

Uninstalling removes nothing, since the records are not XML data and posted
entries are never deleted; recreate the database with ``make demo`` instead.
