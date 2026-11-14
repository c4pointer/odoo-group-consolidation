"""Delta Group scenario, January to April 2026.

Three operating companies and one consolidation company, with the documents
described in docs/expected_numbers.md. Used by the demo module and by the
tests, so the demo a controller clicks through is the data the tests prove.

Conventions:
- every amount below is in the document currency;
- exchange rates are local currency units per 1 USD;
- "accounting date" differs from "invoice date" only where the task says so
  (Ukraine's March invoice, booked by Delta US on 2 April).
"""

from datetime import date

from odoo import Command

# Month-end closing rates, in units of local currency per 1 USD.
# Odoo 20 applies a rate from the day after its date, so each month-end rate is used for
# every transaction of the following month; it is also that month's average rate.
RATES = {
    "UAH": {
        date(2025, 12, 31): 40.0,
        date(2026, 1, 31): 41.0,
        date(2026, 2, 28): 42.0,
        date(2026, 3, 31): 43.0,
        date(2026, 4, 30): 44.0,
    },
    "PLN": {
        date(2025, 12, 31): 4.0,
        date(2026, 1, 31): 4.0,
        date(2026, 2, 28): 4.0,
        date(2026, 3, 31): 3.9,
        date(2026, 4, 30): 3.9,
    },
}

MONTH_ENDS = (date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31))

# Account codes of Odoo's generic chart of accounts (padded to six digits), plus a few added here.
ACC_BANK_PREFIX = "1014"
ACC_RECEIVABLE = "121000"
ACC_PAYABLE = "211000"
ACC_SALARY_PAYABLE = "230000"
ACC_CAPITAL = "301000"
ACC_REVENUE = "400000"
ACC_EXPENSE = "600000"
ACC_RENT = "612000"
ACC_SALARY = "630000"
ACC_IC_LOAN_RECEIVABLE = "192000"
ACC_IC_LOAN_PAYABLE = "292000"
ACC_CASH_IN_TRANSIT = "101800"
ACC_IC_CLEARING = "199900"

EXTRA_ACCOUNTS = {
    ACC_IC_LOAN_RECEIVABLE: ("Loans to group companies", "asset_non_current"),
    ACC_IC_LOAN_PAYABLE: ("Loans from group companies", "liability_non_current"),
    ACC_CASH_IN_TRANSIT: ("Group cash in transit", "asset_current"),
    ACC_IC_CLEARING: ("Intercompany clearing", "asset_current"),
}


