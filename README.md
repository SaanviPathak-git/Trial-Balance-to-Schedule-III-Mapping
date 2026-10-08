# Trial Balance to Schedule III Mapping

Interactive tool that maps trial balance ledgers to the Balance Sheet and Statement of Profit and Loss line items prescribed in Schedule III (Division II, Ind AS) of the Companies Act, 2013.

**Live app:** _add your Streamlit link here_

## What it does
- Reads a trial balance (CSV/Excel) and maps each ledger using a keyword rule master, with fuzzy matching and a confidence score as a fallback
- Lets the user override any mapping; unmapped ledgers block finalisation
- Applies CA judgements: debtors with credit balances and creditors with debit balances are grossed up (never netted); provision for doubtful debts sits against receivables; bank overdraft and cash credit go to current borrowings; closing stock is converted into changes in inventories; profit for the year flows into Other equity
- Produces the Balance Sheet, Profit and Loss, a treatment log, integrity checks and Schedule III ratios, and exports to Excel

## Assumptions
- Raw material purchases are treated as cost of materials consumed (no separate RM stock ledger)
- Closing stock is entered by the user as an adjustment
- Current and non-current split follows ledger naming (for example, "current maturities" go to current borrowings)

## Not yet included
Previous-year comparatives, Division I format, notes to accounts, MSME split of payables, ageing schedules.

## Run locally
    pip install -r requirements.txt
    streamlit run app.py
    python tests/test_engine.py
