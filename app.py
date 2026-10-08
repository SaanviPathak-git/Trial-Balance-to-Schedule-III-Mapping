import io, pandas as pd, streamlit as st
from engine import load_tb, map_ledgers, build, ALL_LINES

st.set_page_config(page_title="TB to Schedule III", layout="wide")
st.title("Trial Balance to Schedule III Mapping")
st.caption("Division II (Ind AS) | maps ledgers to Balance Sheet and Statement of Profit and Loss line items")

with st.sidebar:
    entity = st.text_input("Entity name", "Sample Foods Ltd")
    src = st.file_uploader("Upload trial balance (CSV or Excel)", type=["csv", "xlsx"])
    st.caption("Columns: Ledger, Debit, Credit (or Ledger, Closing Balance with debit positive).")
    closing = st.number_input("Closing stock (not in a pre-adjustment TB)", value=900.0, step=50.0)
    st.caption("All amounts in the same unit as the TB.")

raw = (pd.read_csv(src) if src and src.name.endswith("csv") else pd.read_excel(src)) if src else pd.read_csv("data/sample_tb.csv")
if not src: st.info("Showing the built-in sample trial balance. Upload your own in the sidebar.")
mapped = map_ledgers(load_tb(raw))

t1, t2, t3, t4, t5 = st.tabs(["1. Mapping", "2. Balance Sheet", "3. Profit and Loss", "4. Checks and ratios", "5. Export"])
with t1:
    st.write("Review the mapping. Amber means low confidence; change any line using the dropdown. Unmapped ledgers block finalisation.")
    mapped = st.data_editor(mapped, use_container_width=True, hide_index=True, disabled=["Ledger", "Debit", "Credit", "Confidence", "Method"],
        column_config={"Schedule III line": st.column_config.SelectboxColumn(options=ALL_LINES, width="large")})
res = build(mapped, closing)
fmt = lambda d: d.style.format({"Amount": "{:,.0f}"}, na_rep="")
with t2:
    st.subheader(f"{entity}: Balance Sheet"); st.dataframe(fmt(res["bs"]), use_container_width=True, hide_index=True, height=800)
with t3:
    st.subheader(f"{entity}: Statement of Profit and Loss"); st.dataframe(fmt(res["pl"]), use_container_width=True, hide_index=True)
with t4:
    c = res["checks"]; st.success("All checks passed") if c["Pass"].all() else st.error("Some checks failed")
    st.dataframe(c.assign(Pass=c["Pass"].map({True: "PASS", False: "FAIL"})), use_container_width=True, hide_index=True)
    st.subheader("Treatment log (CA judgements applied)")
    log = res["mapped"].query("Treatment != ''")[["Ledger", "Schedule III line", "Treatment"]]
    st.dataframe(log, use_container_width=True, hide_index=True)
    st.subheader("Schedule III ratios (current year)"); st.dataframe(res["ratios"].style.format({"Value": "{:.2f}"}), hide_index=True)
with t5:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in [("Mapped TB", res["mapped"]), ("Balance Sheet", res["bs"]), ("Profit and Loss", res["pl"]), ("Checks", res["checks"]), ("Ratios", res["ratios"])]:
            df.to_excel(w, sheet_name=name, index=False)
    st.download_button("Download Excel", buf.getvalue(), f"{entity}_ScheduleIII.xlsx")
