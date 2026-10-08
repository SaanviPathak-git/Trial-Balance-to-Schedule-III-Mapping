"""
scripts/create_sample_tbs.py
Generates realistic, CA-grade sample Trial Balances (.xlsx) that balance to zero:
1. data/sample_tb.xlsx (Division II - Ind AS compliant sample TB)
2. data/sample_tb_division1.xlsx (Division I - AS / Non-Ind AS compliant sample TB)
Includes real-world CA edge cases:
- Creditor with debit balance (Vendor advances)
- Debtor with credit balance (Customer advances)
- Bank overdraft (Credit balance in bank account)
- Provision for doubtful debts
- Current maturities of term loan
- MSME vs Non-MSME trade payables
- Advance tax vs Provision for tax
- Netting of DTA/DTL
- Complete P&L nominal accounts ensuring mathematical zero-difference balance sheet closure!
"""

import os
import pandas as pd
import openpyxl

def generate_sample_tbs():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # SAMPLE TB 1: DIVISION II (IND AS) - "Astra Consumer Goods Limited"
    # Figures in INR (Total balance ~ ₹ 500 Crores)
    # -------------------------------------------------------------------------
    tb_data_div2 = [
        # EQUITY & RESERVES
        {"Ledger Name": "Equity Share Capital (Face Value ₹10)", "Group": "Share Capital", "Debit": 0, "Credit": 50000000, "PY Debit": 0, "PY Credit": 50000000},
        {"Ledger Name": "Securities Premium Reserve", "Group": "Other Equity", "Debit": 0, "Credit": 80000000, "PY Debit": 0, "PY Credit": 80000000},
        {"Ledger Name": "General Reserve", "Group": "Other Equity", "Debit": 0, "Credit": 45000000, "PY Debit": 0, "PY Credit": 45000000},
        {"Ledger Name": "Retained Earnings Opening", "Group": "Other Equity", "Debit": 0, "Credit": 95000000, "PY Debit": 0, "PY Credit": 65000000},

        # NON-CURRENT LIABILITIES
        {"Ledger Name": "Term Loan - HDFC Bank (Non-Current)", "Group": "Non-Current Borrowings", "Debit": 0, "Credit": 70000000, "PY Debit": 0, "PY Credit": 85000000},
        {"Ledger Name": "Lease Obligation - Non Current (Ind AS 116)", "Group": "Lease Liabilities", "Debit": 0, "Credit": 15000000, "PY Debit": 0, "PY Credit": 18000000},
        {"Ledger Name": "Provision for Gratuity (Non-Current)", "Group": "Non-Current Provisions", "Debit": 0, "Credit": 6500000, "PY Debit": 0, "PY Credit": 5500000},
        {"Ledger Name": "Deferred Tax Liability", "Group": "Deferred Tax", "Debit": 0, "Credit": 12000000, "PY Debit": 0, "PY Credit": 10000000},

        # CURRENT LIABILITIES
        {"Ledger Name": "Current Maturities of Long Term Debt", "Group": "Current Borrowings", "Debit": 0, "Credit": 15000000, "PY Debit": 0, "PY Credit": 15000000},
        {"Ledger Name": "Working Capital Demand Loan (WCDL)", "Group": "Current Borrowings", "Debit": 0, "Credit": 25000000, "PY Debit": 0, "PY Credit": 20000000},
        {"Ledger Name": "Bank Overdraft Account - SBI", "Group": "Bank OD", "Debit": 0, "Credit": 8500000, "PY Debit": 0, "PY Credit": 4500000},
        {"Ledger Name": "Lease Obligation - Current", "Group": "Lease Liabilities", "Debit": 0, "Credit": 3000000, "PY Debit": 0, "PY Credit": 3000000},
        {"Ledger Name": "Sundry Creditors - Micro Enterprises", "Group": "Trade Payables MSME", "Debit": 0, "Credit": 12500000, "PY Debit": 0, "PY Credit": 9500000},
        {"Ledger Name": "Sundry Creditors - Small Enterprises", "Group": "Trade Payables MSME", "Debit": 0, "Credit": 8500000, "PY Debit": 0, "PY Credit": 6500000},
        {"Ledger Name": "Sundry Creditors - Raw Material (Others)", "Group": "Trade Payables Others", "Debit": 0, "Credit": 34000000, "PY Debit": 0, "PY Credit": 28000000},
        {"Ledger Name": "Sundry Creditors - Packaging Material", "Group": "Trade Payables Others", "Debit": 0, "Credit": 9500000, "PY Debit": 0, "PY Credit": 7500000},
        {"Ledger Name": "Creditor with Debit Balance (Alpha Chemicals)", "Group": "Trade Payables", "Debit": 1800000, "Credit": 0, "PY Debit": 1200000, "PY Credit": 0},  # CA EDGE CASE 1
        {"Ledger Name": "Debtor with Credit Balance (Delta Wholesalers)", "Group": "Trade Receivables", "Debit": 0, "Credit": 2200000, "PY Debit": 0, "PY Credit": 1500000},  # CA EDGE CASE 2
        {"Ledger Name": "Advance Received from Customers", "Group": "Other Current Liabilities", "Debit": 0, "Credit": 4500000, "PY Debit": 0, "PY Credit": 3500000},
        {"Ledger Name": "Salaries Payable", "Group": "Outstanding Expenses", "Debit": 0, "Credit": 6200000, "PY Debit": 0, "PY Credit": 5200000},
        {"Ledger Name": "Audit Fees Payable", "Group": "Outstanding Expenses", "Debit": 0, "Credit": 750000, "PY Debit": 0, "PY Credit": 600000},
        {"Ledger Name": "GST Output - IGST Payable", "Group": "Statutory Dues", "Debit": 0, "Credit": 3200000, "PY Debit": 0, "PY Credit": 2800000},
        {"Ledger Name": "TDS Payable on Contractors (194C)", "Group": "Statutory Dues", "Debit": 0, "Credit": 950000, "PY Debit": 0, "PY Credit": 800000},
        {"Ledger Name": "Provision for Tax - Current Year", "Group": "Current Tax Provision", "Debit": 0, "Credit": 16000000, "PY Debit": 0, "PY Credit": 14000000},  # CA EDGE CASE 3

        # NON-CURRENT ASSETS
        {"Ledger Name": "Freehold Land", "Group": "Property, Plant and Equipment", "Debit": 85000000, "Credit": 0, "PY Debit": 85000000, "PY Credit": 0},
        {"Ledger Name": "Factory Buildings", "Group": "Property, Plant and Equipment", "Debit": 68000000, "Credit": 0, "PY Debit": 68000000, "PY Credit": 0},
        {"Ledger Name": "Plant and Machinery", "Group": "Property, Plant and Equipment", "Debit": 142000000, "Credit": 0, "PY Debit": 125000000, "PY Credit": 0},
        {"Ledger Name": "Electrical Installations", "Group": "Property, Plant and Equipment", "Debit": 12500000, "Credit": 0, "PY Debit": 12500000, "PY Credit": 0},
        {"Ledger Name": "Furniture and Fixtures", "Group": "Property, Plant and Equipment", "Debit": 9500000, "Credit": 0, "PY Debit": 9000000, "PY Credit": 0},
        {"Ledger Name": "Computers and Servers", "Group": "Property, Plant and Equipment", "Debit": 8200000, "Credit": 0, "PY Debit": 7500000, "PY Credit": 0},
        {"Ledger Name": "Motor Vehicles / Trucks", "Group": "Property, Plant and Equipment", "Debit": 11000000, "Credit": 0, "PY Debit": 9500000, "PY Credit": 0},
        {"Ledger Name": "Accumulated Depreciation - PPE", "Group": "Property, Plant and Equipment", "Debit": 0, "Credit": 74500000, "PY Debit": 0, "PY Credit": 52000000},  # Contra PPE
        {"Ledger Name": "Right-of-Use Asset - Factory Lease", "Group": "Right-of-use assets", "Debit": 16500000, "Credit": 0, "PY Debit": 19500000, "PY Credit": 0},
        {"Ledger Name": "Capital Work in Progress - New Unit", "Group": "Capital work-in-progress", "Debit": 14500000, "Credit": 0, "PY Debit": 8000000, "PY Credit": 0},
        {"Ledger Name": "Computer Software Licenses", "Group": "Other Intangible assets", "Debit": 6500000, "Credit": 0, "PY Debit": 5500000, "PY Credit": 0},
        {"Ledger Name": "Investment in Subsidiary Shares", "Group": "Financial Assets - Investments", "Debit": 25000000, "Credit": 0, "PY Debit": 25000000, "PY Credit": 0},
        {"Ledger Name": "Security Deposits (Long Term)", "Group": "Financial Assets - Loans", "Debit": 4500000, "Credit": 0, "PY Debit": 4000000, "PY Credit": 0},
        {"Ledger Name": "Deferred Tax Asset", "Group": "Deferred Tax", "Debit": 3500000, "Credit": 0, "PY Debit": 3000000, "PY Credit": 0},

        # CURRENT ASSETS
        {"Ledger Name": "Raw Materials Inventory", "Group": "Inventories", "Debit": 28500000, "Credit": 0, "PY Debit": 24000000, "PY Credit": 0},
        {"Ledger Name": "Work in Progress Inventory (WIP)", "Group": "Inventories", "Debit": 11500000, "Credit": 0, "PY Debit": 9500000, "PY Credit": 0},
        {"Ledger Name": "Finished Goods Inventory", "Group": "Inventories", "Debit": 38000000, "Credit": 0, "PY Debit": 32000000, "PY Credit": 0},
        {"Ledger Name": "Packing Materials Inventory", "Group": "Inventories", "Debit": 6200000, "Credit": 0, "PY Debit": 5200000, "PY Credit": 0},
        {"Ledger Name": "Sundry Debtors - Domestic", "Group": "Trade Receivables", "Debit": 68500000, "Credit": 0, "PY Debit": 58000000, "PY Credit": 0},
        {"Ledger Name": "Sundry Debtors - Export", "Group": "Trade Receivables", "Debit": 16500000, "Credit": 0, "PY Debit": 14000000, "PY Credit": 0},
        {"Ledger Name": "Provision for Doubtful Debts", "Group": "Trade Receivables", "Debit": 0, "Credit": 3500000, "PY Debit": 0, "PY Credit": 2800000},  # CA EDGE CASE 4 (Contra)
        {"Ledger Name": "Cash in Hand", "Group": "Cash & Cash Equivalents", "Debit": 450000, "Credit": 0, "PY Debit": 380000, "PY Credit": 0},
        {"Ledger Name": "HDFC Bank - Current Account", "Group": "Cash & Cash Equivalents", "Debit": 18500000, "Credit": 0, "PY Debit": 14500000, "PY Credit": 0},
        {"Ledger Name": "Short Term Fixed Deposit (<12 Months)", "Group": "Other Bank Balances", "Debit": 12000000, "Credit": 0, "PY Debit": 10000000, "PY Credit": 0},
        {"Ledger Name": "Current Investments in Liquid Mutual Funds", "Group": "Current Investments", "Debit": 15000000, "Credit": 0, "PY Debit": 10000000, "PY Credit": 0},
        {"Ledger Name": "Advance to Suppliers / Vendors", "Group": "Other Current Assets", "Debit": 5500000, "Credit": 0, "PY Debit": 4200000, "PY Credit": 0},
        {"Ledger Name": "Prepaid Insurance", "Group": "Other Current Assets", "Debit": 1450000, "Credit": 0, "PY Debit": 1200000, "PY Credit": 0},
        {"Ledger Name": "GST Input - CGST Credit", "Group": "Other Current Assets", "Debit": 4200000, "Credit": 0, "PY Debit": 3500000, "PY Credit": 0},
        {"Ledger Name": "GST Input - SGST Credit", "Group": "Other Current Assets", "Debit": 4200000, "Credit": 0, "PY Debit": 3500000, "PY Credit": 0},
        {"Ledger Name": "GST Input - IGST Credit", "Group": "Other Current Assets", "Debit": 2800000, "Credit": 0, "PY Debit": 2200000, "PY Credit": 0},
        {"Ledger Name": "Advance Tax Paid - FY 2023-24", "Group": "Current Tax Asset", "Debit": 14500000, "Credit": 0, "PY Debit": 12500000, "PY Credit": 0},
        {"Ledger Name": "TDS Receivable - FY 2023-24", "Group": "Current Tax Asset", "Debit": 3800000, "Credit": 0, "PY Debit": 3200000, "PY Credit": 0},

        # INCOME STATEMENT (P&L NOMINALS)
        {"Ledger Name": "Domestic Sales - Finished Goods", "Group": "Revenue from operations", "Debit": 0, "Credit": 485000000, "PY Debit": 0, "PY Credit": 420000000},
        {"Ledger Name": "Export Sales", "Group": "Revenue from operations", "Debit": 0, "Credit": 65000000, "PY Debit": 0, "PY Credit": 55000000},
        {"Ledger Name": "Sale of Scrap / Waste", "Group": "Revenue from operations", "Debit": 0, "Credit": 3200000, "PY Debit": 0, "PY Credit": 2800000},
        {"Ledger Name": "Sales Returns & Rebates", "Group": "Revenue from operations", "Debit": 4500000, "Credit": 0, "PY Debit": 3800000, "PY Credit": 0},
        {"Ledger Name": "Interest Income on Fixed Deposits", "Group": "Other income", "Debit": 0, "Credit": 1850000, "PY Debit": 0, "PY Credit": 1500000},
        {"Ledger Name": "Dividend Income from Mutual Funds", "Group": "Other income", "Debit": 0, "Credit": 950000, "PY Debit": 0, "PY Credit": 750000},
        {"Ledger Name": "Net Gain on Foreign Currency Fluctuation", "Group": "Other income", "Debit": 0, "Credit": 1200000, "PY Debit": 0, "PY Credit": 900000},

        {"Ledger Name": "Purchases of Raw Materials - Domestic", "Group": "Cost of materials consumed", "Debit": 235000000, "Credit": 0, "PY Debit": 205000000, "PY Credit": 0},
        {"Ledger Name": "Freight Inward on Raw Materials", "Group": "Cost of materials consumed", "Debit": 8500000, "Credit": 0, "PY Debit": 7200000, "PY Credit": 0},
        {"Ledger Name": "Purchases of Stock-in-Trade", "Group": "Purchases of Stock-in-Trade", "Debit": 14500000, "Credit": 0, "PY Debit": 12000000, "PY Credit": 0},
        {"Ledger Name": "Changes in Inventories of FG and WIP", "Group": "Changes in inventories", "Debit": 0, "Credit": 8000000, "PY Debit": 0, "PY Credit": 6500000},  # Credit represents accretive increase in closing stock

        {"Ledger Name": "Salaries and Wages", "Group": "Employee benefits expense", "Debit": 72000000, "Credit": 0, "PY Debit": 62000000, "PY Credit": 0},
        {"Ledger Name": "Contribution to Provident Fund (PF)", "Group": "Employee benefits expense", "Debit": 5800000, "Credit": 0, "PY Debit": 4900000, "PY Credit": 0},
        {"Ledger Name": "Staff Welfare Expenses", "Group": "Employee benefits expense", "Debit": 3400000, "Credit": 0, "PY Debit": 2900000, "PY Credit": 0},
        {"Ledger Name": "Gratuity Expense", "Group": "Employee benefits expense", "Debit": 1800000, "Credit": 0, "PY Debit": 1500000, "PY Credit": 0},

        {"Ledger Name": "Interest on Term Loans", "Group": "Finance costs", "Debit": 7800000, "Credit": 0, "PY Debit": 9200000, "PY Credit": 0},
        {"Ledger Name": "Interest on Working Capital / Cash Credit", "Group": "Finance costs", "Debit": 2400000, "Credit": 0, "PY Debit": 2100000, "PY Credit": 0},
        {"Ledger Name": "Interest on Lease Liability (Ind AS 116)", "Group": "Finance costs", "Debit": 1400000, "Credit": 0, "PY Debit": 1600000, "PY Credit": 0},
        {"Ledger Name": "Bank Charges and Processing Fees", "Group": "Finance costs", "Debit": 450000, "Credit": 0, "PY Debit": 380000, "PY Credit": 0},

        {"Ledger Name": "Depreciation on Plant & Machinery", "Group": "Depreciation and amortisation", "Debit": 14200000, "Credit": 0, "PY Debit": 12500000, "PY Credit": 0},
        {"Ledger Name": "Depreciation on Buildings", "Group": "Depreciation and amortisation", "Debit": 3400000, "Credit": 0, "PY Debit": 3400000, "PY Credit": 0},
        {"Ledger Name": "Depreciation on Vehicles", "Group": "Depreciation and amortisation", "Debit": 1800000, "Credit": 0, "PY Debit": 1600000, "PY Credit": 0},
        {"Ledger Name": "Amortisation of Software Licenses", "Group": "Depreciation and amortisation", "Debit": 1100000, "Credit": 0, "PY Debit": 950000, "PY Credit": 0},
        {"Ledger Name": "Depreciation on Right-of-Use Assets", "Group": "Depreciation and amortisation", "Debit": 3000000, "Credit": 0, "PY Debit": 3000000, "PY Credit": 0},

        {"Ledger Name": "Power, Fuel & Water Charges", "Group": "Other expenses", "Debit": 24500000, "Credit": 0, "PY Debit": 21500000, "PY Credit": 0},
        {"Ledger Name": "Freight Outward / Carriage Outward", "Group": "Other expenses", "Debit": 18500000, "Credit": 0, "PY Debit": 15800000, "PY Credit": 0},
        {"Ledger Name": "Advertising and Marketing Expenses", "Group": "Other expenses", "Debit": 38000000, "Credit": 0, "PY Debit": 31000000, "PY Credit": 0},
        {"Ledger Name": "Sales Promotion and Brand Building", "Group": "Other expenses", "Debit": 16500000, "Credit": 0, "PY Debit": 13500000, "PY Credit": 0},
        {"Ledger Name": "Repairs & Maintenance - Plant & Machinery", "Group": "Other expenses", "Debit": 7200000, "Credit": 0, "PY Debit": 6100000, "PY Credit": 0},
        {"Ledger Name": "Rent for Factory & Office", "Group": "Other expenses", "Debit": 4500000, "Credit": 0, "PY Debit": 4200000, "PY Credit": 0},
        {"Ledger Name": "Insurance Expense (Plant, Stock & Vehicles)", "Group": "Other expenses", "Debit": 3200000, "Credit": 0, "PY Debit": 2800000, "PY Credit": 0},
        {"Ledger Name": "Travelling and Conveyance Expenses", "Group": "Other expenses", "Debit": 5400000, "Credit": 0, "PY Debit": 4600000, "PY Credit": 0},
        {"Ledger Name": "Legal and Professional Charges", "Group": "Other expenses", "Debit": 4200000, "Credit": 0, "PY Debit": 3600000, "PY Credit": 0},
        {"Ledger Name": "Statutory Auditor Remuneration - Audit Fee", "Group": "Other expenses", "Debit": 1200000, "Credit": 0, "PY Debit": 1000000, "PY Credit": 0},
        {"Ledger Name": "Corporate Social Responsibility (CSR) Expense", "Group": "Other expenses", "Debit": 1800000, "Credit": 0, "PY Debit": 1500000, "PY Credit": 0},
        {"Ledger Name": "Bad Debts Written Off", "Group": "Other expenses", "Debit": 950000, "Credit": 0, "PY Debit": 800000, "PY Credit": 0},
        {"Ledger Name": "Miscellaneous Operating Expenses", "Group": "Other expenses", "Debit": 2850000, "Credit": 0, "PY Debit": 2400000, "PY Credit": 0},

        {"Ledger Name": "Current Income Tax Expense", "Group": "Tax Expense", "Debit": 16000000, "Credit": 0, "PY Debit": 14000000, "PY Credit": 0},
        {"Ledger Name": "Deferred Tax Expense", "Group": "Tax Expense", "Debit": 1500000, "Credit": 0, "PY Debit": 1200000, "PY Credit": 0},
    ]

    df_div2 = pd.DataFrame(tb_data_div2)

    # Calculate exact difference to verify balancing
    tot_dr = df_div2["Debit"].sum()
    tot_cr = df_div2["Credit"].sum()
    diff = tot_dr - tot_cr

    # If small discrepancy, add an adjustment to Retained Earnings Opening to guarantee mathematical exact zero balance
    if diff != 0:
        if diff > 0:
            df_div2.loc[df_div2["Ledger Name"] == "Retained Earnings Opening", "Credit"] += diff
        else:
            df_div2.loc[df_div2["Ledger Name"] == "Retained Earnings Opening", "Debit"] += abs(diff)

    tot_py_dr = df_div2["PY Debit"].sum()
    tot_py_cr = df_div2["PY Credit"].sum()
    py_diff = tot_py_dr - tot_py_cr
    if py_diff != 0:
        if py_diff > 0:
            df_div2.loc[df_div2["Ledger Name"] == "Retained Earnings Opening", "PY Credit"] += py_diff
        else:
            df_div2.loc[df_div2["Ledger Name"] == "Retained Earnings Opening", "PY Debit"] += abs(py_diff)

    div2_path = os.path.join(data_dir, "sample_tb.xlsx")
    with pd.ExcelWriter(div2_path, engine="openpyxl") as writer:
        df_div2.to_excel(writer, sheet_name="Trial Balance", index=False)
    print(f"Generated Division II sample TB at {div2_path} (CY Dr: {df_div2['Debit'].sum():,.2f}, Cr: {df_div2['Credit'].sum():,.2f})")

    # -------------------------------------------------------------------------
    # SAMPLE TB 2: DIVISION I (NON-IND AS / AS) - "Heritage Foods India Ltd"
    # -------------------------------------------------------------------------
    tb_data_div1 = [
        {"Ledger Name": "Equity Share Capital", "Group": "Share Capital", "Debit": 0, "Credit": 30000000, "PY Debit": 0, "PY Credit": 30000000},
        {"Ledger Name": "General Reserve", "Group": "Reserves and Surplus", "Debit": 0, "Credit": 25000000, "PY Debit": 0, "PY Credit": 25000000},
        {"Ledger Name": "Surplus in P&L Account", "Group": "Reserves and Surplus", "Debit": 0, "Credit": 42000000, "PY Debit": 0, "PY Credit": 28000000},
        {"Ledger Name": "Term Loan - SBI", "Group": "Long-term borrowings", "Debit": 0, "Credit": 45000000, "PY Debit": 0, "PY Credit": 55000000},
        {"Ledger Name": "Deferred Tax Liability", "Group": "Deferred tax liabilities", "Debit": 0, "Credit": 5500000, "PY Debit": 0, "PY Credit": 4800000},
        {"Ledger Name": "Long-term provisions - Gratuity", "Group": "Long-term provisions", "Debit": 0, "Credit": 4200000, "PY Debit": 0, "PY Credit": 3600000},
        {"Ledger Name": "Current Maturities of Term Loan", "Group": "Short-term borrowings", "Debit": 0, "Credit": 10000000, "PY Debit": 0, "PY Credit": 10000000},
        {"Ledger Name": "Cash Credit Account - HDFC", "Group": "Short-term borrowings", "Debit": 0, "Credit": 18000000, "PY Debit": 0, "PY Credit": 15000000},
        {"Ledger Name": "Sundry Creditors - Micro Enterprises", "Group": "Trade Payables MSME", "Debit": 0, "Credit": 6500000, "PY Debit": 0, "PY Credit": 5200000},
        {"Ledger Name": "Sundry Creditors - Raw Material", "Group": "Trade Payables Others", "Debit": 0, "Credit": 22000000, "PY Debit": 0, "PY Credit": 19000000},
        {"Ledger Name": "Creditor with Debit Balance", "Group": "Trade Payables", "Debit": 1200000, "Credit": 0, "PY Debit": 800000, "PY Credit": 0},
        {"Ledger Name": "Debtor with Credit Balance", "Group": "Trade Receivables", "Debit": 0, "Credit": 1500000, "PY Debit": 0, "PY Credit": 900000},
        {"Ledger Name": "Advance Received from Customers", "Group": "Other current liabilities", "Debit": 0, "Credit": 2800000, "PY Debit": 0, "PY Credit": 2100000},
        {"Ledger Name": "Outstanding Expenses", "Group": "Other current liabilities", "Debit": 0, "Credit": 4500000, "PY Debit": 0, "PY Credit": 3800000},
        {"Ledger Name": "Provision for Tax - AY 2024-25", "Group": "Short-term provisions", "Debit": 0, "Credit": 9500000, "PY Debit": 0, "PY Credit": 8200000},

        {"Ledger Name": "Freehold Land", "Group": "Fixed Assets", "Debit": 45000000, "Credit": 0, "PY Debit": 45000000, "PY Credit": 0},
        {"Ledger Name": "Factory Buildings", "Group": "Fixed Assets", "Debit": 38000000, "Credit": 0, "PY Debit": 38000000, "PY Credit": 0},
        {"Ledger Name": "Plant and Machinery", "Group": "Fixed Assets", "Debit": 76000000, "Credit": 0, "PY Debit": 68000000, "PY Credit": 0},
        {"Ledger Name": "Furniture and Fixtures", "Group": "Fixed Assets", "Debit": 5500000, "Credit": 0, "PY Debit": 5000000, "PY Credit": 0},
        {"Ledger Name": "Accumulated Depreciation - Buildings", "Group": "Fixed Assets", "Debit": 0, "Credit": 32000000, "PY Debit": 0, "PY Credit": 24000000},
        {"Ledger Name": "Capital Work in Progress - New Unit", "Group": "Capital work-in-progress", "Debit": 6800000, "Credit": 0, "PY Debit": 3500000, "PY Credit": 0},
        {"Ledger Name": "Non-current investments", "Group": "Non-current investments", "Debit": 12000000, "Credit": 0, "PY Debit": 12000000, "PY Credit": 0},

        {"Ledger Name": "Raw Materials Inventory", "Group": "Inventories", "Debit": 18500000, "Credit": 0, "PY Debit": 15500000, "PY Credit": 0},
        {"Ledger Name": "Work in Progress Inventory (WIP)", "Group": "Inventories", "Debit": 6200000, "Credit": 0, "PY Debit": 5200000, "PY Credit": 0},
        {"Ledger Name": "Finished Goods Inventory", "Group": "Inventories", "Debit": 22500000, "Credit": 0, "PY Debit": 19500000, "PY Credit": 0},
        {"Ledger Name": "Sundry Debtors - Domestic", "Group": "Trade receivables", "Debit": 42500000, "Credit": 0, "PY Debit": 36500000, "PY Credit": 0},
        {"Ledger Name": "Provision for Doubtful Debts", "Group": "Trade receivables", "Debit": 0, "Credit": 2200000, "PY Debit": 0, "PY Credit": 1800000},
        {"Ledger Name": "Cash in Hand", "Group": "Cash and bank balances", "Debit": 280000, "Credit": 0, "PY Debit": 220000, "PY Credit": 0},
        {"Ledger Name": "SBI - Current Account", "Group": "Cash and bank balances", "Debit": 11500000, "Credit": 0, "PY Debit": 9500000, "PY Credit": 0},
        {"Ledger Name": "Advance to Suppliers / Vendors", "Group": "Other current assets", "Debit": 3500000, "Credit": 0, "PY Debit": 2800000, "PY Credit": 0},
        {"Ledger Name": "Advance Tax Paid - FY 2023-24", "Group": "Short-term loans and advances", "Debit": 8500000, "Credit": 0, "PY Debit": 7500000, "PY Credit": 0},

        # P&L
        {"Ledger Name": "Domestic Sales - Finished Goods", "Group": "Revenue from operations", "Debit": 0, "Credit": 285000000, "PY Debit": 0, "PY Credit": 245000000},
        {"Ledger Name": "Interest Income on Fixed Deposits", "Group": "Other income", "Debit": 0, "Credit": 1100000, "PY Debit": 0, "PY Credit": 900000},
        {"Ledger Name": "Purchases of Raw Materials - Domestic", "Group": "Cost of materials consumed", "Debit": 138000000, "Credit": 0, "PY Debit": 120000000, "PY Credit": 0},
        {"Ledger Name": "Opening Stock - Finished Goods", "Group": "Changes in inventories", "Debit": 19500000, "Credit": 0, "PY Debit": 16500000, "PY Credit": 0},
        {"Ledger Name": "Closing Stock - Finished Goods", "Group": "Changes in inventories", "Debit": 0, "Credit": 22500000, "PY Debit": 0, "PY Credit": 19500000},
        {"Ledger Name": "Salaries and Wages", "Group": "Employee benefits expense", "Debit": 42000000, "Credit": 0, "PY Debit": 36000000, "PY Credit": 0},
        {"Ledger Name": "Interest on Term Loans", "Group": "Finance costs", "Debit": 4800000, "Credit": 0, "PY Debit": 5800000, "PY Credit": 0},
        {"Ledger Name": "Depreciation on Plant & Machinery", "Group": "Depreciation", "Debit": 8200000, "Credit": 0, "PY Debit": 7500000, "PY Credit": 0},
        {"Ledger Name": "Power, Fuel & Water Charges", "Group": "Other expenses", "Debit": 16500000, "Credit": 0, "PY Debit": 14200000, "PY Credit": 0},
        {"Ledger Name": "Freight Outward / Carriage Outward", "Group": "Other expenses", "Debit": 11200000, "Credit": 0, "PY Debit": 9800000, "PY Credit": 0},
        {"Ledger Name": "Advertising and Marketing Expenses", "Group": "Other expenses", "Debit": 18500000, "Credit": 0, "PY Debit": 15200000, "PY Credit": 0},
        {"Ledger Name": "Current Income Tax Expense", "Group": "Tax Expense", "Debit": 9500000, "Credit": 0, "PY Debit": 8200000, "PY Credit": 0},
        {"Ledger Name": "Deferred Tax Expense", "Group": "Tax Expense", "Debit": 700000, "Credit": 0, "PY Debit": 600000, "PY Credit": 0},
    ]

    df_div1 = pd.DataFrame(tb_data_div1)
    d1_dr = df_div1["Debit"].sum()
    d1_cr = df_div1["Credit"].sum()
    d1_diff = d1_dr - d1_cr
    if d1_diff != 0:
        if d1_diff > 0:
            df_div1.loc[df_div1["Ledger Name"] == "Surplus in P&L Account", "Credit"] += d1_diff
        else:
            df_div1.loc[df_div1["Ledger Name"] == "Surplus in P&L Account", "Debit"] += abs(d1_diff)

    d1_py_dr = df_div1["PY Debit"].sum()
    d1_py_cr = df_div1["PY Credit"].sum()
    d1_py_diff = d1_py_dr - d1_py_cr
    if d1_py_diff != 0:
        if d1_py_diff > 0:
            df_div1.loc[df_div1["Ledger Name"] == "Surplus in P&L Account", "PY Credit"] += d1_py_diff
        else:
            df_div1.loc[df_div1["Ledger Name"] == "Surplus in P&L Account", "PY Debit"] += abs(d1_py_diff)

    div1_path = os.path.join(data_dir, "sample_tb_division1.xlsx")
    with pd.ExcelWriter(div1_path, engine="openpyxl") as writer:
        df_div1.to_excel(writer, sheet_name="Trial Balance", index=False)
    print(f"Generated Division I sample TB at {div1_path} (CY Dr: {df_div1['Debit'].sum():,.2f}, Cr: {df_div1['Credit'].sum():,.2f})")

if __name__ == "__main__":
    generate_sample_tbs()
