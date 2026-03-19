"""
TY-Photoism SCM Portal - 실시간 화물 추적 및 관리 대시보드 (MVP v3)
================================================================
실행 방법:
  1) pip install streamlit folium streamlit-folium plotly pdfplumber xlrd openpyxl
  2) streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from datetime import datetime, date
import html as html_module
import json
import os
import re

# ──────────────────────────────────────────────
# 데이터 영구 저장 (JSON)
# ──────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shipments_data.json")
BL_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bl_files")
os.makedirs(BL_FILES_DIR, exist_ok=True)

# 주요 항구 좌표 매핑
PORT_COORDS = {
    "incheon": [37.4563, 126.5922],
    "busan": [35.1028, 129.0403],
    "taichung": [24.2867, 120.5144],
    "kaohsiung": [22.6163, 120.2921],
    "keelung": [25.1550, 121.7490],
    "taipei": [25.0330, 121.5654],
    "taiwan": [24.2867, 120.5144],
    "hochiminh": [10.7769, 106.7009],
    "haiphong": [20.8449, 106.6881],
    "port klang": [2.9994, 101.3926],
    "singapore": [1.2644, 103.8200],
    "long beach": [33.7544, -118.2167],
    "los angeles": [33.7405, -118.2728],
    "carson": [33.8311, -118.2620],
    "tokyo": [35.6528, 139.8394],
    "osaka": [34.6297, 135.4000],
    "shanghai": [31.3622, 121.5050],
    "shenzhen": [22.4828, 114.0667],
    "hong kong": [22.3193, 114.1694],
    "bangkok": [13.7, 100.5],
    "jakarta": [-6.1, 106.8],
    "manila": [14.5, 121.0],
    "seoul": [37.5665, 126.9780],
    "cheonan": [36.8151, 127.1139],
    "vietnam": [10.7769, 106.7009],
    "korea": [37.4563, 126.5922],
}


def find_port_coords(port_text: str) -> list:
    """항구 텍스트에서 좌표를 찾아 반환"""
    if not port_text:
        return [0, 0]
    lower = port_text.lower()
    for key, coords in PORT_COORDS.items():
        if key in lower:
            return coords
    return [0, 0]


def load_shipments() -> list:
    """JSON 파일에서 선적 데이터 로드. 없으면 기본 데이터 생성. 마일스톤 자동 동기화."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # status_type에 따라 마일스톤 자동 동기화
        return _sync_milestones(data)
    # 초기 더미 데이터
    default_data = get_default_shipments()
    save_shipments(default_data)
    return default_data


def _sync_milestones(shipments: list) -> list:
    """status_type에 따라 마일스톤 상태를 자동 동기화"""
    today = datetime.now().strftime("%Y-%m-%d")
    for s in shipments:
        st_type = s.get("status_type", "transit")
        milestones = s.get("milestones", [])
        if not milestones:
            continue
        if st_type == "completed":
            for ms in milestones:
                ms["status"] = "completed"
                if ms.get("date") in ("TBD", "미정", "", None):
                    ms["date"] = today
        elif st_type == "delayed":
            for ms in milestones:
                name_lower = ms["name"].lower()
                if any(kw in name_lower for kw in ["booking", "etd", "on board", "출발", "선적", "eta", "도착예정", "도착"]):
                    ms["status"] = "completed"
                elif "customs" in name_lower or "통관" in name_lower:
                    ms["status"] = "delayed"
                    if ms.get("date") in ("TBD", "미정", "", None):
                        ms["date"] = today
                elif "delivery" in name_lower or "배송" in name_lower:
                    ms["status"] = "pending"
        elif st_type == "transit":
            for ms in milestones:
                name_lower = ms["name"].lower()
                if any(kw in name_lower for kw in ["booking", "etd", "on board", "출발", "선적"]):
                    ms["status"] = "completed"
                elif "eta" in name_lower or "도착" in name_lower:
                    ms["status"] = "active"
                else:
                    ms["status"] = "pending"
    return shipments


