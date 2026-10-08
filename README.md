# ⚖️ Trial Balance to Schedule III Finalisation Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://trial-balance-to-schedule-iii-mapping-dakt9tfzyfhhwg4lck3nvt.streamlit.app/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-21%20passed-brightgreen.svg)](https://github.com/SaanviPathak-git/Trial-Balance-to-Schedule-III-Mapping)
[![Compliance](https://img.shields.io/badge/Schedule%20III-Div%20I%20%26%20II-navy.svg)](https://github.com/SaanviPathak-git/Trial-Balance-to-Schedule-III-Mapping)

> 🌐 **Live Web Application:**  
> **👉 [https://trial-balance-to-schedule-iii-mapping-dakt9tfzyfhhwg4lck3nvt.streamlit.app/](https://trial-balance-to-schedule-iii-mapping-dakt9tfzyfhhwg4lck3nvt.streamlit.app/)**  
> *(Instant access — explore live with preloaded ₹500 Cr Ind AS & ₹250 Cr AS trial balances, or upload your own).*

---

A production-grade, CA-level statutory finalisation tool that transforms a company's raw Trial Balance (TB) into compliant **Schedule III Financial Statements** (Balance Sheet, Statement of Profit and Loss, and Notes to Accounts) under the **Companies Act, 2013**.

Built specifically for Chartered Accountants, Statutory Auditors, CFOs, and Investment Analysts, this tool moves beyond simple account lookups by embedding a **rigorous CA Judgement Layer** covering classification, grossing up, contra presentation, tax netting, statutory MSME disclosures, and the **11 mandatory MCA Schedule III ratios**.

---

## 🌟 Key Capabilities

### 1. Ingestion & Flexible Trial Balance Parsing
- Ingests Excel (`.xlsx`, `.xls`) or CSV trial balances.
- Supports split columns (`Debit` & `Credit`) or signed net balances.
- Auto-detects account names, parent groups, and comparative Previous Year (PY) balances.
- **Built-in Sample TBs**: Pre-packaged with realistic, fully balanced trial balances for both **Division II (Ind AS - ₹500 Cr)** and **Division I (AS - ₹250 Cr)** for instant recruiter/reviewer exploration.

### 2. Pre-Mapping CA Validation Dashboard
- **Mathematical Balancing Check**: Verifies $\sum \text{Debits} == \sum \text{Credits}$ to ₹ 0.00; flags exact imbalances.
- **Duplicate & Blank Check**: Detects duplicated ledger names or empty rows.
- **Sign Anomaly Detection**:
  - *Creditor with Debit Balance* (flagged for grossing-up to Advances to Suppliers).
  - *Debtor with Credit Balance* (flagged for grossing-up to Advances from Customers).
  - *Negative Physical Cash* (critical audit exception).
  - *Bank Account with Credit Balance* (flagged for reclassification to Short-term Borrowings / Overdraft).
- **Comparative Year Reconciliation**: Checks PY trial balance debits vs credits.

### 3. Three-Layer Mapping Engine
1. **Rule-Based Mapping Master**: 290+ maintained ledger patterns and regex rules mapping common Tally, SAP, Oracle, and ERP names to statutory Schedule III line items.
2. **Fuzzy Matching with Confidence Scoring**: Employs sequence similarity to match unrecognized accounts; highlights matches in **amber** if confidence $< 85\%$ for explicit user sign-off.
3. **User Override with Cross-Run Learning**: Any ledger can be remapped via interactive dropdown, with optional persistence directly to `mapping_master.csv` so the engine learns company-specific charts of accounts across runs.
4. **Zero-Drop Guarantee**: Unmapped ledgers are placed in a mandatory **"Needs Mapping" queue**; statements cannot finalise until this queue is completely resolved.

### 4. The CA Judgement Layer (The Real Finalisation Core)
The engine executes statutory accounting judgements prescribed by MCA notifications and ICAI Guidance Notes:
- **Grossing Up (Non-Netting Rule)**: Vendor debit balances are reclassified to *Other Current Assets (Advances to Suppliers)*; customer credit balances are reclassified to *Other Current Liabilities (Advances from Customers)*. Netting against payables or receivables is strictly prevented.
- **Operating Cycle & Current Maturities**: Borrowings maturing within 12 months are separated from non-current debt and presented under *Current Borrowings*.
- **Contra Presentation**: *Provision for Doubtful Debts / Allowance for ECL* is presented as a contra-asset deduction against gross Trade Receivables.
- **Bank Overdrafts**: Overdrawn bank balances are classified under *Short-Term Borrowings*, never netted against cash in hand or positive bank accounts.
- **Direct Tax Netting**: Advance Tax and TDS receivable are offset against Provision for Tax for identical assessment years to present a single Net Current Tax Asset or Net Current Tax Liability per AS 22 / Ind AS 12.
- **Deferred Tax Netting**: DTA and DTL are offset and presented net as a single non-current line item.
- **Inventory Movement in P&L**: Opening and closing stocks of WIP, Finished Goods, and Stock-in-Trade are converted into *"Changes in inventories of finished goods, WIP and Stock-in-Trade"*, keeping raw material purchases and consumption clean.
- **P&L Profit Carry-Forward**: Net Profit after Tax automatically flows into *Reserves and Surplus* (Division I) or *Other Equity* (Division II), guaranteeing that the Balance Sheet balances to the penny with **₹ 0.00 difference**.
- **MSME Statutory Bifurcation**: Trade payables are split into Micro/Small Enterprises (MSME) dues vs other creditors per the MSMED Act, 2006.
- **Assumptions & Treatment Log**: Every reclassification, gross-up, and tax netting is recorded in an audit trail with statutory citations.

### 5. Mandatory Schedule III 11 Ratios Disclosure (MCA 2021)
Calculates all 11 mandatory ratios for Current Year and Previous Year with variance analysis:
1. Current Ratio
2. Debt-Equity Ratio
3. Debt Service Coverage Ratio (DSCR)
4. Return on Equity Ratio (ROE)
5. Inventory Turnover Ratio
6. Trade Receivables Turnover Ratio
7. Trade Payables Turnover Ratio
8. Net Capital Turnover Ratio (Working Capital Turnover)
9. Net Profit Margin Ratio
10. Return on Capital Employed (ROCE)
11. Return on Investment (ROI)
- **Automatic $>25\%$ Variance Trigger**: Automatically flags changes exceeding 25% and generates statutory explanatory notes as required by Schedule III.

### 6. Audit-Grade Multi-Tab Excel Export (.xlsx)
Generates an 8-sheet formatted workbook:
- **Sheet 1**: Executive Summary & Audit Checks (Pass/Fail cards).
- **Sheet 2**: Balance Sheet (CY & PY with Note Nos).
- **Sheet 3**: Statement of Profit & Loss (CY & PY with Note Nos).
- **Sheet 4**: Notes to Financial Statements (Detailed ledger-level schedules for every note).
- **Sheet 5**: Mapped Trial Balance (Audit trail with confidence scores and CA rule tags).
- **Sheet 6**: Schedule III Ratios & $>25\%$ Variance Analysis.
- **Sheet 7**: CA Judgement & Assumptions Log.
- **Sheet 8**: Statutory Disclosure Checklist (MCA 2021 non-TB disclosures: Ageing, Promoter shareholding, Bank quarterly returns, CSR, Benami, etc.).

### 7. Bridge to FMCG Financial Analysis Engine
The Schedule III output maps 1:1 into the standardized `CompanyFinancials` schema used in the FMCG Corporate Financial Analysis engine. This enables an end-to-end pipeline:
$$\text{Raw Trial Balance} \xrightarrow{\text{Finalisation}} \text{Schedule III Financials} \xrightarrow{\text{Analysis}} \text{DuPont, Leverage, Valuation \& EVA Models}$$

---

## 🏗️ Repository Architecture

```
trial-balance-schedule-iii/
├── README.md                          # Project documentation
├── requirements.txt                   # Production dependencies
├── pytest.ini                         # Pytest configuration
├── data/
│   ├── sample_tb.xlsx                 # Division II (Ind AS) balanced sample TB (₹500 Cr)
│   ├── sample_tb_division1.xlsx       # Division I (AS) balanced sample TB (₹250 Cr)
│   └── mapping_master.csv             # 290+ maintained ledger mapping rules
├── templates/
│   ├── __init__.py
│   └── schedule_iii_schema.py         # Statutory line items & MCA disclosure checklist
├── engine/
│   ├── __init__.py
│   ├── validator.py                   # TB validation, Dr/Cr equality, duplicates, sign sanity
│   ├── mapper.py                      # 3-layer mapping (Rule, Fuzzy, Override + Learning)
│   ├── classifier.py                  # CA judgement layer (Grossing up, netting, OD, MSME)
│   ├── statements.py                  # Balance Sheet, P&L, Notes, and FMCG schema bridge
│   ├── ratios.py                      # Mandatory 11 MCA ratios & >25% variance triggers
│   ├── checks.py                      # 4 Golden audit checks (BS equality, TB integrity)
│   └── excel_export.py                # 8-tab styled Excel workbook exporter
├── app/
│   └── streamlit_app.py               # Interactive CA finalisation web application
├── scripts/
│   ├── generate_mapping_master.py     # Mapping master generator
│   ├── create_sample_tbs.py           # Sample TB generator
│   └── test_pipeline_quick.py         # Quick pipeline verification script
└── tests/
    ├── conftest.py                    # Test configuration
    ├── test_validator.py              # Tests for TB validation
    ├── test_mapper.py                 # Tests for mapping and fuzzy matching
    ├── test_classifier.py             # Tests for CA judgement & grossing up
    ├── test_statements.py             # Tests for BS closure & profit carry-forward
    ├── test_ratios.py                 # Tests for 11 Schedule III ratios
    └── test_integration.py            # End-to-end integration tests (Div I & II)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Dependencies installed via pip:
```bash
pip install -r requirements.txt
```

### 2. Launching the Interactive Web Application
Run the Streamlit application from the repository directory:
```bash
streamlit run app/streamlit_app.py
```
Open your browser at `http://localhost:8501`.
- Choose **"Built-in Sample (Ind AS / Div II)"** or **"Built-in Sample (AS / Div I)"** to immediately test the complete pipeline.
- Or upload your own company's Trial Balance.
- Inspect the Balance Sheet, Profit & Loss, Notes to Accounts, and Ratios.
- Click **"Download Complete Schedule III Finalisation Workbook (.xlsx)"** to export the audit-ready model.

### 3. Running the Test Suite
Run the test suite using `pytest`:
```bash
pytest
```
Expected output:
```text
tests\test_classifier.py ...                                             [ 14%]
tests\test_integration.py ..                                             [ 23%]
tests\test_mapper.py .....                                               [ 47%]
tests\test_ratios.py .                                                   [ 52%]
tests\test_statements.py ...                                             [ 66%]
tests\test_validator.py .......                                          [100%]

============================= 21 passed in 10.18s =============================
```

---

## 🛡️ The 4 Golden Audit Checks

Every finalisation run must pass all 4 statutory gates:
| # | Audit Gate | Verification Formula | Status |
|---|---|---|---|
| **1** | **Balance Sheet Balancing** | $\text{Total Assets} - \text{Total Equity \& Liabilities} == 0.00$ | 🟢 PASS |
| **2** | **TB Ledger Integrity** | $\text{Mapped Count} == \text{Input Count} \;\land\; \text{Net Imbalance} == 0.00$ | 🟢 PASS |
| **3** | **Reserves Roll-Forward** | $\text{Net Profit per P\&L} == \Delta\text{Reserves \& Surplus / Other Equity}$ | 🟢 PASS |
| **4** | **Unmapped Ledgers Queue** | $\text{Needs Mapping Count} == 0$ | 🟢 PASS |

---

## 📈 Integration with the FMCG Analysis Engine
Under `engine/statements.py`, the `export_to_fmcg_schema()` function serializes finalized statements directly into the `CompanyFinancials` structure used by the FMCG financial analysis suite.

```python
from engine.statements import StatementGenerator, RoundingUnit

generator = StatementGenerator(division=Division.DIVISION_II, rounding_unit=RoundingUnit.LAKHS)
stmts = generator.generate(classified_output)

# Export directly to FMCG schema
fmcg_payload = generator.export_to_fmcg_schema(stmts, symbol="BRITANNIA", company_name="Britannia Industries")
```
This payload can be passed directly into DuPont decomposition, Working Capital cycles, Capital Allocation models, and DCF/EVA valuation engines.
