"""
Aircraft Maintenance Reliability Dashboard
Streamlit web application for analyzing Work Orders from AMOS system
"""

import os
import json
from datetime import datetime
import streamlit as st
import pandas as pd
from io import BytesIO
import requests
import streamlit_authenticator as stauth
from analysis import (
    analyze_work_orders,
    get_red_flags,
    generate_recommendation,
    create_tic_tac_matrix,
    results_to_dataframe,
    get_conclusion_display,
    filter_data
)

# Page configuration
st.set_page_config(
    page_title="Reliability Analysis | Aircraft Maintenance",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication Configuration
# In a production environment, move these to streamlit secrets or a database
credentials = {
    'usernames': {
        'admin': {
            'name': 'VNA Engineer',
            'password': '$2b$12$R.S9iA57f7Lz7.6S.PzLQuS0wK.Yc8k8fW1Gv7C8b8b8b8b8b8b8' # This is a hash for 'vna1234'
        }
    }
}

# IMPORTANT: You need to hash passwords for streamlit-authenticator
# You can generate a hash using: stauth.Hasher(['vna1234']).generate()
# For this demo, let's use a simpler dictionary structure for stauth < 0.3.0 or update accordingly
# Let's use the standard configuration format for the latest version

authenticator = stauth.Authenticate(
    credentials,
    'vna_maintenance_v1',
    'vna_auth_key_2024',
    cookie_expiry_days=1
)

# UI/UX Pro Max - Premium Design System (CSS)
st.markdown("""
<style>
    /* Global Settings */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Main Background & Containers */
    .stApp {
        background-color: #0f172a; /* Slate 900 */
        background-image: radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
                          radial-gradient(at 100% 100%, rgba(239, 68, 68, 0.1) 0px, transparent 50%);
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.15);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f8fafc;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    h1 { font-size: 2.5rem; }
    h2 { font-size: 1.8rem; }
    h3 { font-size: 1.2rem; }
    
    /* Metrics */
    .metric-container {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    
    .metric-value {
        font-size: 2.25rem;
        font-weight: 800;
        background: linear-gradient(to right, #fff, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    
    .metric-label {
        color: #94a3b8; /* Slate 400 */
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    
    .metric-icon {
        font-size: 1.5rem;
        margin-bottom: 12px;
        padding: 10px;
        border-radius: 12px;
        display: inline-block;
    }
    
    /* Metric Color Variations */
    .icon-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
    .icon-red { background: rgba(239, 68, 68, 0.2); color: #f87171; }
    .icon-orange { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
    .icon-green { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    
    /* Recommendation Cards */
    .rec-card {
        background: rgba(30, 41, 59, 0.6); /* Slate 800/60 */
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    
    .rec-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .rec-badge {
        background: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .rec-title {
        color: #f8fafc;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .rec-body {
        color: #cbd5e1;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    /* Custom Components */
    .stSelectbox > div > div {
        background-color: rgba(30, 41, 59, 0.5);
        border-color: rgba(255,255,255,0.1);
        color: white;
    }
    
    /* Hide Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* header {visibility: hidden;} - Commented out to allow sidebar toggle */
    
    .block-container {
        padding-top: 2rem !important;
        max-width: 90rem; /* Wider container */
    }
    /* Add styling for connection status */
    .stStatusWidget {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def create_metric_card(value, label, icon="📊", color="blue"):
    """Create a premium styled metric card"""
    return f"""
    <div class="glass-card">
        <div class="metric-container">
            <div class="metric-icon icon-{color}">{icon}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
    </div>
    """

# --- COMMENT SYSTEM & GOOGLE SHEETS SYNC (VIA APPS SCRIPT) ---
COMMENTS_FILE = "technical_comments.csv"
DEFAULT_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwzhSN-4xqbovzj5q3zzx1vNR3X8nH4Fra60M78bZP66ea-gL1phwIDztz08eGA2TuEUA/exec"

def load_comments():
    """Load comments from local CSV"""
    if os.path.exists(COMMENTS_FILE):
        return pd.read_csv(COMMENTS_FILE)
    return pd.DataFrame(columns=['ID', 'Aircraft', 'ATA', 'History', 'Assessment', 'Recommendation', 'Comment', 'Timestamp', 'User'])

def sync_to_google_sheet(api_url, data_payload):
    """Send data to Google Apps Script Web App"""
    try:
        response = requests.post(api_url, json=data_payload)
        if response.status_code == 200:
            return True, "Synced success"
        else:
            return False, f"HTTP Error: {response.status_code}"
    except Exception as e:
        return False, f"Sync Error: {str(e)}"

def save_comment(result, rec_data, comment, user="Engineer", sheet_url=None):
    """Save comment to local CSV and optional Google Sheet via Web App"""
    df = load_comments()
    
    aircraft = result.aircraft
    ata = result.ata
    unique_id = f"{aircraft}_{ata}"
    
    history = rec_data.get('history_plain', '')
    assessment = rec_data.get('assessment', '')
    recommendation = rec_data.get('recommendation', '')
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update Local CSV
    row_data = {
        'ID': unique_id,
        'Aircraft': aircraft,
        'ATA': ata,
        'History': history,
        'Assessment': assessment,
        'Recommendation': recommendation,
        'Comment': comment,
        'Timestamp': timestamp,
        'User': user
    }
    
    mask = (df['ID'] == unique_id)
    if mask.any():
        for key, val in row_data.items():
            df.loc[mask, key] = val
    else:
        new_row = pd.DataFrame([row_data])
        df = pd.concat([df, new_row], ignore_index=True)
    
    df.to_csv(COMMENTS_FILE, index=False)
    
    # Sync to Google Sheet if connected
    if sheet_url:
        payload = {
            "id": unique_id,
            "aircraft": aircraft,
            "ata": ata,
            "history": history,
            "assessment": assessment,
            "recommendation": recommendation,
            "comment": comment,
            "timestamp": timestamp,
            "user": user
        }
        success, msg = sync_to_google_sheet(sheet_url, payload)
        if success:
            return True, "✅ Đã lưu Local & Google Sheet!"
        else:
            return True, f"✅ Đã lưu Local. ⚠️ Lỗi Sync: {msg}"
            
    return True, "✅ Đã lưu Local CSV!"

def get_comment_text(aircraft, ata):
    """Get specific comment text"""
    df = load_comments()
    # Support both old format (Aircraft, ATA) and new format (ID)
    if 'ID' in df.columns:
         mask = (df['ID'] == f"{aircraft}_{ata}")
    else:
         mask = (df['Aircraft'] == aircraft) & (df['ATA'] == ata)
         
    if mask.any():
        return df.loc[mask, 'Comment'].values[0]
    return ""

def create_recommendation_card_html(result, rec_data):
    """Return HTML string for recommendation card"""
    # Use the full_html from the dictionary
    html_content = rec_data.get('full_html', 'No content')
    
    return f"""
    <div class="rec-card">
        <div class="rec-card-header">
            <div class="rec-title">✈️ {result.aircraft} <span style="opacity:0.5; margin: 0 8px;">|</span> ATA {result.ata}</div>
            <span class="rec-badge">NGUY CƠ CAO</span>
        </div>
        <div class="rec-body">{html_content}</div>
    </div>
    """


@st.cache_data
def load_data(file):
    """Load Excel data with caching"""
    return pd.read_excel(file)

# Removed cache for analysis to ensure code updates (like new recommendation logic) are applied immediately
def run_analysis(df, exclude_s):
    """Run analysis (Caching disabled for development iterations)"""
    return analyze_work_orders(df, exclude_type_s=exclude_s)

def main():
    # Login widget
    try:
        name, authentication_status, username = authenticator.login('VNA Technical Login', 'main')
    except Exception as e:
        # Fallback for version differences or config errors
        st.error(f"Lỗi xác thực: {str(e)}")
        return

    if authentication_status == False:
        st.error('Username/password không chính xác.')
        return
    elif authentication_status == None:
        st.warning('Vui lòng đăng nhập để sử dụng công cụ.')
        st.info("💡 **Hệ thống nội bộ**: Vui lòng liên hệ Technical Department để cấp tài khoản.")
        return

    # Sidebar
    with st.sidebar:
        st.markdown(f"**Chào mừng, {name}!**")
        authenticator.logout('Đăng xuất', 'sidebar')
        st.markdown("---")
        
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 3rem; margin-bottom: 10px;">✈️</div>
            <h2 style="color: #C5A065; margin: 0; font-size: 1.8rem;">VNA Technical</h2>
            <p style="color: #e2e8f0; font-size: 0.9rem; margin-top: 5px;">Vietnam Airlines</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("📂 Upload Excel Data", type=['xlsx', 'xls'])
        
        st.markdown("---")
        
        # Options
        st.markdown("### ⚙️ Tùy chọn phân tích")
        exclude_s = st.toggle("Chỉ phân tích Hỏng hóc (Bỏ Type 'S')", value=True, help="Nếu bật, sẽ loại bỏ các dòng có Type là 'S' (Schedule) khỏi phân tích.")
        
        st.markdown("---")
        st.markdown("### ☁️ Google Sheet Sync")
        use_gsheet = st.toggle("Kết nối Google Sheet", value=True)
        
        apps_script_url = None
        if use_gsheet:
            apps_script_url = st.text_input("🔗 Link Apps Script Web App", value=DEFAULT_APPS_SCRIPT_URL, help="Paste URL của Web App triển khai từ Google Apps Script")
            if apps_script_url:
                st.success("✅ Ready to Sync!")
                st.link_button(
                    "📊 Mở Google Sheet",
                    "https://docs.google.com/spreadsheets/d/1Uy3znNoFTVoHl5xQHyQ54Sx70XUdlvDZmEWInK0Mgq0/edit?gid=0#gid=0",
                    use_container_width=True
                )
        
        st.info("💡 **Mẹo:** Khi app cập nhật, bấm **'Rerun'** ở góc phải màn hình để giữ lại dữ liệu, đừng F5.")

    # Main Content
    if uploaded_file is None:
        # Empty State / Landing
        landing_html = """
<div style="text-align: center; padding: 60px 20px;">
<h1 style="margin-bottom: 10px; color: #f1f5f9;">Công cụ phân tích Hỏng hóc</h1>
<h2 style="margin-bottom: 30px; color: #C5A065; font-weight: 400;">Technical Department - Vietnam Airlines</h2>
<p style="font-size: 1.1rem; color: #94a3b8; max-width: 700px; margin: 0 auto 50px auto;">
Hệ thống hỗ trợ đánh giá độ tin cậy tàu bay, phát hiện hỏng hóc lặp lại và theo dõi hiệu quả khắc phục.
</p>
<div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
<div class="glass-card" style="width: 250px; text-align: left;">
<div class="metric-icon icon-blue">&#9889;</div>
<h3 style="margin: 0 0 8px 0;">Nhanh chóng</h3>
<p style="color: #94a3b8; font-size: 0.9rem;">Xử lý hàng nghìn dòng dữ liệu trong tích tắc.</p>
</div>
<div class="glass-card" style="width: 250px; text-align: left;">
<div class="metric-icon icon-green">&#127919;</div>
<h3 style="margin: 0 0 8px 0;">Chính xác</h3>
<p style="color: #94a3b8; font-size: 0.9rem;">Thuật toán phân tích logic khắc phục thông minh.</p>
</div>
<div class="glass-card" style="width: 250px; text-align: left;">
<div class="metric-icon icon-red">&#128737;</div>
<h3 style="margin: 0 0 8px 0;">Cảnh báo</h3>
<p style="color: #94a3b8; font-size: 0.9rem;">Phát hiện sớm các hỏng hóc lặp lại tiềm ẩn.</p>
</div>
</div>
<div style="margin-top: 40px; color: #64748b;">
<p>👈 <b>Mở thanh menu bên trái để tải file dữ liệu</b></p>
</div>
</div>"""
        st.markdown(landing_html, unsafe_allow_html=True)
        return

    # Process Data
    try:
        df = load_data(uploaded_file)
        results = run_analysis(df, exclude_s)
        
        if not results:
            st.error("❌ Không thể đọc dữ liệu. Vui lòng kiểm tra format file.")
            return

        # Dashboard Header
        st.markdown(f"## 📊 Dashboard Phân Tích <span style='font-size: 1rem; color: #94a3b8; font-weight: normal; margin-left: 10px;'>({len(results)} chuỗi sự kiện)</span>", unsafe_allow_html=True)
        
        # Filters
        st.markdown('<div class="glass-card" style="padding: 15px 20px;">', unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns([1, 1, 3])
        
        df_filtered_raw = filter_data(df) # Just to get keys if needed, but we filter results directly
        
        aircraft_list = sorted(set(r.aircraft for r in results))
        ata_list = sorted(set(r.ata_2digit for r in results))
        
        with col_f1:
            selected_ac = st.selectbox("Tàu bay (A/C)", ['All'] + aircraft_list)
        with col_f2:
            selected_ata = st.selectbox("Hệ thống (ATA)", ['All'] + ata_list)
        st.markdown('</div>', unsafe_allow_html=True)

        # Apply logic
        filtered = results
        if selected_ac != 'All':
            filtered = [r for r in filtered if r.aircraft == selected_ac]
        if selected_ata != 'All':
            filtered = [r for r in filtered if r.ata_2digit == selected_ata]

        # Calculate Metrics
        total_wo = sum(r.wo_count for r in filtered)
        red_flags = get_red_flags(filtered)
        reset_cnt = len([r for r in filtered if r.conclusion == 'RESET_ONLY_REPEAT'])
        eff_cnt = len([r for r in filtered if r.conclusion == 'CORRECTIVE_OK'])

        # Display Metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.markdown(create_metric_card(total_wo, "Total Work Orders", "📝", "blue"), unsafe_allow_html=True)
        with m2: st.markdown(create_metric_card(len(red_flags), "Critical Issues", "🚨", "red"), unsafe_allow_html=True)
        with m3: st.markdown(create_metric_card(reset_cnt, "Reset Only", "⚠️", "orange"), unsafe_allow_html=True)
        with m4: st.markdown(create_metric_card(eff_cnt, "Fixed Effectively", "✅", "green"), unsafe_allow_html=True)

        # Tabbed View for Details
        tab1, tab2, tab3 = st.tabs(["🔴 Cảnh báo & Khuyến cáo", "📉 Ma trận Tổng quan", "📋 Dữ liệu chi tiết"])

        with tab1:
            if red_flags:
                st.markdown("### 🚨 Khuyến cáo kỹ thuật & Đánh giá")
                
                # Loop through red flags with index for unique keys
                for i, r in enumerate(red_flags):
                    rec_data = generate_recommendation(r) # Now returns dict
                    if rec_data:
                        # Create 2 columns: Recommendation Card (Left) - Comment (Right)
                        c1, c2 = st.columns([2, 1], gap="medium")
                        
                        with c1:
                            st.markdown(create_recommendation_card_html(r, rec_data), unsafe_allow_html=True)
                            
                        with c2:
                            # Comment handling
                            st.markdown(f"**📝 Ghi chú kỹ thuật**")
                            # Get existing comment
                            current_comment = get_comment_text(r.aircraft, r.ata)
                            
                            new_comment = st.text_area(
                                label="Nội dung đánh giá/Hành động",
                                value=current_comment,
                                height=150,
                                key=f"comment_{r.aircraft}_{r.ata}_{i}",
                                placeholder="Nhập đánh giá của kỹ sư, Link tài liệu, hoặc Link Google Sheet liên quan..."
                            )
                            
                            if st.button("💾 Lưu & Sync", key=f"btn_save_{r.aircraft}_{r.ata}_{i}"):
                                # Updated to pass apps_script_url
                                success, msg = save_comment(r, rec_data, new_comment, sheet_url=apps_script_url)
                                if success:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                        
                        st.markdown("---") # Separator
                        
            else:
                st.success("🎉 Không phát hiện cảnh báo nghiêm trọng nào trong dữ liệu được lọc.")

        with tab2:
            st.markdown("### Ma trận Reliability (A/C vs ATA)")
            
            # Get red flags for summary table
            red_flags_only = get_red_flags(filtered)
            
            if red_flags_only:
                # 1. Summary Table of Critical Issues (Red Flags)
                st.markdown("#### 🔴 Danh sách Hỏng hóc Nghiêm trọng")
                summary_data = []
                for r in red_flags_only:
                    summary_data.append({
                        "Aircraft": r.aircraft,
                        "ATA Chi tiết": r.ata,
                        "Hệ thống": r.ata_2digit,
                        "Số lần": r.wo_count,
                        "Kết luận": "Reset lặp lại" if r.conclusion == "RESET_ONLY_REPEAT" else "Corrective không hiệu quả"
                    })
                
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(
                    summary_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Aircraft": st.column_config.TextColumn("Tàu bay", width="small"),
                        "ATA Chi tiết": st.column_config.TextColumn("ATA Chi tiết", width="medium"),
                        "Hệ thống": st.column_config.TextColumn("Hệ thống", width="small"),
                        "Số lần": st.column_config.NumberColumn("Số lần", width="small"),
                        "Kết luận": st.column_config.TextColumn("Kết luận", width="large"),
                    }
                )
                
                st.markdown("---")
            
            st.markdown("Use the selectors below to view details for specific Aircraft and ATA.")
            
            matrix_df = create_tic_tac_matrix(filtered)
            
            if not matrix_df.empty:
                # 2. Display Matrix
                st.dataframe(
                    matrix_df.style.background_gradient(cmap='Reds', axis=None, vmin=0, vmax=5),
                    use_container_width=True,
                    height=400
                )
                
                st.markdown("---")
                st.markdown("### 🔎 Chi tiết sự kiện")
                
                # 2. Drill Down Selection
                # Get list of A/C and ATAs that are in the filtered results (Red Flags only mostly)
                red_flags_only = get_red_flags(filtered)
                
                if red_flags_only:
                    ac_options = sorted(list(set(r.aircraft for r in red_flags_only)))
                    
                    c_sel1, c_sel2 = st.columns(2)
                    with c_sel1:
                        sel_ac = st.selectbox("Chọn Tàu bay (A/C):", ac_options, key="matrix_ac_sel")
                    
                    # Filter ATAs for selected A/C
                    ata_options = sorted(list(set(r.ata_2digit for r in red_flags_only if r.aircraft == sel_ac)))
                    
                    with c_sel2:
                        sel_ata = st.selectbox("Chọn Hệ thống (ATA):", ata_options, key="matrix_ata_sel")
                    
                    # 3. Find and Display Details
                    selected_result = next((r for r in red_flags_only if r.aircraft == sel_ac and r.ata_2digit == sel_ata), None)
                    
                    if selected_result:
                        # Convert events to DataFrame for nice display
                        detail_data = []
                        for e in selected_result.events:
                            detail_data.append({
                                "Ngày": e.issued_date.strftime('%d/%m/%Y'),
                                "Số WO": e.wo,
                                "Type": e.wo_type,
                                "ATA": selected_result.ata,
                                "Mô tả": e.description,
                                "Hành động": e.action
                            })
                        
                        # Create DataFrame
                        df_details = pd.DataFrame(detail_data)
                        
                        # Rename for display
                        df_display = df_details.rename(columns={
                            "Mô tả": "Mô tả (Description)", 
                            "Hành động": "Hành động (Action)"
                        })

                        # custom HTML table for full text wrapping control
                        html_table = df_display.to_html(index=False, classes='detail-table', escape=True)
                        
                        # CSS and HTML must not be indented to avoid Markdown code block rendering
                        st.markdown(f"""
<style>
.detail-table {{ 
    width: 100%; 
    border-collapse: collapse; 
    color: #e2e8f0; 
    font-size: 0.9rem; 
    margin-bottom: 20px;
}}
.detail-table th {{ 
    background-color: #334155; 
    padding: 12px 10px; 
    text-align: left; 
    border: 1px solid #475569; 
    font-weight: 600;
}}
.detail-table td {{ 
    background-color: rgba(30, 41, 59, 0.4); 
    padding: 10px; 
    border: 1px solid #475569; 
    vertical-align: top; 
    white-space: pre-wrap; /* Text wrapping */
    word-wrap: break-word;
    line-height: 1.5;
}}
.detail-table tr:hover td {{
    background-color: rgba(51, 65, 85, 0.6);
}}
</style>
<div style="overflow-x: auto;">
{html_table}
</div>""", unsafe_allow_html=True)
                        
                        # Show recommendation as well
                        rec_dict = generate_recommendation(selected_result)
                        if rec_dict:
                            st.info(f"💡 **Đánh giá:** {rec_dict.get('assessment', '')}\n\n**Khuyến cáo:** {rec_dict.get('recommendation', '')}")
                    
                else:
                    st.info("Không có dữ liệu cảnh báo để hiển thị chi tiết.")

            else:
                st.info("Không có dữ liệu cho ma trận (Không có cảnh báo đỏ/cam).")

        with tab3:
            st.markdown("### Bảng tổng hợp chi tiết")
            summary_df = results_to_dataframe(filtered)
            
            def color_conclusion(val):
                color = 'white'
                if val == 'CORRECTIVE_NOT_EFFECTIVE': color = '#f87171'
                elif val == 'RESET_ONLY_REPEAT': color = '#fbbf24'
                elif val == 'CORRECTIVE_OK': color = '#34d399'
                return f'color: {color}'

            st.dataframe(
                summary_df.style.applymap(color_conclusion, subset=['Kết luận']),
                use_container_width=True,
                height=600
            )
            
            # Export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                summary_df.to_excel(writer, sheet_name='All Data', index=False)
                if red_flags:
                    rf_df = results_to_dataframe(red_flags)
                    rf_df['Khuyến cáo'] = [generate_recommendation(r).get('full_html', '') for r in red_flags]
                    rf_df.to_excel(writer, sheet_name='Warnings', index=False)
            output.seek(0)
            st.download_button("💾 Tải báo cáo Excel", output, "report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()
