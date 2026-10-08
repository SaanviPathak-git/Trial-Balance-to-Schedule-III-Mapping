"""
tests/test_mapper.py
Unit tests for the three-layer mapping engine.
"""

import pytest
import pandas as pd
from templates.schedule_iii_schema import Division
from engine.mapper import ScheduleIIIMapper


def test_mapper_exact_rule():
    mapper = ScheduleIIIMapper()
    item, conf, source, st_type, cat, drcr, tag = mapper.match_ledger("Equity Share Capital", Division.DIVISION_II)
    assert item == "Equity Share capital"
    assert conf == 1.0
    assert source == "EXACT_RULE"


def test_mapper_pattern_rule():
    mapper = ScheduleIIIMapper()
    item, conf, source, st_type, cat, drcr, tag = mapper.match_ledger("Domestic Sales - Finished Goods", Division.DIVISION_II)
    assert "Revenue from operations" in item
    assert conf >= 0.95


def test_mapper_fuzzy_match():
    mapper = ScheduleIIIMapper()
    # Slight typo: 'Salarie and Wage'
    item, conf, source, st_type, cat, drcr, tag = mapper.match_ledger("Salarie and Wage", Division.DIVISION_II)
    assert item == "Employee benefits expense"
    assert conf > 0.70


def test_mapper_dataframe_mapping():
    mapper = ScheduleIIIMapper()
    df = pd.DataFrame([
        {"ledger_name": "Sundry Debtors", "debit_cy": 100, "credit_cy": 0, "net_cy": 100, "debit_py": 0, "credit_py": 0, "net_py": 0},
        {"ledger_name": "Totally Unknown Ledger XYZ999", "debit_cy": 0, "credit_cy": 100, "net_cy": -100, "debit_py": 0, "credit_py": 0, "net_py": 0},
    ])
    mapped = mapper.map_dataframe(df, Division.DIVISION_II)
    assert len(mapped) == 2
    unmapped = mapper.get_unmapped_ledgers(mapped)
    assert len(unmapped) == 1
    assert unmapped.iloc[0]["ledger_name"] == "Totally Unknown Ledger XYZ999"


def test_mapper_user_override():
    mapper = ScheduleIIIMapper()
    df = pd.DataFrame([
        {"ledger_name": "Special Reserve ABC", "debit_cy": 0, "credit_cy": 100, "net_cy": -100, "debit_py": 0, "credit_py": 0, "net_py": 0},
    ])
    mapped = mapper.map_dataframe(df, Division.DIVISION_II)
    # Remap with override
    remapped = mapper.apply_override(mapped, "Special Reserve ABC", "Other Equity", Division.DIVISION_II, save_to_master=False)
    assert remapped.iloc[0]["target_line_item"] == "Other Equity"
    assert remapped.iloc[0]["match_source"] == "USER_OVERRIDE"
    assert bool(remapped.iloc[0]["is_mapped"]) is True
