import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Code Manager", layout="wide")

# --- CUSTOM CSS FOR STRIPED ROWS & GREEN BUTTONS ---
st.markdown("""
    <style>
    /* Green Claim Button */
    div.stButton > button[kind="primary"] {
        background-color: #28a745;
        color: white;
        border-color: #28a745;
    }
    /* Striped Row Effect */
    .row-container {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }
    .row-container:nth-child(odd) {
        background-color: #f1f3f6;
    }
    .row-container:nth-child(even) {
        background-color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'df_master' not in st.session_state:
    st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])

st.title("🔢 Code Manager")

# --- 1. DATA INPUT SECTION ---
with st.expander("📥 Add Codes or Restore Backup", expanded=True):
    tab1, tab2 = st.tabs(["Upload File (New or Backup)", "Manual Entry"])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload .txt, .xlsx, or .csv backup", type=['txt', 'xlsx', 'csv'])
        if uploaded_file:
            # Handle Backup CSVs
            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file, dtype={'Code': str})
                # Check if this is one of our backup files
                if 'Claimed' in new_data.columns:
                    st.session_state['df_master'] = new_data
                    st.success("✅ Backup restored successfully!")
                else:
                    # Treat as a regular list of codes
                    processed_codes = new_data.iloc[:, 0].dropna().astype(str).str.upper().str.strip()
                    # (Add logic to merge codes here)
            
            # Handle TXT or XLSX
            else:
                if uploaded_file.name.endswith('.txt'):
                    raw_data = pd.read_csv(uploaded_file, header=None, dtype=str)[0]
                else:
                    raw_data = pd.read_excel(uploaded_file, dtype=str).iloc[:, 0]
                
                processed = raw_data.dropna().astype(str).str.upper().str.strip()
                new_codes = processed[processed.str.len() == 4].unique()
                
                existing_codes = st.session_state['df_master']['Code'].values
                unique_new = [c for c in new_codes if c not in existing_codes]
                
                if unique_new:
                    new_rows = pd.DataFrame({'Code': unique_new, 'Claimed': False, 'Timestamp': ""})
                    st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_rows], ignore_index=True)
                    st.success(f"Added {len(unique_new)} new codes.")

# --- 2. SEARCH & SORT CONTROLS ---
st.divider()
ctrl_col1, ctrl_col2 = st.columns([3, 1])
with ctrl_col1:
    search_term = st.text_input("🔍 Search All Tables", placeholder="Type code to filter...").upper()
with ctrl_col2:
    sort_option = st.selectbox("Sort Order", ["Default", "Alphabetical (A-Z)"])

df = st.session_state['df_master'].copy()
if search_term:
    df = df[df['Code'].str.contains(search_term)]
if sort_option == "Alphabetical (A-Z)":
    df = df.sort_values(by="Code")

unclaimed_df = df[df['Claimed'] == False]
claimed_df = df[df['Claimed'] == True]

# --- 3. DISPLAY TABLES ---
st.subheader(f"📂 Unclaimed Codes ({len(unclaimed_df)})")
if not unclaimed_df.empty:
    for idx, row in unclaimed_df.iterrows():
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.write(f"### {row['Code']}")
        if c2.button("Claim", key=f"claim_{row['Code']}", type="primary", use_container_width=True):
            st.session_state['df_master'].at[idx, 'Claimed'] = True
            st.session_state['df_master'].at[idx, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()
        if c3.button("🗑️", key=f"del_un_{row['Code']}", use_container_width=True):
            st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("No unclaimed codes found.")

st.write("---")

st.subheader(f"✅ Claimed Codes ({len(claimed_df)})")
if not claimed_df.empty:
    with st.expander("View Claimed History", expanded=True):
        for idx, row in claimed_df.iterrows():
            cc1, cc2, cc3, cc4 = st.columns([2, 3, 2, 1])
            cc1.write(f"**{row['Code']}**")
            cc2.write(f"`{row['Timestamp']}`")
            if cc3.button("Unclaim", key=f"reset_{row['Code']}", use_container_width=True):
                st.session_state['df_master'].at[idx, 'Claimed'] = False
                st.session_state['df_master'].at[idx, 'Timestamp'] = ""
                st.rerun()
            if cc4.button("🗑️", key=f"del_cl_{row['Code']}", use_container_width=True):
                st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- 4. BOTTOM ACTIONS & PDF GENERATION ---
st.divider()
bot_col1, bot_col2, bot_col3 = st.columns(3)

with bot_col1:
    if not st.session_state['df_master'].empty:
        pdf_bytes = create_pdf(st.session_state['df_master'])
        st.download_button("📄 Download PDF", data=pdf_bytes, file_name="report.pdf", mime="application/pdf", use_container_width=True)

with bot_col2:
    if not st.session_state['df_master'].empty:
        # We ensure the CSV is clean and matches our expected structure
        csv_data = st.session_state['df_master'].to_csv(index=False).encode('utf-8')
        st.download_button("💾 Save Backup (CSV)", data=csv_data, file_name=f"backup_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)

with bot_col3:
    if st.button("🚨 Clear All", use_container_width=True):
        st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])
        st.rerun()
