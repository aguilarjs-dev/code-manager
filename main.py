import streamlit as st
import pandas as pd
from datetime import datetime
import pytz 
import re
from fpdf import FPDF

# 1. PAGE CONFIG
st.set_page_config(page_title="Code Manager")

# Helper for Philippine Time
def get_ph_time():
    ph_tz = pytz.timezone('Asia/Manila')
    return datetime.now(ph_tz)

# 2. PDF GENERATION FUNCTION
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    now_ph = get_ph_time()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="Code Management Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, txt=f"Generated: {now_ph.strftime('%Y-%m-%d %I:%M %p')}", ln=True, align='C')
    pdf.ln(5)

    total_codes = len(dataframe)
    claimed_count = len(dataframe[dataframe['Claimed'] == True])
    unclaimed_count = len(dataframe[dataframe['Claimed'] == False])

    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="REPORT SUMMARY", ln=True, align='L', fill=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(63, 10, txt=f"TOTAL: {total_codes}", border=1, align='C')
    pdf.set_text_color(40, 167, 69)
    pdf.cell(63, 10, txt=f"CLAIMED: {claimed_count}", border=1, align='C')
    pdf.set_text_color(220, 53, 69)
    pdf.cell(64, 10, txt=f"UNCLAIMED: {unclaimed_count}", border=1, ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    def add_table_section(title, data_subset, is_claimed):
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, txt=f"{title} ({len(data_subset)})", ln=True, align='L')
        pdf.set_fill_color(230, 230, 230) 
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(60, 8, "Code", 1, 0, 'C', 1)
        pdf.cell(130, 8, "Timestamp", 1, 1, 'C', 1)
        pdf.set_font("Arial", size=10)
        if data_subset.empty:
            pdf.cell(190, 8, "No records found", 1, 1, 'C')
        else:
            for _, row in data_subset.iterrows():
                pdf.cell(60, 8, str(row['Code']), 1, 0, 'C')
                time_val = str(row['Timestamp']) if is_claimed else "Available"
                pdf.cell(130, 8, time_val, 1, 1, 'C')
        pdf.ln(10)

    add_table_section("Unclaimed Codes", dataframe[dataframe['Claimed'] == False], False)
    add_table_section("Claimed Codes", dataframe[dataframe['Claimed'] == True], True)
    return pdf.output(dest='S').encode('latin-1')

# 3. CSS
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] { background-color: #28a745; color: white; }
    .row-container { padding: 15px 10px; border-bottom: 1px solid #eee; margin: 0 !important; }
    .row-container h3 { margin-top: 0 !important; }
    .row-container:nth-child(odd) { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# 4. SESSION STATE
if 'df_master' not in st.session_state:
    st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])

st.title("🔢 Code Manager")

# 5. AUTO-CLEANER FUNCTION
def extract_code(text):
    # This looks for any 4-character alphanumeric word in the string
    match = re.search(r'\b([A-Z0-9]{4})\b', str(text).upper())
    return match.group(1) if match else None

# 6. INPUT SECTION
with st.expander("📥 Add Codes / Restore Backup", expanded=True):
    tab1, tab2 = st.tabs(["Upload & Clean", "Manual Entry"])
    
    with tab1:
        u_file = st.file_uploader("Upload .txt, .xlsx, or .csv backup", type=['txt', 'xlsx', 'csv'])
        if u_file:
            if u_file.name.endswith('.csv'):
                # Handle direct backup restores
                new_data = pd.read_csv(u_file, dtype={'Code': str})
                if 'Claimed' in new_data.columns:
                    st.session_state['df_master'] = new_data
                    st.toast("✅ Backup restored!")
            else:
                # Handle "Dirty" data extraction (TXT or XLSX)
                if u_file.name.endswith('.txt'):
                    raw = pd.read_csv(u_file, header=None, dtype=str)[0]
                else:
                    raw = pd.read_excel(u_file, dtype=str).iloc[:, 0]
                
                # Apply the cleaner to every row
                cleaned_list = [extract_code(item) for item in raw if extract_code(item)]
                existing = st.session_state['df_master']['Code'].values
                unique_new = [c for c in set(cleaned_list) if c not in existing]
                
                # --- FIXED LOGIC BLOCK ---
                if unique_new:
                    new_rows = pd.DataFrame({'Code': unique_new, 'Claimed': False, 'Timestamp': ""})
                    st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_rows], ignore_index=True)
                    st.toast(f"✅ Extracted {len(unique_new)} codes!")
                    st.rerun() # This stops the rest of the code from showing the "No new codes" message
                
                # This only runs if unique_new was empty
                elif not unique_new and len(cleaned_list) > 0:
                    st.info("All codes in this file are already in your list.")
                else:
                    st.info("No 4-character codes found in this file.")
                # -------------------------

    with tab2:
        m_code = st.text_input("Enter 4-character code:", max_chars=4).strip().upper()
        if st.button("Add Code"):
            if len(m_code) == 4:
                if m_code not in st.session_state['df_master']['Code'].values:
                    new_row = pd.DataFrame({'Code': [m_code], 'Claimed': [False], 'Timestamp': [""]})
                    st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_row], ignore_index=True)
                    st.toast(f"✅ Code {m_code} added!")
                    st.rerun()
                else:
                    st.error("Code already exists!")
            else:
                st.warning("Must be 4 characters.")

# 7. SEARCH & SORT
st.divider()
c1, c2 = st.columns([3, 1])
search = c1.text_input("🔍 Search Codes", placeholder="Type to filter...").upper()
sort_opt = c2.selectbox("Sort Order", ["Default", "Alphabetical"])

df_disp = st.session_state['df_master'].copy()
if search: 
    df_disp = df_disp[df_disp['Code'].str.contains(search)]
if sort_opt == "Alphabetical": 
    df_disp = df_disp.sort_values("Code")

# 8. DISPLAY
u_df = df_disp[df_disp['Claimed'] == False]
c_df = df_disp[df_disp['Claimed'] == True]

st.subheader(f"📂 Unclaimed ({len(u_df)})")
for idx, row in u_df.iterrows():
    col1, col2, col3 = st.columns([2, 2, 1])
    col1.write(f"### {row['Code']}")
    if col2.button("Claim", key=f"c_{row['Code']}", type="primary", use_container_width=True):
        st.session_state['df_master'].at[idx, 'Claimed'] = True
        st.session_state['df_master'].at[idx, 'Timestamp'] = get_ph_time().strftime("%Y-%m-%d %I:%M %p")
        st.rerun()
    if col3.button("🗑️", key=f"d_{row['Code']}", use_container_width=True):
        st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.write("---")
st.subheader(f"✅ Claimed ({len(c_df)})")
with st.expander("History Log", expanded=True):
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

# 9. BOTTOM ACTIONS
st.divider()
b1, b2, b3 = st.columns(3)
if not st.session_state['df_master'].empty:
    with b1:
        st.download_button("📄 PDF Report", data=create_pdf(st.session_state['df_master']), file_name="report.pdf", mime="application/pdf", use_container_width=True)
    with b2:
        csv_backup = st.session_state['df_master'].to_csv(index=False).encode('utf-8')
        st.download_button("💾 Save Backup", data=csv_backup, file_name="backup.csv", mime="text/csv", use_container_width=True)
    with b3:
        if st.button("🚨 Clear All", use_container_width=True):
            st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])
            st.rerun()
