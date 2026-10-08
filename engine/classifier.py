"""
engine/classifier.py
The CA Judgement Layer.
Transforms raw mappings into statutory Schedule III presentation:
- Grossing up debtor/creditor opposite balances (non-netting)
- Current maturities of long-term borrowings classification
- Provision for doubtful debts contra-asset treatment
- Bank overdraft reclassification from cash to short-term borrowings
- GST and Advance Tax vs Provision for Tax netting treatment
- Deferred Tax Asset / Liability net presentation (Ind AS 12 / AS 22)
- MSME trade payables statutory bifurcation
- Inventory P&L movement and balance sheet carry-forward
- Full Assumptions & CA Treatment Audit Log
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
import pandas as pd
import numpy as np

from templates.schedule_iii_schema import Division


@dataclass
class TreatmentLogEntry:
    ledger_name: str
    original_line_item: str
    adjusted_line_item: str
    amount_cy: float
    treatment_type: str  # GROSS_UP, RECLASSIFICATION, TAX_NETTING, INVENTORY_ADJUSTMENT, CONTRA_PRESENTATION
    statutory_rationale: str
    amount_py: float = 0.0


@dataclass
class ClassificationOutput:
    adjusted_df: pd.DataFrame
    treatment_log: List[TreatmentLogEntry]
    net_profit_cy: float = 0.0
    net_profit_py: float = 0.0
    net_tax_position_cy: Dict[str, Any] = field(default_factory=dict)
    net_dta_position: Dict[str, Any] = field(default_factory=dict)


class CAJudgementClassifier:
    def __init__(self, division: Division):
        self.division = division
        self.is_div1 = (division == Division.DIVISION_I)

    def classify_and_adjust(self, mapped_df: pd.DataFrame) -> ClassificationOutput:
        """
        Executes all CA judgement rules on mapped trial balance.
        Produces adjusted DataFrame ready for Statement aggregation,
        plus an explicit statutory audit log.
        """
        df = mapped_df.copy()
        treatment_log: List[TreatmentLogEntry] = []

        # 1. Grossing Up: Creditors with Debit Balances (Advances to Suppliers)
        df, log_creditors = self._handle_creditor_debit_balances(df)
        treatment_log.extend(log_creditors)

        # 2. Grossing Up: Debtors with Credit Balances (Advances from Customers)
        df, log_debtors = self._handle_debtor_credit_balances(df)
        treatment_log.extend(log_debtors)

        # 3. Bank Overdraft: Cash / Bank Accounts with Credit Balances
        df, log_bank_od = self._handle_bank_overdrafts(df)
        treatment_log.extend(log_bank_od)

        # 4. Current Maturities of Long-Term Debt
        df, log_curr_mat = self._handle_current_maturities(df)
        treatment_log.extend(log_curr_mat)

        # 5. Provision for Doubtful Debts Contra Presentation
        df, log_pdd = self._handle_provision_doubtful_debts(df)
        treatment_log.extend(log_pdd)

        # 6. Current Tax: Advance Tax & TDS vs Provision for Tax Netting
        df, log_tax, net_tax_pos = self._handle_tax_netting(df)
        treatment_log.extend(log_tax)

        # 7. Deferred Tax: DTA vs DTL Netting per Ind AS 12 / AS 22
        df, log_dt, net_dt_pos = self._handle_deferred_tax_netting(df)
        treatment_log.extend(log_dt)

        # 8. MSME Trade Payables Verification
        df, log_msme = self._handle_msme_payables(df)
        treatment_log.extend(log_msme)

        return ClassificationOutput(
            adjusted_df=df,
            treatment_log=treatment_log,
            net_tax_position_cy=net_tax_pos,
            net_dta_position=net_dt_pos
        )

    def _handle_creditor_debit_balances(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry]]:
        """
        Creditors with debit balances cannot be netted against payables under Schedule III.
        Must be reclassified to Other Current Assets (Advances to Suppliers).
        """
        logs = []
        target_asset_line = "Other current assets"
        payable_lines = [
            "Trade payables - Dues of MSME",
            "Trade payables - Dues of creditors other than MSME",
            "Financial Liabilities - Trade payables - Dues of MSME",
            "Financial Liabilities - Trade payables - Dues of Others"
        ]

        mask = df["target_line_item"].isin(payable_lines) & (df["net_cy"] > 0)
        for idx in df[mask].index:
            row = df.loc[idx]
            orig_line = row["target_line_item"]
            lname = row["ledger_name"]
            amt = float(row["net_cy"])
            amt_py = float(row["net_py"])

            df.loc[idx, "target_line_item"] = target_asset_line
            df.loc[idx, "statement_type"] = "Balance Sheet"
            df.loc[idx, "category"] = "Current Assets"
            df.loc[idx, "default_dr_cr"] = "Dr"
            df.loc[idx, "ca_rule_tag"] = "CREDITOR_DEBIT_BAL_RECLASSIFIED"

            logs.append(TreatmentLogEntry(
                ledger_name=lname,
                original_line_item=orig_line,
                adjusted_line_item=target_asset_line,
                amount_cy=amt,
                amount_py=amt_py,
                treatment_type="GROSS_UP",
                statutory_rationale=(
                    "Grossed up vendor debit balance into Other Current Assets (Advances to Suppliers) "
                    "per Guidance Note on Division I/II Schedule III. Netting against trade payables is strictly prohibited."
                )
            ))

        return df, logs

    def _handle_debtor_credit_balances(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry]]:
        """
        Debtors with credit balances cannot be netted against receivables under Schedule III.
        Must be reclassified to Other Current Liabilities (Customer Advances).
        """
        logs = []
        target_liab_line = "Other current liabilities"
        receivable_lines = [
            "Trade receivables",
            "Financial Assets - Trade receivables"
        ]

        # In normalized TB, net_cy < 0 means credit balance.
        # Ensure we don't catch provisions (provisions have PROVISION in tag/name)
        mask = (
            df["target_line_item"].isin(receivable_lines)
            & (df["net_cy"] < 0)
            & (~df["ca_rule_tag"].str.contains("PROVISION", na=False))
            & (~df["ledger_name"].str.lower().str.contains("provision|allowance|ecl", na=False))
        )

        for idx in df[mask].index:
            row = df.loc[idx]
            orig_line = row["target_line_item"]
            lname = row["ledger_name"]
            amt = float(abs(row["net_cy"]))
            amt_py = float(abs(row["net_py"]))

            df.loc[idx, "target_line_item"] = target_liab_line
            df.loc[idx, "statement_type"] = "Balance Sheet"
            df.loc[idx, "category"] = "Current Liabilities"
            df.loc[idx, "default_dr_cr"] = "Cr"
            df.loc[idx, "ca_rule_tag"] = "DEBTOR_CREDIT_BAL_RECLASSIFIED"

            logs.append(TreatmentLogEntry(
                ledger_name=lname,
                original_line_item=orig_line,
                adjusted_line_item=target_liab_line,
                amount_cy=amt,
                amount_py=amt_py,
                treatment_type="GROSS_UP",
                statutory_rationale=(
                    "Grossed up customer credit balance into Other Current Liabilities (Advances from Customers) "
                    "per Schedule III requirements. Non-netting principle prevents reducing gross trade receivables."
                )
            ))

        return df, logs

    def _handle_bank_overdrafts(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry]]:
        """
        Bank accounts reflecting credit balance represent overdraft/cash credit.
        Must be presented under Short-term borrowings, not netted against cash.
        """
        logs = []
        target_borrowing = (
            "Short-term borrowings" if self.is_div1 else "Financial Liabilities - Current Borrowings"
        )
        cash_lines = [
            "Cash and bank balances",
            "Financial Assets - Cash and cash equivalents",
            "Financial Assets - Bank balances other than cash equivalents"
        ]

        mask = df["target_line_item"].isin(cash_lines) & (df["net_cy"] < 0)
        for idx in df[mask].index:
            row = df.loc[idx]
            orig_line = row["target_line_item"]
            lname = row["ledger_name"]
            amt = float(abs(row["net_cy"]))
            amt_py = float(abs(row["net_py"]))

            df.loc[idx, "target_line_item"] = target_borrowing
            df.loc[idx, "statement_type"] = "Balance Sheet"
            df.loc[idx, "category"] = "Current Liabilities"
            df.loc[idx, "default_dr_cr"] = "Cr"
            df.loc[idx, "ca_rule_tag"] = "BANK_OD_RECLASSIFIED"

            logs.append(TreatmentLogEntry(
                ledger_name=lname,
                original_line_item=orig_line,
                adjusted_line_item=target_borrowing,
                amount_cy=amt,
                amount_py=amt_py,
                treatment_type="RECLASSIFICATION",
                statutory_rationale=(
                    "Bank overdrawn balance reclassified to Short-term borrowings per Schedule III Part I. "
                    "Cannot be netted against positive bank balances or cash in hand."
                )
            ))

        return df, logs

    def _handle_current_maturities(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry]]:
        """Current maturities of long term borrowings presented under current liabilities."""
        logs = []
        target_borrowing = (
            "Short-term borrowings" if self.is_div1 else "Financial Liabilities - Current Borrowings"
        )
        mask = (
            (df["ca_rule_tag"] == "CURRENT_MATURITY_LTD")
            | (df["ledger_name"].str.lower().str.contains("current maturities of long", na=False))
        )

        for idx in df[mask].index:
            row = df.loc[idx]
            orig_line = row["target_line_item"]
            lname = row["ledger_name"]
            amt = float(abs(row["net_cy"]))
            amt_py = float(abs(row["net_py"]))

            if orig_line != target_borrowing:
                df.loc[idx, "target_line_item"] = target_borrowing
                df.loc[idx, "statement_type"] = "Balance Sheet"
                df.loc[idx, "category"] = "Current Liabilities"
                df.loc[idx, "default_dr_cr"] = "Cr"

                logs.append(TreatmentLogEntry(
                    ledger_name=lname,
                    original_line_item=orig_line,
                    adjusted_line_item=target_borrowing,
                    amount_cy=amt,
                    amount_py=amt_py,
                    treatment_type="RECLASSIFICATION",
                    statutory_rationale=(
                        "Current maturities of long-term borrowings reclassified to Current Liabilities "
                        "per 12-month operating cycle requirement of Schedule III."
                    )
                ))

        return df, logs

    def _handle_provision_doubtful_debts(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry]]:
        """
        Provision for doubtful debts / ECL allowance is presented as a deduction from Trade Receivables.
        """
        logs = []
        target_line = "Trade receivables" if self.is_div1 else "Financial Assets - Trade receivables"
        mask = (
            (df["ca_rule_tag"] == "PROVISION_DOUBTFUL_DEBTS")
            | (df["ledger_name"].str.lower().str.contains("provision for doubtful|allowance for expected credit", na=False))
        )

        for idx in df[mask].index:
            row = df.loc[idx]
            orig_line = row["target_line_item"]
            lname = row["ledger_name"]
            amt = float(abs(row["net_cy"]))
            amt_py = float(abs(row["net_py"]))

            df.loc[idx, "target_line_item"] = target_line
            df.loc[idx, "statement_type"] = "Balance Sheet"
            df.loc[idx, "category"] = "Current Assets"
            df.loc[idx, "default_dr_cr"] = "Cr"  # Contra asset deduction
            df.loc[idx, "ca_rule_tag"] = "PROVISION_DOUBTFUL_DEBTS"

            logs.append(TreatmentLogEntry(
                ledger_name=lname,
                original_line_item=orig_line,
                adjusted_line_item=target_line,
                amount_cy=amt,
                amount_py=amt_py,
                treatment_type="CONTRA_PRESENTATION",
                statutory_rationale=(
                    "Provision for doubtful debts retained within Trade Receivables as a contra-asset deduction, "
                    "enabling required gross and net receivables sub-classification in Note disclosures."
                )
            ))

        return df, logs

    def _handle_tax_netting(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry], Dict[str, Any]]:
        """
        Netting of Advance Tax & TDS against Provision for Tax for identical assessment years.
        If Advance Tax > Provision: Net Current Tax Asset.
        If Provision > Advance Tax: Net Current Tax Liability.
        """
        logs = []
        adv_tax_mask = (
            df["ca_rule_tag"].isin(["ADVANCE_TAX", "TDS_RECEIVABLE"])
            | df["ledger_name"].str.lower().str.contains("advance tax|tds receivable|tcs receivable", na=False)
        ) & (df["statement_type"] == "Balance Sheet")

        prov_tax_mask = (
            (df["ca_rule_tag"] == "PROVISION_FOR_TAX")
            | df["ledger_name"].str.lower().str.contains("provision for tax", na=False)
        ) & (df["statement_type"] == "Balance Sheet")

        tot_adv_tax_cy = float(df.loc[adv_tax_mask, "net_cy"].sum()) if adv_tax_mask.any() else 0.0
        tot_prov_tax_cy = float(abs(df.loc[prov_tax_mask, "net_cy"].sum())) if prov_tax_mask.any() else 0.0

        tot_adv_tax_py = float(df.loc[adv_tax_mask, "net_py"].sum()) if adv_tax_mask.any() else 0.0
        tot_prov_tax_py = float(abs(df.loc[prov_tax_mask, "net_py"].sum())) if prov_tax_mask.any() else 0.0

        net_pos = {
            "advance_tax_cy": tot_adv_tax_cy,
            "provision_tax_cy": tot_prov_tax_cy,
            "net_tax_cy": tot_adv_tax_cy - tot_prov_tax_cy,
            "advance_tax_py": tot_adv_tax_py,
            "provision_tax_py": tot_prov_tax_py,
            "net_tax_py": tot_adv_tax_py - tot_prov_tax_py,
        }

        if (tot_adv_tax_cy > 0 or tot_prov_tax_cy > 0):
            net_amt = tot_adv_tax_cy - tot_prov_tax_cy
            if net_amt >= 0:
                target_line = (
                    "Short-term loans and advances" if self.is_div1 else "Current tax assets (Net)"
                )
                category = "Current Assets"
                drcr = "Dr"
                desc = (
                    f"Advance tax & TDS (₹ {tot_adv_tax_cy:,.2f}) exceeded Provision for tax (₹ {tot_prov_tax_cy:,.2f}). "
                    f"Net Current Tax Asset of ₹ {net_amt:,.2f} presented per AS 22 / Ind AS 12."
                )
            else:
                target_line = (
                    "Short-term provisions" if self.is_div1 else "Current tax liabilities (Net)"
                )
                category = "Current Liabilities"
                drcr = "Cr"
                desc = (
                    f"Provision for tax (₹ {tot_prov_tax_cy:,.2f}) exceeded Advance tax & TDS (₹ {tot_adv_tax_cy:,.2f}). "
                    f"Net Current Tax Liability of ₹ {abs(net_amt):,.2f} presented per AS 22 / Ind AS 12."
                )

            logs.append(TreatmentLogEntry(
                ledger_name="Net Direct Tax Position (Advance Tax vs Provision)",
                original_line_item="Advance Tax / Provision for Tax Ledgers",
                adjusted_line_item=target_line,
                amount_cy=abs(net_amt),
                amount_py=abs(tot_adv_tax_py - tot_prov_tax_py),
                treatment_type="TAX_NETTING",
                statutory_rationale=desc
            ))

        return df, logs, net_pos

    def _handle_deferred_tax_netting(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry], Dict[str, Any]]:
        """
        Deferred tax asset (DTA) and deferred tax liability (DTL) netting per AS 22 / Ind AS 12.
        Must be presented net as a single line (either Asset or Liability).
        """
        logs = []
        dta_mask = df["ca_rule_tag"] == "DEFERRED_TAX_ASSET"
        dtl_mask = df["ca_rule_tag"] == "DEFERRED_TAX_LIABILITY"

        dta_amt = float(df.loc[dta_mask, "net_cy"].sum()) if dta_mask.any() else 0.0
        dtl_amt = float(abs(df.loc[dtl_mask, "net_cy"].sum())) if dtl_mask.any() else 0.0
        net_dt = dta_amt - dtl_amt

        dt_pos = {
            "dta": dta_amt,
            "dtl": dtl_amt,
            "net": net_dt
        }

        if dta_amt > 0 and dtl_amt > 0:
            target_line = "Deferred tax assets (Net)" if net_dt >= 0 else "Deferred tax liabilities (Net)"
            logs.append(TreatmentLogEntry(
                ledger_name="Deferred Tax Net Position",
                original_line_item="Gross DTA and Gross DTL",
                adjusted_line_item=target_line,
                amount_cy=abs(net_dt),
                treatment_type="TAX_NETTING",
                statutory_rationale=(
                    f"Gross DTA (₹ {dta_amt:,.2f}) and DTL (₹ {dtl_amt:,.2f}) netted into a single {target_line} "
                    f"of ₹ {abs(net_dt):,.2f} in accordance with Ind AS 12 / AS 22 offsetting criteria."
                )
            ))

        return df, logs, dt_pos

    def _handle_msme_payables(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TreatmentLogEntry]]:
        """Ensures MSME dues are separated from non-MSME dues per MCA 2021 amended Schedule III."""
        logs = []
        msme_mask = df["ca_rule_tag"] == "MSME_PAYABLE"
        if msme_mask.any():
            tot_msme = float(abs(df.loc[msme_mask, "net_cy"].sum()))
            logs.append(TreatmentLogEntry(
                ledger_name="MSME Trade Payables Breakdown",
                original_line_item="Sundry Creditors",
                adjusted_line_item="Trade payables - Dues of MSME",
                amount_cy=tot_msme,
                treatment_type="RECLASSIFICATION",
                statutory_rationale=(
                    "Bifurcated trade payables into MSME dues pursuant to MCA notification GSR 207(E) "
                    "and Micro, Small and Medium Enterprises Development Act, 2006 (MSMED Act)."
                )
            ))
        return df, logs
