"""Expected figures: docs/expected_numbers.md transcribed for the tests.

Human-owned, like the document it copies. Every number here is written out by
hand from the oracle; nothing is computed, so a wrong formula in the module
cannot make its own expectation. Keys are report line codes.

Sign convention, as in the oracle: revenue and gains positive, costs negative;
assets positive, liabilities and equity positive. Tests allow 0.01 per line.
"""

TOLERANCE = 0.01

# Units of local currency per 1 USD (oracle section 1).
RATES = {
    "UAH": {1: (40.00, 41.00), 2: (41.00, 42.00), 3: (42.00, 43.00), 4: (43.00, 44.00)},
    "PLN": {1: (4.00, 4.00), 2: (4.00, 4.00), 3: (4.00, 3.90), 4: (3.90, 3.90)},
}

# Section 4: standalone results in each company's own currency.
STANDALONE_PL_MARCH = {
    "us": {
        "revenue": 350_000.00,
        "ic_revenue": 0.00,
        "ic_cost": -23_000.00,
        "payroll": -80_000.00,
        "other_costs": -20_000.00,
        "fx": 0.00,
        "net_profit": 227_000.00,
    },
    "ua": {
        "revenue": 420_000.00,
        "ic_revenue": 2_100_000.00,
        "ic_cost": 0.00,
        "payroll": -1_260_000.00,
        "other_costs": -210_000.00,
        "fx": 0.00,
        "net_profit": 1_050_000.00,
    },
    "pl": {
        "revenue": 200_000.00,
        "ic_revenue": 92_000.00,
        "ic_cost": 0.00,
        "payroll": -150_000.00,
        "other_costs": -40_000.00,
        "fx": 0.00,
        "net_profit": 102_000.00,
    },
}

STANDALONE_BS_MARCH = {
    "us": {
        "bank": 760_000.00,
        "receivables": 970_000.00,
        "ic_receivables": 0.00,
        "ic_loan_receivable": 200_000.00,
        "total_assets": 1_930_000.00,
        "payables": 60_000.00,
        "salaries_payable": 240_000.00,
        "ic_payables": 110_000.00,
        "ic_loan_payable": 0.00,
        "share_capital": 1_000_000.00,
        "profit": 520_000.00,
        "total_liabilities_equity": 1_930_000.00,
    },
    "ua": {
        "bank": 8_000_000.00,
        "receivables": 1_230_000.00,
        "ic_receivables": 5_545_000.00,
        "ic_loan_receivable": 0.00,
        "total_assets": 14_775_000.00,
        "payables": 615_000.00,
        "salaries_payable": 3_690_000.00,
        "ic_payables": 0.00,
        "ic_loan_payable": 8_000_000.00,
        "share_capital": 0.00,
        "profit": 2_470_000.00,
        "total_liabilities_equity": 14_775_000.00,
    },
    "pl": {
        "bank": 0.00,
        "receivables": 600_000.00,
        "ic_receivables": 260_000.00,
        "ic_loan_receivable": 0.00,
        "total_assets": 860_000.00,
        "payables": 120_000.00,
        "salaries_payable": 450_000.00,
        "ic_payables": 0.00,
        "ic_loan_payable": 0.00,
        "share_capital": 0.00,
        "profit": 290_000.00,
        "total_liabilities_equity": 860_000.00,
    },
}

# Section 5: net profit translated to USD, by month.
TRANSLATED_PROFIT = {
    "us": {1: 140_000.00, 2: 153_000.00, 3: 227_000.00},
    "ua": {1: 15_000.00, 2: 20_000.00, 3: 25_000.00},
    "pl": {1: 22_500.00, 2: 24_500.00, 3: 25_500.00},
}

# Delta Ukraine, March, line by line in USD (section 5 worked example).
TRANSLATED_PL_MARCH_UA = {
    "revenue": 10_000.00,
    "ic_revenue": 50_000.00,
    "payroll": -30_000.00,
    "other_costs": -5_000.00,
    "net_profit": 25_000.00,
}

# Section 5: balance sheet translated to USD at 31 March (closing 43.00 and 3.90).
TRANSLATED_BS_MARCH = {
    "ua": {
        "bank": 200_000.00,
        "receivables": 28_604.65,
        "ic_receivables": 135_000.00,
        "payables": 14_302.33,
        "salaries_payable": 85_813.95,
        "ic_loan_payable": 200_000.00,
        "profit": 60_000.00,
        "cta": 3_488.37,
    },
    "pl": {
        "bank": 0.00,
        "receivables": 153_846.15,
        "ic_receivables": 65_000.00,
        "payables": 30_769.23,
        "salaries_payable": 115_384.62,
        "ic_loan_payable": 0.00,
        "profit": 72_500.00,
        "cta": 192.30,
    },
}

