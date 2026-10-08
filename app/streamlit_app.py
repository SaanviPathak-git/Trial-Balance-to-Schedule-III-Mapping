"""
app/streamlit_app.py
Interactive Web Application for Trial Balance to Schedule III Statutory Finalisation.
Built for Chartered Accountants, Statutory Auditors, CFOs, and Recruiters.
Features:
- Live TB upload (Excel/CSV) + 1-Click Built-in Sample TBs (Division I & Division II)
- Entity configuration (Division I AS vs Division II Ind AS, Year labels, Rounding unit)
- Pre-mapping CA validation dashboard (Dr=Cr, signs, duplicates)
- 3-Layer mapping engine review with fuzzy confidence & user override learning
- Statutory Balance Sheet & Profit and Loss with Notes to Accounts
- Full ledger drill-down & CA Judgement Assumptions log
- 11 Mandatory Schedule III ratios with 25% statutory variance alerts
- Multi-sheet audit-grade Excel export download (.xlsx)
- Live FMCG Financial Analysis Engine JSON bridge
"""

import os
import sys
import io
import pandas as pd
import streamlit as st

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from templates.schedule_iii_schema import (
    Division,
    StatementType,
    get_line_items_by_division,
    MANDATORY_DISCLOSURE_CHECKLIST,
)
from engine.validator import validate_trial_balance, IssueSeverity
from engine.mapper import ScheduleIIIMapper
from engine.classifier import CAJudgementClassifier
from engine.statements import StatementGenerator, RoundingUnit
from engine.checks import run_finalisation_checks
from engine.ratios import compute_schedule_iii_ratios, ratios_to_dataframe
from engine.excel_export import generate_schedule_iii_excel
from engine.adjustments import parse_adjustments_block, apply_adjustments_to_tb

# Page configuration
st.set_page_config(
    page_title="Schedule III Finalisation Engine | CA Financial Statements",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Theme-Adaptive)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        opacity: 0.85;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if "mapper" not in st.session_state:
        st.session_state.mapper = ScheduleIIIMapper()
    if "raw_df" not in st.session_state:
        st.session_state.raw_df = None
    if "data_source_label" not in st.session_state:
        st.session_state.data_source_label = "None"
    if "user_overrides" not in st.session_state:
        st.session_state.user_overrides = {}
    if "adjustments_text" not in st.session_state:
        st.session_state.adjustments_text = ""


init_session_state()

# Header
st.markdown("<div class='main-title'>⚖️ Trial Balance to Schedule III Finalisation Engine</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Statutory Financial Statement preparation under Companies Act, 2013 | "
    "Full CA Judgement Layer (Grossing up, Operating Cycle, Netting, MSME Disclosures, 11 MCA Ratios)</div>",
    unsafe_allow_html=True
)

# Sidebar: Configuration & Ingestion
st.sidebar.header("📁 1. Trial Balance Input")

sample_choice = st.sidebar.radio(
    "Choose Data Source:",
    ["Upload My File", "Built-in Sample (Ind AS / Div II)", "Built-in Sample (AS / Div I)"],
    index=1
)

uploaded_file = None
if sample_choice == "Upload My File":
    uploaded_file = st.sidebar.file_uploader(
        "Upload Trial Balance (Excel .xlsx / CSV):",
        type=["xlsx", "xls", "csv"],
        help="Columns expected: Ledger Name, Debit & Credit (or Closing Balance). Optional: Group, Previous Year."
    )
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                st.session_state.raw_df = pd.read_csv(uploaded_file)
            else:
                st.session_state.raw_df = pd.read_excel(uploaded_file)
            st.session_state.data_source_label = f"Uploaded File: {uploaded_file.name}"
        except Exception as e:
            st.sidebar.error(f"Error parsing file: {e}")
elif sample_choice == "Built-in Sample (Ind AS / Div II)":
    sample_path = os.path.join(REPO_ROOT, "data", "sample_tb.xlsx")
    if os.path.exists(sample_path):
        st.session_state.raw_df = pd.read_excel(sample_path)
        st.session_state.data_source_label = "Sample: Astra Consumer Goods Ltd (Ind AS Division II - ₹500 Cr)"
