"""
tests/test_validator.py
Unit tests for Trial Balance validation engine.
"""

import pytest
import pandas as pd
from engine.validator import validate_trial_balance, IssueSeverity


def test_validator_balanced_tb():
    df = pd.DataFrame([
        {"Ledger Name": "Share Capital", "Debit": 0, "Credit": 1000},
        {"Ledger Name": "Cash and Bank", "Debit": 1000, "Credit": 0},
    ])
    res = validate_trial_balance(df)
    assert res.is_valid is True
    assert res.difference == 0.0
    assert res.has_blocking_errors is False


def test_validator_out_of_balance():
    df = pd.DataFrame([
        {"Ledger Name": "Share Capital", "Debit": 0, "Credit": 1000},
        {"Ledger Name": "Cash and Bank", "Debit": 950, "Credit": 0},
    ])
    res = validate_trial_balance(df)
    assert res.is_valid is False
    assert abs(res.difference) == 50.0
    assert any(i.code == "TB_OUT_OF_BALANCE" for i in res.issues)


def test_validator_duplicate_ledgers():
    df = pd.DataFrame([
        {"Ledger Name": "HDFC Bank", "Debit": 500, "Credit": 0},
        {"Ledger Name": "HDFC Bank", "Debit": 500, "Credit": 0},
        {"Ledger Name": "Capital", "Debit": 0, "Credit": 1000},
    ])
    res = validate_trial_balance(df)
    assert any(i.code == "DUPLICATE_LEDGER" for i in res.issues)


def test_validator_blank_ledger_name():
    df = pd.DataFrame([
        {"Ledger Name": "", "Debit": 500, "Credit": 0},
        {"Ledger Name": "Capital", "Debit": 0, "Credit": 500},
    ])
    res = validate_trial_balance(df)
    assert any(i.code == "BLANK_LEDGER_NAME" for i in res.issues)


def test_validator_creditor_debit_balance():
    df = pd.DataFrame([
        {"Ledger Name": "Sundry Creditors - Vendor A", "Debit": 500, "Credit": 0},
        {"Ledger Name": "Capital", "Debit": 0, "Credit": 500},
    ])
    res = validate_trial_balance(df)
    assert any(i.code == "CREDITOR_DEBIT_BALANCE" for i in res.issues)


def test_validator_debtor_credit_balance():
    df = pd.DataFrame([
        {"Ledger Name": "Sundry Debtors - Client B", "Debit": 0, "Credit": 500},
        {"Ledger Name": "Bank", "Debit": 500, "Credit": 0},
    ])
    res = validate_trial_balance(df)
    assert any(i.code == "DEBTOR_CREDIT_BALANCE" for i in res.issues)


def test_validator_negative_cash():
    df = pd.DataFrame([
        {"Ledger Name": "Cash in Hand", "Debit": 0, "Credit": 100},
        {"Ledger Name": "Sales", "Debit": 100, "Credit": 0},
    ])
    res = validate_trial_balance(df)
    assert any(i.code == "NEGATIVE_CASH_BALANCE" for i in res.issues)
