import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# 1. PAGE CONFIG
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

# 2. PDF GENERATION FUNCTION (Must be defined at the top level)
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    
    # Title & Date
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="Code Management Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, txt=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(5)

    def add_table_section(title, data_subset, is_claimed):
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(40, 40, 40)
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
                time_val = str(row['Timestamp']) if is_claimed else "Available"
                pdf.cell(130, 8, time_val, 1, 1, 'C')
        pdf.ln(10)

    unclaimed = dataframe[dataframe['Claimed'] == False]
    claimed = dataframe[dataframe['Claimed'] == True]

    add_table_section("Unclaimed Codes", unclaimed, False)
    add_table_section("Claimed Codes", claimed, True)
    
    return pdf.output(dest='S').encode('latin-1')

# 3. CSS STYLING
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #28a745; color: white; }
    .row-container { padding: 10px; border-bottom: 1px solid #eee; margin: 0 !important; }
    .row-container h3 { margin-top: 0 !important; }
    .row-container:nth-child(odd) { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 4. SESSION STATE
if 'df_master' not in st.session_state:
    st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])

st.title("🔢 Code Manager")

# 5. INPUT SECTION
with st.expander("📥 Add Codes or Restore Backup", expanded=True):
    tab1, tab2 = st.tabs(["Upload File", "Manual Entry"])
    with tab1:
        uploaded_file = st.file_uploader("Upload .txt, .xlsx, or .csv backup", type=['txt', 'xlsx', 'csv'])
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file, dtype={'Code': str})
                if 'Claimed' in new_data.columns:
                    st.session_state['df_master'] = new_data
                    st.success("Backup restored!")
            else:
                if uploaded_file.name.endswith('.txt'):
                    raw_data = pd.read_csv(uploaded_file, header=None, dtype=str)[0]
                else:
                    raw_data = pd.read_excel(uploaded_file, dtype=str).iloc[:, 0]
                processed = raw_data.dropna().astype(str).str.upper().str.strip()
                new_codes = processed[processed.str.len() == 4].unique()
                existing = st.session_state['df_master']['Code'].values
                unique_new = [c for c in new_codes if c not in existing]
                if unique_new:
                    new_rows = pd.DataFrame({'Code': unique_new, 'Claimed': False, 'Timestamp': ""})
                    st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_rows], ignore_index=True)
                    st.rerun()

    with tab2:
        manual_code = st.text_input("Enter 4-character code:", max_chars=4)
        if st.button("Add Code"):
            formatted = manual_code.strip().upper()
            if len(formatted) == 4 and formatted not in st.session_state['df_master']['Code'].values:
                new_row = pd.DataFrame({'Code': [formatted], 'Claimed': [False], 'Timestamp': [""]})
                st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_row], ignore_index=True)
                st.rerun()

# 6. SEARCH & SORT
st.divider()
c1, c2 = st.columns([3, 1])
search = c1.text_input("🔍 Search", placeholder="Filter codes...").upper()
sort_opt = c2.selectbox("Sort", ["Default", "Alphabetical"])

df_disp = st.session_state['df_master'].copy()
if search: df_disp = df_disp[df_disp['Code'].str.contains(search)]
if sort_opt == "Alphabetical": df_disp = df_disp.sort_values("Code")

# 7. DISPLAY
u_df = df_disp[df_disp['Claimed'] == False]
c_df = df_disp[df_disp['Claimed'] == True]

st.subheader(f"📂 Unclaimed ({len(u_df)})")
for idx, row in u_df.iterrows():
    col1, col2, col3 = st.columns([2, 2, 1])
    col1.write(f"### {row['Code']}")
    if col2.button("Claim", key=f"c_{row['Code']}", type="primary", use_container_width=True):
        st.session_state['df_master'].at[idx, 'Claimed'] = True
        st.session_state['df_master'].at[idx, 'Timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()
    if col3.button("🗑️", key=f"d_{row['Code']}", use_container_width=True):
        st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.write("---")
st.subheader(f"✅ Claimed ({len(c_df)})")
with st.expander("History", expanded=True):
    for idx, row in c_df.iterrows():
        cc1, cc2, cc3, cc4 = st.columns([2, 3, 2, 1])
        cc1.write(f"**{row['Code']}**")
        cc2.write(f"`{row['Timestamp']}`")
        if cc3.button("Unclaim", key=f"u_{row['Code']}", use_container_width=True):
            st.session_state['df_master'].at[idx, 'Claimed'] = False
            st.session_state['df_master'].at[idx, 'Timestamp'] = ""
            st.rerun()
        if cc4.button("🗑️", key=f"dc_{row['Code']}", use_container_width=True):
            st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# 8. BOTTOM ACTIONS
st.divider()
b1, b2, b3 = st.columns(3)
if not st.session_state['df_master'].empty:
    with b1:
        st.download_button("📄 PDF Report", data=create_pdf(st.session_state['df_master']), file_name="report.pdf", mime="application/pdf", use_container_width=True)
    with b2:
        csv_backup = st.session_state['df_master'].to_csv(index=False).encode('utf-8')
        st.download_button("💾 Save Backup (CSV)", data=csv_backup, file_name="backup.csv", mime="text/csv", use_container_width=True)
    with b3:
        if st.button("🚨 Clear All", use_container_width=True):
            st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])
            st.rerun()
