"""
engine/ratios.py
Mandatory Schedule III 11 Ratios Disclosure per MCA Notification GSR 207(E).
Calculates CY, PY, percentage variance, and automatically flags variances exceeding 25%
as required by the Companies (Accounts) Rules / Schedule III disclosures.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from engine.statements import GeneratedFinancialStatements


@dataclass
class RatioResult:
    ratio_name: str
    numerator_desc: str
    denominator_desc: str
    value_cy: float
    value_py: float
    variance_pct: float
    is_variance_significant: bool  # True if abs(variance_pct) > 25.0%
    unit_str: str  # "x", "%", "days"
    ca_commentary: str


def compute_schedule_iii_ratios(stmts: GeneratedFinancialStatements) -> List[RatioResult]:
    """
    Computes all 11 mandatory Schedule III ratios across CY and PY,
    along with variance calculation and >25% change threshold trigger.
    """
    cy = stmts.raw_totals
    py_notes = {k: v.total_py for k, v in stmts.notes.items()}

    # Helper extraction
    def get_val(key_d1: str, key_d2: str, from_cy: bool = True) -> float:
        d = cy if from_cy else py_notes
        return float(d.get(key_d1, 0.0) or d.get(key_d2, 0.0))

    # --- Balance Sheet & P&L Components ---
    # Current Assets
    inv_cy = get_val("Inventories", "Inventories", True)
    inv_py = get_val("Inventories", "Inventories", False)

    rec_cy = get_val("Trade receivables", "Financial Assets - Trade receivables", True)
    rec_py = get_val("Trade receivables", "Financial Assets - Trade receivables", False)

    cash_cy = get_val("Cash and bank balances", "Financial Assets - Cash and cash equivalents", True) + get_val("", "Financial Assets - Bank balances other than cash equivalents", True)
    cash_py = get_val("Cash and bank balances", "Financial Assets - Cash and cash equivalents", False) + get_val("", "Financial Assets - Bank balances other than cash equivalents", False)

    ci_cy = get_val("Current investments", "Financial Assets - Current Investments", True)
    ci_py = get_val("Current investments", "Financial Assets - Current Investments", False)

    oca_cy = get_val("Other current assets", "Other current assets", True) + get_val("Short-term loans and advances", "Financial Assets - Current Loans", True) + get_val("", "Current tax assets (Net)", True)
    oca_py = get_val("Other current assets", "Other current assets", False) + get_val("Short-term loans and advances", "Financial Assets - Current Loans", False) + get_val("", "Current tax assets (Net)", False)

    tot_ca_cy = inv_cy + rec_cy + cash_cy + ci_cy + oca_cy
    tot_ca_py = inv_py + rec_py + cash_py + ci_py + oca_py

    # Current Liabilities
    stb_cy = get_val("Short-term borrowings", "Financial Liabilities - Current Borrowings", True)
    stb_py = get_val("Short-term borrowings", "Financial Liabilities - Current Borrowings", False)

    tp_cy = (
        get_val("Trade payables - Dues of MSME", "Financial Liabilities - Trade payables - Dues of MSME", True)
        + get_val("Trade payables - Dues of creditors other than MSME", "Financial Liabilities - Trade payables - Dues of Others", True)
    )
    tp_py = (
        get_val("Trade payables - Dues of MSME", "Financial Liabilities - Trade payables - Dues of MSME", False)
        + get_val("Trade payables - Dues of creditors other than MSME", "Financial Liabilities - Trade payables - Dues of Others", False)
    )

    ocl_cy = (
        get_val("Other current liabilities", "Other current liabilities", True)
        + get_val("Short-term provisions", "Current Provisions", True)
        + get_val("", "Financial Liabilities - Current Lease liabilities", True)
        + get_val("", "Financial Liabilities - Other current financial liabilities", True)
        + get_val("", "Current tax liabilities (Net)", True)
    )
    ocl_py = (
        get_val("Other current liabilities", "Other current liabilities", False)
        + get_val("Short-term provisions", "Current Provisions", False)
        + get_val("", "Financial Liabilities - Current Lease liabilities", False)
        + get_val("", "Financial Liabilities - Other current financial liabilities", False)
        + get_val("", "Current tax liabilities (Net)", False)
    )

    tot_cl_cy = stb_cy + tp_cy + ocl_cy
    tot_cl_py = stb_py + tp_py + ocl_py

    # Debt
    lt_debt_cy = get_val("Long-term borrowings", "Financial Liabilities - Non-current Borrowings", True) + get_val("", "Financial Liabilities - Non-current Lease liabilities", True)
    lt_debt_py = get_val("Long-term borrowings", "Financial Liabilities - Non-current Borrowings", False) + get_val("", "Financial Liabilities - Non-current Lease liabilities", False)
    tot_debt_cy = lt_debt_cy + stb_cy
    tot_debt_py = lt_debt_py + stb_py

    # Equity (Net Worth)
    sc_cy = get_val("Share Capital", "Equity Share capital", True)
    sc_py = get_val("Share Capital", "Equity Share capital", False)
    rs_cy = get_val("Reserves and Surplus", "Other Equity", True)
    rs_py = get_val("Reserves and Surplus", "Other Equity", False)
    net_worth_cy = sc_cy + rs_cy
    net_worth_py = sc_py + rs_py

    # P&L numbers
    rev_cy = get_val("Revenue from operations", "Revenue from operations", True)
    rev_py = get_val("Revenue from operations", "Revenue from operations", False)

    cogs_cy = (
        get_val("Cost of materials consumed", "Cost of materials consumed", True)
        + get_val("Purchases of Stock-in-Trade", "Purchases of Stock-in-Trade", True)
        + get_val("Changes in inventories of finished goods, WIP and Stock-in-Trade", "Changes in inventories of finished goods, WIP and Stock-in-Trade", True)
    )
    cogs_py = (
        get_val("Cost of materials consumed", "Cost of materials consumed", False)
        + get_val("Purchases of Stock-in-Trade", "Purchases of Stock-in-Trade", False)
        + get_val("Changes in inventories of finished goods, WIP and Stock-in-Trade", "Changes in inventories of finished goods, WIP and Stock-in-Trade", False)
    )

    purchases_cy = get_val("Purchases of Raw Materials - Domestic", "Cost of materials consumed", True) or cogs_cy
    purchases_py = get_val("Purchases of Raw Materials - Domestic", "Cost of materials consumed", False) or cogs_py

    pat_cy = stmts.net_profit_cy
    pat_py = stmts.net_profit_py

    fin_cost_cy = get_val("Finance costs", "Finance costs", True)
    fin_cost_py = get_val("Finance costs", "Finance costs", False)

    depr_cy = get_val("Depreciation and amortisation expense", "Depreciation and amortisation expense", True)
    depr_py = get_val("Depreciation and amortisation expense", "Depreciation and amortisation expense", False)

    ebit_cy = (rev_cy - cogs_cy - get_val("Employee benefits expense", "Employee benefits expense", True) - get_val("Other expenses", "Other expenses", True)) - depr_cy
    ebit_py = (rev_py - cogs_py - get_val("Employee benefits expense", "Employee benefits expense", False) - get_val("Other expenses", "Other expenses", False)) - depr_py

    capital_employed_cy = net_worth_cy + tot_debt_cy + get_val("Deferred tax liabilities (Net)", "Deferred tax liabilities (Net)", True)
    capital_employed_py = net_worth_py + tot_debt_py + get_val("Deferred tax liabilities (Net)", "Deferred tax liabilities (Net)", False)

    total_assets_cy = (stmts.total_assets_cy * stmts.unit_multiplier) or 1.0
    total_assets_py = (stmts.total_assets_py * stmts.unit_multiplier) or 1.0

    ratios_list: List[RatioResult] = []

    def add_ratio(name: str, num_desc: str, den_desc: str, val_cy: float, val_py: float, unit: str = "x", default_reason: str = ""):
        v_cy = round(val_cy, 2)
        v_py = round(val_py, 2)
        if abs(v_py) > 1e-4:
            var_pct = round(((v_cy - v_py) / abs(v_py)) * 100.0, 2)
        else:
            var_pct = 0.0

        is_sig = abs(var_pct) > 25.0
        if is_sig:
            commentary = f"Significant variance of {var_pct:+.1f}% noted. {default_reason} Explanation is mandatorily required under Schedule III note disclosures."
        else:
            commentary = f"Variance of {var_pct:+.1f}% is within acceptable operational range (<= 25%). No mandatory disclosure trigger."

        ratios_list.append(RatioResult(
            ratio_name=name,
            numerator_desc=num_desc,
            denominator_desc=den_desc,
            value_cy=v_cy,
            value_py=v_py,
            variance_pct=var_pct,
            is_variance_significant=is_sig,
            unit_str=unit,
            ca_commentary=commentary
        ))

    # 1. Current Ratio
    cr_cy = (tot_ca_cy / tot_cl_cy) if tot_cl_cy else 0.0
    cr_py = (tot_ca_py / tot_cl_py) if tot_cl_py else 0.0
    add_ratio("1. Current Ratio", "Current Assets", "Current Liabilities", cr_cy, cr_py, "x", "Change driven by working capital reallocation and current liability repayment cycle.")

    # 2. Debt-Equity Ratio
    de_cy = (tot_debt_cy / net_worth_cy) if net_worth_cy else 0.0
    de_py = (tot_debt_py / net_worth_py) if net_worth_py else 0.0
    add_ratio("2. Debt-Equity Ratio", "Total Debt", "Total Shareholder's Equity", de_cy, de_py, "x", "Reflects changes in long-term borrowings and retained profit accretion.")

    # 3. Debt Service Coverage Ratio (DSCR)
    dscr_cy = ((pat_cy + depr_cy + fin_cost_cy) / (fin_cost_cy + stb_cy * 0.2)) if (fin_cost_cy + stb_cy * 0.2) else 0.0
    dscr_py = ((pat_py + depr_py + fin_cost_py) / (fin_cost_py + stb_py * 0.2)) if (fin_cost_py + stb_py * 0.2) else 0.0
    add_ratio("3. Debt Service Coverage Ratio (DSCR)", "Earnings available for debt service (PAT + Depr + Interest)", "Debt Service (Interest + Scheduled Principal Repayments)", dscr_cy, dscr_py, "x", "Driven by operational cash generation and debt service obligation maturity schedule.")

    # 4. Return on Equity (ROE)
    roe_cy = (pat_cy / net_worth_cy * 100.0) if net_worth_cy else 0.0
    roe_py = (pat_py / net_worth_py * 100.0) if net_worth_py else 0.0
    add_ratio("4. Return on Equity Ratio (ROE)", "Net Profit after taxes", "Shareholder's Equity (Net Worth)", roe_cy, roe_py, "%", "Variance driven by net profit margin expansion/compression relative to equity base.")

    # 5. Inventory Turnover Ratio
    inv_to_cy = (cogs_cy / inv_cy) if inv_cy else 0.0
    inv_to_py = (cogs_py / inv_py) if inv_py else 0.0
    add_ratio("5. Inventory Turnover Ratio", "Cost of Goods Sold (COGS)", "Closing Inventory", inv_to_cy, inv_to_py, "x", "Impacted by inventory holding levels, procurement timing, and sales velocity.")

    # 6. Trade Receivables Turnover Ratio
    rec_to_cy = (rev_cy / rec_cy) if rec_cy else 0.0
    rec_to_py = (rev_py / rec_py) if rec_py else 0.0
    add_ratio("6. Trade Receivables Turnover Ratio", "Revenue from Operations", "Closing Trade Receivables", rec_to_cy, rec_to_py, "x", "Attributable to debtor collection efficiency and customer credit period terms.")

    # 7. Trade Payables Turnover Ratio
    pay_to_cy = (purchases_cy / tp_cy) if tp_cy else 0.0
    pay_to_py = (purchases_py / tp_py) if tp_py else 0.0
    add_ratio("7. Trade Payables Turnover Ratio", "Total Purchases", "Closing Trade Payables", pay_to_cy, pay_to_py, "x", "Reflects vendor payment discipline, MSME credit adherence, and raw material purchase terms.")

    # 8. Net Capital Turnover Ratio (Working Capital Turnover)
    nwc_cy = tot_ca_cy - tot_cl_cy
    nwc_py = tot_ca_py - tot_cl_py
    nct_cy = (rev_cy / nwc_cy) if nwc_cy != 0 else 0.0
    nct_py = (rev_py / nwc_py) if nwc_py != 0 else 0.0
    add_ratio("8. Net Capital Turnover Ratio", "Revenue from Operations", "Working Capital (Current Assets - Current Liabilities)", nct_cy, nct_py, "x", "Shift due to operational revenue scale relative to net current assets deployment.")

    # 9. Net Profit Margin Ratio
    npm_cy = (pat_cy / rev_cy * 100.0) if rev_cy else 0.0
    npm_py = (pat_py / rev_py * 100.0) if rev_py else 0.0
    add_ratio("9. Net Profit Margin Ratio", "Net Profit after taxes", "Revenue from Operations", npm_cy, npm_py, "%", "Change in operating cost structure, raw material input prices, and interest cost burden.")

    # 10. Return on Capital Employed (ROCE)
    roce_cy = (ebit_cy / capital_employed_cy * 100.0) if capital_employed_cy else 0.0
    roce_py = (ebit_py / capital_employed_py * 100.0) if capital_employed_py else 0.0
    add_ratio("10. Return on Capital Employed (ROCE)", "Earnings before interest and taxes (EBIT)", "Capital Employed (Net Worth + Debt + DTL)", roce_cy, roce_py, "%", "Driven by asset productivity and operating margin performance relative to invested capital.")

    # 11. Return on Investment (ROI)
    roi_cy = (pat_cy / total_assets_cy * 100.0) if total_assets_cy else 0.0
    roi_py = (pat_py / total_assets_py * 100.0) if total_assets_py else 0.0
    add_ratio("11. Return on Investment (ROI)", "Net Profit after taxes", "Total Assets", roi_cy, roi_py, "%", "Reflects overall total balance sheet asset utilization efficiency.")

    return ratios_list


def ratios_to_dataframe(ratios: List[RatioResult], cy_label: str, py_label: str) -> pd.DataFrame:
    rows = []
    for r in ratios:
        flag_str = "⚠️ YES (>25%)" if r.is_variance_significant else "✅ NO (<=25%)"
        rows.append({
            "Schedule III Mandatory Ratio": r.ratio_name,
            "Numerator / Denominator Formula": f"{r.numerator_desc} ÷ {r.denominator_desc}",
            f"{cy_label} ({r.unit_str})": r.value_cy,
            f"{py_label} ({r.unit_str})": r.value_py,
            "Variance %": f"{r.variance_pct:+.2f}%",
            "Variance > 25% Flag": flag_str,
            "Statutory Note / CA Explanation": r.ca_commentary
        })
    return pd.DataFrame(rows)
