import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# ---- Load your CSV ----
df = pd.read_csv('Return Inventory File.csv', dtype=str)

# Columns — adjust to your real names
SEARCH_COLUMNS = ['EAN', 'FashBCode']          # barcodes to search
IMG_COL = 'ImageURL'                           # <-- set this to your image URL column
DISPLAY_COLUMNS = ['Pick Location', 'Style', IMG_COL]  # what we show per item

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

# ---- Add barcode ----
def add_item():
    text = st.session_state.text_input.strip()
    if text:
        st.session_state.entered_barcodes.append(text)
    st.session_state.text_input = ""  # clear input

st.text_input("Scan or enter barcode:", key="text_input", on_change=add_item)

# ---- Finish button builds the sequence only once ----
if st.button("Finish"):
    st.session_state.finished = True
    st.session_state.current_idx = 0  # reset pointer

    barcodes = st.session_state.entered_barcodes

    # 1) Count how many times each barcode was entered
    entered_counts = (
        pd.Series(barcodes, name="Barcode")
        .value_counts()
        .rename_axis("Barcode")
        .reset_index(name="Count")
    )

    # 2) Build lookup: Barcode -> (Pick Location, Style, Image)
    map1 = df[[SEARCH_COLUMNS[0]] + DISPLAY_COLUMNS].rename(columns={SEARCH_COLUMNS[0]: "Barcode"})
    map2 = df[[SEARCH_COLUMNS[1]] + DISPLAY_COLUMNS].rename(columns={SEARCH_COLUMNS[1]: "Barcode"})
    mapping = (
        pd.concat([map1, map2], ignore_index=True)
        .dropna(subset=["Barcode"])
        .drop_duplicates()
    )

    # 3) Join counts to mapping (left join keeps unknown barcodes for warning)
    merged = entered_counts.merge(mapping, on="Barcode", how="left")

    # 4) Final summary per (Location, Style, Image): sum counts across barcodes
    result_df = (
        merged.groupby(DISPLAY_COLUMNS, dropna=False)["Count"]
        .sum()
        .reset_index()
        .sort_values(["Pick Location", "Style"], ascending=[True, True])
        .reset_index(drop=True)
    )

    st.session_state.result_df = result_df

    # Optional: show unknown barcodes
    not_found = merged[merged['Pick Location'].isna()]['Barcode'].unique().tolist()
    if not_found:
        st.warning(f"Barcodes not found in file: {not_found}")

# ---- Navigator UI (one item at a time) ----
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
    # keep entered_barcodes if you want to reprocess; otherwise clear:
    # st.session_state.entered_barcodes = []

# ---- Show the current item after Finish ----
if st.session_state.finished and st.session_state.result_df is not None and len(st.session_state.result_df) > 0:
    total = len(st.session_state.result_df)
    i = st.session_state.current_idx
    row = st.session_state.result_df.iloc[i]

    left, right = st.columns([1, 2])

    # IMAGE
    with left:
        img_url = (row.get(IMG_COL) or "").strip()
        if img_url:
            st.image(img_url)
            # st.info("No image available")

    # DETAILS
    with right:
        st.subheader(f"{row['Style']}")
        st.markdown(f"**Pick Location:** {row['Pick Location']}")
        st.markdown(f"**Count:** {int(row['Count'])}")
        st.caption(f"Item {i+1} of {total}")

        # Action buttons
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.button("◀ Prev", on_click=go_prev, disabled=(i == 0))
        with c2:
            st.button("Next ▶", on_click=go_next, disabled=(i >= total - 1))
        # with c3:
        #     st.button("Start Over", on_click=restart)

elif st.session_state.finished and (st.session_state.result_df is None or len(st.session_state.result_df) == 0):
    st.info("No items to display. Click 'Start Over' to try again.")
    st.button("Start Over", on_click=restart)
