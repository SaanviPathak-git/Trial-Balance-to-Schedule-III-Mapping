"""
engine/validator.py
Validation engine for Trial Balance ingestion.
Validates mathematical balancing (Total Dr == Total Cr), detects duplicates,
blank names, zero-balance accounts, sign anomalies (creditor debit, cash credit),
and previous-year reconciliations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
import numpy as np


class IssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    severity: IssueSeverity
    code: str
    message: str
    ledger_name: Optional[str] = None
    amount: Optional[float] = None
    suggested_action: Optional[str] = None


@dataclass
class ValidationResult:
    is_valid: bool
    total_debit: float
    total_credit: float
    difference: float
    total_py_debit: float = 0.0
    total_py_credit: float = 0.0
    py_difference: float = 0.0
    issues: List[ValidationIssue] = field(default_factory=list)
    normalized_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    @property
    def has_blocking_errors(self) -> bool:
        return any(issue.severity == IssueSeverity.ERROR for issue in self.issues)


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Finds matching column case-insensitively and stripped."""
    cols_map = {col.strip().lower(): col for col in df.columns}
    for cand in candidates:
        cand_lower = cand.strip().lower()
        if cand_lower in cols_map:
            return cols_map[cand_lower]
        # Partial match
        for k, v in cols_map.items():
            if cand_lower in k:
                return v
    return None


def normalize_trial_balance(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[ValidationIssue]]:
    """
    Normalizes a raw uploaded TB DataFrame into standard columns:
    [ledger_name, group, debit_cy, credit_cy, net_cy, debit_py, credit_py, net_py]
    Net convention: Debit is positive (+), Credit is negative (-).
    """
    df = raw_df.copy()
    issues: List[ValidationIssue] = []

    # Identify ledger name column
    name_col = find_column(df, ["ledger name", "ledger", "particulars", "account name", "account", "head"])
    if not name_col:
        issues.append(ValidationIssue(
            severity=IssueSeverity.ERROR,
            code="MISSING_LEDGER_COL",
            message="Could not identify a Ledger Name / Particulars column in the uploaded file.",
            suggested_action="Ensure the table has a column named 'Ledger Name' or 'Particulars'."
        ))
        return pd.DataFrame(), issues

    # Identify Group column if available
    group_col = find_column(df, ["group", "ledger group", "parent group", "sub group", "category", "head of account"])

    # Identify CY Debit / Credit columns
    dr_col = find_column(df, ["closing debit", "cy debit", "debit amount", "debit (inr)", "dr amount", "debit", "dr"])
    cr_col = find_column(df, ["closing credit", "cy credit", "credit amount", "credit (inr)", "cr amount", "credit", "cr"])
    net_col = find_column(df, ["closing balance", "net balance", "closing amount", "balance", "amount", "net amount", "cy net"])

    # Identify PY Debit / Credit columns
    py_dr_col = find_column(df, ["py debit", "previous year debit", "ly debit", "dr py", "opening debit"])
    py_cr_col = find_column(df, ["py credit", "previous year credit", "ly credit", "cr py", "opening credit"])
    py_net_col = find_column(df, ["py balance", "previous year balance", "ly balance", "py amount", "opening balance"])

    normalized = pd.DataFrame()
    normalized["ledger_name"] = df[name_col].astype(str).str.strip()
    normalized["group"] = df[group_col].astype(str).str.strip() if group_col else ""

    # Parse CY numbers
    if dr_col and cr_col and dr_col != cr_col:
        normalized["debit_cy"] = pd.to_numeric(df[dr_col], errors="coerce").fillna(0.0).abs()
        normalized["credit_cy"] = pd.to_numeric(df[cr_col], errors="coerce").fillna(0.0).abs()
        normalized["net_cy"] = normalized["debit_cy"] - normalized["credit_cy"]
    elif net_col:
        # Check if there is a Dr/Cr type column
        drcr_type_col = find_column(df, ["type", "dr/cr", "drcr", "balance type"])
        raw_vals = pd.to_numeric(df[net_col], errors="coerce").fillna(0.0)
        if drcr_type_col:
            types = df[drcr_type_col].astype(str).str.strip().str.upper()
            is_cr = types.str.startswith("CR") | types.str.startswith("C")
            normalized["debit_cy"] = np.where(~is_cr, raw_vals.abs(), 0.0)
            normalized["credit_cy"] = np.where(is_cr, raw_vals.abs(), 0.0)
            normalized["net_cy"] = normalized["debit_cy"] - normalized["credit_cy"]
        else:
            # Assumed signed balance: positive = Dr, negative = Cr
            normalized["debit_cy"] = np.where(raw_vals >= 0, raw_vals, 0.0)
            normalized["credit_cy"] = np.where(raw_vals < 0, raw_vals.abs(), 0.0)
            normalized["net_cy"] = raw_vals
    else:
        issues.append(ValidationIssue(
            severity=IssueSeverity.ERROR,
            code="MISSING_AMOUNT_COLS",
            message="No Debit/Credit or Balance amount columns found in the uploaded file.",
            suggested_action="Provide columns such as 'Debit' & 'Credit' or a signed 'Closing Balance'."
        ))
        return pd.DataFrame(), issues

    # Parse PY numbers if present
    if py_dr_col and py_cr_col and py_dr_col != py_cr_col:
        normalized["debit_py"] = pd.to_numeric(df[py_dr_col], errors="coerce").fillna(0.0).abs()
        normalized["credit_py"] = pd.to_numeric(df[py_cr_col], errors="coerce").fillna(0.0).abs()
        normalized["net_py"] = normalized["debit_py"] - normalized["credit_py"]
    elif py_net_col:
        py_vals = pd.to_numeric(df[py_net_col], errors="coerce").fillna(0.0)
        normalized["debit_py"] = np.where(py_vals >= 0, py_vals, 0.0)
        normalized["credit_py"] = np.where(py_vals < 0, py_vals.abs(), 0.0)
        normalized["net_py"] = py_vals
    else:
        normalized["debit_py"] = 0.0
        normalized["credit_py"] = 0.0
        normalized["net_py"] = 0.0

    return normalized, issues


