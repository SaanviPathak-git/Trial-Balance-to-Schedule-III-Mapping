"""
tests/test_statements.py
Unit tests for Statement generation, mathematical balance, and FMCG bridge.
"""

import os
import pytest
import pandas as pd
from templates.schedule_iii_schema import Division
from engine.validator import validate_trial_balance
from engine.mapper import ScheduleIIIMapper
from engine.classifier import CAJudgementClassifier
from engine.statements import StatementGenerator, RoundingUnit


def test_division_ii_balance_sheet_closure():
    tb_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb.xlsx")
    raw_df = pd.read_excel(tb_path)

    val_res = validate_trial_balance(raw_df)
    assert val_res.is_valid is True

    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_II)
    assert len(mapper.get_unmapped_ledgers(mapped_df)) == 0

    classifier = CAJudgementClassifier(Division.DIVISION_II)
    class_out = classifier.classify_and_adjust(mapped_df)

    generator = StatementGenerator(Division.DIVISION_II, RoundingUnit.EXACT)
    stmts = generator.generate(class_out)

    # Mathematical closure check
    assert stmts.bs_diff_cy == 0.0
    assert stmts.bs_diff_py == 0.0
    assert stmts.total_assets_cy == stmts.total_equity_liab_cy


def test_division_i_balance_sheet_closure():
    tb_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb_division1.xlsx")
    raw_df = pd.read_excel(tb_path)

    val_res = validate_trial_balance(raw_df)
    assert val_res.is_valid is True

    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_I)
    assert len(mapper.get_unmapped_ledgers(mapped_df)) == 0

    classifier = CAJudgementClassifier(Division.DIVISION_I)
    class_out = classifier.classify_and_adjust(mapped_df)

    generator = StatementGenerator(Division.DIVISION_I, RoundingUnit.EXACT)
    stmts = generator.generate(class_out)

    assert stmts.bs_diff_cy == 0.0
    assert stmts.bs_diff_py == 0.0
    assert stmts.total_assets_cy == stmts.total_equity_liab_cy


def test_fmcg_bridge_export():
    tb_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb.xlsx")
    raw_df = pd.read_excel(tb_path)

    val_res = validate_trial_balance(raw_df)
    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_II)
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    class_out = classifier.classify_and_adjust(mapped_df)

    generator = StatementGenerator(Division.DIVISION_II, RoundingUnit.LAKHS)
    stmts = generator.generate(class_out)

    fmcg_dict = generator.export_to_fmcg_schema(stmts, "ASTRA", "Astra Consumer Goods Limited")
    assert "income_statements" in fmcg_dict
    assert "balance_sheets" in fmcg_dict
    assert "FY24" in fmcg_dict["income_statements"]
    assert fmcg_dict["income_statements"]["FY24"]["revenue"] > 0
    assert fmcg_dict["balance_sheets"]["FY24"]["total_assets"] > 0
