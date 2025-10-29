import streamlit as st
import pandas as pd

# hide_streamlit_elements = """
#     <style>
#     /* Hide main menu (hamburger) */
#     #MainMenu {visibility: hidden;}

#     /* Hide footer */
#     footer {visibility: hidden;}
#     footer:after {content:""; display:none;}

#     /* Hide Streamlit badge and "share" GitHub button */
#     .viewerBadge_link__1S137 {display: none !important;}
#     .stDeployButton {display: none !important;}
#     iframe[title="streamlit footer"] {display: none !important;}
#     div[data-testid="stDecoration"] {display: none !important;}
#     div[data-testid="stStatusWidget"] {display: none !important;}
#     div[data-testid="stToolbar"] {display: none !important;}

#     /* Hide beta share button container */
#     div[class*="st-emotion-cache"] a[href*="github.com"] {
#         display: none !important;
#     }
#     </style>
# """

# st.markdown(hide_streamlit_elements, unsafe_allow_html=True)

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
)

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ---- Load your CSV ----
df = pd.read_csv('Return Inventory File.csv', dtype=str)

# Example assumptions:
SEARCH_COLUMNS = ['EAN', 'FashBCode']
DISPLAY_COLUMNS = ['Pick Location', 'Style']

# ---- Initialize session state ----
if "entered_barcodes" not in st.session_state:
    st.session_state["entered_barcodes"] = []
if "text_input" not in st.session_state:
    st.session_state["text_input"] = ""
if "finished" not in st.session_state:
    st.session_state["finished"] = False

# ---- Add barcode function ----
def add_item():
    text = st.session_state.text_input.strip()
    if text:
        st.session_state.entered_barcodes.append(text)
    st.session_state.text_input = ""  # clear input

# ---- Input box ----
st.text_input(
    "Scan or enter barcode:",
    key="text_input",
    on_change=add_item
)

# ---- Show currently entered barcodes ----
# if st.session_state.entered_barcodes:
    # st.write("**Barcodes entered:**", len(st.session_state.entered_barcodes))
    # st.write(st.session_state.entered_barcodes)

# ---- Finish button ----
if st.button("Finish"):
    st.session_state["finished"] = True

# ---- Only build dataframe after Finish is clicked ----
if st.session_state["finished"]:
    barcodes = st.session_state.entered_barcodes

    # 1) Count how many times each barcode was entered
    entered_counts = (
        pd.Series(barcodes, name="Barcode")
        .value_counts()
        .rename_axis("Barcode")
        .reset_index(name="Count")
    )

    # 2) Build a lookup table: Barcode -> (ProductName, Location)
    #    (adjust DISPLAY_COLUMNS / SEARCH_COLUMNS to your real names)
    map1 = df[[SEARCH_COLUMNS[0]] + DISPLAY_COLUMNS].rename(columns={SEARCH_COLUMNS[0]: "Barcode"})
    map2 = df[[SEARCH_COLUMNS[1]] + DISPLAY_COLUMNS].rename(columns={SEARCH_COLUMNS[1]: "Barcode"})
    mapping = pd.concat([map1, map2], ignore_index=True).dropna(subset=["Barcode"]).drop_duplicates()

    # 3) Join counts to mapping
    merged = entered_counts.merge(mapping, on="Barcode", how="left")

    # 4) Final summary: total count per (ProductName, Location)
    result_df = (
        merged.groupby(DISPLAY_COLUMNS, dropna=False)["Count"]
        .sum()
        .reset_index()
        .sort_values("Pick Location", ascending=True)
    )
    result_df.set_index(result_df.columns[0], inplace=True)
    st.success("Return List:")
    st.dataframe(result_df)

    # (Optional) show barcodes not found in the file
    not_found = merged[merged[DISPLAY_COLUMNS[0]].isna()]["Barcode"].unique().tolist()
    if not_found:
        st.warning(f"Barcodes not found: {not_found}")