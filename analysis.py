"""
Aircraft Maintenance Work Order Analysis Module
Analyzes Work Orders from AMOS system to identify recurring failures and remediation effectiveness
"""

import pandas as pd
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime


# Keywords for classification
RESET_KEYWORDS = [
    'reset', 'ops test', 'operational test', 'op test', 'bite test',
    'reset cb', 'recycle', 'power reset', 'system reset'
]

CORRECTIVE_KEYWORDS = [
    'replace', 'replaced', 'replacement', 'rpl', 
    'change', 'changed', 'installation', 'install', 'installed',
    'repair', 'repaired', 'fix', 'fixed',
    'rectify', 'rectified', 'wiring', 'rewire', 'rewired', 'chaffing', 'chafing',
    'adjust', 'adjusted', 'modification', 'modified', 'mod',
    'swap', 'swapped'
]

# ATA prefixes to exclude
EXCLUDED_ATA_PREFIXES = ['25', '33', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59']


@dataclass
class WorkOrderEvent:
    """Represents a single work order event"""
    wo: str
    description: str
    action: str
    action_type: str
    wo_type: str
    issued_date: datetime


@dataclass
class AnalysisResult:
    """Represents analysis result for an A/C + ATA combination"""
    aircraft: str
    ata: str
    ata_2digit: str
    wo_count: int
    conclusion: str
    dates: List[str]
    timeline_summary: str
    events: List[WorkOrderEvent]


def get_ata_2digit(ata: str) -> str:
    """Extract 2-digit ATA code from full ATA (xx-xx format)"""
    if pd.isna(ata):
        return ""
    ata_str = str(ata).strip()
    # Handle formats: "21-23", "21", "2123"
    if '-' in ata_str:
        return ata_str.split('-')[0]
    return ata_str[:2] if len(ata_str) >= 2 else ata_str


def format_ata(ata: str) -> str:
    """Ensure ATA is in xx-xx format"""
    if pd.isna(ata):
        return ""
    ata_str = str(ata).strip().replace(" ", "")
    
    # Already in correct format
    if '-' in ata_str:
        return ata_str
    
    # Convert 4-digit to xx-xx
    if len(ata_str) == 4 and ata_str.isdigit():
        return f"{ata_str[:2]}-{ata_str[2:]}"
    
    # 2-digit - just return as is with -00
    if len(ata_str) == 2:
        return f"{ata_str}-00"
    
    return ata_str


def extract_ata_from_text(description: str, action: str, original_ata: str) -> str:
    """
    Extract ATA code from task references in W/O description or action text.
    
    Priority order:
    1. TSM/AFI/FIM references
    2. IPC/IPD references  
    3. AMM/SRM/CMM references
    4. Original ATA if no reference found
    
    Args:
        description: W/O Description text
        action: W/O Action text
        original_ata: Original ATA value from data
        
    Returns:
        Corrected ATA in xx-xx format
    """
    # Combine both texts for searching
    combined_text = f"{str(description)} {str(action)}" if not pd.isna(description) and not pd.isna(action) else ""
    combined_text = combined_text.upper()
    
    # Define reference patterns with priority
    # Pattern: (keyword)(optional: colon/task/space)(ATA pattern like 72-32-86 or 7232)
    reference_patterns = {
        'high': ['TSM', 'AFI', 'FIM'],
        'medium': ['IPC', 'IPD'],
        'low': ['AMM', 'SRM']
    }
    
    # ATA pattern: captures xx-xx or xxxx at start of reference number
    # Example: "72-32-86-..." -> captures "72-32"
    # Example: "723286..." -> captures "7232"
    ata_pattern = r'(\d{2}[-]?\d{2})'
    
    found_atas = {'high': [], 'medium': [], 'low': []}
    
    for priority, keywords in reference_patterns.items():
        for keyword in keywords:
            # Pattern variations: "TSM:", "TSM TASK", "TSM 72-32", etc.
            patterns = [
                rf'{keyword}\s*:\s*{ata_pattern}',
                rf'{keyword}\s+TASK\s+{ata_pattern}',
                rf'{keyword}\s+{ata_pattern}',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, combined_text)
                if matches:
                    for match in matches:
                        # Clean up the match
                        ata_code = match.replace(' ', '').replace('-', '')
                        if len(ata_code) >= 4 and ata_code.isdigit():
                            # Format as xx-xx
                            formatted = f"{ata_code[:2]}-{ata_code[2:4]}"
                            found_atas[priority].append(formatted)
    
    # Return based on priority
    if found_atas['high']:
        return found_atas['high'][0]
    elif found_atas['medium']:
        return found_atas['medium'][0]
    elif found_atas['low']:
        return found_atas['low'][0]
    else:
        # No reference found, use original ATA
        return format_ata(original_ata)



def classify_action(action: str) -> str:
    """
    Classify W/O Action into categories:
    - RESET_ONLY: temporary fixes (reset, ops test, etc.)
    - CORRECTIVE_ACTION: permanent fixes (replace, repair, etc.)
    - UNKNOWN: unclassified
    """
    if pd.isna(action):
        return "UNKNOWN"
    
    action_lower = str(action).lower()
    
    # Check for corrective keywords first (higher priority)
    for keyword in CORRECTIVE_KEYWORDS:
        if keyword in action_lower:
            return "CORRECTIVE_ACTION"
    
    # Check for reset keywords
    for keyword in RESET_KEYWORDS:
        if keyword in action_lower:
            return "RESET_ONLY"
    
    return "UNKNOWN"


def should_exclude_ata(ata: str) -> bool:
    """Check if ATA should be excluded from analysis"""
    ata_2digit = get_ata_2digit(ata)
    return ata_2digit in EXCLUDED_ATA_PREFIXES


def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    """Filter out excluded ATA codes and clean data"""
    # Create a copy
    df = df.copy()
    
    # Ensure ATA column exists
    if 'ATA' not in df.columns:
        return df
    
    # Filter out excluded ATAs
    mask = ~df['ATA'].apply(should_exclude_ata)
    df_filtered = df[mask].copy()
    
    # Format ATA to xx-xx
    df_filtered['ATA_Formatted'] = df_filtered['ATA'].apply(format_ata)
    df_filtered['ATA_2Digit'] = df_filtered['ATA'].apply(get_ata_2digit)
    
    return df_filtered


def create_timeline_summary(events: List[WorkOrderEvent]) -> str:
    """Create a timeline summary of events"""
    summaries = []
    for event in events:
        date_str = event.issued_date.strftime('%d/%m') if isinstance(event.issued_date, datetime) else str(event.issued_date)[:5]
        desc_short = event.description[:50] + '...' if len(str(event.description)) > 50 else event.description
        action_short = event.action[:30] + '...' if len(str(event.action)) > 30 else event.action
        type_str = f"[{event.wo_type}]" if event.wo_type else ""
        summaries.append(f"{date_str} {type_str}: {desc_short} → {action_short}")
    return "; ".join(summaries)


def determine_conclusion(events: List[WorkOrderEvent]) -> str:
    """
    Determine conclusion based on events:
    - SINGLE_EVENT: Only 1 WO
    - RESET_ONLY_REPEAT: ≥2 WO with all RESET_ONLY actions
    - CORRECTIVE_OK: Has CORRECTIVE and no recurrence after (strictly later date)
    - CORRECTIVE_NOT_EFFECTIVE: Has CORRECTIVE but recurrence strictly after (later date)
    """
    if len(events) == 1:
        return "SINGLE_EVENT"
    
    action_types = [e.action_type for e in events]
    
    # Check if all are reset only or unknown (no corrective)
    has_corrective = any(t == "CORRECTIVE_ACTION" for t in action_types)
    
    if not has_corrective:
        return "RESET_ONLY_REPEAT"
    
    # Logic change based on user feedback:
    # "If same day: warning -> fix (effective)"
    # Recurrence is only if event date > last corrective action date
    
    # Find the LAST corrective action event (by date/order)
    last_corrective_event = None
    for e in events:
        if e.action_type == "CORRECTIVE_ACTION":
            last_corrective_event = e
            
    # Should not happen given has_corrective check, but safety first
    if not last_corrective_event: 
        return "RESET_ONLY_REPEAT"
        
    last_corrective_date = last_corrective_event.issued_date.date()
    
    # Check for any event strictly AFTER the last corrective date
    for e in events:
        if e.issued_date.date() > last_corrective_date:
            return "CORRECTIVE_NOT_EFFECTIVE"
    
    return "CORRECTIVE_OK"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to standard expected format:
    - ATA, A/C, WO, W/O Action, Issued, W/O Description, ATA Description
    """
    df.columns = [str(c).strip() for c in df.columns]
    
    # Mapping dictionary (lowercase/variation -> standard)
    column_mapping = {
        'a/c': 'A/C',
        'aircraft': 'A/C',
        'ac': 'A/C',
        'ata': 'ATA',
        'ata chapter': 'ATA',
        'wo': 'WO',
        'work order': 'WO',
        'workorder': 'WO',
        'w/o': 'WO',
        'w/o action': 'W/O Action',
        'work order action': 'W/O Action',
        'action': 'W/O Action',
        'w/o_action': 'W/O Action',
        'issued': 'Issued',
        'issue date': 'Issued',
        'date issued': 'Issued',
        'issue_date': 'Issued',
        'issued_date': 'Issued',
        'w/o description': 'W/O Description',
        'work order description': 'W/O Description',
        'description': 'ATA Description',
        'w/o_description': 'W/O Description',
        'desc': 'ATA Description',
        'type': 'Type',
        'wo type': 'Type',
        'work type': 'Type',
        'wo_type': 'Type',
        'w/o_type': 'Type',
        'record_type': 'Type'
    }
    
    new_columns = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in column_mapping:
            standard_col = column_mapping[col_lower]
            # Prioritize if exact match doesn't exist or overwriting generic 'description'
            if standard_col not in new_columns:
                 new_columns[standard_col] = col
            elif col_lower == 'w/o description': # Priority for specific description
                 new_columns[standard_col] = col
                 
    # Rename columns that were found
    rename_map = {v: k for k, v in new_columns.items()}
    df_normalized = df.rename(columns=rename_map)
    
    return df_normalized


def analyze_work_orders(df: pd.DataFrame, exclude_type_s: bool = False) -> List[AnalysisResult]:
    """Main analysis function - analyze all work orders"""
    results = []
    
    # Normalize columns first
    df = normalize_columns(df)
    
    # Filter Schedule type if requested
    if exclude_type_s and 'Type' in df.columns:
        # Convert to string and strip whitespace for robust comparison
        df = df[df['Type'].astype(str).str.strip().str.upper() != 'S']
    
    # Ensure required columns exist
    required_cols = ['A/C', 'ATA', 'W/O Action', 'Issued']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        # Return empty list, let the app handle the error message based on checking results
        # Or printed to console for debug
        print(f"Missing columns: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        return results
    
    # Filter data
    df_filtered = filter_data(df)
    
    if df_filtered.empty:
        return results
    
    # Convert Issued to datetime
    df_filtered['Issued_Date'] = pd.to_datetime(df_filtered['Issued'], errors='coerce')
    
    # === ATA CORRECTION LOGIC ===
    # Extract corrected ATA from task references in description/action text
    # We now check W/O Description, ATA Description (as fallback) and W/O Action
    df_filtered['ATA Corrected'] = df_filtered.apply(
        lambda row: extract_ata_from_text(
            str(row.get('W/O Description', '')) + " " + str(row.get('ATA Description', '')),
            row.get('W/O Action', ''),
            row.get('ATA', '')
        ),
        axis=1
    )
    
    # Create ATA02 column (2-digit ATA from corrected ATA)
    df_filtered['ATA02'] = df_filtered['ATA Corrected'].apply(get_ata_2digit)
    
    # Use corrected ATA for grouping
    grouped = df_filtered.groupby(['A/C', 'ATA Corrected'])

    
    for (aircraft, ata), group in grouped:
        # Sort by issued date
        group_sorted = group.sort_values('Issued_Date')
        
        # Create events list
        events = []
        for _, row in group_sorted.iterrows():
            action_type = classify_action(row.get('W/O Action', ''))
            
            # Get the best available description for the event
            wo_desc = row.get('W/O Description')
            if pd.isna(wo_desc) or str(wo_desc).strip() == "":
                wo_desc = row.get('ATA Description', '')
                
            events.append(WorkOrderEvent(
                wo=str(row.get('WO', '')),
                description=str(wo_desc),
                action=str(row.get('W/O Action', '')),
                action_type=action_type,
                wo_type=str(row.get('Type', '')).strip().upper(),
                issued_date=row['Issued_Date']
            ))
        
        # Determine conclusion
        conclusion = determine_conclusion(events)
        
        # Create dates list
        dates = [e.issued_date.strftime('%d/%m/%Y') if pd.notna(e.issued_date) else '' for e in events]
        
        # Create timeline summary
        timeline = create_timeline_summary(events)
        
        # Get ATA02 from the group (all rows in group have same ATA02)
        ata_2digit = group['ATA02'].iloc[0] if 'ATA02' in group.columns else get_ata_2digit(ata)
        
        results.append(AnalysisResult(
            aircraft=str(aircraft),
            ata=str(ata),  # This is now ATA Corrected
            ata_2digit=ata_2digit,
            wo_count=len(events),
            conclusion=conclusion,
            dates=dates,
            timeline_summary=timeline,
            events=events
        ))
    
    return results


def get_red_flags(results: List[AnalysisResult]) -> List[AnalysisResult]:
    """Get only red flag results (RESET_ONLY_REPEAT and CORRECTIVE_NOT_EFFECTIVE)"""
    return [r for r in results if r.conclusion in ['RESET_ONLY_REPEAT', 'CORRECTIVE_NOT_EFFECTIVE']]


def get_first_sentence(text: str) -> str:
    """Extract text from the beginning up to the first period (inclusive)."""
    if pd.isna(text) or not text:
        return ""
    text_str = str(text).strip()
    match = re.search(r'[^.!?]*[.!?]', text_str)
    if match:
        return match.group(0)
    # If no period found, return first 80 chars
    return (text_str[:80] + "...") if len(text_str) > 80 else text_str


def clean_wo_from_text(text: str, wo: str) -> str:
    """Remove WO number and common separators from the start of the text."""
    if not text or not wo:
        return text
    wo_clean = str(wo).strip()
    # Match WO at start (with or without brackets) followed by optional separators
    pattern = rf'^\[?{re.escape(wo_clean)}\]?\s*[:;\-\s]*'
    cleaned = re.sub(pattern, '', str(text).strip(), flags=re.IGNORECASE)
    # Also handle some extra junk that might remain like "; " at start
    cleaned = re.sub(r'^[:;\-\s]+', '', cleaned)
    return cleaned


def generate_recommendation(result: AnalysisResult) -> dict:
    """
    Generate detailed technical recommendation with structured data.
    Returns a dict:
    {
        'history_html': str (for display),
        'history_plain': str (for excel/sheet),
        'assessment': str,
        'recommendation': str,
        'full_html': str (for card display)
    }
    """
    
    # 1. Summary of history (Dates + WO + Desc + Action)
    history_lines_html = []
    history_lines_plain = []
    pilot_reports = 0
    
    for e in result.events:
        date_str = e.issued_date.strftime('%d/%m') if pd.notna(e.issued_date) else "N/A"
        
        # Clean WO duplication from text
        clean_desc = clean_wo_from_text(e.description, e.wo)
        clean_action = clean_wo_from_text(e.action, e.wo)
        
        # Extract first sentences
        desc_short = get_first_sentence(clean_desc).replace('\n', ' ')
        action_short = get_first_sentence(clean_action).replace('\n', ' ')
        
        wo_info = f"[{e.wo}]" if e.wo else ""
        type_info = f"[{e.wo_type}]" if e.wo_type else ""
        type_info_html = type_info
        
        if e.wo_type.startswith('P'): # Count pilot reports
            pilot_reports += 1
            type_info_html = f"<span style='color:#ef4444; font-weight:bold;'>[{e.wo_type}]</span>"
            
        # Format: - Date [Type]: [WO] Description -> Action
        line_html = f"- **{date_str}** {type_info_html}: {wo_info} {desc_short} &rarr; {action_short}"
        line_plain = f"- {date_str} {type_info}: {wo_info} {desc_short} -> {action_short}"
        
        history_lines_html.append(line_html)
        history_lines_plain.append(line_plain)
        
    history_text_html = "<br>".join(history_lines_html)
    history_text_plain = "\n".join(history_lines_plain)
    
    # 2. Determine severity and recommendation
    assessment_text = ""
    recommendation_text = ""
    is_severe = pilot_reports >= 2  # Criterion for severe warning
    
    if result.conclusion == "RESET_ONLY_REPEAT":
        assessment_text = "Hỏng hóc lặp lại với biện pháp xử lý chủ yếu là reset/ops test."
        if is_severe:
            recommendation_text = (
                f"⚠️ CẢNH BÁO: Phát hiện {pilot_reports} lần có tin Pilot Report (Type P). "
                f"Hỏng hóc ảnh hưởng trực tiếp đến khai thác.\n"
                f"👉 ĐỀ NGHỊ DỪNG TÀU để tìm nguyên nhân gốc (Root Cause Analysis). "
                f"Không thực hiện reset/swap test thêm. Cần kiểm tra kỹ wiring, chân jack và component liên quan."
            )
        else:
            recommendation_text = (
                f"👉 Đề nghị đánh giá nguyên nhân gốc, kiểm tra tình trạng kết nối (wiring/connector) "
                f"và xem xét thay thế vật tư dự phòng (proactive replacement) để cắt đứt chuỗi hỏng hóc."
            )
            
    elif result.conclusion == "CORRECTIVE_NOT_EFFECTIVE":
        assessment_text = "Đã có biện pháp Corrective nhưng vẫn tái phát."
        if is_severe:
            recommendation_text = (
                f"⚠️ CẢNH BÁO: Hỏng hóc tái phát sau khi đã sửa chữa/thay thế.\n"
                f"👉 ĐỀ NGHỊ DỪNG TÀU để đánh giá lại biện pháp khắc phục. "
                f"Khả năng cao hỏng hóc rình rập hoặc chưa xử lý đúng nguyên nhân gốc."
            )
        else:
            recommendation_text = (
                f"👉 Đề nghị xem xét lại hiệu quả của biện pháp trước đó. "
                f"Cần mở rộng vùng kiểm tra (adjacent components) hoặc thực hiện troubleshooting chuyên sâu hơn."
            )
    else:
        return {}

    # Assemble final card content (HTML for Streamlit)
    recommendation_html = recommendation_text.replace('\n', '<br>')
    final_content_html = (
        f"**Diễn biến hỏng hóc:**<br>"
        f"{history_text_html}<br><br>"
        f"**Đánh giá:** ATA {result.ata} {assessment_text}<br>"
        f"**Khuyến cáo:**<br>{recommendation_html}"
    )
    
    return {
        'history_html': history_text_html,
        'history_plain': history_text_plain,
        'assessment': assessment_text,
        'recommendation': recommendation_text,
        'full_html': final_content_html
    }


def create_tic_tac_matrix(results: List[AnalysisResult]) -> pd.DataFrame:
    """Create a tic-tac matrix of A/C vs ATA 2-digit with warning indicators"""
    red_flags = get_red_flags(results)
    
    if not red_flags:
        return pd.DataFrame()
    
    # Get unique aircraft and ATA 2-digit codes
    aircraft_list = sorted(set(r.aircraft for r in red_flags))
    ata_list = sorted(set(r.ata_2digit for r in red_flags))
    
    # Create matrix
    matrix_data = {}
    for aircraft in aircraft_list:
        row = {}
        for ata in ata_list:
            # Find matching result
            matching = [r for r in red_flags if r.aircraft == aircraft and r.ata_2digit == ata]
            if matching:
                # Use emoji indicators
                conclusions = set(m.conclusion for m in matching)
                if 'CORRECTIVE_NOT_EFFECTIVE' in conclusions:
                    row[f"ATA {ata}"] = "🔴"  # More severe
                else:
                    row[f"ATA {ata}"] = "🟠"  # RESET_ONLY_REPEAT
            else:
                row[f"ATA {ata}"] = ""
        matrix_data[aircraft] = row
    
    df_matrix = pd.DataFrame(matrix_data).T
    df_matrix.index.name = "A/C"
    
    return df_matrix


def results_to_dataframe(results: List[AnalysisResult]) -> pd.DataFrame:
    """Convert analysis results to a DataFrame for display/export"""
    data = []
    for r in results:
        data.append({
            'A/C': r.aircraft,
            'ATA': r.ata,
            'Ngày xảy ra': ', '.join(r.dates),
            'Số WO': r.wo_count,
            'Kết luận': r.conclusion,
            'Tóm tắt tình trạng': r.timeline_summary
        })
    
    return pd.DataFrame(data)


def get_conclusion_display(conclusion: str) -> Tuple[str, str]:
    """Get display text and color for conclusion"""
    mapping = {
        'RESET_ONLY_REPEAT': ('⚠️ Xử lý chưa triệt để', 'orange'),
        'CORRECTIVE_NOT_EFFECTIVE': ('🔴 Corrective không hiệu quả', 'red'),
        'CORRECTIVE_OK': ('✅ Đã xử lý hiệu quả', 'green'),
        'SINGLE_EVENT': ('📋 Đang theo dõi', 'blue')
    }
    return mapping.get(conclusion, (conclusion, 'gray'))