elif sample_choice == "Built-in Sample (AS / Div I)":
    sample_path = os.path.join(REPO_ROOT, "data", "sample_tb_division1.xlsx")
    if os.path.exists(sample_path):
        st.session_state.raw_df = pd.read_excel(sample_path)
        st.session_state.data_source_label = "Sample: Heritage Foods India Ltd (Non-Ind AS Division I - ₹250 Cr)"

st.sidebar.markdown(f"**Active TB:** *{st.session_state.data_source_label}*")

# Sidebar: Entity & Accounting Framework Settings
st.sidebar.header("⚙️ 2. Entity & Framework Settings")

div_default_idx = 1 if "Div II" in sample_choice or sample_choice == "Built-in Sample (Ind AS / Div II)" else 0
selected_division_val = st.sidebar.selectbox(
    "Statutory Framework:",
    [Division.DIVISION_I.value, Division.DIVISION_II.value],
    index=div_default_idx,
    help="Division I applies to Companies (AS) Rules (Non-Ind AS). Division II applies to Companies (Ind AS) Rules."
)
selected_division = Division.DIVISION_I if "Division I" in selected_division_val else Division.DIVISION_II

company_name_input = st.sidebar.text_input(
    "Entity Name:",
    value="Astra Consumer Goods Limited" if selected_division == Division.DIVISION_II else "Heritage Foods India Limited"
)

col_yr1, col_yr2 = st.sidebar.columns(2)
with col_yr1:
    cy_label_input = st.text_input("CY Label:", value="FY 2023-24")
with col_yr2:
    py_label_input = st.text_input("PY Label:", value="FY 2022-23")

rounding_choice = st.sidebar.selectbox(
    "Rounding Unit:",
    [RoundingUnit.LAKHS.value, RoundingUnit.CRORES.value, RoundingUnit.THOUSANDS.value, RoundingUnit.EXACT.value],
    index=0
)
selected_rounding = RoundingUnit(rounding_choice)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "🌐 **Live Web App:**  \n[trial-balance-to-schedule-iii.streamlit.app](https://trial-balance-to-schedule-iii-mapping-dakt9tfzyfhhwg4lck3nvt.streamlit.app/)\n\n"
    "🐙 **GitHub Repo:**  \n[SaanviPathak-git/Trial-Balance-to-Schedule-III-Mapping](https://github.com/SaanviPathak-git/Trial-Balance-to-Schedule-III-Mapping)"
)

# Main Dashboard
if st.session_state.raw_df is None or st.session_state.raw_df.empty:
    st.info("👋 Welcome! Please select a built-in sample TB from the sidebar or upload your company's trial balance to start.")
    st.stop()

raw_df = st.session_state.raw_df

# STEP 1: VALIDATION
val_result = validate_trial_balance(raw_df)

# Top KPI Summary Cards
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
with kpi_col1:
    st.metric("Total Debits (CY)", f"₹ {val_result.total_debit:,.0f}")
with kpi_col2:
    st.metric("Total Credits (CY)", f"₹ {val_result.total_credit:,.0f}")
with kpi_col3:
    diff_val = val_result.difference
    diff_color = "normal" if abs(diff_val) <= 0.05 else "inverse"
    st.metric("TB Imbalance", f"₹ {abs(diff_val):,.2f}", delta="Balanced ✅" if abs(diff_val) <= 0.05 else "Out of Balance ❌", delta_color=diff_color)
with kpi_col4:
    err_count = sum(1 for i in val_result.issues if i.severity == IssueSeverity.ERROR)
    warn_count = sum(1 for i in val_result.issues if i.severity == IssueSeverity.WARNING)
    st.metric("Validation Alerts", f"{len(val_result.issues)} Total", delta=f"{err_count} Err | {warn_count} Warn", delta_color="inverse" if err_count > 0 else "normal")
