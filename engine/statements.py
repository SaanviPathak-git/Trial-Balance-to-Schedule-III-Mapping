"""
engine/statements.py
Generates statutory Schedule III Balance Sheet, Statement of Profit & Loss,
and Notes to Accounts for Division I (AS) and Division II (Ind AS).
Includes P&L profit carry-forward to Reserves/Other Equity, inventory movement,
drill-down queries, unit rounding, and export to FMCG analysis schema.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from templates.schedule_iii_schema import (
    Division,
    StatementType,
    SectionCategory,
    ScheduleIIILineItem,
    get_line_items_by_division
)
from engine.classifier import ClassificationOutput


class RoundingUnit(str, Enum):
    EXACT = "Exact ₹ (Single Rupees)"
    THOUSANDS = "₹ Thousands"
    LAKHS = "₹ Lakhs"
    CRORES = "₹ Crores"


@dataclass
class NoteItem:
    note_no: int
    title: str
    line_item_name: str
    statement_type: StatementType
    category: SectionCategory
    ledgers: List[Dict[str, Any]] = field(default_factory=list)
    total_cy: float = 0.0
    total_py: float = 0.0


@dataclass
class StatementRow:
    line_item_name: str
    note_no: Optional[int]
    category: str
    statement_type: str
    amount_cy: float
    amount_py: float
    is_subtotal: bool = False
    is_heading: bool = False


@dataclass
class GeneratedFinancialStatements:
    division: Division
    rounding_unit: RoundingUnit
    unit_multiplier: float
    cy_label: str
    py_label: str
    balance_sheet_df: pd.DataFrame
    pl_df: pd.DataFrame
    notes: Dict[str, NoteItem]
    drill_down_df: pd.DataFrame
    net_profit_cy: float
    net_profit_py: float
    total_assets_cy: float
    total_equity_liab_cy: float
    total_assets_py: float
    total_equity_liab_py: float
    bs_diff_cy: float
    bs_diff_py: float
    raw_totals: Dict[str, float] = field(default_factory=dict)


def get_rounding_multiplier(unit: RoundingUnit) -> float:
    if unit == RoundingUnit.THOUSANDS:
        return 1e3
    elif unit == RoundingUnit.LAKHS:
        return 1e5
    elif unit == RoundingUnit.CRORES:
        return 1e7
    return 1.0


class StatementGenerator:
    def __init__(self, division: Division, rounding_unit: RoundingUnit = RoundingUnit.LAKHS, cy_label: str = "FY 2023-24", py_label: str = "FY 2022-23"):
        self.division = division
        self.is_div1 = (division == Division.DIVISION_I)
        self.rounding_unit = rounding_unit
        self.multiplier = get_rounding_multiplier(rounding_unit)
        self.cy_label = cy_label
        self.py_label = py_label

    def generate(self, classification_output: ClassificationOutput) -> GeneratedFinancialStatements:
        df = classification_output.adjusted_df.copy()
        schema_items = get_line_items_by_division(self.division)
        schema_dict = {item.name: item for item in schema_items}

        # 1. Aggregate amounts by target_line_item
        # For Dr items, net_cy is positive. For Cr items, net_cy is negative in normalized TB.
        # We store amounts as positive values aligned with Schedule III presentation convention.
        grouped_cy: Dict[str, float] = {}
        grouped_py: Dict[str, float] = {}
        notes_dict: Dict[str, NoteItem] = {}

        # Prepare Notes map
        for item in schema_items:
            notes_dict[item.name] = NoteItem(
                note_no=item.note_no or 0,
                title=f"Note {item.note_no}: {item.name}" if item.note_no else item.name,
                line_item_name=item.name,
                statement_type=item.statement_type,
                category=item.category,
                ledgers=[],
                total_cy=0.0,
                total_py=0.0
            )

        # Populate ledgers into notes
        for _, row in df.iterrows():
            line_item = str(row["target_line_item"]).strip()
            if line_item not in schema_dict:
                continue

            item_meta = schema_dict[line_item]
            # Normal sign convention for presentation:
            # Asset / Expense (Dr): positive when net_cy > 0
            # Liability / Equity / Income (Cr): positive when net_cy < 0
            raw_cy = float(row["net_cy"])
            raw_py = float(row["net_py"])

            if item_meta.default_dr_cr == "Dr":
                # Contra assets like provision for doubtful debts have Cr balance, so they deduct
                val_cy = raw_cy
                val_py = raw_py
            else:
                # Credit items (Revenues, Equity, Liabilities): Cr is negative in net_cy, invert to positive
                val_cy = -raw_cy
                val_py = -raw_py

            grouped_cy[line_item] = grouped_cy.get(line_item, 0.0) + val_cy
            grouped_py[line_item] = grouped_py.get(line_item, 0.0) + val_py

            if line_item in notes_dict:
                notes_dict[line_item].ledgers.append({
                    "ledger_name": str(row["ledger_name"]),
                    "group": str(row.get("group", "")),
                    "amount_cy": val_cy,
                    "amount_py": val_py,
                    "confidence": float(row.get("confidence", 1.0)),
                    "match_source": str(row.get("match_source", "")),
                    "ca_rule_tag": str(row.get("ca_rule_tag", ""))
                })
                notes_dict[line_item].total_cy += val_cy
                notes_dict[line_item].total_py += val_py

        # 2. Compute P&L Totals & Net Profit
        if self.is_div1:
            rev = grouped_cy.get("Revenue from operations", 0.0)
            oth_inc = grouped_cy.get("Other income", 0.0)
            tot_income = rev + oth_inc

            mat_cons = grouped_cy.get("Cost of materials consumed", 0.0)
            pur_traded = grouped_cy.get("Purchases of Stock-in-Trade", 0.0)
            chg_inv = grouped_cy.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0)
            emp_exp = grouped_cy.get("Employee benefits expense", 0.0)
            fin_cost = grouped_cy.get("Finance costs", 0.0)
            dep_amort = grouped_cy.get("Depreciation and amortisation expense", 0.0)
            oth_exp = grouped_cy.get("Other expenses", 0.0)
            tot_expenses = mat_cons + pur_traded + chg_inv + emp_exp + fin_cost + dep_amort + oth_exp

            pbt = tot_income - tot_expenses - grouped_cy.get("Exceptional items", 0.0)
            curr_tax = grouped_cy.get("Current tax expense", 0.0)
            def_tax = grouped_cy.get("Deferred tax expense / (credit)", 0.0)
            pat_cy = pbt - (curr_tax + def_tax)

            # PY P&L
            rev_py = grouped_py.get("Revenue from operations", 0.0)
            oth_inc_py = grouped_py.get("Other income", 0.0)
            tot_income_py = rev_py + oth_inc_py
            tot_expenses_py = (
                grouped_py.get("Cost of materials consumed", 0.0)
                + grouped_py.get("Purchases of Stock-in-Trade", 0.0)
                + grouped_py.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0)
                + grouped_py.get("Employee benefits expense", 0.0)
                + grouped_py.get("Finance costs", 0.0)
                + grouped_py.get("Depreciation and amortisation expense", 0.0)
                + grouped_py.get("Other expenses", 0.0)
            )
            pbt_py = tot_income_py - tot_expenses_py - grouped_py.get("Exceptional items", 0.0)
            pat_py = pbt_py - (grouped_py.get("Current tax expense", 0.0) + grouped_py.get("Deferred tax expense / (credit)", 0.0))

        else:
            # Division II
            rev = grouped_cy.get("Revenue from operations", 0.0)
            oth_inc = grouped_cy.get("Other income", 0.0)
            tot_income = rev + oth_inc

            mat_cons = grouped_cy.get("Cost of materials consumed", 0.0)
            pur_traded = grouped_cy.get("Purchases of Stock-in-Trade", 0.0)
            chg_inv = grouped_cy.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0)
            emp_exp = grouped_cy.get("Employee benefits expense", 0.0)
            fin_cost = grouped_cy.get("Finance costs", 0.0)
            dep_amort = grouped_cy.get("Depreciation and amortisation expense", 0.0)
            oth_exp = grouped_cy.get("Other expenses", 0.0)
            tot_expenses = mat_cons + pur_traded + chg_inv + emp_exp + fin_cost + dep_amort + oth_exp

            pbt = tot_income - tot_expenses - grouped_cy.get("Exceptional items", 0.0)
            curr_tax = grouped_cy.get("Current tax expense", 0.0)
            def_tax = grouped_cy.get("Deferred tax expense / (credit)", 0.0)
            pat_cy = pbt - (curr_tax + def_tax)
            oci_cy = grouped_cy.get("Other Comprehensive Income / (Loss)", 0.0)

            # PY
            rev_py = grouped_py.get("Revenue from operations", 0.0)
            oth_inc_py = grouped_py.get("Other income", 0.0)
            tot_income_py = rev_py + oth_inc_py
            tot_expenses_py = (
                grouped_py.get("Cost of materials consumed", 0.0)
                + grouped_py.get("Purchases of Stock-in-Trade", 0.0)
                + grouped_py.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0)
                + grouped_py.get("Employee benefits expense", 0.0)
                + grouped_py.get("Finance costs", 0.0)
                + grouped_py.get("Depreciation and amortisation expense", 0.0)
                + grouped_py.get("Other expenses", 0.0)
            )
            pbt_py = tot_income_py - tot_expenses_py - grouped_py.get("Exceptional items", 0.0)
            pat_py = pbt_py - (grouped_py.get("Current tax expense", 0.0) + grouped_py.get("Deferred tax expense / (credit)", 0.0))
            oci_py = grouped_py.get("Other Comprehensive Income / (Loss)", 0.0)

        # 3. Apply CA Carry-Forward: Net Profit flows into Reserves & Surplus / Other Equity
        # This is what makes the Balance Sheet balance!
        reserves_line = "Reserves and Surplus" if self.is_div1 else "Other Equity"
        opening_reserves_cy = grouped_cy.get(reserves_line, 0.0)
        closing_reserves_cy = opening_reserves_cy + pat_cy
        grouped_cy[reserves_line] = closing_reserves_cy

        opening_reserves_py = grouped_py.get(reserves_line, 0.0)
        closing_reserves_py = opening_reserves_py + pat_py
        grouped_py[reserves_line] = closing_reserves_py

        # Update the note as well
        if reserves_line in notes_dict:
            notes_dict[reserves_line].total_cy = closing_reserves_cy
            notes_dict[reserves_line].total_py = closing_reserves_py
            notes_dict[reserves_line].ledgers.append({
                "ledger_name": "Add: Profit for the year transferred from Statement of Profit & Loss",
                "group": "Surplus Roll-forward",
                "amount_cy": pat_cy,
                "amount_py": pat_py,
                "confidence": 1.0,
                "match_source": "STATUTORY_ROLLFORWARD",
                "ca_rule_tag": "PL_PROFIT_CARRY_FORWARD"
            })

        # 4. Build Structured Balance Sheet DataFrame
        bs_rows = self._build_balance_sheet_rows(grouped_cy, grouped_py, schema_dict)
        bs_df = pd.DataFrame(bs_rows)

        # 5. Build Structured Profit & Loss DataFrame
        pl_rows = self._build_pl_rows(grouped_cy, grouped_py, schema_dict, pat_cy, pat_py)
        pl_df = pd.DataFrame(pl_rows)

        # 6. Compute Total Assets and Total Equity & Liabilities for Checks
        total_assets_cy = float(bs_df.loc[bs_df["Particulars"] == "TOTAL ASSETS", self.cy_label].values[0] if (bs_df["Particulars"] == "TOTAL ASSETS").any() else 0.0)
        total_eq_liab_cy = float(bs_df.loc[bs_df["Particulars"] == "TOTAL EQUITY AND LIABILITIES", self.cy_label].values[0] if (bs_df["Particulars"] == "TOTAL EQUITY AND LIABILITIES").any() else 0.0)

        total_assets_py = float(bs_df.loc[bs_df["Particulars"] == "TOTAL ASSETS", self.py_label].values[0] if (bs_df["Particulars"] == "TOTAL ASSETS").any() else 0.0)
        total_eq_liab_py = float(bs_df.loc[bs_df["Particulars"] == "TOTAL EQUITY AND LIABILITIES", self.py_label].values[0] if (bs_df["Particulars"] == "TOTAL EQUITY AND LIABILITIES").any() else 0.0)

        # 7. Drill Down Table
        drill_down_df = df[[
            "ledger_name", "group", "debit_cy", "credit_cy", "net_cy",
            "target_line_item", "statement_type", "category",
            "confidence", "match_source", "ca_rule_tag"
        ]].copy()
        drill_down_df.rename(columns={
            "ledger_name": "Ledger Name",
            "group": "Group",
            "debit_cy": "Debit (CY)",
            "credit_cy": "Credit (CY)",
            "net_cy": "Net Balance (CY)",
            "target_line_item": "Schedule III Line Item",
            "statement_type": "Statement",
            "category": "Classification",
            "confidence": "Match Score",
            "match_source": "Source",
            "ca_rule_tag": "CA Rule Tag"
        }, inplace=True)

        return GeneratedFinancialStatements(
            division=self.division,
            rounding_unit=self.rounding_unit,
            unit_multiplier=self.multiplier,
            cy_label=self.cy_label,
            py_label=self.py_label,
            balance_sheet_df=bs_df,
            pl_df=pl_df,
            notes=notes_dict,
            drill_down_df=drill_down_df,
            net_profit_cy=pat_cy,
            net_profit_py=pat_py,
            total_assets_cy=total_assets_cy,
            total_equity_liab_cy=total_eq_liab_cy,
            total_assets_py=total_assets_py,
            total_equity_liab_py=total_eq_liab_py,
            bs_diff_cy=round(total_assets_cy - total_eq_liab_cy, 2),
            bs_diff_py=round(total_assets_py - total_eq_liab_py, 2),
            raw_totals=grouped_cy
        )

    def _val(self, val: float) -> float:
        """Scales raw value by rounding unit multiplier."""
        return round(val / self.multiplier, 4)

    def _build_balance_sheet_rows(self, cy: Dict[str, float], py: Dict[str, float], schema_dict: Dict[str, ScheduleIIILineItem]) -> List[Dict[str, Any]]:
        rows = []
        if self.is_div1:
            # --- DIVISION I BALANCE SHEET ---
            rows.append({"Particulars": "I. EQUITY AND LIABILITIES", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            
            # (1) Shareholders' Funds
            rows.append({"Particulars": "(1) Shareholders' Funds", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            sc_cy, sc_py = cy.get("Share Capital", 0.0), py.get("Share Capital", 0.0)
            rs_cy, rs_py = cy.get("Reserves and Surplus", 0.0), py.get("Reserves and Surplus", 0.0)
            mrw_cy, mrw_py = cy.get("Money received against share warrants", 0.0), py.get("Money received against share warrants", 0.0)
            tot_shf_cy = sc_cy + rs_cy + mrw_cy
            tot_shf_py = sc_py + rs_py + mrw_py

            rows.append({"Particulars": "   (a) Share capital", "Note No.": 1, self.cy_label: self._val(sc_cy), self.py_label: self._val(sc_py), "is_header": False})
            rows.append({"Particulars": "   (b) Reserves and surplus", "Note No.": 2, self.cy_label: self._val(rs_cy), self.py_label: self._val(rs_py), "is_header": False})
            if mrw_cy > 0 or mrw_py > 0:
                rows.append({"Particulars": "   (c) Money received against share warrants", "Note No.": 3, self.cy_label: self._val(mrw_cy), self.py_label: self._val(mrw_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Shareholders' Funds", "Note No.": "", self.cy_label: self._val(tot_shf_cy), self.py_label: self._val(tot_shf_py), "is_subtotal": True})

            # (2) Share application money pending allotment
            samp_cy, samp_py = cy.get("Share application money pending allotment", 0.0), py.get("Share application money pending allotment", 0.0)
            if samp_cy > 0 or samp_py > 0:
                rows.append({"Particulars": "(2) Share application money pending allotment", "Note No.": 4, self.cy_label: self._val(samp_cy), self.py_label: self._val(samp_py), "is_header": False})

            # (3) Non-current liabilities
            rows.append({"Particulars": "(3) Non-Current Liabilities", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            ltb_cy, ltb_py = cy.get("Long-term borrowings", 0.0), py.get("Long-term borrowings", 0.0)
            dtl_cy, dtl_py = cy.get("Deferred tax liabilities (Net)", 0.0), py.get("Deferred tax liabilities (Net)", 0.0)
            oltl_cy, oltl_py = cy.get("Other Long term liabilities", 0.0), py.get("Other Long term liabilities", 0.0)
            ltp_cy, ltp_py = cy.get("Long-term provisions", 0.0), py.get("Long-term provisions", 0.0)
            tot_ncl_cy = ltb_cy + dtl_cy + oltl_cy + ltp_cy
            tot_ncl_py = ltb_py + dtl_py + oltl_py + ltp_py

            rows.append({"Particulars": "   (a) Long-term borrowings", "Note No.": 5, self.cy_label: self._val(ltb_cy), self.py_label: self._val(ltb_py), "is_header": False})
            rows.append({"Particulars": "   (b) Deferred tax liabilities (Net)", "Note No.": 6, self.cy_label: self._val(dtl_cy), self.py_label: self._val(dtl_py), "is_header": False})
            rows.append({"Particulars": "   (c) Other Long term liabilities", "Note No.": 7, self.cy_label: self._val(oltl_cy), self.py_label: self._val(oltl_py), "is_header": False})
            rows.append({"Particulars": "   (d) Long-term provisions", "Note No.": 8, self.cy_label: self._val(ltp_cy), self.py_label: self._val(ltp_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Non-Current Liabilities", "Note No.": "", self.cy_label: self._val(tot_ncl_cy), self.py_label: self._val(tot_ncl_py), "is_subtotal": True})

            # (4) Current liabilities
            rows.append({"Particulars": "(4) Current Liabilities", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            stb_cy, stb_py = cy.get("Short-term borrowings", 0.0), py.get("Short-term borrowings", 0.0)
            tp_msme_cy, tp_msme_py = cy.get("Trade payables - Dues of MSME", 0.0), py.get("Trade payables - Dues of MSME", 0.0)
            tp_oth_cy, tp_oth_py = cy.get("Trade payables - Dues of creditors other than MSME", 0.0), py.get("Trade payables - Dues of creditors other than MSME", 0.0)
            ocl_cy, ocl_py = cy.get("Other current liabilities", 0.0), py.get("Other current liabilities", 0.0)
            stp_cy, stp_py = cy.get("Short-term provisions", 0.0), py.get("Short-term provisions", 0.0)
            tot_cl_cy = stb_cy + tp_msme_cy + tp_oth_cy + ocl_cy + stp_cy
            tot_cl_py = stb_py + tp_msme_py + tp_oth_py + ocl_py + stp_py

            rows.append({"Particulars": "   (a) Short-term borrowings", "Note No.": 9, self.cy_label: self._val(stb_cy), self.py_label: self._val(stb_py), "is_header": False})
            rows.append({"Particulars": "   (b) Trade payables:", "Note No.": 10, self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "       (A) Dues of micro & small enterprises (MSME)", "Note No.": "10A", self.cy_label: self._val(tp_msme_cy), self.py_label: self._val(tp_msme_py), "is_header": False})
            rows.append({"Particulars": "       (B) Dues of other creditors", "Note No.": "10B", self.cy_label: self._val(tp_oth_cy), self.py_label: self._val(tp_oth_py), "is_header": False})
            rows.append({"Particulars": "   (c) Other current liabilities", "Note No.": 11, self.cy_label: self._val(ocl_cy), self.py_label: self._val(ocl_py), "is_header": False})
            rows.append({"Particulars": "   (d) Short-term provisions", "Note No.": 12, self.cy_label: self._val(stp_cy), self.py_label: self._val(stp_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Current Liabilities", "Note No.": "", self.cy_label: self._val(tot_cl_cy), self.py_label: self._val(tot_cl_py), "is_subtotal": True})

            # TOTAL EQUITY AND LIABILITIES
            tot_eq_liab_cy = tot_shf_cy + samp_cy + tot_ncl_cy + tot_cl_cy
            tot_eq_liab_py = tot_shf_py + samp_py + tot_ncl_py + tot_cl_py
            rows.append({"Particulars": "TOTAL EQUITY AND LIABILITIES", "Note No.": "", self.cy_label: self._val(tot_eq_liab_cy), self.py_label: self._val(tot_eq_liab_py), "is_total": True})

            # II. ASSETS
            rows.append({"Particulars": "II. ASSETS", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})

            # (1) Non-current assets
            rows.append({"Particulars": "(1) Non-Current Assets", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            ppe_cy, ppe_py = cy.get("Property, Plant and Equipment (Tangible Assets)", 0.0), py.get("Property, Plant and Equipment (Tangible Assets)", 0.0)
            int_cy, int_py = cy.get("Intangible assets", 0.0), py.get("Intangible assets", 0.0)
            cwip_cy, cwip_py = cy.get("Capital work-in-progress", 0.0), py.get("Capital work-in-progress", 0.0)
            int_dev_cy, int_dev_py = cy.get("Intangible assets under development", 0.0), py.get("Intangible assets under development", 0.0)
            nci_cy, nci_py = cy.get("Non-current investments", 0.0), py.get("Non-current investments", 0.0)
            dta_cy, dta_py = cy.get("Deferred tax assets (Net)", 0.0), py.get("Deferred tax assets (Net)", 0.0)
            ltla_cy, ltla_py = cy.get("Long-term loans and advances", 0.0), py.get("Long-term loans and advances", 0.0)
            onca_cy, onca_py = cy.get("Other non-current assets", 0.0), py.get("Other non-current assets", 0.0)
            tot_nca_cy = ppe_cy + int_cy + cwip_cy + int_dev_cy + nci_cy + dta_cy + ltla_cy + onca_cy
            tot_nca_py = ppe_py + int_py + cwip_py + int_dev_py + nci_py + dta_py + ltla_py + onca_py

            rows.append({"Particulars": "   (a) Property, Plant and Equipment and Intangibles:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "       (i) Property, Plant and Equipment", "Note No.": 13, self.cy_label: self._val(ppe_cy), self.py_label: self._val(ppe_py), "is_header": False})
            rows.append({"Particulars": "       (ii) Intangible assets", "Note No.": 14, self.cy_label: self._val(int_cy), self.py_label: self._val(int_py), "is_header": False})
            rows.append({"Particulars": "       (iii) Capital work-in-progress", "Note No.": 15, self.cy_label: self._val(cwip_cy), self.py_label: self._val(cwip_py), "is_header": False})
            if int_dev_cy > 0 or int_dev_py > 0:
                rows.append({"Particulars": "       (iv) Intangible assets under development", "Note No.": 16, self.cy_label: self._val(int_dev_cy), self.py_label: self._val(int_dev_py), "is_header": False})
            rows.append({"Particulars": "   (b) Non-current investments", "Note No.": 17, self.cy_label: self._val(nci_cy), self.py_label: self._val(nci_py), "is_header": False})
            rows.append({"Particulars": "   (c) Deferred tax assets (Net)", "Note No.": 18, self.cy_label: self._val(dta_cy), self.py_label: self._val(dta_py), "is_header": False})
            rows.append({"Particulars": "   (d) Long-term loans and advances", "Note No.": 19, self.cy_label: self._val(ltla_cy), self.py_label: self._val(ltla_py), "is_header": False})
            rows.append({"Particulars": "   (e) Other non-current assets", "Note No.": 20, self.cy_label: self._val(onca_cy), self.py_label: self._val(onca_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Non-Current Assets", "Note No.": "", self.cy_label: self._val(tot_nca_cy), self.py_label: self._val(tot_nca_py), "is_subtotal": True})

            # (2) Current assets
            rows.append({"Particulars": "(2) Current Assets", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            ci_cy, ci_py = cy.get("Current investments", 0.0), py.get("Current investments", 0.0)
            inv_cy, inv_py = cy.get("Inventories", 0.0), py.get("Inventories", 0.0)
            tr_cy, tr_py = cy.get("Trade receivables", 0.0), py.get("Trade receivables", 0.0)
            cash_cy, cash_py = cy.get("Cash and bank balances", 0.0), py.get("Cash and bank balances", 0.0)
            stla_cy, stla_py = cy.get("Short-term loans and advances", 0.0), py.get("Short-term loans and advances", 0.0)
            oca_cy, oca_py = cy.get("Other current assets", 0.0), py.get("Other current assets", 0.0)
            tot_ca_cy = ci_cy + inv_cy + tr_cy + cash_cy + stla_cy + oca_cy
            tot_ca_py = ci_py + inv_py + tr_py + cash_py + stla_py + oca_py

            rows.append({"Particulars": "   (a) Current investments", "Note No.": 21, self.cy_label: self._val(ci_cy), self.py_label: self._val(ci_py), "is_header": False})
            rows.append({"Particulars": "   (b) Inventories", "Note No.": 22, self.cy_label: self._val(inv_cy), self.py_label: self._val(inv_py), "is_header": False})
            rows.append({"Particulars": "   (c) Trade receivables", "Note No.": 23, self.cy_label: self._val(tr_cy), self.py_label: self._val(tr_py), "is_header": False})
            rows.append({"Particulars": "   (d) Cash and bank balances", "Note No.": 24, self.cy_label: self._val(cash_cy), self.py_label: self._val(cash_py), "is_header": False})
            rows.append({"Particulars": "   (e) Short-term loans and advances", "Note No.": 25, self.cy_label: self._val(stla_cy), self.py_label: self._val(stla_py), "is_header": False})
            rows.append({"Particulars": "   (f) Other current assets", "Note No.": 26, self.cy_label: self._val(oca_cy), self.py_label: self._val(oca_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Current Assets", "Note No.": "", self.cy_label: self._val(tot_ca_cy), self.py_label: self._val(tot_ca_py), "is_subtotal": True})

            # TOTAL ASSETS
            tot_assets_cy = tot_nca_cy + tot_ca_cy
            tot_assets_py = tot_nca_py + tot_ca_py
            rows.append({"Particulars": "TOTAL ASSETS", "Note No.": "", self.cy_label: self._val(tot_assets_cy), self.py_label: self._val(tot_assets_py), "is_total": True})

        else:
            # --- DIVISION II BALANCE SHEET (IND AS) ---
            rows.append({"Particulars": "ASSETS", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "(1) Non-Current Assets", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})

            ppe_cy, ppe_py = cy.get("Property, Plant and Equipment", 0.0), py.get("Property, Plant and Equipment", 0.0)
            cwip_cy, cwip_py = cy.get("Capital work-in-progress", 0.0), py.get("Capital work-in-progress", 0.0)
            rou_cy, rou_py = cy.get("Right-of-use assets", 0.0), py.get("Right-of-use assets", 0.0)
            gw_cy, gw_py = cy.get("Goodwill", 0.0), py.get("Goodwill", 0.0)
            int_cy, int_py = cy.get("Other Intangible assets", 0.0), py.get("Other Intangible assets", 0.0)
            fa_nci_cy, fa_nci_py = cy.get("Financial Assets - Non-current Investments", 0.0), py.get("Financial Assets - Non-current Investments", 0.0)
            fa_nctr_cy, fa_nctr_py = cy.get("Financial Assets - Non-current Trade Receivables", 0.0), py.get("Financial Assets - Non-current Trade Receivables", 0.0)
            fa_ncloan_cy, fa_ncloan_py = cy.get("Financial Assets - Non-current Loans", 0.0), py.get("Financial Assets - Non-current Loans", 0.0)
            fa_ncoth_cy, fa_ncoth_py = cy.get("Financial Assets - Other non-current financial assets", 0.0), py.get("Financial Assets - Other non-current financial assets", 0.0)
            dta_cy, dta_py = cy.get("Deferred tax assets (Net)", 0.0), py.get("Deferred tax assets (Net)", 0.0)
            onca_cy, onca_py = cy.get("Other non-current assets", 0.0), py.get("Other non-current assets", 0.0)
            tot_nca_cy = ppe_cy + cwip_cy + rou_cy + gw_cy + int_cy + fa_nci_cy + fa_nctr_cy + fa_ncloan_cy + fa_ncoth_cy + dta_cy + onca_cy
            tot_nca_py = ppe_py + cwip_py + rou_py + gw_py + int_py + fa_nci_py + fa_nctr_py + fa_ncloan_py + fa_ncoth_py + dta_py + onca_py

            rows.append({"Particulars": "   (a) Property, Plant and Equipment", "Note No.": 1, self.cy_label: self._val(ppe_cy), self.py_label: self._val(ppe_py), "is_header": False})
            rows.append({"Particulars": "   (b) Capital work-in-progress", "Note No.": 2, self.cy_label: self._val(cwip_cy), self.py_label: self._val(cwip_py), "is_header": False})
            if rou_cy > 0 or rou_py > 0:
                rows.append({"Particulars": "   (c) Right-of-use assets", "Note No.": 3, self.cy_label: self._val(rou_cy), self.py_label: self._val(rou_py), "is_header": False})
            if gw_cy > 0 or gw_py > 0:
                rows.append({"Particulars": "   (d) Goodwill", "Note No.": 4, self.cy_label: self._val(gw_cy), self.py_label: self._val(gw_py), "is_header": False})
            rows.append({"Particulars": "   (e) Other Intangible assets", "Note No.": 5, self.cy_label: self._val(int_cy), self.py_label: self._val(int_py), "is_header": False})
            rows.append({"Particulars": "   (f) Financial Assets:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "       (i) Investments", "Note No.": 8, self.cy_label: self._val(fa_nci_cy), self.py_label: self._val(fa_nci_py), "is_header": False})
            if fa_nctr_cy > 0 or fa_nctr_py > 0:
                rows.append({"Particulars": "       (ii) Trade receivables", "Note No.": 9, self.cy_label: self._val(fa_nctr_cy), self.py_label: self._val(fa_nctr_py), "is_header": False})
            if fa_ncloan_cy > 0 or fa_ncloan_py > 0:
                rows.append({"Particulars": "       (iii) Loans", "Note No.": 10, self.cy_label: self._val(fa_ncloan_cy), self.py_label: self._val(fa_ncloan_py), "is_header": False})
            if fa_ncoth_cy > 0 or fa_ncoth_py > 0:
                rows.append({"Particulars": "       (iv) Other non-current financial assets", "Note No.": 11, self.cy_label: self._val(fa_ncoth_cy), self.py_label: self._val(fa_ncoth_py), "is_header": False})
            rows.append({"Particulars": "   (g) Deferred tax assets (Net)", "Note No.": 12, self.cy_label: self._val(dta_cy), self.py_label: self._val(dta_py), "is_header": False})
            rows.append({"Particulars": "   (h) Other non-current assets", "Note No.": 13, self.cy_label: self._val(onca_cy), self.py_label: self._val(onca_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Non-Current Assets", "Note No.": "", self.cy_label: self._val(tot_nca_cy), self.py_label: self._val(tot_nca_py), "is_subtotal": True})

            # (2) Current assets
            rows.append({"Particulars": "(2) Current Assets", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            inv_cy, inv_py = cy.get("Inventories", 0.0), py.get("Inventories", 0.0)
            fa_ci_cy, fa_ci_py = cy.get("Financial Assets - Current Investments", 0.0), py.get("Financial Assets - Current Investments", 0.0)
            fa_tr_cy, fa_tr_py = cy.get("Financial Assets - Trade receivables", 0.0), py.get("Financial Assets - Trade receivables", 0.0)
            fa_cash_cy, fa_cash_py = cy.get("Financial Assets - Cash and cash equivalents", 0.0), py.get("Financial Assets - Cash and cash equivalents", 0.0)
            fa_bank_cy, fa_bank_py = cy.get("Financial Assets - Bank balances other than cash equivalents", 0.0), py.get("Financial Assets - Bank balances other than cash equivalents", 0.0)
            fa_loan_cy, fa_loan_py = cy.get("Financial Assets - Current Loans", 0.0), py.get("Financial Assets - Current Loans", 0.0)
            fa_coth_cy, fa_coth_py = cy.get("Financial Assets - Other current financial assets", 0.0), py.get("Financial Assets - Other current financial assets", 0.0)
            cta_cy, cta_py = cy.get("Current tax assets (Net)", 0.0), py.get("Current tax assets (Net)", 0.0)
            oca_cy, oca_py = cy.get("Other current assets", 0.0), py.get("Other current assets", 0.0)
            tot_ca_cy = inv_cy + fa_ci_cy + fa_tr_cy + fa_cash_cy + fa_bank_cy + fa_loan_cy + fa_coth_cy + cta_cy + oca_cy
            tot_ca_py = inv_py + fa_ci_py + fa_tr_py + fa_cash_py + fa_bank_py + fa_loan_py + fa_coth_py + cta_py + oca_py

            rows.append({"Particulars": "   (a) Inventories", "Note No.": 14, self.cy_label: self._val(inv_cy), self.py_label: self._val(inv_py), "is_header": False})
            rows.append({"Particulars": "   (b) Financial Assets:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "       (i) Investments", "Note No.": 15, self.cy_label: self._val(fa_ci_cy), self.py_label: self._val(fa_ci_py), "is_header": False})
            rows.append({"Particulars": "       (ii) Trade receivables", "Note No.": 16, self.cy_label: self._val(fa_tr_cy), self.py_label: self._val(fa_tr_py), "is_header": False})
            rows.append({"Particulars": "       (iii) Cash and cash equivalents", "Note No.": 17, self.cy_label: self._val(fa_cash_cy), self.py_label: self._val(fa_cash_py), "is_header": False})
            rows.append({"Particulars": "       (iv) Bank balances other than cash equivalents", "Note No.": 18, self.cy_label: self._val(fa_bank_cy), self.py_label: self._val(fa_bank_py), "is_header": False})
            if fa_loan_cy > 0 or fa_loan_py > 0:
                rows.append({"Particulars": "       (v) Loans", "Note No.": 19, self.cy_label: self._val(fa_loan_cy), self.py_label: self._val(fa_loan_py), "is_header": False})
            if fa_coth_cy > 0 or fa_coth_py > 0:
                rows.append({"Particulars": "       (vi) Other current financial assets", "Note No.": 20, self.cy_label: self._val(fa_coth_cy), self.py_label: self._val(fa_coth_py), "is_header": False})
            rows.append({"Particulars": "   (c) Current tax assets (Net)", "Note No.": 21, self.cy_label: self._val(cta_cy), self.py_label: self._val(cta_py), "is_header": False})
            rows.append({"Particulars": "   (d) Other current assets", "Note No.": 22, self.cy_label: self._val(oca_cy), self.py_label: self._val(oca_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Current Assets", "Note No.": "", self.cy_label: self._val(tot_ca_cy), self.py_label: self._val(tot_ca_py), "is_subtotal": True})

            tot_assets_cy = tot_nca_cy + tot_ca_cy
            tot_assets_py = tot_nca_py + tot_ca_py
            rows.append({"Particulars": "TOTAL ASSETS", "Note No.": "", self.cy_label: self._val(tot_assets_cy), self.py_label: self._val(tot_assets_py), "is_total": True})

            # EQUITY AND LIABILITIES
            rows.append({"Particulars": "EQUITY AND LIABILITIES", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            eq_sc_cy, eq_sc_py = cy.get("Equity Share capital", 0.0), py.get("Equity Share capital", 0.0)
            eq_oe_cy, eq_oe_py = cy.get("Other Equity", 0.0), py.get("Other Equity", 0.0)
            tot_eq_cy = eq_sc_cy + eq_oe_cy
            tot_eq_py = eq_sc_py + eq_oe_py

            rows.append({"Particulars": "(1) Equity", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "   (a) Equity share capital", "Note No.": 23, self.cy_label: self._val(eq_sc_cy), self.py_label: self._val(eq_sc_py), "is_header": False})
            rows.append({"Particulars": "   (b) Other equity", "Note No.": 24, self.cy_label: self._val(eq_oe_cy), self.py_label: self._val(eq_oe_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Equity", "Note No.": "", self.cy_label: self._val(tot_eq_cy), self.py_label: self._val(tot_eq_py), "is_subtotal": True})

            # Non-Current Liabilities
            rows.append({"Particulars": "(2) Non-Current Liabilities", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            fl_ncb_cy, fl_ncb_py = cy.get("Financial Liabilities - Non-current Borrowings", 0.0), py.get("Financial Liabilities - Non-current Borrowings", 0.0)
            fl_ncl_cy, fl_ncl_py = cy.get("Financial Liabilities - Non-current Lease liabilities", 0.0), py.get("Financial Liabilities - Non-current Lease liabilities", 0.0)
            fl_ncoth_cy, fl_ncoth_py = cy.get("Financial Liabilities - Other non-current financial liabilities", 0.0), py.get("Financial Liabilities - Other non-current financial liabilities", 0.0)
            ncprov_cy, ncprov_py = cy.get("Non-current Provisions", 0.0), py.get("Non-current Provisions", 0.0)
            dtl_cy, dtl_py = cy.get("Deferred tax liabilities (Net)", 0.0), py.get("Deferred tax liabilities (Net)", 0.0)
            oncl_cy, oncl_py = cy.get("Other non-current liabilities", 0.0), py.get("Other non-current liabilities", 0.0)
            tot_ncl_cy = fl_ncb_cy + fl_ncl_cy + fl_ncoth_cy + ncprov_cy + dtl_cy + oncl_cy
            tot_ncl_py = fl_ncb_py + fl_ncl_py + fl_ncoth_py + ncprov_py + dtl_py + oncl_py

            rows.append({"Particulars": "   (a) Financial Liabilities:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "       (i) Borrowings", "Note No.": 25, self.cy_label: self._val(fl_ncb_cy), self.py_label: self._val(fl_ncb_py), "is_header": False})
            if fl_ncl_cy > 0 or fl_ncl_py > 0:
                rows.append({"Particulars": "       (ia) Lease liabilities", "Note No.": 26, self.cy_label: self._val(fl_ncl_cy), self.py_label: self._val(fl_ncl_py), "is_header": False})
            if fl_ncoth_cy > 0 or fl_ncoth_py > 0:
                rows.append({"Particulars": "       (ii) Other financial liabilities", "Note No.": 28, self.cy_label: self._val(fl_ncoth_cy), self.py_label: self._val(fl_ncoth_py), "is_header": False})
            rows.append({"Particulars": "   (b) Provisions", "Note No.": 29, self.cy_label: self._val(ncprov_cy), self.py_label: self._val(ncprov_py), "is_header": False})
            rows.append({"Particulars": "   (c) Deferred tax liabilities (Net)", "Note No.": 30, self.cy_label: self._val(dtl_cy), self.py_label: self._val(dtl_py), "is_header": False})
            if oncl_cy > 0 or oncl_py > 0:
                rows.append({"Particulars": "   (d) Other non-current liabilities", "Note No.": 31, self.cy_label: self._val(oncl_cy), self.py_label: self._val(oncl_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Non-Current Liabilities", "Note No.": "", self.cy_label: self._val(tot_ncl_cy), self.py_label: self._val(tot_ncl_py), "is_subtotal": True})

            # Current Liabilities
            rows.append({"Particulars": "(3) Current Liabilities", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            fl_cb_cy, fl_cb_py = cy.get("Financial Liabilities - Current Borrowings", 0.0), py.get("Financial Liabilities - Current Borrowings", 0.0)
            fl_cl_cy, fl_cl_py = cy.get("Financial Liabilities - Current Lease liabilities", 0.0), py.get("Financial Liabilities - Current Lease liabilities", 0.0)
            tp_msme_cy, tp_msme_py = cy.get("Financial Liabilities - Trade payables - Dues of MSME", 0.0), py.get("Financial Liabilities - Trade payables - Dues of MSME", 0.0)
            tp_oth_cy, tp_oth_py = cy.get("Financial Liabilities - Trade payables - Dues of Others", 0.0), py.get("Financial Liabilities - Trade payables - Dues of Others", 0.0)
            fl_coth_cy, fl_coth_py = cy.get("Financial Liabilities - Other current financial liabilities", 0.0), py.get("Financial Liabilities - Other current financial liabilities", 0.0)
            ocl_cy, ocl_py = cy.get("Other current liabilities", 0.0), py.get("Other current liabilities", 0.0)
            cprov_cy, cprov_py = cy.get("Current Provisions", 0.0), py.get("Current Provisions", 0.0)
            ctl_cy, ctl_py = cy.get("Current tax liabilities (Net)", 0.0), py.get("Current tax liabilities (Net)", 0.0)
            tot_cl_cy = fl_cb_cy + fl_cl_cy + tp_msme_cy + tp_oth_cy + fl_coth_cy + ocl_cy + cprov_cy + ctl_cy
            tot_cl_py = fl_cb_py + fl_cl_py + tp_msme_py + tp_oth_py + fl_coth_py + ocl_py + cprov_py + ctl_py

            rows.append({"Particulars": "   (a) Financial Liabilities:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "       (i) Borrowings", "Note No.": 32, self.cy_label: self._val(fl_cb_cy), self.py_label: self._val(fl_cb_py), "is_header": False})
            if fl_cl_cy > 0 or fl_cl_py > 0:
                rows.append({"Particulars": "       (ia) Lease liabilities", "Note No.": 33, self.cy_label: self._val(fl_cl_cy), self.py_label: self._val(fl_cl_py), "is_header": False})
            rows.append({"Particulars": "       (ii) Trade payables:", "Note No.": 34, self.cy_label: None, self.py_label: None, "is_header": True})
            rows.append({"Particulars": "           (A) Dues of micro & small enterprises (MSME)", "Note No.": "34A", self.cy_label: self._val(tp_msme_cy), self.py_label: self._val(tp_msme_py), "is_header": False})
            rows.append({"Particulars": "           (B) Dues of other creditors", "Note No.": "34B", self.cy_label: self._val(tp_oth_cy), self.py_label: self._val(tp_oth_py), "is_header": False})
            if fl_coth_cy > 0 or fl_coth_py > 0:
                rows.append({"Particulars": "       (iii) Other current financial liabilities", "Note No.": 35, self.cy_label: self._val(fl_coth_cy), self.py_label: self._val(fl_coth_py), "is_header": False})
            rows.append({"Particulars": "   (b) Other current liabilities", "Note No.": 36, self.cy_label: self._val(ocl_cy), self.py_label: self._val(ocl_py), "is_header": False})
            rows.append({"Particulars": "   (c) Provisions", "Note No.": 37, self.cy_label: self._val(cprov_cy), self.py_label: self._val(cprov_py), "is_header": False})
            if ctl_cy > 0 or ctl_py > 0:
                rows.append({"Particulars": "   (d) Current tax liabilities (Net)", "Note No.": 38, self.cy_label: self._val(ctl_cy), self.py_label: self._val(ctl_py), "is_header": False})
            rows.append({"Particulars": "   Sub-total: Current Liabilities", "Note No.": "", self.cy_label: self._val(tot_cl_cy), self.py_label: self._val(tot_cl_py), "is_subtotal": True})

            tot_eq_liab_cy = tot_eq_cy + tot_ncl_cy + tot_cl_cy
            tot_eq_liab_py = tot_eq_py + tot_ncl_py + tot_cl_py
            rows.append({"Particulars": "TOTAL EQUITY AND LIABILITIES", "Note No.": "", self.cy_label: self._val(tot_eq_liab_cy), self.py_label: self._val(tot_eq_liab_py), "is_total": True})

        return rows

    def _build_pl_rows(self, cy: Dict[str, float], py: Dict[str, float], schema_dict: Dict[str, ScheduleIIILineItem], pat_cy: float, pat_py: float) -> List[Dict[str, Any]]:
        rows = []
        rev_note = 27 if self.is_div1 else 39
        oth_inc_note = 28 if self.is_div1 else 40
        mat_note = 29 if self.is_div1 else 41
        pur_note = 30 if self.is_div1 else 42
        chg_note = 31 if self.is_div1 else 43
        emp_note = 32 if self.is_div1 else 44
        fin_note = 33 if self.is_div1 else 45
        dep_note = 34 if self.is_div1 else 46
        oth_exp_note = 35 if self.is_div1 else 47

        rev_cy, rev_py = cy.get("Revenue from operations", 0.0), py.get("Revenue from operations", 0.0)
        oth_inc_cy, oth_inc_py = cy.get("Other income", 0.0), py.get("Other income", 0.0)
        tot_inc_cy = rev_cy + oth_inc_cy
        tot_inc_py = rev_py + oth_inc_py

        mat_cy, mat_py = cy.get("Cost of materials consumed", 0.0), py.get("Cost of materials consumed", 0.0)
        pur_cy, pur_py = cy.get("Purchases of Stock-in-Trade", 0.0), py.get("Purchases of Stock-in-Trade", 0.0)
        chg_cy, chg_py = cy.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0), py.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0)
        emp_cy, emp_py = cy.get("Employee benefits expense", 0.0), py.get("Employee benefits expense", 0.0)
        fin_cy, fin_py = cy.get("Finance costs", 0.0), py.get("Finance costs", 0.0)
        dep_cy, dep_py = cy.get("Depreciation and amortisation expense", 0.0), py.get("Depreciation and amortisation expense", 0.0)
        oth_exp_cy, oth_exp_py = cy.get("Other expenses", 0.0), py.get("Other expenses", 0.0)
        tot_exp_cy = mat_cy + pur_cy + chg_cy + emp_cy + fin_cy + dep_cy + oth_exp_cy
        tot_exp_py = mat_py + pur_py + chg_py + emp_py + fin_py + dep_py + oth_exp_py

        pbt_cy = tot_inc_cy - tot_exp_cy
        pbt_py = tot_inc_py - tot_exp_py

        cur_tax_cy, cur_tax_py = cy.get("Current tax expense", 0.0), py.get("Current tax expense", 0.0)
        def_tax_cy, def_tax_py = cy.get("Deferred tax expense / (credit)", 0.0), py.get("Deferred tax expense / (credit)", 0.0)
        tot_tax_cy = cur_tax_cy + def_tax_cy
        tot_tax_py = cur_tax_py + def_tax_py

        rows.append({"Particulars": "I. Revenue from operations", "Note No.": rev_note, self.cy_label: self._val(rev_cy), self.py_label: self._val(rev_py), "is_header": False})
        rows.append({"Particulars": "II. Other income", "Note No.": oth_inc_note, self.cy_label: self._val(oth_inc_cy), self.py_label: self._val(oth_inc_py), "is_header": False})
        rows.append({"Particulars": "III. Total Income (I + II)", "Note No.": "", self.cy_label: self._val(tot_inc_cy), self.py_label: self._val(tot_inc_py), "is_subtotal": True})
        
        rows.append({"Particulars": "IV. Expenses:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
        rows.append({"Particulars": "   Cost of materials consumed", "Note No.": mat_note, self.cy_label: self._val(mat_cy), self.py_label: self._val(mat_py), "is_header": False})
        rows.append({"Particulars": "   Purchases of Stock-in-Trade", "Note No.": pur_note, self.cy_label: self._val(pur_cy), self.py_label: self._val(pur_py), "is_header": False})
        rows.append({"Particulars": "   Changes in inventories of FG, WIP and Stock-in-Trade", "Note No.": chg_note, self.cy_label: self._val(chg_cy), self.py_label: self._val(chg_py), "is_header": False})
        rows.append({"Particulars": "   Employee benefits expense", "Note No.": emp_note, self.cy_label: self._val(emp_cy), self.py_label: self._val(emp_py), "is_header": False})
        rows.append({"Particulars": "   Finance costs", "Note No.": fin_note, self.cy_label: self._val(fin_cy), self.py_label: self._val(fin_py), "is_header": False})
        rows.append({"Particulars": "   Depreciation and amortisation expense", "Note No.": dep_note, self.cy_label: self._val(dep_cy), self.py_label: self._val(dep_py), "is_header": False})
        rows.append({"Particulars": "   Other expenses", "Note No.": oth_exp_note, self.cy_label: self._val(oth_exp_cy), self.py_label: self._val(oth_exp_py), "is_header": False})
        rows.append({"Particulars": "   Total Expenses (IV)", "Note No.": "", self.cy_label: self._val(tot_exp_cy), self.py_label: self._val(tot_exp_py), "is_subtotal": True})

        rows.append({"Particulars": "V. Profit Before Tax (III - IV)", "Note No.": "", self.cy_label: self._val(pbt_cy), self.py_label: self._val(pbt_py), "is_subtotal": True})
        
        rows.append({"Particulars": "VI. Tax Expense:", "Note No.": "", self.cy_label: None, self.py_label: None, "is_header": True})
        rows.append({"Particulars": "   (1) Current tax", "Note No.": 37 if self.is_div1 else 49, self.cy_label: self._val(cur_tax_cy), self.py_label: self._val(cur_tax_py), "is_header": False})
        rows.append({"Particulars": "   (2) Deferred tax", "Note No.": 38 if self.is_div1 else 50, self.cy_label: self._val(def_tax_cy), self.py_label: self._val(def_tax_py), "is_header": False})
        rows.append({"Particulars": "   Total Tax Expense", "Note No.": "", self.cy_label: self._val(tot_tax_cy), self.py_label: self._val(tot_tax_py), "is_subtotal": True})

        rows.append({"Particulars": "VII. Profit for the period (V - VI)", "Note No.": "", self.cy_label: self._val(pat_cy), self.py_label: self._val(pat_py), "is_total": True})

        if not self.is_div1:
            oci_cy = cy.get("Other Comprehensive Income / (Loss)", 0.0)
            oci_py = py.get("Other Comprehensive Income / (Loss)", 0.0)
            tci_cy = pat_cy + oci_cy
            tci_py = pat_py + oci_py
            rows.append({"Particulars": "VIII. Other Comprehensive Income", "Note No.": 51, self.cy_label: self._val(oci_cy), self.py_label: self._val(oci_py), "is_header": False})
            rows.append({"Particulars": "IX. Total Comprehensive Income (VII + VIII)", "Note No.": "", self.cy_label: self._val(tci_cy), self.py_label: self._val(tci_py), "is_total": True})

        return rows

    def export_to_fmcg_schema(self, stmts: GeneratedFinancialStatements, symbol: str = "SCHEDULE_III_CO", company_name: str = "Corporate Entity") -> Dict[str, Any]:
        """
        Exports statements into standardized FMCG Financial Analysis Engine dictionary schema!
        Enables instant pipeline connectivity into ratio, DuPont, leverage and EVA models.
        """
        raw = stmts.raw_totals
        # Values in INR Crores for FMCG engine convention
        cr_div = 1e7

        is_cy = {
            "fiscal_year": "FY24",
            "revenue": round(raw.get("Revenue from operations", 0.0) / cr_div, 2),
            "cogs": round((raw.get("Cost of materials consumed", 0.0) + raw.get("Purchases of Stock-in-Trade", 0.0) + raw.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0)) / cr_div, 2),
            "gross_profit": round((raw.get("Revenue from operations", 0.0) - (raw.get("Cost of materials consumed", 0.0) + raw.get("Purchases of Stock-in-Trade", 0.0) + raw.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0))) / cr_div, 2),
            "employee_expense": round(raw.get("Employee benefits expense", 0.0) / cr_div, 2),
            "other_operating_expenses": round(raw.get("Other expenses", 0.0) / cr_div, 2),
            "total_operating_expenses": round((raw.get("Cost of materials consumed", 0.0) + raw.get("Purchases of Stock-in-Trade", 0.0) + raw.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0) + raw.get("Employee benefits expense", 0.0) + raw.get("Other expenses", 0.0)) / cr_div, 2),
            "ebitda": round((raw.get("Revenue from operations", 0.0) + raw.get("Other income", 0.0) - (raw.get("Cost of materials consumed", 0.0) + raw.get("Purchases of Stock-in-Trade", 0.0) + raw.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0) + raw.get("Employee benefits expense", 0.0) + raw.get("Other expenses", 0.0))) / cr_div, 2),
            "depreciation": round(raw.get("Depreciation and amortisation expense", 0.0) / cr_div, 2),
            "ebit": round(((raw.get("Revenue from operations", 0.0) - (raw.get("Cost of materials consumed", 0.0) + raw.get("Purchases of Stock-in-Trade", 0.0) + raw.get("Changes in inventories of finished goods, WIP and Stock-in-Trade", 0.0) + raw.get("Employee benefits expense", 0.0) + raw.get("Other expenses", 0.0))) - raw.get("Depreciation and amortisation expense", 0.0)) / cr_div, 2),
            "other_income": round(raw.get("Other income", 0.0) / cr_div, 2),
            "interest_expense": round(raw.get("Finance costs", 0.0) / cr_div, 2),
            "pbt": round((stmts.net_profit_cy + raw.get("Current tax expense", 0.0) + raw.get("Deferred tax expense / (credit)", 0.0)) / cr_div, 2),
            "tax_expense": round((raw.get("Current tax expense", 0.0) + raw.get("Deferred tax expense / (credit)", 0.0)) / cr_div, 2),
            "pat": round(stmts.net_profit_cy / cr_div, 2),
            "shares_outstanding_cr": 10.0,
            "eps": round(stmts.net_profit_cy / (10.0 * 1e7), 2) if stmts.net_profit_cy else 0.0,
            "dps": 0.0,
            "total_dividend_paid": 0.0
        }

        # Long term debt
        lt_debt = raw.get("Long-term borrowings", 0.0) or raw.get("Financial Liabilities - Non-current Borrowings", 0.0)
        st_debt = raw.get("Short-term borrowings", 0.0) or raw.get("Financial Liabilities - Current Borrowings", 0.0)
        tp = raw.get("Trade payables - Dues of creditors other than MSME", 0.0) + raw.get("Trade payables - Dues of MSME", 0.0) + raw.get("Financial Liabilities - Trade payables - Dues of Others", 0.0) + raw.get("Financial Liabilities - Trade payables - Dues of MSME", 0.0)
        nfa = raw.get("Property, Plant and Equipment (Tangible Assets)", 0.0) or raw.get("Property, Plant and Equipment", 0.0)
        cash = raw.get("Cash and bank balances", 0.0) or (raw.get("Financial Assets - Cash and cash equivalents", 0.0) + raw.get("Financial Assets - Bank balances other than cash equivalents", 0.0))
        rec = raw.get("Trade receivables", 0.0) or raw.get("Financial Assets - Trade receivables", 0.0)
        inv = raw.get("Inventories", 0.0)
        sc = raw.get("Share Capital", 0.0) or raw.get("Equity Share capital", 0.0)
        rs = raw.get("Reserves and Surplus", 0.0) or raw.get("Other Equity", 0.0)

        bs_cy = {
            "fiscal_year": "FY24",
            "share_capital": round(sc / cr_div, 2),
            "reserves_and_surplus": round(rs / cr_div, 2),
            "total_equity": round((sc + rs) / cr_div, 2),
            "long_term_debt": round(lt_debt / cr_div, 2),
            "short_term_debt": round(st_debt / cr_div, 2),
            "total_debt": round((lt_debt + st_debt) / cr_div, 2),
            "trade_payables": round(tp / cr_div, 2),
            "other_current_liabilities": round(raw.get("Other current liabilities", 0.0) / cr_div, 2),
            "total_current_liabilities": round((st_debt + tp + raw.get("Other current liabilities", 0.0)) / cr_div, 2),
            "total_liabilities": round((lt_debt + st_debt + tp + raw.get("Other current liabilities", 0.0)) / cr_div, 2),
            "net_fixed_assets": round(nfa / cr_div, 2),
            "intangible_assets": round((raw.get("Intangible assets", 0.0) or raw.get("Other Intangible assets", 0.0)) / cr_div, 2),
            "non_current_investments": round((raw.get("Non-current investments", 0.0) or raw.get("Financial Assets - Non-current Investments", 0.0)) / cr_div, 2),
            "other_non_current_assets": round(raw.get("Other non-current assets", 0.0) / cr_div, 2),
            "inventories": round(inv / cr_div, 2),
            "trade_receivables": round(rec / cr_div, 2),
            "cash_and_equivalents": round(cash / cr_div, 2),
            "other_current_assets": round(raw.get("Other current assets", 0.0) / cr_div, 2),
            "total_current_assets": round((inv + rec + cash + raw.get("Other current assets", 0.0)) / cr_div, 2),
            "total_assets": round((stmts.total_assets_cy * stmts.unit_multiplier) / cr_div, 2),
            "invested_capital": round(((sc + rs) + (lt_debt + st_debt) - cash) / cr_div, 2)
        }

        return {
            "metadata": {
                "symbol": symbol,
                "company_name": company_name,
                "currency": "INR",
                "unit": "INR Crores"
            },
            "income_statements": {"FY24": is_cy},
            "balance_sheets": {"FY24": bs_cy},
            "years": ["FY24"]
        }
