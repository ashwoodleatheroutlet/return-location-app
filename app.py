import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# ---- Load CSV ----
df = pd.read_csv("Return Inventory File.csv", dtype=str)

df["Colour"] = df["Colour"].fillna("").str.title()

SEARCH_COLUMNS = ["EAN", "FashBCode"]
IMG_COL = "ImageURL"
DISPLAY_COLUMNS = ["Pick Location", "Style", "Colour", IMG_COL]

# ---- Session state ----
defaults = {
    "entered_barcodes": [],
    "text_input": "",
    "selected_style": "",
    "pending_style": "",
    "selected_colour": "",
    "finished": False,
    "result_df": None,
    "current_idx": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---- Add barcode ----
def add_item():
    text = st.session_state.text_input.strip()
    if text:
        st.session_state.entered_barcodes.append(text)
    st.session_state.text_input = ""

st.text_input("Scan or enter barcode:", key="text_input", on_change=add_item)

# ---- Style dropdown ----
style_options = (
    df["Style"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .sort_values()
    .tolist()
)

def style_selected():
    selected = st.session_state.selected_style.strip()
    if selected:
        st.session_state.pending_style = selected
    st.session_state.selected_style = ""

st.selectbox(
    "Or search by style:",
    options=[""] + style_options,
    key="selected_style",
    on_change=style_selected
)

# ---- Colour dropdown appears only after style selected ----
if st.session_state.pending_style:
    colour_options = (
        df.loc[
            df["Style"].astype(str).str.strip() == st.session_state.pending_style,
            "Colour"
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    def colour_selected():
        colour = st.session_state.selected_colour.strip()

        if colour:
            st.session_state.entered_barcodes.append(
                f"{st.session_state.pending_style}||{colour}"
            )

        st.session_state.pending_style = ""
        st.session_state.selected_colour = ""

    st.selectbox(
        f"Select colour for {st.session_state.pending_style}:",
        options=[""] + colour_options,
        key="selected_colour",
        on_change=colour_selected
    )

# ---- Finish button ----
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

    map1 = df[[SEARCH_COLUMNS[0]] + DISPLAY_COLUMNS].rename(
        columns={SEARCH_COLUMNS[0]: "Barcode"}
    )

    map2 = df[[SEARCH_COLUMNS[1]] + DISPLAY_COLUMNS].rename(
        columns={SEARCH_COLUMNS[1]: "Barcode"}
    )

    map3 = df[DISPLAY_COLUMNS].copy()
    map3["Barcode"] = (
        map3["Style"].astype(str).str.strip()
        + "||"
        + map3["Colour"].astype(str).str.strip()
    )

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
        .sort_values(["Pick Location", "Style", "Colour"], ascending=[True, True, True])
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

# ---- Navigation ----
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
    st.session_state.text_input = ""
    st.session_state.selected_style = ""
    st.session_state.pending_style = ""
    st.session_state.selected_colour = ""

def has_value(value):
    return pd.notna(value) and str(value).strip() != ""

# ---- Show current item ----
if st.session_state.finished and st.session_state.result_df is not None and len(st.session_state.result_df) > 0:
    total = len(st.session_state.result_df)
    i = st.session_state.current_idx
    row = st.session_state.result_df.iloc[i]

    left, right = st.columns([1, 2])

    with left:
        if has_value(row.get(IMG_COL)):
            st.image(str(row[IMG_COL]).strip())

    with right:
        if has_value(row.get("Style")):
            st.subheader(str(row["Style"]).strip())
        else:
            st.subheader("Style not found")

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