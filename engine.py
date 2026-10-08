"""Trial Balance -> Schedule III (Division II, Ind AS) mapping engine."""
import re, difflib
import pandas as pd

EQ = ["Equity share capital", "Other equity"]
NCL = ["Borrowings (non-current)", "Lease liabilities (non-current)", "Provisions (non-current)", "Deferred tax liabilities (net)"]
CL = ["Borrowings (current)", "Trade payables", "Other financial liabilities", "Other current liabilities", "Provisions (current)", "Current tax liabilities (net)"]
NCA = ["Property, plant and equipment", "Capital work-in-progress", "Other intangible assets", "Non-current investments", "Other non-current financial assets", "Deferred tax assets (net)"]
CA = ["Inventories", "Trade receivables", "Cash and cash equivalents", "Other bank balances", "Other current assets"]
INC = ["Revenue from operations", "Other income"]
CHG = "Changes in inventories of finished goods, WIP and stock-in-trade"
EXP = ["Cost of materials consumed", "Purchases of stock-in-trade", CHG, "Employee benefits expense", "Finance costs", "Depreciation and amortisation expense", "Other expenses"]
TAX = ["Tax expense"]
ALL_LINES = EQ + NCL + CL + NCA + CA + INC + EXP + TAX + ["UNMAPPED"]
DEBIT_NATURE = set(NCA + CA + EXP + TAX)

RULES = [
("accumulated dep", NCA[0]), ("accumulated amort", NCA[2]),
("depreciation|amortisation|amortization", EXP[5]),
("current tax expense|income tax expense|deferred tax expense|tax expense", TAX[0]),
("interest income|interest received|dividend|other income|misc income|discount received", INC[1]),
("interest on|interest paid|finance charge|loan processing", EXP[4]),
("bank charges", EXP[6]),
("current maturities|cash credit|overdraft|working capital loan", CL[0]),
("term loan|debenture|secured loan|unsecured loan|vehicle loan", NCL[0]),
("lease liab", NCL[1]),
("provision for doubtful|provision for bad|allowance for", CA[1]),
("provision for tax|provision for income tax|income tax payable", CL[5]),
("provision for gratuity|gratuity payable", NCL[2]),
("provision for|bonus payable", CL[4]),
("deferred tax liab", NCL[3]), ("deferred tax asset", NCA[5]),
("customer advance|advance from customer|advance received", CL[3]),
("gst output|output gst|gst payable|tds payable|statutory|esi payable|pf payable", CL[3]),
("outstanding|expenses payable|accrued", CL[2]),
("advance to|advances to|gst input|input gst|input tax|tds receivable|tcs receivable|prepaid", CA[4]),
("security deposit|rent deposit", NCA[4]),
("fixed deposit|fd with|margin money", CA[3]),
("cash in hand|petty cash|current account|savings account|bank balance|balance with bank", CA[2]),
("investment", NCA[3]), ("capital work|cwip", NCA[1]),
("software|goodwill|patent|trademark|licen", NCA[2]),
("land|building|plant|machinery|furniture|vehicle|computer|office equipment|equipment", NCA[0]),
("debtors|receivable", CA[1]), ("creditors|trade payable", CL[1]),
("share capital", EQ[0]), ("reserve|retained|surplus|securities premium|profit and loss", EQ[1]),
("opening stock|opening inventory", CHG),
("sales|revenue|service income|job work income", INC[0]),
("purchase of stock|purchase - traded|purchases - traded|traded goods", EXP[1]),
("purchase|raw material|packing material|freight inward|consumable", EXP[0]),
("salary|salaries|wages|director remuneration|staff|provident fund|bonus", EXP[3]),
("rent|electricity|power|freight|advertis|repair|audit|travel|insurance|legal|professional|telephone|commission|printing|office|rates and taxes|misc", EXP[6]),
]
_COMPILED = [(re.compile(r"\b(?:" + p + ")"), line) for p, line in RULES]
_KEYS = [(k, line) for p, line in RULES for k in p.split("|")]

