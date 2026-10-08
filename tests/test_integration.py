"""
tests/test_integration.py
End-to-end integration tests for Trial Balance Schedule III finalisation.
"""

import os
import io
import pytest
import pandas as pd
from templates.schedule_iii_schema import Division
from engine.validator import validate_trial_balance
from engine.mapper import ScheduleIIIMapper
from engine.classifier import CAJudgementClassifier
from engine.statements import StatementGenerator, RoundingUnit
from engine.checks import run_finalisation_checks
from engine.ratios import compute_schedule_iii_ratios
from engine.excel_export import generate_schedule_iii_excel


def test_full_pipeline_division_ii_ind_as():
    tb_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb.xlsx")
    raw_df = pd.read_excel(tb_path)

    # 1. Validation
    val_res = validate_trial_balance(raw_df)
    assert val_res.is_valid is True
    assert val_res.difference == 0.0

    # 2. Mapping
    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_II)
    unmapped = mapper.get_unmapped_ledgers(mapped_df)
    assert len(unmapped) == 0

    # 3. CA Classification
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    classified_out = classifier.classify_and_adjust(mapped_df)
    assert len(classified_out.treatment_log) > 0

    # 4. Statements Generation
    generator = StatementGenerator(Division.DIVISION_II, RoundingUnit.LAKHS)
    stmts = generator.generate(classified_out)
    assert stmts.bs_diff_cy == 0.0
    assert stmts.bs_diff_py == 0.0

    # 5. Audit Checks
    audit_summary = run_finalisation_checks(stmts, val_res.normalized_df, unmapped_count=0)
    assert audit_summary.all_passed is True
    assert audit_summary.passed_count == 4
    assert audit_summary.failed_count == 0

    # 6. Ratios
    ratios = compute_schedule_iii_ratios(stmts)
    assert len(ratios) == 11

    # 7. Excel Export
    excel_buf = generate_schedule_iii_excel(
        stmts=stmts,
        audit_summary=audit_summary,
        ratios=ratios,
        treatment_logs=classified_out.treatment_log,
        company_name="Astra Consumer Goods Limited"
    )
    assert isinstance(excel_buf, io.BytesIO)
    assert len(excel_buf.getvalue()) > 10000


def test_full_pipeline_division_i_as():
    tb_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb_division1.xlsx")
    raw_df = pd.read_excel(tb_path)

    val_res = validate_trial_balance(raw_df)
    assert val_res.is_valid is True

    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_I)
    assert len(mapper.get_unmapped_ledgers(mapped_df)) == 0

    classifier = CAJudgementClassifier(Division.DIVISION_I)
    classified_out = classifier.classify_and_adjust(mapped_df)

    generator = StatementGenerator(Division.DIVISION_I, RoundingUnit.LAKHS)
    stmts = generator.generate(classified_out)
    assert stmts.bs_diff_cy == 0.0
    assert stmts.bs_diff_py == 0.0

    audit_summary = run_finalisation_checks(stmts, val_res.normalized_df, unmapped_count=0)
    assert audit_summary.all_passed is True
    assert audit_summary.passed_count == 4