class DeltaScenario:
    """Builds the Delta Group companies and documents. Call `build()` once."""

    def __init__(self, env):
        self.env = env
        self.usd = env.ref("base.USD")
        self.uah = env.ref("base.UAH")
        self.pln = env.ref("base.PLN")
        self.companies = {}
        self.partners = {}
        self.usd_bank = {}
        self.moves = {}
        self.consolidation_group = None

    # ------------------------------------------------------------------ build

    def build(self):
        self._setup_currencies()
        self._setup_companies()
        self._setup_partners()
        self._post_delta_us()
        self._post_delta_ukraine()
        self._post_delta_poland()
        self._post_intercompany()
        self._setup_consolidation()
        return self

    # ------------------------------------------------------------- reference data

    def _setup_currencies(self):
        (self.usd | self.uah | self.pln).active = True
        rate_model = self.env["res.currency.rate"]
        for currency in (self.uah, self.pln):
            for day, units_per_usd in RATES[currency.name].items():
                # Global rates (no company) apply to every company in the database.
                rate_model.create(
                    {
                        "currency_id": currency.id,
                        "name": day,
                        "rate": units_per_usd,
                        "company_id": False,
                    }
                )

    def _setup_companies(self):
        specs = {
            "us": ("Delta US Inc.", self.usd, "base.us"),
            "ua": ("Delta Ukraine LLC", self.uah, "base.ua"),
            "pl": ("Delta Poland sp. z o.o.", self.pln, "base.pl"),
            "group": ("Delta Group Consolidation", self.usd, "base.us"),
        }
        chart = self.env["account.chart.template"]
        for key, (name, currency, country) in specs.items():
            company = self.env["res.company"].create(
                {"name": name, "currency_id": currency.id, "country_id": self.env.ref(country).id}
            )
            chart.try_loading("generic_coa", company, install_demo=False)
            # Loading a chart resets the currency to the template's fiscal country (US for
            # the generic chart); restore the company's own currency before any entry exists.
            company.currency_id = currency
            self.companies[key] = company

        self._create_extra_accounts()
        for key in ("ua", "pl"):
            self.usd_bank[key] = self.env["account.journal"].create(
                {
                    "name": "Bank USD",
                    "code": "BUSD",
                    "type": "bank",
                    "currency_id": self.usd.id,
                    "company_id": self.companies[key].id,
                }
            )
        self.env["account.journal"].create(
            {
                "name": "Eliminations",
                "code": "ELIM",
                "type": "general",
                "company_id": self.companies["group"].id,
            }
        )

        user = self.env.user
        user.company_ids = [Command.link(c.id) for c in self.companies.values()]
        user.company_id = self.companies["us"]

    def _create_extra_accounts(self):
        needed = {
            "us": [ACC_IC_LOAN_RECEIVABLE],
            "ua": [ACC_IC_LOAN_PAYABLE],
            "group": list(EXTRA_ACCOUNTS),
        }
        for key, codes in needed.items():
            company = self.companies[key]
            for code in codes:
                name, account_type = EXTRA_ACCOUNTS[code]
                self.env["account.account"].with_company(company).create(
                    {
                        "code": code,
                        "name": name,
                        "account_type": account_type,
                        "company_ids": [Command.set(company.ids)],
                    }
                )

    def _setup_partners(self):
        partner = self.env["res.partner"]
        for key in ("us", "ua", "pl"):
            self.partners[key] = self.companies[key].partner_id
        externals = {
            "us_client": "Northwind Health (US client)",
            "us_vendor": "Cumulus Cloud Hosting (US vendor)",
            "ua_client": "Dnipro Logistics (Ukrainian client)",
            "ua_vendor": "Podil Business Centre (Kyiv office rent)",
            "pl_client": "Wisla Retail (Polish client)",
            "pl_vendor": "Krakow Facility Services (Polish vendor)",
        }
        for key, name in externals.items():
            self.partners[key] = partner.create({"name": name, "is_company": True})

    # -------------------------------------------------------------- documents

    def _post_delta_us(self):
        us = self.companies["us"]
        bank = self._default_bank_account(us)
        self._entry(
            us,
            date(2026, 1, 1),
            "Share capital paid in by external shareholders",
            [(bank, 1_000_000.0), (self._account(us, ACC_CAPITAL), -1_000_000.0)],
        )
        for month_end, sales in zip(MONTH_ENDS, (300_000.0, 320_000.0, 350_000.0), strict=True):
            day = month_end.replace(day=25)
            self._invoice(
                us,
                "out_invoice",
                "us_client",
                day,
                sales,
                self.usd,
                ACC_REVENUE,
                "Software delivery to US client",
            )
            self._invoice(
                us, "in_invoice", "us_vendor", day, 20_000.0, self.usd, ACC_EXPENSE, "Cloud hosting"
            )
            self._payroll(us, month_end, 80_000.0)

    def _post_delta_ukraine(self):
        ua = self.companies["ua"]
        monthly = zip(
            MONTH_ENDS,
            (400_000.0, 410_000.0, 420_000.0),
            (200_000.0, 205_000.0, 210_000.0),
            (1_200_000.0, 1_230_000.0, 1_260_000.0),
            strict=True,
        )
        for month_end, sales, rent, payroll in monthly:
            day = month_end.replace(day=15)
            self._invoice(
                ua,
                "out_invoice",
                "ua_client",
                day,
                sales,
                self.uah,
                ACC_REVENUE,
                "Engineering services to local client",
            )
            self._invoice(
                ua, "in_invoice", "ua_vendor", day, rent, self.uah, ACC_RENT, "Office rent"
            )
            self._payroll(ua, month_end, payroll)

    def _post_delta_poland(self):
        pl = self.companies["pl"]
        for month_end in MONTH_ENDS:
            day = month_end.replace(day=15)
            self._invoice(
                pl,
                "out_invoice",
                "pl_client",
                day,
                200_000.0,
                self.pln,
                ACC_REVENUE,
                "Design services to Polish client",
            )
            self._invoice(
                pl,
                "in_invoice",
                "pl_vendor",
                day,
                40_000.0,
                self.pln,
                ACC_EXPENSE,
                "Facility services",
            )
            self._payroll(pl, month_end, 150_000.0)

    def _post_intercompany(self):
        us, ua, pl = (self.companies[k] for k in ("us", "ua", "pl"))

        # Loan of USD 200,000 from Delta US to Delta Ukraine on 15 January (rate 40.00).
        self._entry(
            us,
            date(2026, 1, 15),
            "Loan to Delta Ukraine",
            [
                (self._account(us, ACC_IC_LOAN_RECEIVABLE), 200_000.0, "ua"),
                (self._default_bank_account(us), -200_000.0),
            ],
        )
        self._entry(
            ua,
            date(2026, 1, 15),
            "Loan from Delta US",
            [
                (self.usd_bank["ua"].default_account_id, 8_000_000.0, None, 200_000.0),
                (self._account(ua, ACC_IC_LOAN_PAYABLE), -8_000_000.0, "us", -200_000.0),
            ],
            journal=self.usd_bank["ua"],
        )

        # Ukraine -> US: invoices on the last day of each month; Delta US books March on 2 April.
        for month_end, amount in zip(MONTH_ENDS, (40_000.0, 45_000.0, 50_000.0), strict=True):
            key = f"ua_inv_{month_end.month}"
            self.moves[key] = self._invoice(
                ua,
                "out_invoice",
                "us",
                month_end,
                amount,
                self.usd,
                ACC_REVENUE,
                "Engineering services for client projects",
            )
            booked = date(2026, 4, 2) if month_end.month == 3 else month_end
            self.moves[f"us_bill_ua_{month_end.month}"] = self._invoice(
                us,
                "in_invoice",
                "ua",
                month_end,
                amount,
                self.usd,
                ACC_EXPENSE,
                "Engineering services from Delta Ukraine",
                accounting_date=booked,
                ref=self.moves[key].name,
            )

        # Poland -> US: invoices on the last day of each month, booked the same day by Delta US.
        for month_end, amount in zip(MONTH_ENDS, (20_000.0, 22_000.0, 25_000.0), strict=True):
            key = f"pl_inv_{month_end.month}"
            self.moves[key] = self._invoice(
                pl,
                "out_invoice",
                "us",
                month_end,
                amount,
                self.usd,
                ACC_REVENUE,
                "Design services for client projects",
            )
            self.moves[f"us_bill_pl_{month_end.month}"] = self._invoice(
                us,
                "in_invoice",
                "pl",
                month_end,
                amount,
                self.usd,
                ACC_EXPENSE,
                "Design services from Delta Poland",
                ref=self.moves[key].name,
            )

        # Partial credit note of USD 2,000 on Poland's February invoice, both sides on 15 March.
        credit_day = date(2026, 3, 15)
        self.moves["pl_refund"] = self._invoice(
            pl,
            "out_refund",
            "us",
            credit_day,
            2_000.0,
            self.usd,
            ACC_REVENUE,
            "Partial credit: February design services",
            reversed_entry=self.moves["pl_inv_2"],
        )
        self.moves["us_refund_pl"] = self._invoice(
            us,
            "in_refund",
            "pl",
            credit_day,
            2_000.0,
            self.usd,
            ACC_EXPENSE,
            "Partial credit: February design services",
            reversed_entry=self.moves["us_bill_pl_2"],
            ref=self.moves["pl_refund"].name,
        )

        # Delta US pays Poland USD 40,000 on 31 March; Poland records it on 1 April at 3.90.
        # The invoices were booked at 4.00, so reconciliation books a realised FX loss of
        # PLN 4,000 in April.
        us_payment = self._entry(
            us,
            date(2026, 3, 31),
            "Payment to Delta Poland: January and February net of credit note",
            [
                (self._account(us, ACC_PAYABLE), 40_000.0, "pl"),
                (self._default_bank_account(us), -40_000.0),
            ],
            journal=self._default_bank_journal(us),
        )
        self._reconcile(
            us_payment,
            self.moves["us_bill_pl_1"] | self.moves["us_bill_pl_2"] | self.moves["us_refund_pl"],
            "liability_payable",
        )
        pl_receipt = self._entry(
            pl,
            date(2026, 4, 1),
            "Receipt from Delta US: January and February net of credit note",
            [
                (self.usd_bank["pl"].default_account_id, 156_000.0, None, 40_000.0),
                (self._account(pl, ACC_RECEIVABLE), -156_000.0, "us", -40_000.0),
            ],
            journal=self.usd_bank["pl"],
        )
        self._reconcile(
            pl_receipt,
            self.moves["pl_inv_1"] | self.moves["pl_inv_2"] | self.moves["pl_refund"],
            "asset_receivable",
        )

    # ------------------------------------------------------------ consolidation

    def _setup_consolidation(self):
        """The consolidation group with the rates of oracle section 1, January to April."""
        group_company = self.companies["group"]
        rates = []
        for currency in (self.uah, self.pln):
            month_ends = sorted(RATES[currency.name])
            # The average for a month is the previous month-end rate (see RATES above).
            for previous, month_end in zip(month_ends, month_ends[1:], strict=False):
                rates.append(
                    Command.create(
                        {
                            "currency_id": currency.id,
                            "date": month_end,
                            "average_rate": RATES[currency.name][previous],
                            "closing_rate": RATES[currency.name][month_end],
                        }
                    )
                )
        self.consolidation_group = self.env["account.consolidation.group"].create(
            {
                "name": "Delta Group",
                "company_id": group_company.id,
                "member_company_ids": [
                    Command.set([self.companies[k].id for k in ("us", "ua", "pl")])
                ],
                "journal_id": self.env["account.journal"]
                .search([("company_id", "=", group_company.id), ("code", "=", "ELIM")])
                .id,
                "clearing_account_id": self._account(group_company, ACC_IC_CLEARING).id,
                "transit_account_id": self._account(group_company, ACC_CASH_IN_TRANSIT).id,
                "start_date": date(2026, 1, 1),
                "rate_ids": rates,
            }
        )

    # ---------------------------------------------------------------- helpers

    def _account(self, company, code):
        account = (
            self.env["account.account"]
            .with_company(company)
            .search([("code", "=", code), ("company_ids", "in", company.id)], limit=1)
        )
        if not account:
            raise ValueError(f"Account {code} not found in {company.name}")
        return account

    def _default_bank_journal(self, company):
        return self.env["account.journal"].search(
            [
                ("company_id", "=", company.id),
                ("type", "=", "bank"),
                ("currency_id", "in", (False, company.currency_id.id)),
            ],
            limit=1,
        )

    def _default_bank_account(self, company):
        return self._default_bank_journal(company).default_account_id

    def _invoice(
        self,
        company,
        move_type,
        partner_key,
        invoice_date,
        amount,
        currency,
        account_code,
        label,
        accounting_date=None,
        ref=None,
        reversed_entry=None,
    ):
        move = (
            self.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": move_type,
                    "company_id": company.id,
                    "partner_id": self.partners[partner_key].id,
                    "invoice_date": invoice_date,
                    "date": accounting_date or invoice_date,
                    "currency_id": currency.id,
                    "ref": ref,
                    "reversed_entry_id": reversed_entry.id if reversed_entry else False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": label,
                                "quantity": 1.0,
                                "price_unit": amount,
                                "account_id": self._account(company, account_code).id,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )
        move.action_post()
        return move

    def _payroll(self, company, month_end, amount):
        return self._entry(
            company,
            month_end,
            f"Payroll accrual {month_end:%B %Y}",
            [
                (self._account(company, ACC_SALARY), amount),
                (self._account(company, ACC_SALARY_PAYABLE), -amount),
            ],
        )

    def _entry(self, company, entry_date, ref, lines, journal=None):
        """Post a journal entry.

        Each line is (account, balance[, partner_key[, usd_amount]]): balance is in
        company currency, positive for debit; usd_amount marks a USD-denominated line.
        """
        line_vals = []
        for account, balance, *rest in lines:
            partner_key = rest[0] if rest else None
            usd_amount = rest[1] if len(rest) > 1 else None
            vals = {
                "name": ref,
                "account_id": account.id,
                "debit": max(balance, 0.0),
                "credit": max(-balance, 0.0),
                "partner_id": self.partners[partner_key].id if partner_key else False,
            }
            if usd_amount is not None:
                vals.update({"currency_id": self.usd.id, "amount_currency": usd_amount})
            line_vals.append(Command.create(vals))
        journal = journal or self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "general"), ("code", "=", "MISC")],
            limit=1,
        )
        move = (
            self.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": "entry",
                    "company_id": company.id,
                    "date": entry_date,
                    "ref": ref,
                    "journal_id": journal.id,
                    "line_ids": line_vals,
                }
            )
        )
        move.action_post()
        return move

    @staticmethod
    def _reconcile(payment, documents, account_type):
        lines = (payment | documents).line_ids.filtered(
            lambda line: line.account_id.account_type == account_type and not line.reconciled
        )
        lines.reconcile()