def load_tb(df):
    """Accept Ledger + Debit/Credit, or Ledger + signed Closing Balance (Dr positive)."""
    df = df.copy(); df.columns = [str(c).strip().lower() for c in df.columns]
    name = next(c for c in df.columns if "ledger" in c or "account" in c or "name" in c)
    out = pd.DataFrame({"Ledger": df[name].astype(str).str.strip()})
    if "debit" in df.columns and "credit" in df.columns:
        out["Debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        out["Credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    else:
        bal = pd.to_numeric(df[next(c for c in df.columns if "balance" in c)], errors="coerce").fillna(0)
        out["Debit"], out["Credit"] = bal.clip(lower=0), (-bal).clip(lower=0)
    return out[out["Ledger"].ne("") & (out["Debit"] + out["Credit"] != 0)].reset_index(drop=True)

def map_one(name):
    n = name.lower()
    for rx, line in _COMPILED:
        if rx.search(n): return line, 100, "Rule"
    best = max(((difflib.SequenceMatcher(None, n, k).ratio(), line) for k, line in _KEYS), default=(0, ""))
    return (best[1], round(best[0] * 100), "Fuzzy") if best[0] >= 0.6 else ("UNMAPPED", 0, "None")

def map_ledgers(tb):
    m = tb.copy()
    res = m["Ledger"].map(map_one)
    m["Schedule III line"] = [r[0] for r in res]; m["Confidence"] = [r[1] for r in res]; m["Method"] = [r[2] for r in res]
    return m

def classify(m):
    """Gross-up: debtors with credit balance -> other current liabilities; creditors with debit balance -> other current assets."""
    m = m.copy(); m["Treatment"] = ""
    net = m["Debit"] - m["Credit"]; low = m["Ledger"].str.lower()
    a = (m["Schedule III line"] == CA[1]) & (net < 0) & ~low.str.contains("provision|allowance")
    b = (m["Schedule III line"] == CL[1]) & (net > 0)
    m.loc[a, ["Schedule III line", "Treatment"]] = [CL[3], "Debtor with credit balance grossed up to other current liabilities"]
    m.loc[b, ["Schedule III line", "Treatment"]] = [CA[4], "Creditor with debit balance grossed up to other current assets"]
    return m

def build(mapped, closing_stock=0.0):
    m = classify(mapped)
    if closing_stock:  # closing stock is not in a pre-adjustment TB: add as adjustment
        adj = pd.DataFrame([
            {"Ledger": "Closing stock (adjustment)", "Debit": closing_stock, "Credit": 0, "Schedule III line": CA[0], "Confidence": 100, "Method": "Adjustment", "Treatment": "Closing stock entered by user"},
            {"Ledger": "Closing stock (adjustment)", "Debit": 0, "Credit": closing_stock, "Schedule III line": CHG, "Confidence": 100, "Method": "Adjustment", "Treatment": "Closing stock credited to changes in inventories"}])
        m = pd.concat([m, adj], ignore_index=True)
    amt = {l: 0.0 for l in ALL_LINES}
    for line, g in m.groupby("Schedule III line"):
        d, c = g["Debit"].sum(), g["Credit"].sum()
        amt[line] = d - c if line in DEBIT_NATURE else c - d
    income = sum(amt[l] for l in INC); exp = sum(amt[l] for l in EXP)
    pbt = income - exp; pat = pbt - amt[TAX[0]]
    other_eq = amt[EQ[1]] + pat
    A = lambda ls: sum(amt[l] for l in ls)
    bs = [("EQUITY AND LIABILITIES", None), ("Equity share capital", amt[EQ[0]]), ("Other equity (incl. profit for the year)", other_eq),
          ("Total equity", amt[EQ[0]] + other_eq), ("Non-current liabilities", None)] + [(l, amt[l]) for l in NCL] + \
         [("Total non-current liabilities", A(NCL)), ("Current liabilities", None)] + [(l, amt[l]) for l in CL] + \
         [("Total current liabilities", A(CL)), ("TOTAL EQUITY AND LIABILITIES", amt[EQ[0]] + other_eq + A(NCL) + A(CL)),
          ("ASSETS", None), ("Non-current assets", None)] + [(l, amt[l]) for l in NCA] + [("Total non-current assets", A(NCA)), ("Current assets", None)] + \
         [(l, amt[l]) for l in CA] + [("Total current assets", A(CA)), ("TOTAL ASSETS", A(NCA) + A(CA))]
    pl = [(l, amt[l]) for l in INC] + [("Total income", income)] + [(l, amt[l]) for l in EXP] + \
         [("Total expenses", exp), ("Profit before tax", pbt), ("Tax expense", amt[TAX[0]]), ("Profit for the year", pat)]
    tot_a, tot_l = A(NCA) + A(CA), amt[EQ[0]] + other_eq + A(NCL) + A(CL)
    checks = [
        ("TB debits equal credits", abs(mapped["Debit"].sum() - mapped["Credit"].sum()) < 0.5, f"Dr {mapped['Debit'].sum():,.0f} / Cr {mapped['Credit'].sum():,.0f}"),
        ("No unmapped ledgers", not (mapped["Schedule III line"] == "UNMAPPED").any(), f"{(mapped['Schedule III line'] == 'UNMAPPED').sum()} unmapped"),
        ("Balance Sheet balances", abs(tot_a - tot_l) < 0.5, f"Assets {tot_a:,.0f} / E&L {tot_l:,.0f}"),
        ("Profit transferred to Other equity", abs((other_eq - amt[EQ[1]]) - pat) < 0.5, f"PAT {pat:,.0f}"),
        ("Low-confidence mappings reviewed", not ((mapped["Confidence"] < 85) & (mapped["Method"] == "Fuzzy")).any(), f"{((mapped['Confidence'] < 85) & (mapped['Method'] == 'Fuzzy')).sum()} to review"),
    ]
    cogs = amt[EXP[0]] + amt[EXP[1]] + amt[CHG]
    opening = m.loc[m["Ledger"].str.lower().str.contains("opening stock"), "Debit"].sum()
    avg_inv = (opening + amt[CA[0]]) / 2 if opening else amt[CA[0]]
    debt = amt[NCL[0]] + amt[CL[0]] + amt[NCL[1]]; eq = amt[EQ[0]] + other_eq
    rev = amt[INC[0]]; ebit = pbt + amt[EXP[4]]
    z = lambda a, b: a / b if b else float("nan")
    ratios = [("Current ratio (x)", z(A(CA), A(CL))), ("Debt-equity ratio (x)", z(debt, eq)),
              ("Net profit margin (%)", 100 * z(pat, rev)), ("Return on equity (%)", 100 * z(pat, eq)),
              ("Return on capital employed (%)", 100 * z(ebit, eq + debt)), ("Inventory turnover (x)", z(cogs, avg_inv)),
              ("Trade receivables turnover (x)", z(rev, amt[CA[1]])), ("Trade payables turnover (x)", z(amt[EXP[0]] + amt[EXP[1]], amt[CL[1]])),
              ("Interest cover (x)", z(ebit, amt[EXP[4]]))]
    return dict(mapped=m, bs=pd.DataFrame(bs, columns=["Particulars", "Amount"]), pl=pd.DataFrame(pl, columns=["Particulars", "Amount"]),
                checks=pd.DataFrame(checks, columns=["Check", "Pass", "Detail"]), ratios=pd.DataFrame(ratios, columns=["Ratio", "Value"]))
