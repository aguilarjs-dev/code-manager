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
with st.expander("📥 Add Codes (File or Manual)", expanded=True):
    tab1, tab2 = st.tabs(["Upload File", "Manual Entry"])
    with tab1:
        uploaded_file = st.file_uploader("Upload .txt or .xlsx", type=['txt', 'xlsx'])
        if uploaded_file:
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

    with tab2:
        manual_code = st.text_input("Enter 4-character code:", max_chars=4)
        if st.button("Add Code"):
            formatted = manual_code.strip().upper()
            if len(formatted) != 4:
                st.error("❌ Code must be exactly 4 characters.")
            elif formatted in st.session_state['df_master']['Code'].values:
                st.warning(f"⚠️ Code {formatted} already exists.")
            else:
                new_row = pd.DataFrame({'Code': [formatted], 'Claimed': [False], 'Timestamp': [""]})
                st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_row], ignore_index=True)
                st.toast(f"✅ Code {formatted} added!")

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
bot_col1, bot_col2 = st.columns(2)

def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    
    # Title & Date
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="Code Management Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, txt=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(5)

    # Helper function to create table sections
    def add_table_section(title, data_subset, is_claimed):
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(40, 40, 40)
        # EMOJIS REMOVED HERE to prevent Latin-1 encoding errors
        pdf.cell(190, 10, txt=title, ln=True, align='L')
        
        # Table Header
        pdf.set_fill_color(230, 230, 230) 
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(60, 8, "Code", 1, 0, 'C', 1)
        pdf.cell(130, 8, "Timestamp / Status", 1, 1, 'C', 1)

        # Table Body
        pdf.set_font("Arial", size=10)
        pdf.set_text_color(0, 0, 0)
        
        if data_subset.empty:
            pdf.cell(190, 8, "No codes in this section", 1, 1, 'C')
        else:
            for _, row in data_subset.iterrows():
                pdf.cell(60, 8, str(row['Code']), 1, 0, 'C')
                time_val = str(row['Timestamp']) if is_claimed else "-"
                pdf.cell(130, 8, time_val, 1, 1, 'C')
        pdf.ln(10)

    # Filter data
    unclaimed = dataframe[dataframe['Claimed'] == False]
    claimed = dataframe[dataframe['Claimed'] == True]

    # Add Sections - Removed Emojis from these strings
    add_table_section("Unclaimed Codes", unclaimed, False)
    add_table_section("Claimed Codes", claimed, True)
    
    # Use 'latin-1' or 'utf-8' carefully. FPDF1.7 standard is latin-1 for core fonts.
    return pdf.output(dest='S').encode('latin-1')

with bot_col1:
    if not st.session_state['df_master'].empty:
        pdf_bytes = create_pdf(st.session_state['df_master'])
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"Code_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

with bot_col2:
    if st.button("🚨 Clear All Codes", use_container_width=True):
        st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])
        st.rerun()