"""
engine/adjustments.py
Natural Language / English Adjustment Entries Engine.
Parses year-end audit adjustments written in plain English and applies them
as balanced double-entry Journal Vouchers (JVs) to the Trial Balance.

Supports natural phrasing:
- "Closing stock valued at ₹ 4,50,00,000" / "Closing stock of 4.5 crores"
- "Provide depreciation of ₹ 25,00,000 on Plant & Machinery"
- "Outstanding audit fee of ₹ 1,50,000 to be provided"
- "Prepaid insurance of ₹ 2,00,000"
- "Write off bad debts of ₹ 5,00,000"
- "Create provision for doubtful debts of ₹ 8,00,000"
- "Provide current tax of ₹ 35,00,000"
- "Transfer ₹ 10,00,000 to General Reserve"
- Standard double-entry phrases:
  - "Debit Rent ₹ 50,000 and Credit Rent Payable ₹ 50,000"
  - "Dr Salaries 10,00,000, Cr Salaries Payable 10,00,000"
  - "Debit Cash 5,00,000 to Sales 5,00,000"
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
import numpy as np


@dataclass
class AdjustmentJournalEntry:
    entry_id: str
    raw_text: str
    debit_account: str
    credit_account: str
    amount: float
    narration: str
    category: str
    is_balanced: bool = True
    error_message: Optional[str] = None


def parse_inr_amount(text: str) -> Optional[float]:
    """
    Extracts numerical amount supporting:
    - ₹ or Rs / INR symbols
    - Comma formats (e.g. 4,50,00,000 or 4,500,000)
    - Words like 'crores', 'crore', 'cr', 'lakhs', 'lakh', 'k'
    """
    cleaned = text.replace("₹", " ").replace("Rs.", " ").replace("Rs", " ").replace("INR", " ")
    
    # 1. Match number followed by word multiplier: e.g. "4.5 crores", "50 lakhs", "10k"
    word_pattern = re.search(r"(\d+(?:\.\d+)?)\s*(crores?|cr|lakhs?|lac|lacs?|k|thousand|million|bn)\b", cleaned, re.IGNORECASE)
    if word_pattern:
        num = float(word_pattern.group(1))
        unit = word_pattern.group(2).lower()
        if unit in ["crore", "crores", "cr"]:
            return num * 1e7
        elif unit in ["lakh", "lakhs", "lac", "lacs"]:
            return num * 1e5
        elif unit in ["k", "thousand"]:
            return num * 1e3
        elif unit in ["million"]:
            return num * 1e6

    # 2. Match standard numerical string with optional commas
    num_pattern = re.search(r"(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)", cleaned)
    if num_pattern:
        s = num_pattern.group(1).replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def parse_english_adjustment_line(line: str, entry_index: int = 1) -> Optional[AdjustmentJournalEntry]:
    """
    Parses a single English adjustment sentence into a balanced double-entry JV.
    """
    text = line.strip()
    if not text or text.startswith("#") or text.startswith("//"):
        return None

    entry_id = f"JV-{entry_index:02d}"
    text_lower = text.lower()

    # --- 1. CLOSING STOCK ---
    # e.g. "Closing stock valued at ₹ 4,50,00,000" or "Closing inventory was 50 lakhs"
    if "closing stock" in text_lower or "closing inventory" in text_lower:
        amt = parse_inr_amount(text)
        if amt:
            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Finished Goods Inventory",
                credit_account="Changes in inventories of finished goods, WIP and Stock-in-Trade",
                amount=amt,
                narration="Being closing inventory recognized at reporting date per AS 2 / Ind AS 2.",
                category="CLOSING_STOCK"
            )

    # --- 2. DEPRECIATION ---
    # e.g. "Provide depreciation of ₹ 25,00,000 on Plant & Machinery"
    depr_match = re.search(r"depreciation (?:of )?(.*?)(?: on (.*?))?$", text_lower)
    if "depreciation" in text_lower:
        amt = parse_inr_amount(text)
        if amt:
            # Asset target
            asset = "Plant and Machinery"
            if "building" in text_lower:
                asset = "Factory Buildings"
            elif "vehicle" in text_lower or "truck" in text_lower:
                asset = "Motor Vehicles / Trucks"
            elif "computer" in text_lower or "server" in text_lower:
                asset = "Computers and Servers"
            elif "furniture" in text_lower:
                asset = "Furniture and Fixtures"
            elif "intangible" in text_lower or "software" in text_lower:
                asset = "Computer Software Licenses"

            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Depreciation and amortisation expense",
                credit_account=f"Accumulated Depreciation - {asset}" if "intangible" not in text_lower else asset,
                amount=amt,
                narration=f"Being depreciation provided on {asset} for the reporting period.",
                category="DEPRECIATION"
            )

    # --- 3. OUTSTANDING EXPENSES ---
    # e.g. "Outstanding audit fee of ₹ 1,50,000" or "Provide for outstanding salary ₹ 5,00,000"
    if "outstanding" in text_lower or "expense payable" in text_lower or ("provide for" in text_lower and ("payable" in text_lower or "salary" in text_lower or "rent" in text_lower or "audit" in text_lower)):
        amt = parse_inr_amount(text)
        if amt:
            exp_name = "Other expenses"
            payable_name = "Outstanding Expenses"
            if "salary" in text_lower or "wages" in text_lower:
                exp_name = "Salaries and Wages"
                payable_name = "Salaries Payable"
            elif "audit" in text_lower:
                exp_name = "Statutory Auditor Remuneration - Audit Fee"
                payable_name = "Audit Fees Payable"
            elif "rent" in text_lower:
                exp_name = "Rent for Factory & Office"
                payable_name = "Rent Payable"
            elif "electricity" in text_lower or "power" in text_lower:
                exp_name = "Power, Fuel & Water Charges"
                payable_name = "Electricity Charges Payable"

            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account=exp_name,
                credit_account=payable_name,
                amount=amt,
                narration=f"Being provision created for accrued {payable_name}.",
                category="OUTSTANDING_EXPENSE"
            )

    # --- 4. PREPAID EXPENSES ---
    # e.g. "Prepaid insurance of ₹ 2,00,000" or "Insurance prepaid ₹ 50,000"
    if "prepaid" in text_lower:
        amt = parse_inr_amount(text)
        if amt:
            exp_name = "Other expenses"
            if "insurance" in text_lower:
                exp_name = "Insurance Expense (Plant, Stock & Vehicles)"
            elif "rent" in text_lower:
                exp_name = "Rent for Factory & Office"

            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Prepaid Expenses",
                credit_account=exp_name,
                amount=amt,
                narration=f"Being unexpired portion of {exp_name} carried forward to next period.",
                category="PREPAID_EXPENSE"
            )

    # --- 5. BAD DEBTS & PROVISION FOR DOUBTFUL DEBTS ---
    if "bad debt" in text_lower:
        amt = parse_inr_amount(text)
        if amt:
            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Bad Debts Written Off",
                credit_account="Sundry Debtors - Domestic",
                amount=amt,
                narration="Being irrecoverable receivables written off as bad debts.",
                category="BAD_DEBTS"
            )

    if "provision for doubtful" in text_lower or "allowance for ecl" in text_lower or "pdd" in text_lower:
        amt = parse_inr_amount(text)
        if amt:
            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Provision for Doubtful Debts Expense",
                credit_account="Provision for Doubtful Debts",
                amount=amt,
                narration="Being allowance for expected credit losses created against trade receivables.",
                category="PROVISION_DOUBTFUL"
            )

    # --- 6. PROVISION FOR TAX ---
    if "provision for tax" in text_lower or "current tax provision" in text_lower or ("tax" in text_lower and "provide" in text_lower):
        amt = parse_inr_amount(text)
        if amt:
            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Current Income Tax Expense",
                credit_account="Provision for Tax - Current Year",
                amount=amt,
                narration="Being provision for corporate income tax created for the current financial year.",
                category="TAX_PROVISION"
            )

    # --- 7. TRANSFER TO RESERVES ---
    if "transfer" in text_lower and ("reserve" in text_lower or "general reserve" in text_lower):
        amt = parse_inr_amount(text)
        if amt:
            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account="Retained Earnings",
                credit_account="General Reserve",
                amount=amt,
                narration="Being appropriation of surplus profits transferred to General Reserve.",
                category="RESERVE_TRANSFER"
            )

    # --- 8. STRUCTURED DOUBLE ENTRY PHRASES ---
    # e.g. "Debit Rent 50000 and Credit Rent Payable 50000"
    # or "Dr Salaries 100000, Cr Salaries Payable 100000"
    structured = re.search(r"(?:debit|dr\.?)\s+(.*?)\s+(?:amounting to\s+|of\s+|for\s+)?([₹0-9,\.kcr\s]+?)(?:,|and|\s+to)?\s+(?:credit|cr\.?)\s+(.*?)(?:\s+(?:amounting to\s+|of\s+|for\s+)?([₹0-9,\.kcr\s]+))?$", text_lower)
    if structured:
        dr_acct = structured.group(1).strip().title()
        amt_str = structured.group(2)
        cr_acct = structured.group(3).strip().title()
        amt = parse_inr_amount(amt_str)
        if amt and dr_acct and cr_acct:
            return AdjustmentJournalEntry(
                entry_id=entry_id,
                raw_text=text,
                debit_account=dr_acct,
                credit_account=cr_acct,
                amount=amt,
                narration="Being manual journal voucher posted via natural language adjustment.",
                category="CUSTOM_JV"
            )

    # Fallback: attempt to find any amount
    amt = parse_inr_amount(text)
    if amt:
        return AdjustmentJournalEntry(
            entry_id=entry_id,
            raw_text=text,
            debit_account="Unclassified Adjustment Debit",
            credit_account="Unclassified Adjustment Credit",
            amount=amt,
            narration=f"Parsed from: {text}",
            category="CUSTOM_JV"
        )

    return None


def parse_adjustments_block(text: str) -> List[AdjustmentJournalEntry]:
    """
    Parses a multiline block of English text into a list of AdjustmentJournalEntry objects.
    """
    entries = []
    lines = text.strip().splitlines()
    idx = 1
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
        entry = parse_english_adjustment_line(line_clean, entry_index=idx)
        if entry:
            entries.append(entry)
            idx += 1
    return entries


def apply_adjustments_to_tb(
    normalized_df: pd.DataFrame,
    adjustments: List[AdjustmentJournalEntry]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Applies parsed adjustment journal entries onto the normalized Trial Balance DataFrame.
    Returns:
    1. adjusted_tb: Updated normalized TB with new net balances.
    2. jv_worksheet: Table of all posted Journal Vouchers for audit review.
    """
    df = normalized_df.copy()
    jv_rows = []

    for jv in adjustments:
        amt = jv.amount
        dr_acct = jv.debit_account.strip()
        cr_acct = jv.credit_account.strip()

        jv_rows.append({
            "JV ID": jv.entry_id,
            "Original English Text": jv.raw_text,
            "Debit Account": dr_acct,
            "Credit Account": cr_acct,
            "Amount (₹)": amt,
            "Narration": jv.narration,
            "Category": jv.category
        })

        # Apply Debit Leg (+ in net_cy)
        dr_mask = df["ledger_name"].str.lower() == dr_acct.lower()
        if dr_mask.any():
            df.loc[dr_mask, "debit_cy"] += amt
            df.loc[dr_mask, "net_cy"] += amt
        else:
            # Add new ledger row
            new_dr_row = {
                "ledger_name": dr_acct,
                "group": "Audit Adjustments",
                "debit_cy": amt,
                "credit_cy": 0.0,
                "net_cy": amt,
                "debit_py": 0.0,
                "credit_py": 0.0,
                "net_py": 0.0
            }
            df = pd.concat([df, pd.DataFrame([new_dr_row])], ignore_index=True)

        # Apply Credit Leg (- in net_cy)
        cr_mask = df["ledger_name"].str.lower() == cr_acct.lower()
        if cr_mask.any():
            df.loc[cr_mask, "credit_cy"] += amt
            df.loc[cr_mask, "net_cy"] -= amt
        else:
            # Add new ledger row
            new_cr_row = {
                "ledger_name": cr_acct,
                "group": "Audit Adjustments",
                "debit_cy": 0.0,
                "credit_cy": amt,
                "net_cy": -amt,
                "debit_py": 0.0,
                "credit_py": 0.0,
                "net_py": 0.0
            }
            df = pd.concat([df, pd.DataFrame([new_cr_row])], ignore_index=True)

    jv_worksheet = pd.DataFrame(jv_rows)
    return df, jv_worksheet