def validate_trial_balance(raw_df: pd.DataFrame, tolerance: float = 0.05) -> ValidationResult:
    """
    Executes full CA validation on the Trial Balance:
    1. Debits equal Credits check
    2. Duplicates check
    3. Blank ledger names check
    4. Zero balances check
    5. Sign sanity checks (Debtors Cr, Creditors Dr, Cash Cr / Bank OD)
    6. Previous year balance checks
    """
    normalized_df, issues = normalize_trial_balance(raw_df)

    if normalized_df.empty:
        return ValidationResult(
            is_valid=False,
            total_debit=0.0,
            total_credit=0.0,
            difference=0.0,
            issues=issues,
            normalized_df=pd.DataFrame()
        )

    # 1. Mathematical Balancing Check (CY)
    tot_dr = float(normalized_df["debit_cy"].sum())
    tot_cr = float(normalized_df["credit_cy"].sum())
    diff = round(tot_dr - tot_cr, 2)

    if abs(diff) > tolerance:
        issues.append(ValidationIssue(
            severity=IssueSeverity.ERROR,
            code="TB_OUT_OF_BALANCE",
            message=f"Trial balance is out of balance by ₹ {abs(diff):,.2f}. Total Debits: ₹ {tot_dr:,.2f}, Total Credits: ₹ {tot_cr:,.2f}.",
            amount=diff,
            suggested_action="Review journal entries or unmapped difference suspense accounts before finalizing."
        ))

    # 2. Blank Names Check
    blank_mask = (normalized_df["ledger_name"] == "") | (normalized_df["ledger_name"].isna()) | (normalized_df["ledger_name"].str.lower() == "nan")
    if blank_mask.any():
        blank_indices = normalized_df[blank_mask].index.tolist()
        issues.append(ValidationIssue(
            severity=IssueSeverity.ERROR,
            code="BLANK_LEDGER_NAME",
            message=f"Found {len(blank_indices)} rows with blank or missing ledger names at row(s) {[i+1 for i in blank_indices]}.",
            suggested_action="Specify ledger names or remove blank rows from the trial balance."
        ))

    # 3. Duplicate Ledgers Check
    duplicates = normalized_df[normalized_df.duplicated(subset=["ledger_name"], keep=False)]
    if not duplicates.empty:
        dup_names = duplicates["ledger_name"].unique().tolist()
        for dname in dup_names:
            if dname:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code="DUPLICATE_LEDGER",
                    message=f"Duplicate ledger detected: '{dname}' appears {len(duplicates[duplicates['ledger_name'] == dname])} times.",
                    ledger_name=dname,
                    suggested_action="Merge duplicate accounts or distinguish them with sub-ledger tags."
                ))

    # 4. Zero Balance Ledgers Check
    zero_mask = (normalized_df["debit_cy"] == 0.0) & (normalized_df["credit_cy"] == 0.0)
    zero_count = int(zero_mask.sum())
    if zero_count > 0:
        issues.append(ValidationIssue(
            severity=IssueSeverity.INFO,
            code="ZERO_BALANCE_LEDGERS",
            message=f"{zero_count} ledgers have zero closing balance in the current year.",
            suggested_action="Zero-balance ledgers will be excluded from financial statements unless comparative PY exists."
        ))

    # 5. Sign Sanity Checks (CA Judgement Flags)
    for _, row in normalized_df.iterrows():
        lname = str(row["ledger_name"]).strip()
        lname_lower = lname.lower()
        net = row["net_cy"]

        # Creditor / Trade Payable with Debit Balance
        if any(term in lname_lower for term in ["creditor", "vendor", "supplier", "payable"]) and not any(ex in lname_lower for ex in ["prepaid", "advance to"]):
            if net > 0:  # Debit balance
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code="CREDITOR_DEBIT_BALANCE",
                    message=f"Creditor '{lname}' has a debit balance of ₹ {abs(net):,.2f}.",
                    ledger_name=lname,
                    amount=net,
                    suggested_action="Judgement required: Gross up to 'Other Current Assets (Advances to Suppliers)' per Schedule III, do NOT net with payables."
                ))

        # Debtor / Trade Receivable with Credit Balance
        if any(term in lname_lower for term in ["debtor", "customer", "client", "receivable"]) and not any(ex in lname_lower for ex in ["provision", "allowance", "advance from", "advance received", "customer advance"]):
            if net < 0:  # Credit balance
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code="DEBTOR_CREDIT_BALANCE",
                    message=f"Debtor '{lname}' has a credit balance of ₹ {abs(net):,.2f}.",
                    ledger_name=lname,
                    amount=net,
                    suggested_action="Judgement required: Gross up to 'Other Current Liabilities (Advances from Customers)', do NOT net with receivables."
                ))

        # Cash / Bank Account with Credit Balance (Overdraft)
        if any(term in lname_lower for term in ["cash in hand", "petty cash"]) and net < 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                code="NEGATIVE_CASH_BALANCE",
                message=f"Cash account '{lname}' has a negative / credit balance of ₹ {abs(net):,.2f}.",
                ledger_name=lname,
                amount=net,
                suggested_action="Physical cash cannot be negative. Investigate cash book entries or unrecorded receipts."
            ))
        elif any(term in lname_lower for term in ["bank", "current account", "hnb", "sbi", "hdfc", "icici"]) and not any(term in lname_lower for term in ["charges", "loan", "od", "overdraft", "cc", "interest"]):
            if net < 0:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code="BANK_CREDIT_BALANCE",
                    message=f"Bank account '{lname}' reflects an overdraft / credit balance of ₹ {abs(net):,.2f}.",
                    ledger_name=lname,
                    amount=net,
                    suggested_action="Judgement required: Reclassify under 'Short-term borrowings (Bank Overdraft)', do NOT net with positive bank balances."
                ))

    # 6. Previous Year Balance Checks
    tot_py_dr = float(normalized_df["debit_py"].sum())
    tot_py_cr = float(normalized_df["credit_py"].sum())
    py_diff = round(tot_py_dr - tot_py_cr, 2)

    if (tot_py_dr > 0 or tot_py_cr > 0) and abs(py_diff) > tolerance:
        issues.append(ValidationIssue(
            severity=IssueSeverity.WARNING,
            code="PY_TB_OUT_OF_BALANCE",
            message=f"Previous Year Trial Balance has a mismatch of ₹ {abs(py_diff):,.2f} (PY Dr: ₹ {tot_py_dr:,.2f}, PY Cr: ₹ {tot_py_cr:,.2f}).",
            amount=py_diff,
            suggested_action="Verify PY audited financial statements to ensure opening balances match."
        ))

    has_errors = any(i.severity == IssueSeverity.ERROR for i in issues)

    return ValidationResult(
        is_valid=not has_errors,
        total_debit=tot_dr,
        total_credit=tot_cr,
        difference=diff,
        total_py_debit=tot_py_dr,
        total_py_credit=tot_py_cr,
        py_difference=py_diff,
        issues=issues,
        normalized_df=normalized_df
    )
