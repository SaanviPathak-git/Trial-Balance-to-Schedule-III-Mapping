"""
tests/test_adjustments.py
Unit tests for English natural language adjustment entries engine.
"""

import pytest
import pandas as pd
from engine.adjustments import (
    parse_inr_amount,
    parse_english_adjustment_line,
    parse_adjustments_block,
    apply_adjustments_to_tb,
)


def test_parse_inr_amount():
    assert parse_inr_amount("₹ 4,50,00,000") == 45000000.0
    assert parse_inr_amount("4.5 crores") == 45000000.0
    assert parse_inr_amount("50 lakhs") == 5000000.0
    assert parse_inr_amount("Rs 1,25,000") == 125000.0
    assert parse_inr_amount("25k") == 25000.0


def test_parse_closing_stock():
    text = "Closing stock valued at ₹ 4,50,00,000 at the end of the year"
    jv = parse_english_adjustment_line(text, 1)
    assert jv is not None
    assert jv.category == "CLOSING_STOCK"
    assert jv.amount == 45000000.0
    assert "Inventory" in jv.debit_account
    assert "inventories" in jv.credit_account.lower()


def test_parse_depreciation():
    text = "Provide depreciation of 25 lakhs on Plant & Machinery"
    jv = parse_english_adjustment_line(text, 2)
    assert jv is not None
    assert jv.category == "DEPRECIATION"
    assert jv.amount == 2500000.0
    assert "Depreciation" in jv.debit_account
    assert "Plant and Machinery" in jv.credit_account


def test_parse_outstanding_expense():
    text = "Outstanding audit fee of ₹ 1,50,000 to be provided"
    jv = parse_english_adjustment_line(text, 3)
    assert jv is not None
    assert jv.category == "OUTSTANDING_EXPENSE"
    assert jv.amount == 150000.0
    assert "Audit" in jv.debit_account
    assert "Audit Fees Payable" in jv.credit_account


def test_parse_prepaid_expense():
    text = "Prepaid insurance of ₹ 2,00,000 to be carried forward"
    jv = parse_english_adjustment_line(text, 4)
    assert jv is not None
    assert jv.category == "PREPAID_EXPENSE"
    assert jv.amount == 200000.0
    assert jv.debit_account == "Prepaid Expenses"
    assert "Insurance" in jv.credit_account


def test_parse_bad_debts():
    text = "Write off bad debts of ₹ 5,00,000"
    jv = parse_english_adjustment_line(text, 5)
    assert jv is not None
    assert jv.category == "BAD_DEBTS"
    assert jv.amount == 500000.0
    assert "Bad Debts" in jv.debit_account
    assert "Debtors" in jv.credit_account


def test_parse_tax_provision():
    text = "Provide current tax of ₹ 35,00,000"
    jv = parse_english_adjustment_line(text, 6)
    assert jv is not None
    assert jv.category == "TAX_PROVISION"
    assert jv.amount == 3500000.0
    assert "Current Income Tax" in jv.debit_account
    assert "Provision for Tax" in jv.credit_account


def test_parse_structured_jv():
    text = "Debit Rent ₹ 50,000 and Credit Rent Payable ₹ 50,000"
    jv = parse_english_adjustment_line(text, 7)
    assert jv is not None
    assert jv.category == "CUSTOM_JV"
    assert jv.amount == 50000.0
    assert jv.debit_account == "Rent"
    assert jv.credit_account == "Rent Payable"


def test_apply_adjustments_to_tb_maintains_balance():
    # Start with a balanced TB
    df = pd.DataFrame([
        {"ledger_name": "Cash", "group": "Cash", "debit_cy": 1000000.0, "credit_cy": 0.0, "net_cy": 1000000.0, "debit_py": 0.0, "credit_py": 0.0, "net_py": 0.0},
        {"ledger_name": "Capital", "group": "Equity", "debit_cy": 0.0, "credit_cy": 1000000.0, "net_cy": -1000000.0, "debit_py": 0.0, "credit_py": 0.0, "net_py": 0.0},
    ])
    
    entries_text = """
    Outstanding audit fee of ₹ 1,50,000 to be provided
    Prepaid insurance of ₹ 50,000
    """
    jvs = parse_adjustments_block(entries_text)
    assert len(jvs) == 2

    adjusted_df, jv_sheet = apply_adjustments_to_tb(df, jvs)
    
    # Check mathematical balance: sum of net_cy must strictly equal 0
    total_net = adjusted_df["net_cy"].sum()
    assert round(total_net, 2) == 0.0
    assert len(jv_sheet) == 2