def save_shipments(shipments: list) -> None:
    """선적 데이터를 JSON 파일에 저장"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(shipments, f, ensure_ascii=False, indent=2)


def get_default_shipments() -> list:
    """기본 더미 데이터 반환"""
    return [
        {
            "hbl": "TYL-PH-260301",
            "direction": "수입 (Import)",
            "direction_key": "import",
            "origin_country": "대만",
            "dest_country": "한국",
            "commodity": "HITI 프린터",
            "status": "해상 운송 중",
            "status_en": "In Transit",
            "status_type": "transit",
            "transport_mode": "해상 (Sea)",
            "carrier": "Evergreen Marine",
            "vessel": "EVER GOLDEN V.0326E",
            "origin_port": "타이중항 (Taichung)",
            "dest_port": "인천항 (Incheon)",
            "origin_coords": [24.2867, 120.5144],
            "dest_coords": [37.4563, 126.5922],
            "current_coords": [30.5, 124.8],
            "weight_kg": 2400,
            "packages": 48,
            "incoterms": "CIF Incheon",
            "has_issue": False,
            "issue_detail": None,
            "milestones": [
                {"name": "Booking\nConfirmed", "date": "2026-03-01", "status": "completed"},
                {"name": "ETD\n출발", "date": "2026-03-10", "status": "completed"},
                {"name": "On Board\n선적", "date": "2026-03-10", "status": "completed"},
                {"name": "ETA\n도착예정", "date": "2026-03-22", "status": "active"},
                {"name": "Customs\n통관", "date": "2026-03-23", "status": "pending"},
                {"name": "Delivery\n배송", "date": "2026-03-25", "status": "pending"},
            ],
        },
        {
            "hbl": "TYL-PH-260302",
            "direction": "수출 (Export)",
            "direction_key": "export",
            "origin_country": "한국",
            "dest_country": "말레이시아",
            "commodity": "키오스크 (Kiosk)",
            "status": "통관 지연 - SIRIM 인증 대기",
            "status_en": "Customs Delayed",
            "status_type": "delayed",
            "transport_mode": "해상 (Sea)",
            "carrier": "HMM",
            "vessel": "HMM PROMISE V.0312E",
            "origin_port": "부산항 (Busan)",
            "dest_port": "포트클랑 (Port Klang)",
            "origin_coords": [35.1028, 129.0403],
            "dest_coords": [2.9994, 101.3926],
            "current_coords": [2.9994, 101.3926],
            "weight_kg": 5200,
            "packages": 12,
            "incoterms": "FOB Busan",
            "has_issue": True,
            "issue_detail": {
                "title": "SIRIM 인증 검토 지연",
                "description": (
                    "말레이시아 SIRIM(Standards and Industrial Research Institute of Malaysia) "
                    "인증 심사가 지연되고 있습니다. 키오스크 제품의 전자파 적합성(EMC) 및 안전 시험 "
                    "결과 추가 서류가 요청되었습니다."
                ),
                "expected_delay": "3~5 영업일 추가 소요 예상",
                "action_required": "EMC 시험 성적서 원본 및 제품 매뉴얼 영문본 제출 필요",
            },
            "milestones": [
                {"name": "Booking\nConfirmed", "date": "2026-02-20", "status": "completed"},
                {"name": "ETD\n출발", "date": "2026-02-28", "status": "completed"},
                {"name": "On Board\n선적", "date": "2026-02-28", "status": "completed"},
                {"name": "ETA\n도착", "date": "2026-03-12", "status": "completed"},
                {"name": "Customs\n통관", "date": "2026-03-13", "status": "delayed"},
                {"name": "Delivery\n배송", "date": "미정", "status": "pending"},
            ],
        },
        {
            "hbl": "TYL-PH-260303",
            "direction": "수출 (Export)",
            "direction_key": "export",
            "origin_country": "한국",
            "dest_country": "미국",
            "commodity": "인화지 (Photo Paper)",
            "status": "카슨 JSL 창고 입고 완료",
            "status_en": "Delivered",
            "status_type": "completed",
            "transport_mode": "해상 (Sea)",
            "carrier": "ONE (Ocean Network Express)",
            "vessel": "ONE CONTINUITY V.0305W",
            "origin_port": "부산항 (Busan)",
            "dest_port": "롱비치항 (Long Beach)",
            "origin_coords": [35.1028, 129.0403],
            "dest_coords": [33.7544, -118.2167],
            "current_coords": [33.8311, -118.2620],
            "weight_kg": 8600,
            "packages": 320,
            "incoterms": "DDP Carson",
            "has_issue": False,
            "issue_detail": None,
            "milestones": [
                {"name": "Booking\nConfirmed", "date": "2026-02-10", "status": "completed"},
                {"name": "ETD\n출발", "date": "2026-02-15", "status": "completed"},
                {"name": "On Board\n선적", "date": "2026-02-15", "status": "completed"},
                {"name": "ETA\n도착", "date": "2026-03-08", "status": "completed"},
                {"name": "Customs\n통관", "date": "2026-03-10", "status": "completed"},
                {"name": "Delivery\n배송", "date": "2026-03-14", "status": "completed"},
            ],
        },
    ]


# ──────────────────────────────────────────────
# B/L 파서 (PDF / Excel)
# ──────────────────────────────────────────────
def parse_bl_pdf(uploaded_file) -> dict:
    """PDF B/L에서 주요 정보 추출"""
    import pdfplumber

    result = {
        "hbl": "",
        "shipper": "",
        "consignee": "",
        "vessel": "",
        "origin_port": "",
        "dest_port": "",
        "commodity": "",
        "weight_kg": 0,
        "packages": 0,
        "cbm": 0.0,
        "on_board_date": "",
        "freight_terms": "",
        "hs_code": "",
        "container": "",
    }

    with pdfplumber.open(uploaded_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    lines = full_text.split("\n")
    lines = [line.strip() for line in lines if line.strip()]

    if not lines:
        return result

    # B/L 번호 — 첫 줄 또는 TYL 패턴
    for line in lines[:5]:
        bl_match = re.search(r"(TYL\w+[-]?\w*)", line)
        if bl_match:
            result["hbl"] = bl_match.group(1)
            break
    if not result["hbl"] and lines:
        result["hbl"] = lines[0].strip()

    # Shipper — B/L 번호 다음 줄
    bl_idx = 0
    for i, line in enumerate(lines):
        if result["hbl"] and result["hbl"] in line:
            bl_idx = i
            break
    if bl_idx + 1 < len(lines):
        result["shipper"] = lines[bl_idx + 1]

    # 선박명 — 일반적인 선박명 패턴 검색
    for line in lines:
        vessel_match = re.search(
            r"([A-Z][A-Z\s]+(?:V\.\d+\w*|VOY[.\s]*\d+))",
            line,
        )
        if vessel_match:
            result["vessel"] = vessel_match.group(1).strip()
            break
    if not result["vessel"]:
        for line in lines:
            if any(kw in line.upper() for kw in ["CONTINENTAL", "PEGASUS", "EVER ", "HMM ", "ONE "]):
                vessel_match = re.search(r"([A-Z][A-Z\s]+\d+\w*)", line)
                if vessel_match:
                    result["vessel"] = vessel_match.group(1).strip()
                    break

    # On Board Date
    for line in lines:
        date_match = re.search(
            r"(?:ON\s*BOARD\s*DATE[:\s]*)?([A-Z]{3}[.\s]*\d{1,2}[,.\s]*\d{4})",
            line,
        )
        if date_match:
            result["on_board_date"] = date_match.group(1).strip()

    # 중량
    weight_match = re.search(r"([\d,]+\.?\d*)\s*KGS", full_text, re.IGNORECASE)
    if weight_match:
        result["weight_kg"] = float(weight_match.group(1).replace(",", ""))

    # CBM
    cbm_match = re.search(r"([\d,]+\.?\d*)\s*CBM", full_text, re.IGNORECASE)
    if cbm_match:
        result["cbm"] = float(cbm_match.group(1).replace(",", ""))

    # 포장 수량
    pkg_match = re.search(r"(\d+)\s*(?:CTNS?|PKGS?|PACKAGES?|CARTONS?)", full_text, re.IGNORECASE)
    if pkg_match:
        result["packages"] = int(pkg_match.group(1))

    # 컨테이너
    container_match = re.search(r"([A-Z]{4}\d{7})", full_text)
    if container_match:
        result["container"] = container_match.group(1)

    # Freight Terms
    if "FREIGHT COLLECT" in full_text.upper():
        result["freight_terms"] = "Freight Collect"
    elif "FREIGHT PREPAID" in full_text.upper():
        result["freight_terms"] = "Freight Prepaid"

    # HS Code
    hs_match = re.search(r"HS\s*CODE[:\s]*([\d.,\s]+)", full_text, re.IGNORECASE)
    if hs_match:
        result["hs_code"] = hs_match.group(1).strip()

    # 품목 — "SAID TO CONTAIN" 이후 또는 "CONTAIN" 이후
    commodity_lines = []
    capture = False
    for line in lines:
        if "SAID TO CONTAIN" in line.upper() or "CONTAIN" in line.upper():
            capture = True
            # 같은 줄에 있는 경우
            after = re.split(r"SAID TO CONTAIN\s*:?\s*", line, flags=re.IGNORECASE)
            if len(after) > 1 and after[1].strip():
                commodity_lines.append(after[1].strip())
            continue
        if capture:
            if any(kw in line.upper() for kw in [
                "INVOICE", "HS CODE", "ON BOARD", "SURRENDERED",
                "FREIGHT", "SAY :", "CONTAINER",
            ]):
                break
            if line.strip() and not re.match(r"^[A-Z]{4}\d{7}", line):
                commodity_lines.append(line.strip())

    result["commodity"] = " / ".join(commodity_lines[:4]) if commodity_lines else ""

    # 항구 — 텍스트에서 주요 항구명 찾기
    port_patterns = [
        "INCHEON", "BUSAN", "HOCHIMINH", "HAIPHONG", "TAICHUNG",
        "KAOHSIUNG", "PORT KLANG", "LONG BEACH", "SINGAPORE",
        "SHANGHAI", "TOKYO", "OSAKA", "HONG KONG", "TAIPEI",
    ]
    found_ports = []
    for port in port_patterns:
        if port in full_text.upper():
            found_ports.append(port.title())

    # 일반적으로 B/L에서 첫 번째 항구가 선적항, 두 번째가 도착항
    if len(found_ports) >= 2:
        result["origin_port"] = found_ports[0]
        result["dest_port"] = found_ports[1]
    elif len(found_ports) == 1:
        result["origin_port"] = found_ports[0]

    # Consignee 찾기 — Shipper 다음 블록
    for i, line in enumerate(lines):
        if result["shipper"] and result["shipper"] in line:
            # 몇 줄 뒤에 consignee가 나옴
            for j in range(i + 1, min(i + 8, len(lines))):
                if "CO.,LTD" in lines[j].upper() or "COMPANY" in lines[j].upper():
                    result["consignee"] = lines[j].strip()
                    break
            break

    return result


def parse_invoice_excel(uploaded_file) -> dict:
    """엑셀 인보이스에서 주요 정보 추출"""
    import xlrd

    result = {
        "shipper": "",
        "consignee": "",
        "carrier": "",
        "sailing_date": "",
        "invoice_no": "",
        "origin_port": "",
        "dest_port": "",
        "commodity": "",
        "incoterms": "",
        "items": [],
        "total_weight": 0,
        "total_packages": 0,
    }

    try:
        wb = xlrd.open_workbook(file_contents=uploaded_file.read())
    except Exception:
        uploaded_file.seek(0)
        try:
            import openpyxl
            wb_openpyxl = openpyxl.load_workbook(uploaded_file)
            sheet = wb_openpyxl.active
            # openpyxl 처리
            rows = []
            for row in sheet.iter_rows(values_only=True):
                rows.append([str(c) if c is not None else "" for c in row])
            return _parse_invoice_rows(rows, result)
        except Exception as e:
            result["shipper"] = f"파싱 오류: {e}"
            return result

    sheet = wb.sheet_by_index(0)
    rows = []
    for row_idx in range(sheet.nrows):
        row = []
        for col_idx in range(sheet.ncols):
            cell = sheet.cell_value(row_idx, col_idx)
            row.append(str(cell) if cell else "")
        rows.append(row)

    return _parse_invoice_rows(rows, result)


def _parse_invoice_rows(rows: list, result: dict) -> dict:
    """엑셀 행 데이터에서 인보이스 정보 추출"""
    for i, row in enumerate(rows):
        row_text = " ".join(str(c) for c in row).upper()

        # Shipper (일반적으로 Row 2)
        if i >= 1 and i <= 3:
            for cell in row:
                cell_str = str(cell).strip()
                if cell_str and "SHIPPER" not in cell_str.upper() and "CARRIER" not in cell_str.upper():
                    if any(kw in cell_str.upper() for kw in ["CO.", "LTD", "INC", "CORP"]):
                        if not result["shipper"]:
                            result["shipper"] = cell_str
                    elif re.match(r"\d{1,2}\.\w+\.\d{4}", cell_str):
                        result["sailing_date"] = cell_str

        # Carrier
        if "CARRIER" in row_text or i == 1:
            for j, cell in enumerate(row):
                if j > 0 and str(cell).strip():
                    val = str(cell).strip()
                    if val and "CARRIER" not in val.upper() and "SAILING" not in val.upper():
                        if not result["carrier"] and len(val) > 2:
                            result["carrier"] = val

        # Consignee
        if "ACCOUNT" in row_text or "MESSERS" in row_text:
            for j in range(i + 1, min(i + 3, len(rows))):
                for cell in rows[j]:
                    cell_str = str(cell).strip()
                    if cell_str and any(kw in cell_str.upper() for kw in ["CO.", "LTD", "INC"]):
                        result["consignee"] = cell_str
                        break

        # Invoice No
        if ("INVOICE" in row_text and "NO" in row_text) or ("NO." in row_text and "DATE" in row_text):
            for j in range(i, min(i + 3, len(rows))):
                for cell in rows[j]:
                    cs = str(cell).strip()
                    inv_match = re.search(r"([A-Z]+-\d{6,})", cs)
                    if inv_match and not result["invoice_no"]:
                        result["invoice_no"] = inv_match.group(1)

        # Ports & Incoterms (같은 행에 Port of loading, Final destination, Remarks가 있을 수 있음)
        if "PORT" in row_text or "LOADING" in row_text or "DESTINATION" in row_text:
            if i + 1 < len(rows):
                next_row = rows[i + 1]
                # 빈 셀을 제외한 값만 추출
                non_empty = [str(c).strip() for c in next_row if str(c).strip()]
                incoterms_list = ["EXW", "FOB", "CIF", "DDP", "DAP", "CFR", "FCA", "CPT", "CIP"]
                ports = []
                for val in non_empty:
                    if val.upper() in incoterms_list:
                        result["incoterms"] = val
                    else:
                        ports.append(val)
                if len(ports) >= 1 and not result["origin_port"]:
                    result["origin_port"] = ports[0]
                if len(ports) >= 2 and not result["dest_port"]:
                    result["dest_port"] = ports[1]

        # 품목 행 (숫자로 시작하는 행)
        if row and str(row[0]).strip():
            try:
                item_no = float(str(row[0]).strip())
                if 1 <= item_no <= 20 and len(row) >= 3:
                    desc = str(row[1]).strip() if len(row) > 1 else ""
                    qty = str(row[2]).strip() if len(row) > 2 else ""
                    if desc and desc != "0.0":
                        result["items"].append({
                            "description": desc,
                            "quantity": qty,
                        })
                        if not result["commodity"]:
                            result["commodity"] = desc
                        else:
                            result["commodity"] += f" / {desc}"
            except (ValueError, IndexError):
                pass

    # Sailing date from row 2
    if not result["sailing_date"] and len(rows) > 2:
        for cell in rows[2]:
            date_match = re.search(r"(\d{1,2}\.\w{3}\.\d{4})", str(cell))
            if date_match:
                result["sailing_date"] = date_match.group(1)

    # Carrier from row 2
    if not result["carrier"] and len(rows) > 2:
        row2 = rows[2] if len(rows) > 2 else []
        for cell in row2:
            val = str(cell).strip()
            if val and not any(kw in val.upper() for kw in [
                "CO.", "LTD", "INC", "SHIPPER", "NO.",
            ]):
                if re.match(r"^[A-Z\s-]+$", val) and len(val) >= 3:
                    result["carrier"] = val

    return result


# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="TY-Photoism SCM Portal",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# 커스텀 CSS (다크 블루 테마)
# ──────────────────────────────────────────────
st.markdown("""
<style>
    /* 밝은 배경 */
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 50%, #f8fafc 100%);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown span {
        color: #334155;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #e2e8f0;
    }
    .portal-header {
        background: linear-gradient(90deg, #1e40af 0%, #2563eb 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 15px rgba(37,99,235,0.2);
    }
    .portal-header h1 {
        color: #ffffff; font-size: 1.6rem; margin: 0; font-weight: 700;
    }
    .portal-header .subtitle {
        color: #bfdbfe; font-size: 0.85rem; margin: 0;
    }
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 2.2rem; font-weight: 800; margin: 0.3rem 0; }
    .kpi-label { color: #64748b; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-blue { color: #2563eb; }
    .kpi-green { color: #059669; }
    .kpi-orange { color: #d97706; }
    .kpi-red { color: #dc2626; }
    .section-title {
        color: #1e293b; font-size: 1.15rem; font-weight: 600;
        margin: 1.5rem 0 0.8rem 0; padding-bottom: 0.5rem;
        border-bottom: 2px solid #2563eb33;
        display: flex; align-items: center; gap: 0.5rem;
    }
    .shipment-card {
        background: #ffffff;
        border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 1.2rem; margin-bottom: 0.8rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .shipment-card.alert { border-left: 4px solid #dc2626; }
    .shipment-hbl { color: #1e40af; font-weight: 700; font-size: 1rem; }
    .shipment-info { color: #475569; font-size: 0.85rem; margin-top: 0.3rem; }
    .status-badge {
        display: inline-block; padding: 0.25rem 0.75rem;
        border-radius: 20px; font-size: 0.75rem; font-weight: 600;
    }
    .badge-transit { background: #dbeafe; color: #1e40af; }
    .badge-delayed { background: #fee2e2; color: #991b1b; }
    .badge-completed { background: #d1fae5; color: #065f46; }
    .badge-customs { background: #fef3c7; color: #92400e; }
    .alert-banner {
        background: linear-gradient(135deg, #fef2f2, #fee2e2);
        border: 1px solid #fca5a5; border-radius: 10px;
        padding: 1rem 1.5rem; margin: 0.8rem 0;
        display: flex; align-items: flex-start; gap: 0.8rem;
    }
    .alert-title { color: #991b1b; font-weight: 700; font-size: 0.95rem; }
    .alert-desc { color: #7f1d1d; font-size: 0.82rem; margin-top: 0.3rem; }
    .info-table { width: 100%; border-collapse: collapse; }
    .info-table td { padding: 0.4rem 0.6rem; font-size: 0.82rem; border-bottom: 1px solid #f1f5f9; }
    .info-table .label { color: #94a3b8; width: 120px; }
    .info-table .value { color: #1e293b; font-weight: 500; }
    div[data-testid="stSelectbox"] label { color: #475569 !important; }
    div[data-testid="stRadio"] label { color: #475569 !important; }
    div[data-testid="stMultiSelect"] label { color: #475569 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px 8px 0 0;
        color: #64748b; padding: 0.5rem 1.2rem;
    }
    .stTabs [aria-selected="true"] { background-color: #2563eb !important; color: #ffffff !important; }
    .footer {
        text-align: center; color: #94a3b8; font-size: 0.7rem;
        margin-top: 2rem; padding: 1rem; border-top: 1px solid #e2e8f0;
    }
    .parse-result {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
    }
    .parse-field { color: #64748b; font-size: 0.75rem; margin-bottom: 0.1rem; }
    .parse-value { color: #1e293b; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.6rem; }
    .success-banner {
        background: linear-gradient(135deg, #ecfdf5, #d1fae5);
        border: 1px solid #6ee7b7; border-radius: 10px;
        padding: 1rem 1.5rem; margin: 0.8rem 0; color: #065f46;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────
def get_status_badge(status_type: str, label: str) -> str:
    badge_class = {
        "transit": "badge-transit", "delayed": "badge-delayed",
        "completed": "badge-completed", "customs": "badge-customs",
    }.get(status_type, "badge-transit")
    return f'<span class="status-badge {badge_class}">{label}</span>'


def filter_shipments(shipments: list, direction_filter: str, status_filter: list) -> list:
    filtered = list(shipments)
    if direction_filter != "전체":
        key = "import" if direction_filter == "수입" else "export"
        filtered = [s for s in filtered if s.get("direction_key") == key]
    if status_filter:
        filtered = [s for s in filtered if s.get("status_type") in status_filter]
    return filtered


def render_timeline_component(shipment: dict) -> None:
    milestones = shipment.get("milestones", [])
    if not milestones:
        st.info("마일스톤 데이터가 없습니다.")
        return

    completed_count = sum(1 for m in milestones if m["status"] == "completed")
    total = len(milestones)
    progress_pct = (completed_count / total) * 100 if total else 0
    for i, m in enumerate(milestones):
        if m["status"] in ("active", "delayed"):
            progress_pct = ((i + 0.5) / total) * 100
            break

    icons = {
        "completed": ("dot-completed", "&#10003;"),
        "active": ("dot-active", "&#9679;"),
        "pending": ("dot-pending", "&#9675;"),
        "delayed": ("dot-delayed", "!"),
    }
    steps_html = ""
    for m in milestones:
        dot_class, dot_icon = icons.get(m["status"], ("dot-pending", "&#9675;"))
        name_lines = m["name"].replace("\n", "<br>")
        steps_html += f"""
        <div class="tl-step">
            <div class="tl-dot {dot_class}">{dot_icon}</div>
            <div class="tl-label">{name_lines}</div>
            <div class="tl-date">{m['date']}</div>
        </div>"""

    badge = get_status_badge(shipment.get("status_type", "transit"), shipment.get("status_en", ""))
    issue_html = ""
    if shipment.get("has_issue") and shipment.get("issue_detail"):
        d = shipment["issue_detail"]
        issue_html = f"""
        <div class="tl-alert">
            <div style="font-size:1.3rem;">&#128680;</div>
            <div>
                <div class="tl-alert-title">{d['title']}</div>
                <div class="tl-alert-desc">{d['description']}<br><br>
                    <b>&#9201; 예상 지연:</b> {d['expected_delay']}<br>
                    <b>&#128203; 필요 조치:</b> {d['action_required']}</div>
            </div>
        </div>"""

    full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{background:transparent;font-family:'Segoe UI',sans-serif;color:#1e293b}}
        .tl-card{{background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:1.2rem;box-shadow:0 1px 4px rgba(0,0,0,0.05)}}
        .tl-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem}}
        .tl-hbl{{color:#1e40af;font-weight:700;font-size:1rem}}
        .tl-route{{color:#64748b;font-size:.82rem;margin-bottom:1rem}}
        .status-badge{{display:inline-block;padding:.25rem .75rem;border-radius:20px;font-size:.75rem;font-weight:600}}
        .badge-transit{{background:#dbeafe;color:#1e40af}}.badge-delayed{{background:#fee2e2;color:#991b1b}}.badge-completed{{background:#d1fae5;color:#065f46}}
        .tl-wrapper{{position:relative;padding:0 .5rem}}
        .tl-line{{position:absolute;top:18px;left:10%;right:10%;height:3px;background:#e2e8f0;z-index:0}}
        .tl-line-fill{{height:100%;background:linear-gradient(90deg,#059669,#2563eb);border-radius:2px}}
        .tl-steps{{display:flex;justify-content:space-between;position:relative;z-index:1}}
        .tl-step{{display:flex;flex-direction:column;align-items:center;flex:1}}
        .tl-dot{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.85rem;font-weight:700;margin-bottom:.5rem}}
        .dot-completed{{background:#059669;color:#fff}}
        .dot-active{{background:#2563eb;color:#fff;box-shadow:0 0 0 4px rgba(37,99,235,.2),0 0 12px rgba(37,99,235,.3);animation:pulse 2s infinite}}
        .dot-pending{{background:#e2e8f0;color:#94a3b8}}
        .dot-delayed{{background:#dc2626;color:#fff;box-shadow:0 0 0 4px rgba(220,38,38,.2)}}
        @keyframes pulse{{0%,100%{{box-shadow:0 0 0 4px rgba(37,99,235,.2),0 0 12px rgba(37,99,235,.15)}}50%{{box-shadow:0 0 0 8px rgba(37,99,235,.1),0 0 20px rgba(37,99,235,.25)}}}}
        .tl-label{{color:#64748b;font-size:.72rem;text-align:center;line-height:1.3}}
        .tl-date{{color:#94a3b8;font-size:.65rem;text-align:center;margin-top:.2rem}}
        .tl-alert{{background:linear-gradient(135deg,#fef2f2,#fee2e2);border:1px solid #fca5a5;border-radius:10px;padding:1rem 1.2rem;margin-top:1rem;display:flex;align-items:flex-start;gap:.8rem}}
        .tl-alert-title{{color:#991b1b;font-weight:700;font-size:.9rem}}
        .tl-alert-desc{{color:#7f1d1d;font-size:.8rem;margin-top:.3rem;line-height:1.5}}
    </style></head><body>
    <div class="tl-card">
        <div class="tl-header">
            <span class="tl-hbl">{shipment.get('hbl','')} &mdash; {shipment.get('commodity','')}</span>{badge}
        </div>
        <div class="tl-route">{shipment.get('origin_port','')} &rarr; {shipment.get('dest_port','')} &nbsp;|&nbsp; {shipment.get('carrier','')} &nbsp;|&nbsp; {shipment.get('vessel','')}</div>
        <div class="tl-wrapper">
            <div class="tl-line"><div class="tl-line-fill" style="width:{progress_pct}%"></div></div>
            <div class="tl-steps">{steps_html}</div>
        </div>{issue_html}
    </div></body></html>"""

    height = 230 if not shipment.get("has_issue") else 370
    components.html(full_html, height=height, scrolling=False)


def build_tracking_map(shipments: list) -> folium.Map:
    m = folium.Map(location=[25, 140], zoom_start=2, tiles="CartoDB positron", attr="TY Logistics", min_zoom=2, max_bounds=True)
    colors = {"transit": "#3b82f6", "delayed": "#ef4444", "completed": "#10b981"}

    for s in shipments:
        color = colors.get(s.get("status_type"), "#3b82f6")
        origin = s.get("origin_coords", [0, 0])
        dest = s.get("dest_coords", [0, 0])
        current = s.get("current_coords", origin)

        if origin == [0, 0] and dest == [0, 0]:
            continue

        folium.CircleMarker(location=origin, radius=7, color="#60a5fa", fill=True, fill_color="#60a5fa", fill_opacity=0.9, tooltip=f"출발: {s.get('origin_port','')}").add_to(m)
        folium.CircleMarker(location=dest, radius=7, color=color, fill=True, fill_color=color, fill_opacity=0.9, tooltip=f"도착: {s.get('dest_port','')}").add_to(m)

        icon_map = {"transit": ("ship", "blue"), "delayed": ("exclamation-triangle", "red"), "completed": ("check-circle", "green")}
        icon_name, icon_color = icon_map.get(s.get("status_type"), ("ship", "blue"))
        folium.Marker(
            location=current,
            popup=folium.Popup(f"<div style='min-width:200px;font-family:Segoe UI,sans-serif;'><b style='color:#2563eb;font-size:14px;'>{s.get('hbl','')}</b><br><br><b>품목:</b> {s.get('commodity','')}<br><b>상태:</b> {s.get('status','')}<br><b>선박:</b> {s.get('vessel','')}</div>", max_width=280),
            tooltip=f"{s.get('hbl','')} - {s.get('commodity','')}",
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
        ).add_to(m)

        origin_lng, dest_lng = origin[1], dest[1]
        if abs(origin_lng - dest_lng) > 180:
            mid_lat = (origin[0] + dest[0]) / 2 + 8
            folium.PolyLine(locations=[origin, [origin[0]+5, origin[1]+15], [mid_lat, 180]], color=color, weight=2.5, opacity=0.7, dash_array="8").add_to(m)
            folium.PolyLine(locations=[[mid_lat, -180], [dest[0]+5, dest[1]-15], current, dest], color=color, weight=2.5, opacity=0.7, dash_array="8").add_to(m)
        else:
            folium.PolyLine(locations=[origin, current, dest], color=color, weight=2.5, opacity=0.7, dash_array="8").add_to(m)

    if shipments:
        all_coords = []
        for s in shipments:
            for key in ["origin_coords", "dest_coords", "current_coords"]:
                c = s.get(key, [0, 0])
                if c != [0, 0]:
                    all_coords.append(c)
        if all_coords:
            m.fit_bounds(all_coords, padding=(30, 30))
    return m


def build_status_donut(shipments: list) -> go.Figure:
    status_counts = {}
    labels_map = {"transit": "운송 중", "delayed": "지연/이슈", "completed": "도착 완료"}
    colors_map = {"transit": "#3b82f6", "delayed": "#ef4444", "completed": "#10b981"}
    for s in shipments:
        st_type = s.get("status_type", "transit")
        status_counts[st_type] = status_counts.get(st_type, 0) + 1
    fig = go.Figure(data=[go.Pie(labels=[labels_map.get(k, k) for k in status_counts], values=list(status_counts.values()), hole=0.55, marker=dict(colors=[colors_map.get(k, "#64748b") for k in status_counts], line=dict(color="#ffffff", width=2)), textinfo="label+value", textfont=dict(size=12, color="#334155"))])
    fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=10,b=10), height=200, font=dict(color="#334155"), annotations=[dict(text=f"<b>{sum(status_counts.values())}</b><br>건", x=0.5, y=0.5, font=dict(size=22, color="#1e40af"), showarrow=False)])
    return fig


def build_direction_donut(shipments: list) -> go.Figure:
    imports = sum(1 for s in shipments if s.get("direction_key") == "import")
    exports = sum(1 for s in shipments if s.get("direction_key") == "export")
    fig = go.Figure(data=[go.Pie(labels=["수입 (Import)", "수출 (Export)"], values=[imports, exports], hole=0.55, marker=dict(colors=["#6366f1", "#f59e0b"], line=dict(color="#ffffff", width=2)), textinfo="label+value", textfont=dict(size=12, color="#334155"))])
    fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=10,b=10), height=200, font=dict(color="#334155"))
    return fig


# ──────────────────────────────────────────────
# B/L 업로드 페이지
# ──────────────────────────────────────────────
def render_upload_page(shipments: list) -> list:
    """B/L 업로드 및 데이터 관리 페이지"""
    st.markdown("""
    <div class="portal-header">
        <div>
            <h1>B/L Upload & Data Management</h1>
            <p class="subtitle">B/L (PDF) 또는 인보이스 (Excel) 파일을 업로드하면 자동으로 정보를 읽어옵니다</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    upload_tab, manage_tab = st.tabs(["📤 B/L 업로드", "📋 데이터 관리"])

    with upload_tab:
        st.markdown('<div class="section-title">📄 파일 업로드</div>', unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "B/L (PDF) 또는 인보이스 (Excel) 파일 선택",
            type=["pdf", "xls", "xlsx"],
            help="B/L PDF 또는 Commercial Invoice Excel 파일을 업로드하세요.",
        )

        if uploaded_file:
            file_type = uploaded_file.name.split(".")[-1].lower()
            parsed = {}

            with st.spinner("파일을 분석하고 있습니다..."):
                if file_type == "pdf":
                    parsed = parse_bl_pdf(uploaded_file)
                elif file_type in ("xls", "xlsx"):
                    parsed = parse_invoice_excel(uploaded_file)

            st.markdown('<div class="section-title">🔍 파싱 결과 (검토 후 수정 가능)</div>', unsafe_allow_html=True)

            # 파싱 결과를 편집 가능한 폼으로 표시
            with st.form("bl_form"):
                col1, col2 = st.columns(2)

                with col1:
                    hbl = st.text_input("H/BL 번호", value=parsed.get("hbl", parsed.get("invoice_no", "")))
                    direction = st.selectbox("구분", ["수출 (Export)", "수입 (Import)"], index=0)
                    shipper = st.text_input("Shipper (송하인)", value=parsed.get("shipper", ""))
                    consignee = st.text_input("Consignee (수하인)", value=parsed.get("consignee", ""))
                    commodity = st.text_input("품목", value=parsed.get("commodity", ""))
                    vessel = st.text_input("선박명", value=parsed.get("vessel", ""))

                with col2:
                    carrier = st.text_input("선사 (Carrier)", value=parsed.get("carrier", ""))
                    origin_port = st.text_input("선적항 (Port of Loading)", value=parsed.get("origin_port", ""))
                    dest_port = st.text_input("도착항 (Port of Discharge)", value=parsed.get("dest_port", ""))
                    weight = st.number_input("총 중량 (KG)", value=int(parsed.get("weight_kg", parsed.get("total_weight", 0))))
                    packages = st.number_input("포장 수량", value=int(parsed.get("packages", parsed.get("total_packages", 0))))
                    incoterms = st.text_input("Incoterms", value=parsed.get("incoterms", parsed.get("freight_terms", "")))
                    on_board_date = st.text_input("On Board Date", value=parsed.get("on_board_date", parsed.get("sailing_date", "")))

                status_type = st.selectbox("현재 상태", ["transit", "delayed", "completed"], format_func=lambda x: {"transit": "운송 중", "delayed": "지연/이슈", "completed": "도착 완료"}[x])

                issue_note = st.text_area(
                    "📌 Issue / 특이사항",
                    value="",
                    height=100,
                    placeholder="진행 중 문제사항이나 특이사항을 입력하세요. (예: SIRIM 인증 대기 중, 서류 미비로 통관 지연 등)",
                )

                submitted = st.form_submit_button("✅ 대시보드에 등록", use_container_width=True)

                if submitted:
                    direction_key = "import" if "수입" in direction else "export"
                    status_labels = {
                        "transit": ("해상 운송 중", "In Transit"),
                        "delayed": ("통관 지연", "Customs Delayed"),
                        "completed": ("도착 완료", "Delivered"),
                    }
                    status_kr, status_en = status_labels.get(status_type, ("운송 중", "In Transit"))

                    origin_coords = find_port_coords(origin_port)
                    dest_coords = find_port_coords(dest_port)
                    # 현재 위치: 운송 중이면 중간, 도착이면 도착지
                    if status_type == "transit":
                        current_coords = [
                            (origin_coords[0] + dest_coords[0]) / 2,
                            (origin_coords[1] + dest_coords[1]) / 2,
                        ]
                    else:
                        current_coords = dest_coords

                    today = datetime.now().strftime("%Y-%m-%d")
                    new_shipment = {
                        "hbl": hbl or f"TYL-{datetime.now().strftime('%y%m%d%H%M')}",
                        "direction": direction,
                        "direction_key": direction_key,
                        "origin_country": origin_port.split("(")[-1].replace(")", "").strip() if "(" in origin_port else origin_port,
                        "dest_country": dest_port.split("(")[-1].replace(")", "").strip() if "(" in dest_port else dest_port,
                        "commodity": commodity,
                        "status": status_kr,
                        "status_en": status_en,
                        "status_type": status_type,
                        "transport_mode": "해상 (Sea)",
                        "carrier": carrier,
                        "vessel": vessel,
                        "origin_port": origin_port,
                        "dest_port": dest_port,
                        "origin_coords": origin_coords,
                        "dest_coords": dest_coords,
                        "current_coords": current_coords,
                        "weight_kg": weight,
                        "packages": packages,
                        "incoterms": incoterms,
                        "has_issue": status_type == "delayed" or bool(issue_note.strip()),
                        "issue_note": issue_note.strip(),
                        "issue_detail": {
                            "title": "이슈 발생" if issue_note.strip() else "통관 지연",
                            "description": issue_note.strip() or "통관 진행 중 지연이 발생했습니다.",
                            "expected_delay": "확인 필요",
                            "action_required": "담당자 확인 필요",
                        } if (status_type == "delayed" or issue_note.strip()) else None,
                        "milestones": [
                            {"name": "Booking\nConfirmed", "date": today, "status": "completed"},
                            {"name": "ETD\n출발", "date": on_board_date or today, "status": "completed" if status_type != "transit" else "completed"},
                            {"name": "On Board\n선적", "date": on_board_date or today, "status": "completed"},
                            {"name": "ETA\n도착예정", "date": "TBD", "status": "active" if status_type == "transit" else "completed"},
                            {"name": "Customs\n통관", "date": "TBD", "status": "delayed" if status_type == "delayed" else ("completed" if status_type == "completed" else "pending")},
                            {"name": "Delivery\n배송", "date": "TBD", "status": "completed" if status_type == "completed" else "pending"},
                        ],
                    }

                    # 업로드된 B/L 원본 파일 저장
                    if uploaded_file:
                        safe_name = re.sub(r'[^\w\-.]', '_', uploaded_file.name)
                        bl_filename = f"{new_shipment['hbl']}_{safe_name}"
                        bl_filepath = os.path.join(BL_FILES_DIR, bl_filename)
                        uploaded_file.seek(0)
                        with open(bl_filepath, "wb") as bf:
                            bf.write(uploaded_file.read())
                        new_shipment["bl_file"] = bl_filename

                    shipments.append(new_shipment)
                    save_shipments(shipments)
                    st.markdown('<div class="success-banner">✅ 선적이 대시보드에 등록되었습니다! 왼쪽 메뉴에서 "대시보드"를 선택하면 확인할 수 있습니다.</div>', unsafe_allow_html=True)
                    st.balloons()

            # 파싱된 원본 데이터 미리보기
            if parsed:
                with st.expander("📝 파싱 원본 데이터 보기"):
                    for key, val in parsed.items():
                        if val and val != 0 and val != 0.0:
                            st.markdown(f"**{key}:** {val}")

    with manage_tab:
        st.markdown('<div class="section-title">📋 등록된 선적 관리</div>', unsafe_allow_html=True)

        # 저장/삭제 완료 메시지 표시
        if st.session_state.get("manage_msg"):
            st.success(st.session_state["manage_msg"])
            st.session_state["manage_msg"] = None

        if not shipments:
            st.info("등록된 선적이 없습니다.")
            return shipments

        for i, s in enumerate(shipments):
            # 삭제 버튼을 왼쪽에 바로 노출, expander를 오른쪽에 배치
            del_col, exp_col = st.columns([0.06, 0.94])
            with del_col:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button("❌", key=f"quickdel_{i}", help=f"{s.get('hbl', '')} 삭제"):
                    hbl_name = shipments[i].get("hbl", "")
                    shipments.pop(i)
                    save_shipments(shipments)
                    st.session_state["manage_msg"] = f"🗑️ {hbl_name} 삭제 완료!"
                    st.rerun()
            with exp_col:
                with st.expander(f"{s.get('hbl', '')} — {s.get('commodity', '')} ({s.get('direction', '')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_origin = st.text_input("선적항", value=s.get("origin_port", ""), key=f"origin_{i}")
                        edit_dest = st.text_input("도착항", value=s.get("dest_port", ""), key=f"dest_{i}")
                        edit_vessel = st.text_input("선박", value=s.get("vessel", ""), key=f"vessel_{i}")
                        edit_carrier = st.text_input("선사", value=s.get("carrier", ""), key=f"carrier_{i}")
                    with col2:
                        edit_weight = st.number_input("중량 (kg)", value=int(s.get("weight_kg", 0)), key=f"weight_{i}")
                        edit_packages = st.number_input("수량 (pkgs)", value=int(s.get("packages", 0)), key=f"pkgs_{i}")
                        edit_incoterms = st.text_input("Incoterms", value=s.get("incoterms", ""), key=f"inco_{i}")
                        edit_status = st.selectbox(
                            "상태 변경",
                            ["transit", "delayed", "completed"],
                            index=["transit", "delayed", "completed"].index(s.get("status_type", "transit")),
                            format_func=lambda x: {"transit": "운송 중", "delayed": "지연/이슈", "completed": "도착 완료"}[x],
                            key=f"status_{i}",
                        )

                    edit_issue = st.text_area(
                        "📌 Issue / 특이사항",
                        value=s.get("issue_note", ""),
                        height=80,
                        placeholder="문제사항이나 특이사항을 입력하세요.",
                        key=f"issue_{i}",
                    )

                    if st.button("💾 변경사항 저장", key=f"save_{i}", use_container_width=True, type="primary"):
                        status_labels = {"transit": ("해상 운송 중", "In Transit"), "delayed": ("통관 지연", "Customs Delayed"), "completed": ("도착 완료", "Delivered")}
                        shipments[i]["origin_port"] = edit_origin
                        shipments[i]["dest_port"] = edit_dest
                        shipments[i]["vessel"] = edit_vessel
                        shipments[i]["carrier"] = edit_carrier
                        shipments[i]["weight_kg"] = edit_weight
                        shipments[i]["packages"] = edit_packages
                        shipments[i]["incoterms"] = edit_incoterms
                        shipments[i]["issue_note"] = edit_issue.strip()
                        shipments[i]["status_type"] = edit_status
                        shipments[i]["status_en"] = status_labels[edit_status][1]
                        shipments[i]["status"] = status_labels[edit_status][0]
                        shipments[i]["has_issue"] = edit_status == "delayed" or bool(edit_issue.strip())
                        if edit_issue.strip():
                            shipments[i]["issue_detail"] = {
                                "title": "이슈 발생",
                                "description": edit_issue.strip(),
                                "expected_delay": "확인 필요",
                                "action_required": "담당자 확인 필요",
                            }
                        elif edit_status != "delayed":
                            shipments[i]["issue_detail"] = None
                        shipments[i]["origin_coords"] = find_port_coords(edit_origin)
                        shipments[i]["dest_coords"] = find_port_coords(edit_dest)
                        if edit_status == "completed":
                            shipments[i]["current_coords"] = shipments[i]["dest_coords"]
                        # 마일스톤 상태도 동기화
                        today = datetime.now().strftime("%Y-%m-%d")
                        milestones = shipments[i].get("milestones", [])
                        if edit_status == "completed":
                            for ms in milestones:
                                ms["status"] = "completed"
                                if ms["date"] == "TBD" or ms["date"] == "미정":
                                    ms["date"] = today
                        elif edit_status == "delayed":
                            for j, ms in enumerate(milestones):
                                name_lower = ms["name"].lower()
                                if "customs" in name_lower or "통관" in name_lower:
                                    ms["status"] = "delayed"
                                    if ms["date"] == "TBD" or ms["date"] == "미정":
                                        ms["date"] = today
                                elif j < len(milestones) - 1 and ms["status"] in ("pending", "active"):
                                    if any(kw in name_lower for kw in ["booking", "etd", "on board", "eta", "출발", "선적", "도착"]):
                                        ms["status"] = "completed"
                                elif "delivery" in name_lower or "배송" in name_lower:
                                    ms["status"] = "pending"
                        elif edit_status == "transit":
                            for j, ms in enumerate(milestones):
                                name_lower = ms["name"].lower()
                                if any(kw in name_lower for kw in ["booking", "etd", "on board", "출발", "선적"]):
                                    ms["status"] = "completed"
                                elif "eta" in name_lower or "도착예정" in name_lower or "도착" in name_lower:
                                    ms["status"] = "active"
                                else:
                                    ms["status"] = "pending"
                        shipments[i]["milestones"] = milestones
                        save_shipments(shipments)
                        st.session_state["manage_msg"] = f"✅ {s.get('hbl', '')} 저장 완료!"
                        st.rerun()

        # CSV 다운로드
        st.markdown('<div class="section-title">📥 데이터 내보내기</div>', unsafe_allow_html=True)
        csv_rows = ["H/BL,구분,품목,선적항,도착항,선사,선박,중량(kg),수량,상태"]
        for s in shipments:
            csv_rows.append(f"{s.get('hbl','')},{s.get('direction','')},{s.get('commodity','')},{s.get('origin_port','')},{s.get('dest_port','')},{s.get('carrier','')},{s.get('vessel','')},{s.get('weight_kg',0)},{s.get('packages',0)},{s.get('status','')}")
        csv_data = "\n".join(csv_rows)
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv_data.encode("utf-8-sig"),
            file_name=f"shipments_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    return shipments


# ──────────────────────────────────────────────
# 대시보드 메인 페이지
# ──────────────────────────────────────────────
def render_dashboard(shipments: list, direction_filter: str, status_filter: list):
    shipments = _sync_milestones(shipments)
    filtered = filter_shipments(shipments, direction_filter, status_filter)

    st.markdown("""
    <div class="portal-header">
        <div>
            <h1>TY-Photoism SCM Portal</h1>
            <p class="subtitle">Real-time Cargo Tracking & Management Dashboard</p>
        </div>
        <div style="text-align:right;">
            <p class="subtitle">Powered by TY Logistics</p>
            <p class="subtitle">Last Updated: """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 이슈 알림
    issue_shipments = [s for s in filtered if s.get("has_issue")]
    for s in issue_shipments:
        detail = s.get("issue_detail")
        if detail:
            st.markdown(f"""
            <div class="alert-banner">
                <div style="font-size:1.5rem;">⚠️</div>
                <div>
                    <div class="alert-title">🚨 {s['hbl']} — {detail['title']}</div>
                    <div class="alert-desc">{detail['description']}<br>
                        <b>예상 지연:</b> {detail['expected_delay']}<br>
                        <b>필요 조치:</b> {detail['action_required']}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    # KPI
    st.markdown('<div class="section-title">📊 Dashboard Overview</div>', unsafe_allow_html=True)
    total = len(filtered)
    in_transit = sum(1 for s in filtered if s.get("status_type") == "transit")
    delayed = sum(1 for s in filtered if s.get("status_type") == "delayed")
    completed = sum(1 for s in filtered if s.get("status_type") == "completed")
    imports = sum(1 for s in filtered if s.get("direction_key") == "import")
    exports = sum(1 for s in filtered if s.get("direction_key") == "export")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">전체 선적</div><div class="kpi-value kpi-blue">{total}</div><div class="kpi-label">수입 {imports} / 수출 {exports}</div></div>', unsafe_allow_html=True)
        if total > 0:
            if st.button("📋 전체 목록 보기", key="btn_all_list", use_container_width=True):
                st.session_state["show_shipment_list"] = "all"
                st.session_state.pop("selected_shipment_hbl", None)
    with k2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">운송 중</div><div class="kpi-value kpi-blue">{in_transit}</div><div class="kpi-label">In Transit</div></div>', unsafe_allow_html=True)
        if in_transit > 0:
            if st.button("📋 운송 중 목록", key="btn_transit_list", use_container_width=True):
                st.session_state["show_shipment_list"] = "transit"
                st.session_state.pop("selected_shipment_hbl", None)
    with k3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">통관/지연</div><div class="kpi-value kpi-orange">{delayed}</div><div class="kpi-label">Customs / Delayed</div></div>', unsafe_allow_html=True)
        if delayed > 0:
            if st.button("📋 지연 목록", key="btn_delayed_list", use_container_width=True):
                st.session_state["show_shipment_list"] = "delayed"
                st.session_state.pop("selected_shipment_hbl", None)
    with k4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">도착 완료</div><div class="kpi-value kpi-green">{completed}</div><div class="kpi-label">Delivered</div></div>', unsafe_allow_html=True)
        if completed > 0:
            if st.button("📋 완료 목록", key="btn_completed_list", use_container_width=True):
                st.session_state["show_shipment_list"] = "completed"
                st.session_state.pop("selected_shipment_hbl", None)

    # ── 선적 목록 팝업 (KPI 클릭 시 표시) ──
    list_mode = st.session_state.get("show_shipment_list")
    if list_mode:
        list_title_map = {"all": "전체 선적", "transit": "운송 중", "delayed": "통관/지연", "completed": "도착 완료"}
        if list_mode == "all":
            list_items = filtered
        else:
            list_items = [s for s in filtered if s.get("status_type") == list_mode]

        st.markdown(f'<div class="section-title">📋 {list_title_map.get(list_mode, "")} 목록 ({len(list_items)}건)</div>', unsafe_allow_html=True)

        if st.button("✕ 목록 닫기", key="close_list"):
            st.session_state.pop("show_shipment_list", None)
            st.session_state.pop("selected_shipment_hbl", None)
            st.rerun()

        status_icons = {"transit": "🚢", "delayed": "⚠️", "completed": "✅"}
        list_cols = st.columns(min(len(list_items), 3)) if len(list_items) <= 3 else st.columns(3)
        for i, s in enumerate(list_items):
            col_idx = i % 3
            with (list_cols[col_idx] if len(list_items) > 1 else list_cols[0]):
                icon = status_icons.get(s.get("status_type", ""), "📦")
                direction_label = s.get("direction", "")
                route = f"{s.get('origin_port', '')} → {s.get('dest_port', '')}"
                st.markdown(f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:0.8rem;margin-bottom:0.5rem;">
                    <div style="font-weight:700;color:#1e40af;font-size:0.9rem;">{icon} {s.get('hbl','')}</div>
                    <div style="font-size:0.75rem;color:#475569;margin-top:0.3rem;">{s.get('commodity','')} | {direction_label}</div>
                    <div style="font-size:0.7rem;color:#64748b;">{route}</div>
                </div>""", unsafe_allow_html=True)
                if st.button(f"🔍 상세 보기", key=f"select_{s.get('hbl', i)}_{i}", use_container_width=True):
                    st.session_state["selected_shipment_hbl"] = s.get("hbl")
                    st.session_state.pop("show_shipment_list", None)
                    st.rerun()

    # ── 선택된 선적 상세 (Active Shipments로 스크롤) ──
    selected_hbl_from_list = st.session_state.get("selected_shipment_hbl")

    # 차트
    chart1, chart2 = st.columns(2)
    with chart1:
        st.markdown('<div class="section-title">📈 Status Distribution</div>', unsafe_allow_html=True)
        if filtered:
            st.plotly_chart(build_status_donut(filtered), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("필터 조건에 해당하는 선적이 없습니다.")
    with chart2:
        st.markdown('<div class="section-title">🔄 Import / Export Ratio</div>', unsafe_allow_html=True)
        if filtered:
            st.plotly_chart(build_direction_donut(filtered), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("필터 조건에 해당하는 선적이 없습니다.")

    # 맵 + 선적 리스트
    map_col, list_col = st.columns([3, 2])
    with map_col:
        st.markdown('<div class="section-title">🗺️ End-to-End Tracking Map</div>', unsafe_allow_html=True)
        if filtered:
            st_folium(build_tracking_map(filtered), width=None, height=450, returned_objects=[])
        else:
            st.info("필터 조건에 해당하는 선적이 없습니다.")

    with list_col:
        st.markdown('<div class="section-title">📦 Active Shipments</div>', unsafe_allow_html=True)

        # 선택된 선적이 있으면 해당 건만 표시
        display_shipments = list(filtered)
        if selected_hbl_from_list:
            selected_ship = [s for s in display_shipments if s.get("hbl") == selected_hbl_from_list]
            if selected_ship:
                display_shipments = selected_ship
                st.markdown(f'<div style="background:#dbeafe;border:1px solid #3b82f6;border-radius:8px;padding:0.5rem 1rem;margin-bottom:0.5rem;text-align:center;font-size:0.8rem;color:#1e40af;">🔍 <b>{selected_hbl_from_list}</b> 선적 상세</div>', unsafe_allow_html=True)
                if st.button("📋 전체 목록으로 돌아가기", key="clear_selection", use_container_width=True):
                    st.session_state.pop("selected_shipment_hbl", None)
                    st.rerun()

        for idx, s in enumerate(display_shipments):
            alert_class = " alert" if s.get("has_issue") else ""
            badge = get_status_badge(s.get("status_type", ""), s.get("status_en", ""))
            # HTML 특수문자 이스케이프
            esc = html_module.escape
            hbl_esc = esc(str(s.get('hbl', '')))
            direction_esc = esc(str(s.get('direction', '')))
            commodity_esc = esc(str(s.get('commodity', '')))
            origin_esc = esc(str(s.get('origin_port', '')))
            dest_esc = esc(str(s.get('dest_port', '')))
            vessel_esc = esc(str(s.get('vessel', '')))
            transport_esc = esc(str(s.get('transport_mode', '')))
            incoterms_esc = esc(str(s.get('incoterms', '')))
            status_esc = esc(str(s.get('status', '')))
            issue_row = ""
            if s.get("issue_note"):
                issue_esc = esc(str(s.get("issue_note", "")))
                issue_row = f'<tr><td class="label">⚠️ Issue</td><td class="value" style="color:#dc2626;font-weight:600;">{issue_esc}</td></tr>'
            card_html = (
                f'<div class="shipment-card{alert_class}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span class="shipment-hbl">{hbl_esc}</span>{badge}'
                f'</div>'
                f'<div class="shipment-info">'
                f'<table class="info-table">'
                f'<tr><td class="label">구분</td><td class="value">{direction_esc}</td></tr>'
                f'<tr><td class="label">품목</td><td class="value">{commodity_esc}</td></tr>'
                f'<tr><td class="label">경로</td><td class="value">{origin_esc} → {dest_esc}</td></tr>'
                f'<tr><td class="label">선박</td><td class="value">{vessel_esc}</td></tr>'
                f'<tr><td class="label">운송</td><td class="value">{transport_esc} | {incoterms_esc}</td></tr>'
                f'<tr><td class="label">중량/수량</td><td class="value">{s.get("weight_kg",0):,} kg / {s.get("packages",0)} pkgs</td></tr>'
                f'<tr><td class="label">상태</td><td class="value">{status_esc}</td></tr>'
                f'{issue_row}'
                f'</table>'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            # B/L 파일 다운로드 버튼
            bl_file = s.get("bl_file", "")
            if bl_file:
                bl_path = os.path.join(BL_FILES_DIR, bl_file)
                if os.path.exists(bl_path):
                    with open(bl_path, "rb") as bf:
                        file_bytes = bf.read()
                    ext = bl_file.split(".")[-1].lower()
                    mime = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    st.download_button(
                        label=f"📎 B/L 다운로드 ({bl_file.split('_', 1)[-1]})",
                        data=file_bytes,
                        file_name=bl_file.split("_", 1)[-1] if "_" in bl_file else bl_file,
                        mime=mime,
                        key=f"dl_bl_{idx}",
                        use_container_width=True,
                    )
        if not filtered:
            st.info("필터 조건에 해당하는 선적이 없습니다.")

    # 타임라인
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📍 Shipment Milestone Timeline</div>', unsafe_allow_html=True)
    if filtered:
        selected_hbl = st.selectbox("선적 선택 (H/BL)", options=[s["hbl"] for s in filtered], format_func=lambda hbl: next(f"{hbl} — {s['commodity']} ({s['direction']})" for s in filtered if s["hbl"] == hbl))
        selected = next(s for s in filtered if s["hbl"] == selected_hbl)
        render_timeline_component(selected)
    else:
        st.info("필터 조건에 해당하는 선적이 없습니다.")

    st.markdown('<div class="footer">TY-Photoism SCM Portal MVP v3.0 | Built by TY Logistics | Data is for demonstration purposes only</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 사용자 인증 & 관리
# ──────────────────────────────────────────────
DEFAULT_USERS = {
    "admin": {"password": "ty2026!", "role": "admin", "name": "TY Logistics 관리자"},
    "james": {"password": "james2026", "role": "admin", "name": "James (TY)"},
    "photoism": {"password": "photoism2026", "role": "viewer", "name": "Photoism SCM팀"},
    "viewer": {"password": "view2026", "role": "viewer", "name": "External Viewer"},
}

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_data.json")


def load_users():
    """JSON 파일에서 사용자 데이터 로드. 없으면 기본값 사용."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {**DEFAULT_USERS}


def save_users(users):
    """사용자 데이터를 JSON 파일에 저장."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def render_user_management():
    """관리자용 사용자 계정 관리 페이지"""
    st.markdown('<div class="section-title">👥 사용자 계정 관리</div>', unsafe_allow_html=True)

    users = load_users()

    # ── 새 사용자 등록 ──
    st.markdown("### ➕ 새 사용자 등록")
    with st.form("new_user_form", clear_on_submit=True):
        nc1, nc2 = st.columns(2)
        with nc1:
            new_id = st.text_input("아이디", placeholder="영문/숫자 조합")
            new_name = st.text_input("표시 이름", placeholder="예: Photoism 김대리")
        with nc2:
            new_pw = st.text_input("비밀번호", type="password", placeholder="6자 이상")
            new_role = st.selectbox("권한", ["viewer", "admin"], format_func=lambda x: {"viewer": "👁️ 뷰어 (대시보드만)", "admin": "🔑 관리자 (전체 접근)"}[x])

        submitted = st.form_submit_button("✅ 사용자 등록", use_container_width=True, type="primary")
        if submitted:
            if not new_id or not new_pw or not new_name:
                st.error("모든 필드를 입력해 주세요.")
            elif len(new_pw) < 4:
                st.error("비밀번호는 4자 이상이어야 합니다.")
            elif new_id in users:
                st.error(f"'{new_id}'는 이미 존재하는 아이디입니다.")
            else:
                users[new_id] = {"password": new_pw, "role": new_role, "name": new_name}
                save_users(users)
                st.success(f"✅ '{new_id}' 계정이 생성되었습니다.")
                st.rerun()

    st.divider()

    # ── 등록된 사용자 목록 ──
    st.markdown("### 📋 등록된 사용자 목록")

    admin_users = {k: v for k, v in users.items() if v["role"] == "admin"}
    viewer_users = {k: v for k, v in users.items() if v["role"] == "viewer"}

    # 관리자 목록
    st.markdown("**🔑 관리자 계정**")
    for uid, udata in admin_users.items():
        with st.expander(f"🔑 {uid} — {udata['name']}"):
            st.markdown(f"- **아이디**: `{uid}`")
            st.markdown(f"- **이름**: {udata['name']}")
            st.markdown(f"- **권한**: 관리자")
            st.caption("⚠️ 관리자 계정은 보안을 위해 여기서 삭제할 수 없습니다.")

    st.markdown("")

    # 뷰어 목록 (수정/삭제 가능)
    st.markdown("**👁️ 뷰어 계정**")
    if not viewer_users:
        st.info("등록된 뷰어 계정이 없습니다.")
    else:
        for uid, udata in viewer_users.items():
            with st.expander(f"👁️ {uid} — {udata['name']}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    edit_name = st.text_input("표시 이름", value=udata["name"], key=f"name_{uid}")
                    edit_pw = st.text_input("새 비밀번호 (변경 시 입력)", type="password", key=f"pw_{uid}", placeholder="변경하지 않으려면 비워두세요")
                with ec2:
                    st.text_input("현재 비밀번호", value=udata["password"], key=f"curpw_{uid}", disabled=True)
                    edit_role = st.selectbox("권한 변경", ["viewer", "admin"], index=0 if udata["role"] == "viewer" else 1, key=f"role_{uid}", format_func=lambda x: {"viewer": "👁️ 뷰어", "admin": "🔑 관리자"}[x])

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("💾 저장", key=f"save_{uid}", use_container_width=True):
                        users[uid]["name"] = edit_name
                        users[uid]["role"] = edit_role
                        if edit_pw:
                            users[uid]["password"] = edit_pw
                        save_users(users)
                        st.success(f"✅ '{uid}' 계정이 수정되었습니다.")
                        st.rerun()
                with bc2:
                    if st.button("🗑️ 삭제", key=f"del_{uid}", use_container_width=True, type="secondary"):
                        del users[uid]
                        save_users(users)
                        st.success(f"'{uid}' 계정이 삭제되었습니다.")
                        st.rerun()

    st.divider()
    st.markdown(f"<p style='color:#64748b;font-size:.75rem;'>총 {len(users)}개 계정 (관리자 {len(admin_users)} / 뷰어 {len(viewer_users)})</p>", unsafe_allow_html=True)


def render_login():
    """로그인 페이지"""
    st.markdown("""
    <div style="display:flex;justify-content:center;align-items:center;min-height:60vh;">
        <div style="text-align:center;">
            <h1 style="color:#1e40af;font-size:2.5rem;margin-bottom:0.2rem;">TY-Photoism SCM Portal</h1>
            <p style="color:#64748b;font-size:1rem;margin-bottom:2rem;">Real-time Cargo Tracking & Management Dashboard</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:2rem;box-shadow:0 4px 15px rgba(0,0,0,0.08);">', unsafe_allow_html=True)
        st.markdown("#### 로그인")
        username = st.text_input("아이디", placeholder="아이디를 입력하세요")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")

        if st.button("로그인", use_container_width=True, type="primary"):
            users = load_users()
            user = users.get(username)
            if user and user["password"] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = user["role"]
                st.session_state["display_name"] = user["name"]
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-top:1.5rem;color:#94a3b8;font-size:0.75rem;">
            <p>내부 관리자: B/L 업로드 & 데이터 관리 가능</p>
            <p>외부 뷰어: 대시보드 조회만 가능</p>
            <p style="margin-top:1rem;">Powered by TY Logistics</p>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    # 로그인 체크
    if not st.session_state.get("logged_in"):
        render_login()
        return

    role = st.session_state.get("role", "viewer")
    display_name = st.session_state.get("display_name", "")
    is_admin = role == "admin"

    shipments = load_shipments()

    with st.sidebar:
        st.markdown(f'<div style="text-align:center;padding:1rem 0;"><h2 style="color:#1e40af;margin:0;">TY Logistics</h2><p style="color:#64748b;font-size:.75rem;margin:.3rem 0 0 0;">Photoism SCM Portal v3</p></div>', unsafe_allow_html=True)
        st.divider()

        # 사용자 정보 표시
        role_badge = "🔑 관리자" if is_admin else "👁️ 뷰어"
        st.markdown(f"**{display_name}** &nbsp; {role_badge}")

        if st.button("로그아웃", use_container_width=True):
            for key in ["logged_in", "username", "role", "display_name"]:
                st.session_state.pop(key, None)
            st.rerun()

        st.divider()

        # 메뉴 — 관리자만 B/L 업로드, 사용자 관리 접근 가능
        if is_admin:
            page = st.radio("메뉴", ["📊 대시보드", "📤 B/L 업로드 & 관리", "👥 사용자 관리"], label_visibility="collapsed")
        else:
            page = "📊 대시보드"
            st.radio("메뉴", ["📊 대시보드"], label_visibility="collapsed", disabled=True)

        if page == "📊 대시보드":
            st.divider()
            st.markdown("**필터**")
            direction_filter = st.radio("수입/수출 구분", ["전체", "수입", "수출"], horizontal=True)
            status_options = {"transit": "운송 중", "delayed": "지연/이슈", "completed": "도착 완료"}
            selected_statuses = st.multiselect("상태 필터", options=list(status_options.keys()), default=list(status_options.keys()), format_func=lambda x: status_options[x])
            st.divider()
            st.markdown("**선적 요약**")
            for s in shipments:
                icon = {"transit": "🚢", "delayed": "⚠️", "completed": "✅"}.get(s.get("status_type"), "📦")
                st.markdown(f"{icon} **{s.get('hbl','')}**  \n{s.get('commodity','')} → {s.get('dest_country','')}")
        else:
            direction_filter = "전체"
            selected_statuses = ["transit", "delayed", "completed"]

        st.divider()
        st.markdown(f"<p style='color:#475569;font-size:.7rem;'>총 {len(shipments)}건 등록 | Last sync: {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

    if page == "📊 대시보드":
        render_dashboard(shipments, direction_filter, selected_statuses)
    elif page == "📤 B/L 업로드 & 관리" and is_admin:
        render_upload_page(shipments)
    elif page == "👥 사용자 관리" and is_admin:
        render_user_management()


if __name__ == "__main__":
    main()