with kpi_col5:
    st.metric("Total Ledgers", f"{len(val_result.normalized_df)}")

# STEP 1.5: NATURAL LANGUAGE YEAR-END ADJUSTMENTS
parsed_jvs = []
jv_worksheet = pd.DataFrame()
working_tb_df = val_result.normalized_df.copy()

num_active_lines = len([l for l in st.session_state.adjustments_text.strip().splitlines() if l.strip() and not l.strip().startswith("#")])
expander_title = (
    f"✍️ Year-End Adjustments in Plain English ({num_active_lines} Active JVs Posted ✅)"
    if num_active_lines > 0
    else "✍️ Year-End Adjustments in Plain English (Optional: Closing Stock, Depreciation, Accruals, JVs)"
)

with st.expander(expander_title, expanded=True):
    st.markdown(
        "Enter statutory year-end audit adjustments in **natural English** (one entry per line). "
        "The engine parses amounts, identifies debit & credit heads, and generates balanced double-entry JVs updating the Trial Balance."
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.2, 3])
    with col_btn1:
        if st.button("⚡ Load Sample Adjustments"):
            st.session_state.adjustments_text = (
                "Closing stock valued at ₹ 4,50,00,000\n"
                "Provide depreciation of 25 lakhs on Plant & Machinery\n"
                "Outstanding audit fee of ₹ 1,50,000 to be provided\n"
                "Prepaid insurance of ₹ 2,00,000 to be carried forward\n"
                "Provide current tax of ₹ 35,00,000"
            )
            st.rerun()
    with col_btn2:
        if st.button("🧹 Clear Adjustments"):
            st.session_state.adjustments_text = ""
            st.rerun()
    with col_btn3:
        st.caption("Supports ₹, crores, lakhs, commas, plus closing stock, depreciation, accruals, prepayments, bad debts & custom JVs.")

    raw_adj_input = st.text_area(
        "English Adjustment Entries (one per line):",
        value=st.session_state.adjustments_text,
        height=130,
        placeholder="Closing stock valued at ₹ 4,50,00,000\nProvide depreciation of 25 lakhs on Plant & Machinery\nOutstanding audit fee of ₹ 1,50,000\nPrepaid insurance of ₹ 2,00,000\nProvide current tax of ₹ 35,00,000",
        key="adj_input_area"
    )
    if raw_adj_input != st.session_state.adjustments_text:
        st.session_state.adjustments_text = raw_adj_input
        st.rerun()

    if st.session_state.adjustments_text.strip():
        parsed_jvs = parse_adjustments_block(st.session_state.adjustments_text)
        if parsed_jvs:
            working_tb_df, jv_worksheet = apply_adjustments_to_tb(val_result.normalized_df, parsed_jvs)
            total_adj_amt = sum(j.amount for j in parsed_jvs)
            
            st.success(
                f"✅ **{len(parsed_jvs)} Adjustment JVs Posted Successfully!** "
                f"Total Adjusted Volume: **₹ {total_adj_amt:,.2f}** | "
                f"Total Dr: ₹ {total_adj_amt:,.2f} | Total Cr: ₹ {total_adj_amt:,.2f} | "
                f"Net JV Imbalance: **₹ 0.00** (Strictly Balanced)",
                icon="⚖️"
            )
            
            # Show quick JV table
            preview_cols = ["JV ID", "Original English Text", "Debit Account", "Credit Account", "Amount (₹)", "Narration"]
            preview_display = jv_worksheet[preview_cols].copy()
            preview_display["Amount (₹)"] = preview_display["Amount (₹)"].apply(lambda x: f"₹ {x:,.2f}")
            st.dataframe(preview_display, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No valid adjustment entries recognized from the text above. Check syntax guide in Tab 2.")
    else:
        working_tb_df = val_result.normalized_df.copy()

# STEP 2: MAPPING
mapper = st.session_state.mapper
mapped_df = mapper.map_dataframe(working_tb_df, selected_division)

# Apply any session overrides
for lname, target_item in st.session_state.user_overrides.items():
    mapped_df = mapper.apply_override(mapped_df, lname, target_item, selected_division, save_to_master=False)

unmapped_df = mapper.get_unmapped_ledgers(mapped_df)
review_df = mapper.get_review_queue(mapped_df)

# Tabs
tab_checks, tab_adj, tab_stmts, tab_notes, tab_ratios, tab_mapping, tab_judgement, tab_fmcg, tab_checklist = st.tabs([
    "🛡️ 1. Audit Checks",
    "✍️ 2. Adjustments & JVs",
    "📊 3. Balance Sheet & P&L",
    "📝 4. Notes to Accounts",
    "📈 5. Mandatory 11 Ratios",
    "🗺️ 6. Mapping & Override",
    "⚖️ 7. CA Judgement Log",
    "🔗 8. FMCG Model Bridge",
    "📋 9. MCA Checklist"
])

# Process Classification and Statements if no blocking errors
can_finalise = not val_result.has_blocking_errors and len(unmapped_df) == 0

if can_finalise:
    classifier = CAJudgementClassifier(selected_division)
    classified_output = classifier.classify_and_adjust(mapped_df)

    generator = StatementGenerator(
        division=selected_division,
        rounding_unit=selected_rounding,
        cy_label=cy_label_input,
        py_label=py_label_input
    )
    stmts = generator.generate(classified_output)
    audit_summary = run_finalisation_checks(stmts, working_tb_df, unmapped_count=len(unmapped_df))
    ratios_list = compute_schedule_iii_ratios(stmts)
    ratios_df = ratios_to_dataframe(ratios_list, cy_label_input, py_label_input)

# TAB 1: AUDIT CHECKS
with tab_checks:
    st.subheader("🛡️ Finalisation Audit Status Panels")
    if not can_finalise:
        st.error("⛔ Statements cannot be finalised yet. Please resolve validation errors or unmapped ledgers in Tab 6.")
        if len(unmapped_df) > 0:
            st.warning(f"There are **{len(unmapped_df)} unmapped ledgers** in the queue. Schedule III requires 100% mapping coverage.")
    else:
        # Display 4 golden checks panels (Theme-Adaptive)
        for chk in audit_summary.checks:
            if chk.is_passed:
                st.success(f"**{chk.name}**\n\n{chk.summary_message}", icon="✅")
            else:
                st.error(f"**{chk.name}**\n\n{chk.summary_message}", icon="❌")

        st.markdown("---")
        # Validation Issues List
        st.subheader("🔍 Pre-Mapping Validation Anomaly Audit")
        if not val_result.issues:
            st.success("No anomalies or sign issues identified in the uploaded Trial Balance.")
        else:
            for iss in val_result.issues:
                if iss.severity == IssueSeverity.ERROR:
                    st.error(f"**[{iss.code}]** {iss.message} — *Suggested Action: {iss.suggested_action}*")
                elif iss.severity == IssueSeverity.WARNING:
                    st.warning(f"**[{iss.code}]** {iss.message} — *Suggested Action: {iss.suggested_action}*")
                else:
                    st.info(f"**[{iss.code}]** {iss.message}")

        # Excel Export Button
        st.markdown("---")
        st.subheader("📥 Export Finalised Financial Statements to Excel")
        excel_buffer = generate_schedule_iii_excel(
            stmts=stmts,
            audit_summary=audit_summary,
            ratios=ratios_list,
            treatment_logs=classified_output.treatment_log,
            company_name=company_name_input,
            adjustments_worksheet=jv_worksheet if not jv_worksheet.empty else None
        )
        st.download_button(
            label="📊 Download Complete Schedule III Finalisation Workbook (.xlsx)",
            data=excel_buffer.getvalue(),
            file_name=f"{company_name_input.replace(' ', '_')}_Schedule_III_Finalisation_{cy_label_input}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# TAB 2: ADJUSTMENTS & JVs
with tab_adj:
    st.subheader("✍️ Year-End Audit Adjustments & Posted Journal Vouchers")
    st.caption("Review natural language adjustment entries, double-entry JV voucher schedule, and ledger-level pre/post comparison.")

    with st.expander("📝 Enter or Edit Adjustment Entries Directly Here", expanded=(not bool(parsed_jvs))):
        with st.form("tab2_adjustment_form"):
            t2_input = st.text_area(
                "Type adjustment entries in plain English (one per line):",
                value=st.session_state.adjustments_text,
                height=130,
                placeholder="Closing stock valued at ₹ 4,50,00,000\nProvide depreciation of 25 lakhs on Plant & Machinery\nOutstanding audit fee of ₹ 1,50,000\nPrepaid insurance of ₹ 2,00,000\nProvide current tax of ₹ 35,00,000",
                key="tab2_adj_textarea"
            )
            col_t1, col_t2 = st.columns([1, 1])
            with col_t1:
                apply_t2 = st.form_submit_button("🚀 Apply Adjustments")
            with col_t2:
                load_sample_t2 = st.form_submit_button("⚡ Load Sample Adjustments")

            if apply_t2:
                st.session_state.adjustments_text = t2_input
                st.rerun()
            if load_sample_t2:
                st.session_state.adjustments_text = (
                    "Closing stock valued at ₹ 4,50,00,000\n"
                    "Provide depreciation of 25 lakhs on Plant & Machinery\n"
                    "Outstanding audit fee of ₹ 1,50,000 to be provided\n"
                    "Prepaid insurance of ₹ 2,00,000 to be carried forward\n"
                    "Provide current tax of ₹ 35,00,000"
                )
                st.rerun()

    if not parsed_jvs:
        st.info("ℹ️ No adjustment entries currently applied. Enter them in the box above or click '⚡ Load Sample Adjustments' to test.")
    else:
        adj_col1, adj_col2, adj_col3 = st.columns(3)
        total_adj_amt = sum(j.amount for j in parsed_jvs)
        with adj_col1:
            st.metric("Total Posted JVs", f"{len(parsed_jvs)}")
        with adj_col2:
            st.metric("Total Adjustment Value", f"₹ {total_adj_amt:,.2f}")
        with adj_col3:
            st.metric("Double-Entry Imbalance", "₹ 0.00", delta="Strictly Balanced ✅")
        
        st.markdown("#### 📜 Statutory Journal Vouchers Schedule")
        jv_display = jv_worksheet.copy()
        jv_display["Amount (₹)"] = jv_display["Amount (₹)"].apply(lambda x: f"₹ {x:,.2f}")
        st.dataframe(jv_display, use_container_width=True, hide_index=True)
        
        # Pre vs Post Ledger Impact Comparison
        st.markdown("---")
        st.subheader("🔄 Ledger Impact: Before vs. After Adjustments")
        st.caption("Trace how each ledger was updated by the adjustment entries.")
        
        affected_accts = set()
        for j in parsed_jvs:
            affected_accts.add(j.debit_account.lower())
            affected_accts.add(j.credit_account.lower())
        
        impact_rows = []
        for acct_low in sorted(affected_accts):
            pre_rows = val_result.normalized_df[val_result.normalized_df["ledger_name"].str.lower() == acct_low]
            post_rows = working_tb_df[working_tb_df["ledger_name"].str.lower() == acct_low]
            
            disp_name = post_rows["ledger_name"].iloc[0] if not post_rows.empty else (pre_rows["ledger_name"].iloc[0] if not pre_rows.empty else acct_low.title())
            pre_bal = pre_rows["net_cy"].iloc[0] if not pre_rows.empty else 0.0
            post_bal = post_rows["net_cy"].iloc[0] if not post_rows.empty else 0.0
            diff = post_bal - pre_bal
            
            impact_rows.append({
                "Ledger Account": disp_name,
                "Pre-Adjustment Net": f"₹ {pre_bal:,.2f}",
                "Net Adjustment": f"{'+' if diff > 0 else ''}₹ {diff:,.2f}",
                "Post-Adjustment Net": f"₹ {post_bal:,.2f}",
                "Leg Type": "Debit Leg (+)" if diff > 0 else "Credit Leg (-)"
            })
        st.dataframe(pd.DataFrame(impact_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("💡 English Adjustment Syntax & Examples Guide")
    st.markdown("""
    The natural language parser supports everyday audit adjustments in plain English:
    
    | Category | Example English Phrasing | Debit Account | Credit Account |
    | :--- | :--- | :--- | :--- |
    | **Closing Stock** | `Closing stock valued at ₹ 4,50,00,000` or `Closing inventory of 4.5 crores` | Finished Goods Inventory (Current Assets) | Changes in Inventories (P&L) |
    | **Depreciation** | `Provide depreciation of 25 lakhs on Plant & Machinery` | Depreciation Expense (P&L) | Accumulated Depreciation (Contra-Asset) |
    | **Outstanding Expenses** | `Outstanding audit fee of ₹ 1,50,000 to be provided` or `Salaries payable ₹ 5,00,000` | Audit / Salaries Expense (P&L) | Audit / Salaries Payable (Current Liabilities) |
    | **Prepaid Expenses** | `Prepaid insurance of ₹ 2,00,000 to be carried forward` | Prepaid Expenses (Current Assets) | Insurance Expense (P&L) |
    | **Bad Debts Written Off** | `Write off bad debts of ₹ 5,00,000` | Bad Debts Expense (P&L) | Sundry Debtors (Current Assets) |
    | **Provision for Bad Debts** | `Create provision for doubtful debts of ₹ 8,00,000` | Provision for Doubtful Debts Expense (P&L) | Provision for Doubtful Debts (Contra-Asset) |
    | **Tax Provision** | `Provide current tax of ₹ 35,00,000` | Current Tax Expense (P&L) | Provision for Tax (Current Liabilities) |
    | **Reserves Transfer** | `Transfer ₹ 10,00,000 to General Reserve` | Retained Earnings | General Reserve |
    | **Custom Double Entry** | `Debit Rent ₹ 50,000 and Credit Rent Payable ₹ 50,000` or `Dr Salaries 100000, Cr Salaries Payable 100000` | User Debit Account | User Credit Account |
    """)

# TAB 3: BALANCE SHEET & P&L
with tab_stmts:
    if not can_finalise:
        st.warning("Statements pending mapping finalisation.")
    else:
        st.subheader(f"Balance Sheet as at 31st March ({selected_division_val})")
        st.caption(f"Entity: {company_name_input} | Reporting Unit: {selected_rounding.value}")

        # Clean display of Balance Sheet
        bs_display_df = stmts.balance_sheet_df.copy()
        # Drop internal styling flags for display
        cols_to_drop = [c for c in ["is_header", "is_subtotal", "is_total"] if c in bs_display_df.columns]
        bs_display_df.drop(columns=cols_to_drop, inplace=True)
        st.dataframe(bs_display_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader(f"Statement of Profit and Loss ({selected_division_val})")
        st.caption(f"For the period ended 31st March | Reporting Unit: {selected_rounding.value}")

        pl_display_df = stmts.pl_df.copy()
        cols_to_drop_pl = [c for c in ["is_header", "is_subtotal", "is_total"] if c in pl_display_df.columns]
        pl_display_df.drop(columns=cols_to_drop_pl, inplace=True)
        st.dataframe(pl_display_df, use_container_width=True, hide_index=True)

# TAB 4: NOTES TO ACCOUNTS
with tab_notes:
    if not can_finalise:
        st.warning("Notes pending mapping finalisation.")
    else:
        st.subheader("📝 Notes Forming Part of the Financial Statements")
        st.caption("Drill-down into underlying trial balance ledgers supporting each statutory Schedule III line item.")

        notes_sorted = sorted(stmts.notes.items(), key=lambda x: x[1].note_no)
        note_titles = [f"{n.title} (₹ {round(n.total_cy / stmts.unit_multiplier, 2):,.2f})" for k, n in notes_sorted if n.ledgers or n.total_cy != 0]

        selected_note_label = st.selectbox("Select Note to Inspect:", note_titles)
        if selected_note_label:
            # Find the note
            matched_note = None
            for k, n in notes_sorted:
                if selected_note_label.startswith(n.title):
                    matched_note = n
                    break

            if matched_note:
                st.markdown(f"#### {matched_note.title}")
                st.markdown(f"**Classification:** `{matched_note.statement_type.value}` | `{matched_note.category.value}`")
                
                col_n1, col_n2 = st.columns(2)
                col_n1.metric(f"Total {cy_label_input}", f"₹ {round(matched_note.total_cy / stmts.unit_multiplier, 2):,.2f}")
                col_n2.metric(f"Total {py_label_input}", f"₹ {round(matched_note.total_py / stmts.unit_multiplier, 2):,.2f}")

                if matched_note.ledgers:
                    note_table = []
                    for l in matched_note.ledgers:
                        note_table.append({
                            "Ledger Name": l["ledger_name"],
                            "Group": l.get("group", ""),
                            f"{cy_label_input}": f"₹ {round(l['amount_cy'] / stmts.unit_multiplier, 2):,.2f}",
                            f"{py_label_input}": f"₹ {round(l['amount_py'] / stmts.unit_multiplier, 2):,.2f}",
                            "Rule Tag": l.get("ca_rule_tag", ""),
                            "Match Source": l.get("match_source", "")
                        })
                    st.dataframe(pd.DataFrame(note_table), use_container_width=True, hide_index=True)
                else:
                    st.info("No ledgers mapped under this statutory note.")

# TAB 5: RATIOS
with tab_ratios:
    if not can_finalise:
        st.warning("Ratios pending mapping finalisation.")
    else:
        st.subheader("📈 Schedule III Mandatory 11 Ratios Disclosure")
        st.caption("Pursuant to MCA Notification GSR 207(E) amending Schedule III. Automatically highlights changes exceeding 25%.")

        sig_count = sum(1 for r in ratios_list if r.is_variance_significant)
        if sig_count > 0:
            st.warning(f"⚠️ **{sig_count} ratios** exhibit a change exceeding **25%** compared to the preceding year. Schedule III mandatorily requires commentary on reasons for material variation in the notes.")

        st.dataframe(ratios_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📋 Statutory Variance Explanations for Notes to Accounts")
        for r in ratios_list:
            if r.is_variance_significant:
                with st.expander(f"⚠️ {r.ratio_name} — Variance: {r.variance_pct:+.2f}%"):
                    st.markdown(f"**Formula:** `{r.numerator_desc} ÷ {r.denominator_desc}`")
                    st.markdown(f"**CY:** `{r.value_cy}{r.unit_str}` | **PY:** `{r.value_py}{r.unit_str}`")
                    st.markdown(f"**Schedule III Note Disclosure Draft:**")
                    st.info(r.ca_commentary)

# TAB 6: MAPPING & OVERRIDE
with tab_mapping:
    st.subheader("🗺️ Three-Layer Mapping Engine & Learning Master")
    st.caption("Layer 1: Pattern/Keyword Rules | Layer 2: Fuzzy Matching (Amber <85%) | Layer 3: User Override with Learning")

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Mapped Ledgers", f"{len(mapped_df) - len(unmapped_df)} / {len(mapped_df)}")
    m_col2.metric("Needs Mapping Queue", f"{len(unmapped_df)}", delta="Must be 0 to Finalise", delta_color="inverse" if len(unmapped_df) > 0 else "normal")
    m_col3.metric("Amber Review (<85%)", f"{len(review_df)}")

    # Unmapped Queue Block
    if len(unmapped_df) > 0:
        st.error(f"🚨 {len(unmapped_df)} Ledgers require mapping classification:")
        st.dataframe(
            unmapped_df[["ledger_name", "group", "net_cy", "target_line_item", "confidence"]],
            use_container_width=True,
            hide_index=True
        )

    # User Override Box
    st.markdown("---")
    st.subheader("✏️ Override / Remap a Ledger")
    with st.form("override_form"):
        o_col1, o_col2, o_col3 = st.columns([2, 2, 1])
        all_ledger_names = mapped_df["ledger_name"].tolist()
        with o_col1:
            sel_ledger_override = st.selectbox("Select Ledger to Remap:", all_ledger_names)
        with o_col2:
            target_options = [item.name for item in get_line_items_by_division(selected_division)]
            sel_target_override = st.selectbox("Select Statutory Line Item:", target_options)
        with o_col3:
            save_permanently = st.checkbox("Learn Permanently (Save to Master CSV)", value=True)
            submit_override = st.form_submit_button("Apply Override 🚀")

        if submit_override:
            st.session_state.user_overrides[sel_ledger_override] = sel_target_override
            if save_permanently:
                mapper.apply_override(
                    mapped_df=mapped_df,
                    ledger_name=sel_ledger_override,
                    target_line_item=sel_target_override,
                    division=selected_division,
                    save_to_master=True
                )
            st.success(f"Successfully remapped '{sel_ledger_override}' to '{sel_target_override}'!")
            st.rerun()

    # Complete Mapping Table
    st.markdown("---")
    st.subheader("📋 Mapped Trial Balance Inspection")
    search_q = st.text_input("Filter ledgers by keyword:", "")
    view_table = mapped_df.copy()
    if search_q:
        view_table = view_table[view_table["ledger_name"].str.contains(search_q, case=False, na=False)]

    display_cols = ["ledger_name", "group", "debit_cy", "credit_cy", "target_line_item", "confidence", "match_source", "ca_rule_tag"]
    st.dataframe(view_table[display_cols], use_container_width=True, hide_index=True)

# TAB 7: CA JUDGEMENT LOG
with tab_judgement:
    st.subheader("⚖️ Assumptions & CA Treatment Audit Log")
    st.caption("Every statutory reclassification, gross-up, contra-presentation, and tax netting is audited below.")

    if not can_finalise:
        st.warning("CA Judgement log available once ledgers are mapped.")
    else:
        log_rows = []
        for t in classified_output.treatment_log:
            log_rows.append({
                "Ledger / Item": t.ledger_name,
                "Treatment Type": t.treatment_type,
                "Original Line": t.original_line_item,
                "Final Schedule III Line": t.adjusted_line_item,
                "Amount (₹)": f"₹ {t.amount_cy:,.2f}",
                "Statutory Rationale": t.statutory_rationale
            })

        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)

# TAB 8: FMCG MODEL BRIDGE
with tab_fmcg:
    st.subheader("🔗 FMCG Corporate Financial Analysis Engine Bridge")
    st.markdown("""
    The Schedule III output maps 1:1 into the FMCG engine's standardized data schema (`CompanyFinancials`).
    This creates an end-to-end audit and valuation pipeline:
    **Trial Balance ➔ Schedule III Finalisation ➔ FMCG Ratios, DuPont & Valuation Analysis.**
    """)
    if can_finalise:
        fmcg_json = generator.export_to_fmcg_schema(stmts, symbol="SCHEDULE_III_CORP", company_name=company_name_input)
        st.json(fmcg_json)
    else:
        st.warning("Finalise statements to view the FMCG schema export.")

# TAB 9: STATUTORY DISCLOSURE CHECKLIST
with tab_checklist:
    st.subheader("📋 Schedule III Non-TB Additional Disclosures (MCA 2021)")
    st.caption("Statutory requirements that cannot be fulfilled by trial balance balances alone. Marked as 'Needs Input' rather than skipped.")

    for d in MANDATORY_DISCLOSURE_CHECKLIST:
        badge_color = "amber" if "Input" in d["status"] else "green"
        with st.expander(f"📌 {d['item']} [{d['status']}]"):
            st.markdown(f"**MCA Reference:** `{d['reference']}`")
            st.markdown(f"**Audit Description:** {d['description']}")
            st.markdown(f"**Required Disclosure Fields:**")
            st.code(", ".join(d["fields"]), language="text")
