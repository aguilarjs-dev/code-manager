import streamlit as st
import pandas as pd
from datetime import datetime
import pytz 
import re
import json
from fpdf import FPDF
from streamlit_javascript import st_javascript

# 1. PAGE CONFIG
st.set_page_config(page_title="Code Manager Pro")

# --- LOCAL STORAGE HELPERS ---
def save_to_local(df):
    """Saves the current dataframe to the browser's localStorage."""
    json_data = df.to_json(orient='records')
    st_javascript(f"localStorage.setItem('code_manager_v1', '{json_data}');")

def load_from_local():
    """Retrieves data from the browser's localStorage."""
    result = st_javascript("localStorage.getItem('code_manager_v1');")
    if result and result != "null":
        try:
            return pd.DataFrame(json.loads(result))
        except:
            return None
    return None

# Helper for Philippine Time
def get_ph_time():
    ph_tz = pytz.timezone('Asia/Manila')
    return datetime.now(ph_tz)

# 2. PDF GENERATION FUNCTION
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    now_ph = get_ph_time()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="Code Management Report", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, txt=f"Generated: {now_ph.strftime('%Y-%m-%d %I:%M %p')}", ln=True, align='C')
    pdf.ln(5)

    # Summary Statistics
    total_codes = len(dataframe)
    claimed_count = len(dataframe[dataframe['Claimed'] == True])
    unclaimed_count = len(dataframe[dataframe['Claimed'] == False])

    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="REPORT SUMMARY", ln=True, align='L', fill=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(63, 10, txt=f"TOTAL: {total_codes}", border=1, align='C')
    pdf.cell(63, 10, txt=f"CLAIMED: {claimed_count}", border=1, align='C')
    pdf.cell(64, 10, txt=f"UNCLAIMED: {unclaimed_count}", border=1, ln=True, align='C')
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
    [data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    </style>
    """, unsafe_allow_html=True)

# 4. INITIALIZE SESSION STATE (Browser Sync)
if 'df_master' not in st.session_state:
    local_data = load_from_local()
    if local_data is not None:
        st.session_state['df_master'] = local_data
    else:
        st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])

# 5. DASHBOARD METRICS
st.title("🔢 Code Manager Pro")
m1, m2, m3 = st.columns(3)
total = len(st.session_state['df_master'])
claimed = len(st.session_state['df_master'][st.session_state['df_master']['Claimed'] == True])
unclaimed = total - claimed

m1.metric("Total Codes", total)
m2.metric("Claimed ✅", claimed, delta=f"{claimed/total*100:.1f}%" if total > 0 else None)
m3.metric("Unclaimed 📂", unclaimed)

# 6. AUTO-CLEANER HELPER
def extract_code(text):
    match = re.search(r'\b([A-Z0-9]{4})\b', str(text).upper())
    return match.group(1) if match else None

# 7. INPUTS
with st.expander("📥 Add Codes / Restore Backup", expanded=False):
    t1, t2 = st.tabs(["Upload & Clean", "Manual Entry"])
    with t1:
        u_file = st.file_uploader("Upload .txt, .xlsx, or .csv", type=['txt', 'xlsx', 'csv'])
        if u_file:
            if u_file.name.endswith('.csv'):
                df_backup = pd.read_csv(u_file, dtype={'Code': str})
                if 'Claimed' in df_backup.columns:
                    st.session_state['df_master'] = df_backup
                    save_to_local(st.session_state['df_master'])
                    st.toast("✅ Backup restored!")
            else:
                raw = pd.read_csv(u_file, header=None, dtype=str)[0] if u_file.name.endswith('.txt') else pd.read_excel(u_file, dtype=str).iloc[:, 0]
                cleaned = [extract_code(i) for i in raw if extract_code(i)]
                existing = st.session_state['df_master']['Code'].values
                unique = [c for c in set(cleaned) if c not in existing]
                if unique:
                    new_df = pd.DataFrame({'Code': unique, 'Claimed': False, 'Timestamp': ""})
                    st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_df], ignore_index=True)
                    save_to_local(st.session_state['df_master'])
                    st.toast(f"✅ Extracted {len(unique)} codes!")
                    st.rerun()
                elif not unique and len(cleaned) > 0:
                    st.info("All codes from file are already in the list.")
                else:
                    st.error("No 4-character codes found.")

    with t2:
        m_code = st.text_input("Manual 4-Char Code").strip().upper()
        if st.button("Add Code"):
            if len(m_code) == 4 and m_code not in st.session_state['df_master']['Code'].values:
                new_row = pd.DataFrame({'Code': [m_code], 'Claimed': [False], 'Timestamp': [""]})
                st.session_state['df_master'] = pd.concat([st.session_state['df_master'], new_row], ignore_index=True)
                save_to_local(st.session_state['df_master'])
                st.toast(f"✅ {m_code} added!")
                st.rerun()
            else:
                st.warning("Invalid code or already exists.")

# 8. SEARCH & SORT
st.divider()
c1, c2 = st.columns([3, 1])
search = c1.text_input("🔍 Search Codes", placeholder="Type to filter...").upper()
sort_opt = c2.selectbox("Sort Order", ["Default", "Alphabetical"])

df_disp = st.session_state['df_master'].copy()
if search: df_disp = df_disp[df_disp['Code'].str.contains(search)]
if sort_opt == "Alphabetical": df_disp = df_disp.sort_values("Code")

# 9. DISPLAY LISTS
u_df = df_disp[df_disp['Claimed'] == False]
c_df = df_disp[df_disp['Claimed'] == True]

st.subheader(f"📂 Unclaimed ({len(u_df)})")
for idx, row in u_df.iterrows():
    col1, col2, col3 = st.columns([2, 2, 1])
    col1.write(f"### {row['Code']}")
    if col2.button("Claim", key=f"c_{row['Code']}", type="primary", use_container_width=True):
        st.session_state['df_master'].at[idx, 'Claimed'] = True
        st.session_state['df_master'].at[idx, 'Timestamp'] = get_ph_time().strftime("%Y-%m-%d %I:%M %p")
        save_to_local(st.session_state['df_master'])
        st.rerun()
    if col3.button("🗑️", key=f"d_{row['Code']}", use_container_width=True):
        st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
        save_to_local(st.session_state['df_master'])
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
            save_to_local(st.session_state['df_master'])
            st.rerun()
        if cc4.button("🗑️", key=f"dc_{row['Code']}", use_container_width=True):
            st.session_state['df_master'] = st.session_state['df_master'].drop(idx)
            save_to_local(st.session_state['df_master'])
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# 10. BOTTOM ACTIONS
st.divider()
b1, b2, b3 = st.columns(3)
if not st.session_state['df_master'].empty:
    with b1:
        st.download_button("📄 PDF Report", data=create_pdf(st.session_state['df_master']), file_name="report.pdf", mime="application/pdf", use_container_width=True)
    with b2:
        csv_data = st.session_state['df_master'].to_csv(index=False).encode('utf-8')
        st.download_button("💾 Save Backup", data=csv_data, file_name="backup.csv", mime="text/csv", use_container_width=True)
    with b3:
        if st.button("🚨 Clear All", use_container_width=True):
            st.session_state['df_master'] = pd.DataFrame(columns=['Code', 'Claimed', 'Timestamp'])
            st_javascript("localStorage.removeItem('code_manager_v1');")
            st.rerun()
