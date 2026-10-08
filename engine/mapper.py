"""
engine/mapper.py
Three-layer Schedule III mapping engine:
1. Rule-based keyword and pattern matching
2. Fuzzy matching with similarity confidence score (difflib / token overlap)
3. User override with automatic persistence into mapping_master.csv
Enforces strict CA compliance: unmapped ledgers sit in a 'needs mapping' queue
and statements cannot finalise until all ledgers are mapped.
"""

import os
import re
import difflib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import pandas as pd

from templates.schedule_iii_schema import Division, get_line_items_by_division


@dataclass
class MappingRecord:
    ledger_name: str
    target_line_item: str
    division: Division
    statement_type: str
    category: str
    default_dr_cr: str
    ca_rule_tag: str
    confidence: float
    match_source: str  # "EXACT_RULE", "PATTERN_RULE", "FUZZY_MATCH", "USER_OVERRIDE"
    needs_review: bool  # Amber flag if confidence < 0.85
    net_cy: float = 0.0
    debit_cy: float = 0.0
    credit_cy: float = 0.0
    net_py: float = 0.0


class UnmappedLedgersException(Exception):
    """Raised when statements finalisation is attempted with unmapped ledgers."""
    pass


class ScheduleIIIMapper:
    def __init__(self, master_csv_path: Optional[str] = None):
        if master_csv_path is None:
            master_csv_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "mapping_master.csv"
            )
        self.master_csv_path = os.path.abspath(master_csv_path)
        self.master_df = self._load_master()

    def _load_master(self) -> pd.DataFrame:
        if os.path.exists(self.master_csv_path):
            return pd.read_csv(self.master_csv_path, encoding="utf-8")
        else:
            return pd.DataFrame(columns=[
                "keyword_or_pattern", "division_i_line_item", "division_ii_line_item",
                "statement_type", "category", "default_dr_cr", "ca_rule_tag"
            ])

    def reload(self):
        self.master_df = self._load_master()

    def _clean_text(self, text: str) -> str:
        t = str(text).lower().strip()
        t = re.sub(r"[^\w\s]", " ", t)
        return " ".join(t.split())

    def match_ledger(self, ledger_name: str, division: Division) -> Tuple[Optional[str], float, str, str, str, str, str]:
        """
        Matches a single ledger name against the master mapping table.
        Returns:
            (target_line_item, confidence, match_source, statement_type, category, default_dr_cr, ca_rule_tag)
        """
        cleaned = self._clean_text(ledger_name)
        line_item_col = "division_i_line_item" if division == Division.DIVISION_I else "division_ii_line_item"

        # 1. Exact match (case-insensitive)
        for _, row in self.master_df.iterrows():
            pat = str(row["keyword_or_pattern"]).strip()
            if cleaned == self._clean_text(pat):
                return (
                    str(row[line_item_col]),
                    1.0,
                    "EXACT_RULE",
                    str(row["statement_type"]),
                    str(row["category"]),
                    str(row["default_dr_cr"]),
                    str(row["ca_rule_tag"])
                )

        # 2. Pattern / Substring matching
        best_pattern_match = None
        best_pattern_len = 0
        for _, row in self.master_df.iterrows():
            pat = str(row["keyword_or_pattern"]).strip()
            pat_clean = self._clean_text(pat)
            if len(pat_clean) >= 3 and (pat_clean in cleaned or cleaned in pat_clean):
                if len(pat_clean) > best_pattern_len:
                    best_pattern_len = len(pat_clean)
                    best_pattern_match = row

        if best_pattern_match is not None:
            # High confidence pattern match
            return (
                str(best_pattern_match[line_item_col]),
                0.95,
                "PATTERN_RULE",
                str(best_pattern_match["statement_type"]),
                str(best_pattern_match["category"]),
                str(best_pattern_match["default_dr_cr"]),
                str(best_pattern_match["ca_rule_tag"])
            )

        # 3. Fuzzy matching using SequenceMatcher
        candidates = self.master_df["keyword_or_pattern"].astype(str).tolist()
        best_ratio = 0.0
        best_candidate_idx = -1

        for idx, cand in enumerate(candidates):
            ratio = difflib.SequenceMatcher(None, cleaned, self._clean_text(cand)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_candidate_idx = idx

        if best_ratio >= 0.55 and best_candidate_idx >= 0:
            row = self.master_df.iloc[best_candidate_idx]
            return (
                str(row[line_item_col]),
                round(best_ratio, 2),
                "FUZZY_MATCH",
                str(row["statement_type"]),
                str(row["category"]),
                str(row["default_dr_cr"]),
                str(row["ca_rule_tag"])
            )

        # 4. Unmapped
        return (None, 0.0, "UNMAPPED", "", "", "", "")

    def map_dataframe(self, normalized_df: pd.DataFrame, division: Division) -> pd.DataFrame:
        """
        Maps an entire normalized trial balance DataFrame.
        Adds mapping columns:
        - target_line_item
        - confidence
        - match_source
        - statement_type
        - category
        - default_dr_cr
        - ca_rule_tag
        - needs_review (amber if confidence < 0.85)
        - is_mapped (bool)
        """
        records = []
        for _, row in normalized_df.iterrows():
            lname = str(row["ledger_name"]).strip()
            line_item, conf, source, st_type, cat, drcr, tag = self.match_ledger(lname, division)
            
            is_mapped = bool(line_item and line_item != "None" and line_item != "nan")
            needs_review = bool(is_mapped and conf < 0.85)

            rec = {
                "ledger_name": lname,
                "group": str(row.get("group", "")),
                "debit_cy": float(row.get("debit_cy", 0.0)),
                "credit_cy": float(row.get("credit_cy", 0.0)),
                "net_cy": float(row.get("net_cy", 0.0)),
                "debit_py": float(row.get("debit_py", 0.0)),
                "credit_py": float(row.get("credit_py", 0.0)),
                "net_py": float(row.get("net_py", 0.0)),
                "target_line_item": line_item if is_mapped else "NEEDS MAPPING",
                "confidence": conf,
                "match_source": source,
                "statement_type": st_type,
                "category": cat,
                "default_dr_cr": drcr,
                "ca_rule_tag": tag,
                "needs_review": needs_review,
                "is_mapped": is_mapped
            }
            records.append(rec)

        return pd.DataFrame(records)

    def get_unmapped_ledgers(self, mapped_df: pd.DataFrame) -> pd.DataFrame:
        """Returns the queue of unmapped ledgers."""
        return mapped_df[~mapped_df["is_mapped"] | (mapped_df["target_line_item"] == "NEEDS MAPPING")].copy()

    def get_review_queue(self, mapped_df: pd.DataFrame) -> pd.DataFrame:
        """Returns ledgers needing user confirmation (amber queue, confidence < 85%)."""
        return mapped_df[mapped_df["needs_review"]].copy()

    def apply_override(
        self,
        mapped_df: pd.DataFrame,
        ledger_name: str,
        target_line_item: str,
        division: Division,
        save_to_master: bool = True
    ) -> pd.DataFrame:
        """
        Remaps a ledger with a user override, updating the in-memory mapped DataFrame
        and permanently persisting to mapping_master.csv if save_to_master is True.
        """
        # Find item definition from schema
        valid_items = get_line_items_by_division(division)
        schema_dict = {item.name: item for item in valid_items}
        matched_item = schema_dict.get(target_line_item)

        st_type = matched_item.statement_type.value if matched_item else "Balance Sheet"
        cat = matched_item.category.value if matched_item else "Current Assets"
        drcr = matched_item.default_dr_cr if matched_item else "Dr"
        tag = "USER_OVERRIDE"

        # Update in mapped_df
        mask = mapped_df["ledger_name"] == ledger_name
        if mask.any():
            mapped_df.loc[mask, "target_line_item"] = target_line_item
            mapped_df.loc[mask, "confidence"] = 1.0
            mapped_df.loc[mask, "match_source"] = "USER_OVERRIDE"
            mapped_df.loc[mask, "statement_type"] = st_type
            mapped_df.loc[mask, "category"] = cat
            mapped_df.loc[mask, "default_dr_cr"] = drcr
            mapped_df.loc[mask, "ca_rule_tag"] = tag
            mapped_df.loc[mask, "needs_review"] = False
            mapped_df.loc[mask, "is_mapped"] = True

        if save_to_master:
            self._save_override_to_master(
                ledger_name=ledger_name,
                target_line_item=target_line_item,
                division=division,
                statement_type=st_type,
                category=cat,
                default_dr_cr=drcr,
                ca_rule_tag=tag
            )

        return mapped_df

    def _save_override_to_master(
        self,
        ledger_name: str,
        target_line_item: str,
        division: Division,
        statement_type: str,
        category: str,
        default_dr_cr: str,
        ca_rule_tag: str
    ):
        """Persists the user's mapping decision to mapping_master.csv."""
        div_col = "division_i_line_item" if division == Division.DIVISION_I else "division_ii_line_item"
        other_div_col = "division_ii_line_item" if division == Division.DIVISION_I else "division_i_line_item"

        # Check if ledger already exists in master
        existing_mask = self.master_df["keyword_or_pattern"].str.lower() == ledger_name.lower()
        if existing_mask.any():
            self.master_df.loc[existing_mask, div_col] = target_line_item
            self.master_df.loc[existing_mask, "statement_type"] = statement_type
            self.master_df.loc[existing_mask, "category"] = category
            self.master_df.loc[existing_mask, "default_dr_cr"] = default_dr_cr
            self.master_df.loc[existing_mask, "ca_rule_tag"] = ca_rule_tag
        else:
            new_row = {
                "keyword_or_pattern": ledger_name,
                div_col: target_line_item,
                other_div_col: target_line_item,
                "statement_type": statement_type,
                "category": category,
                "default_dr_cr": default_dr_cr,
                "ca_rule_tag": ca_rule_tag
            }
            self.master_df = pd.concat([self.master_df, pd.DataFrame([new_row])], ignore_index=True)

        # Save to disk
        self.master_df.to_csv(self.master_csv_path, index=False, encoding="utf-8")
