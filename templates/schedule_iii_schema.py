"""
templates/schedule_iii_schema.py
Master statutory line item schemas, divisions, and disclosure checklists 
for Schedule III to the Companies Act, 2013 (Division I - AS and Division II - Ind AS).
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class Division(str, Enum):
    DIVISION_I = "Division I (Non-Ind AS / AS)"
    DIVISION_II = "Division II (Ind AS)"


class StatementType(str, Enum):
    BALANCE_SHEET = "Balance Sheet"
    PROFIT_AND_LOSS = "Profit & Loss"


class SectionCategory(str, Enum):
    EQUITY = "Equity"
    NON_CURRENT_LIABILITIES = "Non-Current Liabilities"
    CURRENT_LIABILITIES = "Current Liabilities"
    NON_CURRENT_ASSETS = "Non-Current Assets"
    CURRENT_ASSETS = "Current Assets"
    INCOME = "Income"
    EXPENSES = "Expenses"
    TAX_AND_OCI = "Tax & OCI"


@dataclass
class ScheduleIIILineItem:
    code: str
    name: str
    division: Division
    statement_type: StatementType
    category: SectionCategory
    default_dr_cr: str  # "Dr" for assets/expenses, "Cr" for liabilities/equity/income
    is_heading: bool = False
    is_subtotal: bool = False
    is_mandatory_ratio_input: bool = False
    parent_code: Optional[str] = None
    note_no: Optional[int] = None
    fmcg_mapped_field: Optional[str] = None  # Mapping to FMCG engine schema


# --- DIVISION I LINE ITEMS (Non-Ind AS / AS) ---
DIVISION_I_LINE_ITEMS: List[ScheduleIIILineItem] = [
    # EQUITY & LIABILITIES
    # Shareholders' Funds
    ScheduleIIILineItem("D1_SC", "Share Capital", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.EQUITY, "Cr", note_no=1, fmcg_mapped_field="share_capital"),
    ScheduleIIILineItem("D1_RS", "Reserves and Surplus", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.EQUITY, "Cr", note_no=2, fmcg_mapped_field="reserves_and_surplus"),
    ScheduleIIILineItem("D1_MRW", "Money received against share warrants", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.EQUITY, "Cr", note_no=3),
    ScheduleIIILineItem("D1_SAMP", "Share application money pending allotment", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.EQUITY, "Cr", note_no=4),
    
    # Non-Current Liabilities
    ScheduleIIILineItem("D1_LTB", "Long-term borrowings", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=5, fmcg_mapped_field="long_term_debt"),
    ScheduleIIILineItem("D1_DTL", "Deferred tax liabilities (Net)", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=6),
    ScheduleIIILineItem("D1_OLTL", "Other Long term liabilities", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=7),
    ScheduleIIILineItem("D1_LTP", "Long-term provisions", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=8),
    
    # Current Liabilities
    ScheduleIIILineItem("D1_STB", "Short-term borrowings", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=9, fmcg_mapped_field="short_term_debt"),
    ScheduleIIILineItem("D1_TP_MSME", "Trade payables - Dues of MSME", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=10, fmcg_mapped_field="trade_payables"),
    ScheduleIIILineItem("D1_TP_OTHER", "Trade payables - Dues of creditors other than MSME", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=10, fmcg_mapped_field="trade_payables"),
    ScheduleIIILineItem("D1_OCL", "Other current liabilities", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=11, fmcg_mapped_field="other_current_liabilities"),
    ScheduleIIILineItem("D1_STP", "Short-term provisions", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=12),
    
    # ASSETS
    # Non-Current Assets
    ScheduleIIILineItem("D1_PPE", "Property, Plant and Equipment (Tangible Assets)", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=13, fmcg_mapped_field="net_fixed_assets"),
    ScheduleIIILineItem("D1_INTANGIBLE", "Intangible assets", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=14, fmcg_mapped_field="intangible_assets"),
    ScheduleIIILineItem("D1_CWIP", "Capital work-in-progress", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=15),
    ScheduleIIILineItem("D1_INTANGIBLE_DEV", "Intangible assets under development", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=16),
    ScheduleIIILineItem("D1_NCI", "Non-current investments", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=17, fmcg_mapped_field="non_current_investments"),
    ScheduleIIILineItem("D1_DTA", "Deferred tax assets (Net)", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=18),
    ScheduleIIILineItem("D1_LTLA", "Long-term loans and advances", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=19),
    ScheduleIIILineItem("D1_ONCA", "Other non-current assets", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=20, fmcg_mapped_field="other_non_current_assets"),
    
    # Current Assets
    ScheduleIIILineItem("D1_CI", "Current investments", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=21),
    ScheduleIIILineItem("D1_INV", "Inventories", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=22, fmcg_mapped_field="inventories"),
    ScheduleIIILineItem("D1_TR", "Trade receivables", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=23, fmcg_mapped_field="trade_receivables"),
    ScheduleIIILineItem("D1_CASH", "Cash and bank balances", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=24, fmcg_mapped_field="cash_and_equivalents"),
    ScheduleIIILineItem("D1_STLA", "Short-term loans and advances", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=25),
    ScheduleIIILineItem("D1_OCA", "Other current assets", Division.DIVISION_I, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=26, fmcg_mapped_field="other_current_assets"),

    # PROFIT & LOSS (DIVISION I)
    ScheduleIIILineItem("D1_REV", "Revenue from operations", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.INCOME, "Cr", note_no=27, fmcg_mapped_field="revenue"),
    ScheduleIIILineItem("D1_OTH_INC", "Other income", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.INCOME, "Cr", note_no=28, fmcg_mapped_field="other_income"),
    ScheduleIIILineItem("D1_MAT_CONS", "Cost of materials consumed", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=29, fmcg_mapped_field="cogs"),
    ScheduleIIILineItem("D1_PUR_TRADED", "Purchases of Stock-in-Trade", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=30, fmcg_mapped_field="cogs"),
    ScheduleIIILineItem("D1_CHG_INV", "Changes in inventories of finished goods, WIP and Stock-in-Trade", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=31, fmcg_mapped_field="cogs"),
    ScheduleIIILineItem("D1_EMP_EXP", "Employee benefits expense", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=32, fmcg_mapped_field="employee_expense"),
    ScheduleIIILineItem("D1_FIN_COST", "Finance costs", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=33, fmcg_mapped_field="interest_expense"),
    ScheduleIIILineItem("D1_DEP_AMORT", "Depreciation and amortisation expense", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=34, fmcg_mapped_field="depreciation"),
    ScheduleIIILineItem("D1_OTH_EXP", "Other expenses", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=35, fmcg_mapped_field="other_operating_expenses"),
    ScheduleIIILineItem("D1_EXCEPTIONAL", "Exceptional items", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=36),
    ScheduleIIILineItem("D1_CURR_TAX", "Current tax expense", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.TAX_AND_OCI, "Dr", note_no=37, fmcg_mapped_field="tax_expense"),
    ScheduleIIILineItem("D1_DEF_TAX", "Deferred tax expense / (credit)", Division.DIVISION_I, StatementType.PROFIT_AND_LOSS, SectionCategory.TAX_AND_OCI, "Dr", note_no=38, fmcg_mapped_field="tax_expense"),
]


# --- DIVISION II LINE ITEMS (Ind AS) ---
DIVISION_II_LINE_ITEMS: List[ScheduleIIILineItem] = [
    # ASSETS
    # Non-Current Assets
    ScheduleIIILineItem("D2_PPE", "Property, Plant and Equipment", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=1, fmcg_mapped_field="net_fixed_assets"),
    ScheduleIIILineItem("D2_CWIP", "Capital work-in-progress", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=2),
    ScheduleIIILineItem("D2_ROU", "Right-of-use assets", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=3),
    ScheduleIIILineItem("D2_GOODWILL", "Goodwill", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=4, fmcg_mapped_field="intangible_assets"),
    ScheduleIIILineItem("D2_OTHER_INTANGIBLE", "Other Intangible assets", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=5, fmcg_mapped_field="intangible_assets"),
    ScheduleIIILineItem("D2_INTANGIBLE_DEV", "Intangible assets under development", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=6),
    ScheduleIIILineItem("D2_INV_PROP", "Investment Property", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=7),
    # Financial Assets (Non-current)
    ScheduleIIILineItem("D2_FA_NCI", "Financial Assets - Non-current Investments", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=8, fmcg_mapped_field="non_current_investments"),
    ScheduleIIILineItem("D2_FA_NCTR", "Financial Assets - Non-current Trade Receivables", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=9),
    ScheduleIIILineItem("D2_FA_NCLOAN", "Financial Assets - Non-current Loans", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=10),
    ScheduleIIILineItem("D2_FA_NCOTH", "Financial Assets - Other non-current financial assets", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=11),
    ScheduleIIILineItem("D2_DTA", "Deferred tax assets (Net)", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=12),
    ScheduleIIILineItem("D2_ONCA", "Other non-current assets", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_ASSETS, "Dr", note_no=13, fmcg_mapped_field="other_non_current_assets"),

    # Current Assets
    ScheduleIIILineItem("D2_INV", "Inventories", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=14, fmcg_mapped_field="inventories"),
    # Financial Assets (Current)
    ScheduleIIILineItem("D2_FA_CI", "Financial Assets - Current Investments", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=15),
    ScheduleIIILineItem("D2_FA_TR", "Financial Assets - Trade receivables", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=16, fmcg_mapped_field="trade_receivables"),
    ScheduleIIILineItem("D2_FA_CASH", "Financial Assets - Cash and cash equivalents", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=17, fmcg_mapped_field="cash_and_equivalents"),
    ScheduleIIILineItem("D2_FA_BANK", "Financial Assets - Bank balances other than cash equivalents", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=18, fmcg_mapped_field="cash_and_equivalents"),
    ScheduleIIILineItem("D2_FA_CLOAN", "Financial Assets - Current Loans", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=19),
    ScheduleIIILineItem("D2_FA_COTH", "Financial Assets - Other current financial assets", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=20),
    ScheduleIIILineItem("D2_CTA", "Current tax assets (Net)", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=21),
    ScheduleIIILineItem("D2_OCA", "Other current assets", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_ASSETS, "Dr", note_no=22, fmcg_mapped_field="other_current_assets"),

    # EQUITY & LIABILITIES
    # Equity
    ScheduleIIILineItem("D2_EQ_SC", "Equity Share capital", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.EQUITY, "Cr", note_no=23, fmcg_mapped_field="share_capital"),
    ScheduleIIILineItem("D2_EQ_OE", "Other Equity", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.EQUITY, "Cr", note_no=24, fmcg_mapped_field="reserves_and_surplus"),

    # Non-Current Liabilities
    # Financial Liabilities (Non-current)
    ScheduleIIILineItem("D2_FL_NCBORR", "Financial Liabilities - Non-current Borrowings", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=25, fmcg_mapped_field="long_term_debt"),
    ScheduleIIILineItem("D2_FL_NCLEASE", "Financial Liabilities - Non-current Lease liabilities", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=26, fmcg_mapped_field="long_term_debt"),
    ScheduleIIILineItem("D2_FL_NCTP_MSME", "Financial Liabilities - Non-current Trade payables (MSME)", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=27),
    ScheduleIIILineItem("D2_FL_NCTP_OTH", "Financial Liabilities - Non-current Trade payables (Others)", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=27),
    ScheduleIIILineItem("D2_FL_NCOTH", "Financial Liabilities - Other non-current financial liabilities", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=28),
    ScheduleIIILineItem("D2_NCPROV", "Non-current Provisions", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=29),
    ScheduleIIILineItem("D2_DTL", "Deferred tax liabilities (Net)", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=30),
    ScheduleIIILineItem("D2_ONCL", "Other non-current liabilities", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.NON_CURRENT_LIABILITIES, "Cr", note_no=31),

    # Current Liabilities
    # Financial Liabilities (Current)
    ScheduleIIILineItem("D2_FL_CBORR", "Financial Liabilities - Current Borrowings", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=32, fmcg_mapped_field="short_term_debt"),
    ScheduleIIILineItem("D2_FL_CLEASE", "Financial Liabilities - Current Lease liabilities", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=33, fmcg_mapped_field="short_term_debt"),
    ScheduleIIILineItem("D2_FL_CTP_MSME", "Financial Liabilities - Trade payables - Dues of MSME", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=34, fmcg_mapped_field="trade_payables"),
    ScheduleIIILineItem("D2_FL_CTP_OTH", "Financial Liabilities - Trade payables - Dues of Others", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=34, fmcg_mapped_field="trade_payables"),
    ScheduleIIILineItem("D2_FL_COTH", "Financial Liabilities - Other current financial liabilities", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=35),
    ScheduleIIILineItem("D2_OCL", "Other current liabilities", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=36, fmcg_mapped_field="other_current_liabilities"),
    ScheduleIIILineItem("D2_CPROV", "Current Provisions", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=37),
    ScheduleIIILineItem("D2_CTL", "Current tax liabilities (Net)", Division.DIVISION_II, StatementType.BALANCE_SHEET, SectionCategory.CURRENT_LIABILITIES, "Cr", note_no=38),

    # PROFIT & LOSS (DIVISION II)
    ScheduleIIILineItem("D2_REV", "Revenue from operations", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.INCOME, "Cr", note_no=39, fmcg_mapped_field="revenue"),
    ScheduleIIILineItem("D2_OTH_INC", "Other income", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.INCOME, "Cr", note_no=40, fmcg_mapped_field="other_income"),
    ScheduleIIILineItem("D2_MAT_CONS", "Cost of materials consumed", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=41, fmcg_mapped_field="cogs"),
    ScheduleIIILineItem("D2_PUR_TRADED", "Purchases of Stock-in-Trade", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=42, fmcg_mapped_field="cogs"),
    ScheduleIIILineItem("D2_CHG_INV", "Changes in inventories of finished goods, WIP and Stock-in-Trade", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=43, fmcg_mapped_field="cogs"),
    ScheduleIIILineItem("D2_EMP_EXP", "Employee benefits expense", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=44, fmcg_mapped_field="employee_expense"),
    ScheduleIIILineItem("D2_FIN_COST", "Finance costs", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=45, fmcg_mapped_field="interest_expense"),
    ScheduleIIILineItem("D2_DEP_AMORT", "Depreciation and amortisation expense", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=46, fmcg_mapped_field="depreciation"),
    ScheduleIIILineItem("D2_OTH_EXP", "Other expenses", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=47, fmcg_mapped_field="other_operating_expenses"),
    ScheduleIIILineItem("D2_EXCEPTIONAL", "Exceptional items", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.EXPENSES, "Dr", note_no=48),
    ScheduleIIILineItem("D2_CURR_TAX", "Current tax expense", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.TAX_AND_OCI, "Dr", note_no=49, fmcg_mapped_field="tax_expense"),
    ScheduleIIILineItem("D2_DEF_TAX", "Deferred tax expense / (credit)", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.TAX_AND_OCI, "Dr", note_no=50, fmcg_mapped_field="tax_expense"),
    ScheduleIIILineItem("D2_OCI", "Other Comprehensive Income / (Loss)", Division.DIVISION_II, StatementType.PROFIT_AND_LOSS, SectionCategory.TAX_AND_OCI, "Cr", note_no=51),
]


# Lookup dictionaries by code and by name
def get_line_items_by_division(division: Division) -> List[ScheduleIIILineItem]:
    if division == Division.DIVISION_I:
        return DIVISION_I_LINE_ITEMS
    return DIVISION_II_LINE_ITEMS


def get_line_item_dict(division: Division) -> Dict[str, ScheduleIIILineItem]:
    items = get_line_items_by_division(division)
    return {item.name: item for item in items}


# MCA Statutory Additional Disclosures Checklist (Non-TB Supported Disclosures)
MANDATORY_DISCLOSURE_CHECKLIST = [
    {
        "item": "Title deeds of Immovable Property not held in name of the Company",
        "reference": "Schedule III General Instructions, Part I",
        "description": "Details of land/building where title deed is not held in company name (promoter, director, relative, etc.).",
        "status": "Needs Input",
        "fields": ["Relevant line item", "Description of property", "Gross carrying value", "Title deeds held in name of", "Whether promoter/director", "Period held", "Reason for not being in company name"]
    },
    {
        "item": "Ageing Schedules for Trade Receivables, Trade Payables, CWIP & Intangibles",
        "reference": "MCA Notification GSR 207(E) dt 24th March 2021",
        "description": "Bifurcation into <6 months, 6m-1yr, 1-2yr, 2-3yr, >3yr; Undisputed/Disputed; Good/Significant increase in credit risk/Credit impaired.",
        "status": "Needs Input",
        "fields": ["Ageing buckets (<6m, 6m-1y, 1-2y, 2-3y, >3y)", "Disputed vs Undisputed dues", "Unbilled dues"]
    },
    {
        "item": "Promoter Shareholding & Changes during the year",
        "reference": "Schedule III Clause 6(L) Part I",
        "description": "Promoter name, No. of shares at beginning & end of year, % of total shares, % change during the year.",
        "status": "Needs Input",
        "fields": ["Promoter Name", "No. of shares", "% of total shares", "% change during year"]
    },
    {
        "item": "Reconciliation of Quarterly Statements of Current Assets filed with Banks",
        "reference": "Schedule III Clause 6(VA) Part I",
        "description": "Where company has borrowings from banks/FIs on the security of current assets, quarterly stock/debtor returns must reconcile with books of accounts.",
        "status": "Needs Input",
        "fields": ["Quarter ended", "Name of Bank", "Amount as per books", "Amount reported to bank", "Reason for material discrepancies"]
    },
    {
        "item": "Wilful Defaulter Declaration",
        "reference": "Schedule III Clause 6(X) Part I",
        "description": "Disclosure if declared wilful defaulter by any bank/financial institution or other lender.",
        "status": "Confirmed (Clean)",
        "fields": ["Date of declaration", "Details of default", "Lender name"]
    },
    {
        "item": "Relationship with Struck-off Companies under Section 248",
        "reference": "Schedule III Clause 6(Y) Part I",
        "description": "Transactions/balances with companies struck off by ROC under Section 248 of the Act.",
        "status": "Needs Input",
        "fields": ["Name of struck off company", "Nature of transactions", "Balance outstanding", "Relationship"]
    },
    {
        "item": "Registration of Charges or Satisfaction with ROC",
        "reference": "Schedule III Clause 6(Z) Part I",
        "description": "Details of charges or satisfaction yet to be registered with Registrar of Companies beyond statutory period.",
        "status": "Needs Input",
        "fields": ["Charge ID", "Lender", "Amount", "Period of delay", "Reason for non-registration"]
    },
    {
        "item": "Compliance with number of layers of companies (Section 2(87))",
        "reference": "Companies (Restriction on number of layers) Rules, 2017",
        "description": "Whether company has adhered to statutory ceiling on subsidiary layers.",
        "status": "Compliant",
        "fields": ["Number of downstream layers"]
    },
    {
        "item": "Corporate Social Responsibility (CSR) Disclosure",
        "reference": "Section 135 & Schedule VII of Companies Act 2013",
        "description": "Amount required to be spent vs actual spent, shortfall, ongoing projects, CSR provision.",
        "status": "Needs Input",
        "fields": ["Average Net Profit (Sec 198)", "2% CSR Obligation", "Amount spent", "Shortfall / Unspent amount", "Transferred to Unspent CSR A/c"]
    },
    {
        "item": "Undisclosed Income & Benami Property Transactions",
        "reference": "Prohibition of Benami Property Transactions Act, 1988",
        "description": "Details of any proceedings initiated or pending against company for holding Benami property.",
        "status": "None Reported",
        "fields": ["Details of property", "Year of acquisition", "Status of proceedings"]
    },
    {
        "item": "Details of Crypto Currency or Virtual Currency",
        "reference": "Schedule III MCA Notification 2021",
        "description": "Profit/loss on crypto transactions, currency held as at balance sheet date, customer deposits/advances.",
        "status": "Not Applicable",
        "fields": ["Profit/loss on transactions", "Amount held", "Deposits/advances from customers"]
    }
]