# Section 6: profit and loss eliminations, (seller, buyer) -> month ->
# (seller revenue, buyer cost, difference to IC clearing), all in USD.
PL_ELIMINATIONS = {
    ("ua", "us"): {
        1: (40_000.00, 40_000.00, 0.00),
        2: (45_000.00, 45_000.00, 0.00),
        3: (50_000.00, 0.00, 50_000.00),
    },
    ("pl", "us"): {
        1: (20_000.00, 20_000.00, 0.00),
        2: (22_000.00, 22_000.00, 0.00),
        3: (23_000.00, 23_000.00, 0.00),
    },
}

# Section 6: balance sheet eliminations at 31 March, (creditor, debtor) ->
# (receivable, payable, cash in transit, IC clearing), all in USD.
BS_ELIMINATIONS_MARCH = {
    ("ua", "us", "trade"): (135_000.00, 85_000.00, 0.00, 50_000.00),
    ("pl", "us", "trade"): (65_000.00, 25_000.00, 40_000.00, 0.00),
    ("us", "ua", "loan"): (200_000.00, 200_000.00, 0.00, 0.00),
}

# Control: the IC clearing account nets to zero at every month end.
IC_CLEARING_BALANCE = 0.00

# Section 7: group profit and loss in USD, by month and January-March.
GROUP_PL = {
    1: {
        "revenue": 360_000.00,
        "ic_revenue": 0.00,
        "ic_cost": 0.00,
        "payroll": -147_500.00,
        "other_costs": -35_000.00,
        "net_profit": 177_500.00,
    },
    2: {
        "revenue": 380_000.00,
        "ic_revenue": 0.00,
        "ic_cost": 0.00,
        "payroll": -147_500.00,
        "other_costs": -35_000.00,
        "net_profit": 197_500.00,
    },
    3: {
        "revenue": 410_000.00,
        "ic_revenue": 0.00,
        "ic_cost": 0.00,
        "payroll": -147_500.00,
        "other_costs": -35_000.00,
        "net_profit": 227_500.00,
    },
}

GROUP_PL_YTD_MARCH = {
    "revenue": 1_150_000.00,
    "ic_revenue": 0.00,
    "ic_cost": 0.00,
    "payroll": -442_500.00,
    "other_costs": -105_000.00,
    "net_profit": 602_500.00,
}

# Section 7: group balance sheet at 31 March, by column.
GROUP_BS_MARCH = {
    "companies": {
        "bank": 960_000.00,
        "cash_in_transit": 0.00,
        "receivables": 1_152_450.80,
        "ic_receivables": 200_000.00,
        "ic_loan_receivable": 200_000.00,
        "total_assets": 2_512_450.80,
        "payables": 105_071.56,
        "salaries_payable": 441_198.57,
        "ic_payables": 110_000.00,
        "ic_loan_payable": 200_000.00,
        "share_capital": 1_000_000.00,
        "profit": 652_500.00,
        "cta": 3_680.67,
        "total_liabilities_equity": 2_512_450.80,
    },
    "eliminations": {
        "bank": 0.00,
        "cash_in_transit": 40_000.00,
        "receivables": 0.00,
        "ic_receivables": -200_000.00,
        "ic_loan_receivable": -200_000.00,
        "total_assets": -360_000.00,
        "payables": 0.00,
        "salaries_payable": 0.00,
        "ic_payables": -110_000.00,
        "ic_loan_payable": -200_000.00,
        "share_capital": 0.00,
        "profit": -50_000.00,
        "cta": 0.00,
        "total_liabilities_equity": -360_000.00,
    },
    "group": {
        "bank": 960_000.00,
        "cash_in_transit": 40_000.00,
        "receivables": 1_152_450.80,
        "ic_receivables": 0.00,
        "ic_loan_receivable": 0.00,
        "total_assets": 2_152_450.80,
        "payables": 105_071.56,
        "salaries_payable": 441_198.57,
        "ic_payables": 0.00,
        "ic_loan_payable": 0.00,
        "share_capital": 1_000_000.00,
        "profit": 602_500.00,
        "cta": 3_680.67,
        "total_liabilities_equity": 2_152_450.80,
    },
}

# Section 8: April, when the cut-off and the payment in transit unwind.
APRIL = {
    "group_net_profit": -1_025.64,
    "pl_fx": -1_025.64,  # Delta Poland's realised loss of PLN 4,000 at 3.90, kept in the group
    "pl_fx_local": -4_000.00,
    "us_ic_cost": -50_000.00,  # Ukraine's March invoice, booked by Delta US on 2 April
    "cash_in_transit": 0.00,
    "ic_clearing": 0.00,
    "receivable_equals_payable": {("ua", "us"): 135_000.00, ("pl", "us"): 25_000.00},
    "ua_us_ytd_revenue_and_cost": 135_000.00,
}
