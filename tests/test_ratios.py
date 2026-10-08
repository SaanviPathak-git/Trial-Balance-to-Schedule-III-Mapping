"""
tests/test_ratios.py
Unit tests for Schedule III mandatory ratios and variance triggers.
"""

import os
import pytest
import pandas as pd
from templates.schedule_iii_schema import Division
from engine.validator import validate_trial_balance
from engine.mapper import ScheduleIIIMapper
from engine.classifier import CAJudgementClassifier
from engine.statements import StatementGenerator, RoundingUnit
from engine.ratios import compute_schedule_iii_ratios


def test_11_ratios_computation():
    tb_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb.xlsx")
    raw_df = pd.read_excel(tb_path)

    val_res = validate_trial_balance(raw_df)
    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_II)
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    class_out = classifier.classify_and_adjust(mapped_df)
    generator = StatementGenerator(Division.DIVISION_II, RoundingUnit.LAKHS)
    stmts = generator.generate(class_out)

    ratios = compute_schedule_iii_ratios(stmts)
    assert len(ratios) == 11
    ratio_names = [r.ratio_name for r in ratios]

    # Verify key statutory ratios are present
    assert any("Current Ratio" in name for name in ratio_names)
    assert any("Debt-Equity" in name for name in ratio_names)
    assert any("Debt Service Coverage" in name for name in ratio_names)
    assert any("Return on Equity" in name for name in ratio_names)
    assert any("Inventory Turnover" in name for name in ratio_names)
    assert any("Trade Receivables Turnover" in name for name in ratio_names)
    assert any("Trade Payables Turnover" in name for name in ratio_names)
    assert any("Net Capital Turnover" in name for name in ratio_names)
    assert any("Net Profit Margin" in name for name in ratio_names)
    assert any("Return on Capital Employed" in name for name in ratio_names)
    assert any("Return on Investment" in name for name in ratio_names)

    for r in ratios:
        assert isinstance(r.value_cy, float)
        assert isinstance(r.value_py, float)
        assert isinstance(r.is_variance_significant, bool)
