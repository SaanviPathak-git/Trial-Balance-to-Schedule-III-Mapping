"""
scripts/test_pipeline_quick.py
Quick end-to-end verification of the finalisation pipeline.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from templates.schedule_iii_schema import Division
from engine.validator import validate_trial_balance
from engine.mapper import ScheduleIIIMapper
from engine.classifier import CAJudgementClassifier
from engine.statements import StatementGenerator, RoundingUnit
from engine.checks import run_finalisation_checks
from engine.ratios import compute_schedule_iii_ratios
from engine.excel_export import generate_schedule_iii_excel

def test_div2_pipeline():
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb.xlsx")
    raw_df = pd.read_excel(file_path)

    print("--- 1. VALIDATION ---")
    val_res = validate_trial_balance(raw_df)
    print(f"Validation Result: is_valid={val_res.is_valid}, Total Dr={val_res.total_debit:,.2f}, Total Cr={val_res.total_credit:,.2f}, Diff={val_res.difference}")
    print(f"Issues count: {len(val_res.issues)}")
    for iss in val_res.issues:
        print(f"  [{iss.severity.value}] {iss.code}: {iss.message}")

    print("\n--- 2. MAPPING ---")
    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_II)
    unmapped = mapper.get_unmapped_ledgers(mapped_df)
    review_queue = mapper.get_review_queue(mapped_df)
    print(f"Mapped {len(mapped_df)} ledgers. Unmapped count: {len(unmapped)}. Amber review count: {len(review_queue)}")
    if len(unmapped) > 0:
        print("Unmapped ledgers:")
        print(unmapped[["ledger_name", "net_cy"]])

    print("\n--- 3. CA CLASSIFICATION & JUDGEMENT ---")
    classifier = CAJudgementClassifier(Division.DIVISION_II)
    classified_out = classifier.classify_and_adjust(mapped_df)
    print(f"Treatment log entries count: {len(classified_out.treatment_log)}")
    for t in classified_out.treatment_log:
        print(f"  - [{t.treatment_type}] {t.ledger_name}: ₹ {t.amount_cy:,.2f} -> {t.adjusted_line_item}")

    print("\n--- 4. STATEMENTS GENERATION ---")
    generator = StatementGenerator(Division.DIVISION_II, RoundingUnit.LAKHS, "FY 2023-24", "FY 2022-23")
    stmts = generator.generate(classified_out)
    print(f"Net Profit (CY): ₹ {stmts.net_profit_cy:,.2f}")
    print(f"Total Assets (CY): ₹ {stmts.total_assets_cy:,.2f}")
    print(f"Total Equity & Liab (CY): ₹ {stmts.total_equity_liab_cy:,.2f}")
    print(f"BS Difference (CY): ₹ {stmts.bs_diff_cy:,.2f}")
    print(f"BS Difference (PY): ₹ {stmts.bs_diff_py:,.2f}")

    print("\n--- 5. AUDIT CHECKS ---")
    audit_summary = run_finalisation_checks(stmts, val_res.normalized_df, unmapped_count=len(unmapped))
    print(f"All Checks Passed: {audit_summary.all_passed} (Passed: {audit_summary.passed_count}, Failed: {audit_summary.failed_count})")
    for chk in audit_summary.checks:
        print(f"  [{chk.status}] {chk.name}: {chk.summary_message}")

    print("\n--- 6. RATIOS ---")
    ratios = compute_schedule_iii_ratios(stmts)
    print(f"Computed {len(ratios)} ratios:")
    for r in ratios:
        flag = "⚠️ >25%" if r.is_variance_significant else "✅ OK"
        print(f"  {r.ratio_name}: CY={r.value_cy}{r.unit_str}, PY={r.value_py}{r.unit_str}, Var={r.variance_pct:+.1f}% [{flag}]")

    print("\n--- 7. EXCEL EXPORT ---")
    excel_buf = generate_schedule_iii_excel(stmts, audit_summary, ratios, classified_out.treatment_log, "Astra Consumer Goods Limited")
    out_excel_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_finalised_statements.xlsx")
    with open(out_excel_path, "wb") as f:
        f.write(excel_buf.getvalue())
    print(f"Successfully exported {len(excel_buf.getvalue())} bytes to {out_excel_path}")

    print("\n--- 8. FMCG BRIDGE ---")
    fmcg_dict = generator.export_to_fmcg_schema(stmts, "ASTRA", "Astra Consumer Goods Limited")
    print(f"FMCG Bridge Success: Revenue=₹ {fmcg_dict['income_statements']['FY24']['revenue']} Cr, PAT=₹ {fmcg_dict['income_statements']['FY24']['pat']} Cr, Assets=₹ {fmcg_dict['balance_sheets']['FY24']['total_assets']} Cr")

def test_div1_pipeline():
    print("\n=======================================================")
    print("TESTING DIVISION I (NON-IND AS / AS) PIPELINE")
    print("=======================================================")
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_tb_division1.xlsx")
    raw_df = pd.read_excel(file_path)

    val_res = validate_trial_balance(raw_df)
    print(f"Validation Result: is_valid={val_res.is_valid}, Total Dr={val_res.total_debit:,.2f}, Total Cr={val_res.total_credit:,.2f}, Diff={val_res.difference}")

    mapper = ScheduleIIIMapper()
    mapped_df = mapper.map_dataframe(val_res.normalized_df, Division.DIVISION_I)
    unmapped = mapper.get_unmapped_ledgers(mapped_df)
    print(f"Mapped {len(mapped_df)} ledgers. Unmapped count: {len(unmapped)}")

    classifier = CAJudgementClassifier(Division.DIVISION_I)
    classified_out = classifier.classify_and_adjust(mapped_df)
    print(f"Treatment log entries: {len(classified_out.treatment_log)}")

    generator = StatementGenerator(Division.DIVISION_I, RoundingUnit.LAKHS, "FY 2023-24", "FY 2022-23")
    stmts = generator.generate(classified_out)
    print(f"Net Profit (CY): ₹ {stmts.net_profit_cy:,.2f}")
    print(f"Total Assets (CY): ₹ {stmts.total_assets_cy:,.2f}")
    print(f"Total Equity & Liab (CY): ₹ {stmts.total_equity_liab_cy:,.2f}")
    print(f"BS Diff (CY): ₹ {stmts.bs_diff_cy:,.2f}, BS Diff (PY): ₹ {stmts.bs_diff_py:,.2f}")

    audit_summary = run_finalisation_checks(stmts, val_res.normalized_df, unmapped_count=len(unmapped))
    print(f"All Checks Passed: {audit_summary.all_passed} (Passed: {audit_summary.passed_count}, Failed: {audit_summary.failed_count})")
    for chk in audit_summary.checks:
        print(f"  [{chk.status}] {chk.name}: {chk.summary_message}")

if __name__ == "__main__":
    test_div2_pipeline()
    test_div1_pipeline()
