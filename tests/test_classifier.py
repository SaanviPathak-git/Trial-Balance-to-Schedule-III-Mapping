"""
tests/test_classifier.py
Unit tests for the CA Judgement Layer.
"""

import pytest
import pandas as pd
from templates.schedule_iii_schema import Division
from engine.classifier import CAJudgementClassifier


def test_gross_up_creditor_debit_balance():
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    df = pd.DataFrame([{
        "ledger_name": "Sundry Creditors - Vendor Advance",
        "target_line_item": "Financial Liabilities - Trade payables - Dues of Others",
        "statement_type": "Balance Sheet",
        "category": "Current Liabilities",
        "default_dr_cr": "Cr",
        "ca_rule_tag": "NON_MSME_PAYABLE",
        "confidence": 1.0,
        "match_source": "EXACT_RULE",
        "net_cy": 50000.0,  # Debit balance
        "net_py": 0.0,
    }])
    out = classifier.classify_and_adjust(df)
    adjusted_item = out.adjusted_df.iloc[0]["target_line_item"]
    assert adjusted_item == "Other current assets"
    assert len(out.treatment_log) >= 1
    assert out.treatment_log[0].treatment_type == "GROSS_UP"


def test_gross_up_debtor_credit_balance():
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    df = pd.DataFrame([{
        "ledger_name": "Sundry Debtors - Client Advance",
        "target_line_item": "Financial Assets - Trade receivables",
        "statement_type": "Balance Sheet",
        "category": "Current Assets",
        "default_dr_cr": "Dr",
        "ca_rule_tag": "TRADE_RECEIVABLES",
        "confidence": 1.0,
        "match_source": "EXACT_RULE",
        "net_cy": -75000.0,  # Credit balance
        "net_py": 0.0,
    }])
    out = classifier.classify_and_adjust(df)
    adjusted_item = out.adjusted_df.iloc[0]["target_line_item"]
    assert adjusted_item == "Other current liabilities"
    assert len(out.treatment_log) >= 1
    assert out.treatment_log[0].treatment_type == "GROSS_UP"


def test_bank_overdraft_reclassification():
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    df = pd.DataFrame([{
        "ledger_name": "HDFC Current Account Overdrawn",
        "target_line_item": "Financial Assets - Cash and cash equivalents",
        "statement_type": "Balance Sheet",
        "category": "Current Assets",
        "default_dr_cr": "Dr",
        "ca_rule_tag": "BANK_BALANCE",
        "confidence": 1.0,
        "match_source": "EXACT_RULE",
        "net_cy": -150000.0,  # Credit balance
        "net_py": 0.0,
    }])
    out = classifier.classify_and_adjust(df)
    adjusted_item = out.adjusted_df.iloc[0]["target_line_item"]
    assert adjusted_item == "Financial Liabilities - Current Borrowings"
    assert any(t.treatment_type == "RECLASSIFICATION" for t in out.treatment_log)
