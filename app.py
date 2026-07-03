import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# ---- Load your CSV ----
df = pd.read_csv("Return Inventory File.csv", dtype=str)

df["Colour"] = df["Colour"].fillna("").str.title()

# Columns
SEARCH_COLUMNS = ["EAN", "FashBCode"]
IMG_COL = "ImageURL"
DISPLAY_COLUMNS = ["Pick Location", "Style", "Colour", IMG_COL]

# ---- Session state ----
if "entered_barcodes" not in st.session_state:
    st.session_state.entered_barcodes = []
if "text_input" not in st.session_state:
    st.session_state.text_input = ""
if "finished" not in st.session_state:
    st.session_state.finished = False
if "result_df" not in st.session_state:
    st.session_state.result_df = None
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

# ---- Add barcode/style ----
def add_item():
    text = st.session_state.text_input.strip()
    if text:
        st.session_state.entered_barcodes.append(text)
    st.session_state.text_input = ""

st.text_input("Scan or enter barcode/style:", key="text_input", on_change=add_item)

# ---- Searchable style dropdown ----
style_options = (
    df["Style"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .sort_values()
    .tolist()
)

selected_style = st.selectbox(
    "Or search by style:",
    options=[""] + style_options,
    index=0
)

if selected_style:
    if st.button("Add selected style"):
        st.session_state.entered_barcodes.append(selected_style)
        st.success(f"Added style: {selected_style}")

# Optional: show what has been entered
if st.session_state.entered_barcodes:
    st.write("Entered items:", st.session_state.entered_barcodes)

# ---- Finish button builds the sequence ----
if st.button("Finish"):
    st.session_state.finished = True
    st.session_state.current_idx = 0

    entries = st.session_state.entered_barcodes

    entered_counts = (
        pd.Series(entries, name="Barcode")
        .value_counts()
        .rename_axis("Barcode")
        .reset_index(name="Count")
    )

    # Build lookup: EAN / FashBCode / Style -> details
    map1 = df[[SEARCH_COLUMNS[0]] + DISPLAY_COLUMNS].rename(columns={SEARCH_COLUMNS[0]: "Barcode"})
    map2 = df[[SEARCH_COLUMNS[1]] + DISPLAY_COLUMNS].rename(columns={SEARCH_COLUMNS[1]: "Barcode"})
    map3 = df[["Style"] + DISPLAY_COLUMNS].rename(columns={"Style": "Barcode"})

    mapping = (
        pd.concat([map1, map2, map3], ignore_index=True)
        .dropna(subset=["Barcode"])
        .drop_duplicates()
    )

    entered_counts["Barcode"] = entered_counts["Barcode"].astype(str).str.strip()
    mapping["Barcode"] = mapping["Barcode"].astype(str).str.strip()

    merged = entered_counts.merge(mapping, on="Barcode", how="left")

    result_df = (
        merged.groupby(DISPLAY_COLUMNS, dropna=False)["Count"]
        .sum()
        .reset_index()
        .sort_values(["Pick Location", "Style"], ascending=[True, True])
        .reset_index(drop=True)
    )

    st.session_state.result_df = result_df

    known_barcodes = mapping["Barcode"].dropna().astype(str).str.strip().unique()

    not_found = [
        barcode for barcode in entered_counts["Barcode"].astype(str).str.strip().unique()
        if barcode not in known_barcodes
    ]

    if not_found:
        st.warning(f"Items not found in file: {not_found}")

# ---- Navigator UI ----
def go_next():
    if st.session_state.result_df is None:
        return
    if st.session_state.current_idx < len(st.session_state.result_df) - 1:
        st.session_state.current_idx += 1

def go_prev():
    if st.session_state.current_idx > 0:
        st.session_state.current_idx -= 1

def restart():
    st.session_state.finished = False
    st.session_state.result_df = None
    st.session_state.current_idx = 0
    st.session_state.entered_barcodes = []

# ---- Show current item ----
if st.session_state.finished and st.session_state.result_df is not None and len(st.session_state.result_df) > 0:
    total = len(st.session_state.result_df)
    i = st.session_state.current_idx
    row = st.session_state.result_df.iloc[i]

    def has_value(value):
        return pd.notna(value) and str(value).strip() != ""

    left, right = st.columns([1, 2])

    with left:
        if has_value(row.get(IMG_COL)):
            st.image(str(row[IMG_COL]).strip())

    with right:
        if has_value(row.get("Style")):
            st.subheader(str(row["Style"]).strip())

        if has_value(row.get("Colour")):
            st.subheader(str(row["Colour"]).strip())

        if has_value(row.get("Pick Location")):
            st.markdown(f"**Pick Location:** {str(row['Pick Location']).strip()}")

        st.markdown(f"**Count:** {int(row['Count'])}")

        st.caption(f"Item {i + 1} of {total}")

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.button("◀ Prev", on_click=go_prev, disabled=(i == 0))
        with c2:
            st.button("Next ▶", on_click=go_next, disabled=(i >= total - 1))
        with c3:
            st.button("Start Over", on_click=restart)

elif st.session_state.finished:
    st.info("No items to display.")
    st.button("Start Over", on_click=restart)