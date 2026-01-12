import io
import pandas as pd
import jinja2
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

# --- CẤU HÌNH & DATA MAPPING (CONSTANTS) ---
NUM_MEMBERS = 18
BOSS_NAME = "Công"
RESIGNED_MEMBERS = [
    'Vũ Thiên Ân', 'Phùng Minh Cường', 'Lê Quốc Thái', 'Nguyễn Thị Tiên',
    'Phạm Tiến Dũng', 'Hà Minh Tân', 'Đại Anh Dũng ', 'Phạm Như Hòa',
    'Nguyễn Hoàng Gia Khanh', 'Nguyễn Tống Gia Huy'
]

USER_INFO = {
    'Nguyễn Trần Phúc': {'project': 'Migration', 'sub_system': 'Limit/PLN', 'hdb_lead': 'Hoàng Thị Thu Thảo'},
    'Nguyễn Ngọc Diệp': {'project': 'Migration', 'sub_system': 'OP', 'hdb_lead': 'Lê Thuần Kiều Nhu'},
    'Lê Nguyễn Minh Tân': {'project': 'Migration', 'sub_system': 'Collateral', 'hdb_lead': 'Võ Thiện Nhân'},
    'Dương Gia Bảo': {'project': 'Migration', 'sub_system': 'BS BG', 'hdb_lead': 'Nguyễn Đỗ Thuỳ Trinh'},
    'Nguyễn Tường Anh': {'project': 'Migration', 'sub_system': 'MM', 'hdb_lead': 'Nguyễn Đỗ Thuỳ Trinh'},
    'Bùi Việt Ngữ': {'project': 'FE Portal', 'sub_system': 'Deposit', 'hdb_lead': 'Tech Lead: Trần Đình Thông, Tô Thành Duy'},
    'Nguyễn Tấn Dũng': {'project': 'FE Portal', 'sub_system': 'Onboarding', 'hdb_lead': 'Tech Lead: Nguyễn Tiến Phúc, Tô Thành Duy'},
    'Đinh Thành Nguyên Đạt': {'project': 'Phần Mềm Gsoft', 'sub_system': '', 'hdb_lead': 'Hoàng Thị Thu Thảo'},
}

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body { font-family: Arial, sans-serif; font-size: 13px; line-height: 1.4; }
    table { width: 80%; border-collapse: collapse; margin-top: 15px; }
    th, td { border: 1px solid #333; padding: 8px; vertical-align: top; }
    th { background-color: #f2f2f2; font-weight: bold; text-align: center; }
    .center { text-align: center; }
    .task-cell div { margin-bottom: 4px; }
  </style>
</head>
<body>
  <p>Hi {{ boss_name }},</p>
  <p>Anh gửi báo cáo công việc cho ngày <strong>{{ report_date }}</strong> nhé.</p>
  <p><strong>Báo cáo công việc:</strong></p>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Dự Án</th>
        <th>Phân Hệ</th>
        <th>Đầu Mối HDBank</th>
        <th>Nhân Sự KMS</th>
        <th>Ngày Công</th>
        <th>Công việc</th>
      </tr>
    </thead>
    <tbody>
      {% for row in rows %}
      <tr>
        <td class="center">{{ row.no }}</td>
        {% if row.p_span > 0 %}<td rowspan="{{ row.p_span }}">{{ row.project }}</td>{% endif %}
        <td>{{ row.sub_system }}</td>
        {% if row.h_span > 0 %}<td rowspan="{{ row.h_span }}">{{ row.hdb_lead }}</td>{% endif %}
        <td><strong>{{ row.kms_staff }}</strong></td>
        <td class="center">{{ row.manday }}</td>
        <td class="task-cell">{{ row.tasks | safe }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <p style="margin-top: 20px;">Trân trọng,<br>An Lâm.</p>
</body>
</html>
"""

# --- HELPER FUNCTIONS ---
def calculate_spans(data_list, column_name):
    """Tính toán rowspan cho cột."""
    spans = []
    i = 0
    while i < len(data_list):
        val = data_list[i][column_name]
        count = 1
        for j in range(i + 1, len(data_list)):
            if data_list[j][column_name] == val and val not in ["", "-"]:
                count += 1
            else:
                break
        for k in range(count):
            spans.append(count if k == 0 else 0)
        i += count
    return spans

def process_excel_data(file_content: bytes, date_input: str):
    """Xử lý logic chính: Đọc Excel -> Filter -> Map Data -> Render HTML"""
    try:
        # Đọc file từ memory (bytes) thay vì file path
        df = pd.read_excel(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Không thể đọc file Excel. Lỗi: {str(e)}")

    # Fix lỗi ngày tháng: Chuyển cột đầu tiên về string format MM/DD/YYYY
    if hasattr(df.iloc[:, 0], 'dt'):
        df.iloc[:, 0] = df.iloc[:, 0].dt.strftime('%m/%d/%Y').fillna('')
    else:
        df.iloc[:, 0] = df.iloc[:, 0].astype(str)

    # Filter theo ngày
    filtered = df[df.iloc[:, 0] == date_input]

    if filtered.empty:
        # Lấy danh sách ngày có trong file để gợi ý lỗi
        available_dates = df.iloc[:, 0].unique().tolist()
        raise LookupError(f"Không tìm thấy dữ liệu cho ngày {date_input}. Các ngày có trong file: {available_dates[:5]}...")

    # Lấy hàng dữ liệu đầu tiên tìm được
    member_data_row = filtered.iloc[0]
    rows = []

    # Duyệt qua các cột nhân sự
    # Kiểm tra bounds để tránh lỗi index nếu file excel thay đổi cấu trúc
    max_col = min(1 + NUM_MEMBERS, len(df.columns))
    
    for i in range(1, max_col):
        member_name = df.columns[i].strip()
        report_text = member_data_row.iloc[i] # Dùng .iloc để an toàn hơn

        if member_name in RESIGNED_MEMBERS:
            continue

        if pd.notnull(report_text) and str(report_text).strip() != "":
            info = USER_INFO.get(member_name, {'project': 'Khác', 'sub_system': '-', 'hdb_lead': '-'})

            # Tách dòng công việc
            tasks = [t.strip('- ').strip() for t in str(report_text).split('\n') if t.strip()]
            formatted_tasks = "".join([f"<div>- {t}</div>" for t in tasks])

            rows.append({
                'project': info['project'],
                'sub_system': info['sub_system'],
                'hdb_lead': info['hdb_lead'],
                'kms_staff': member_name,
                'manday': 1,
                'tasks': formatted_tasks
            })

    if not rows:
        raise LookupError("Tìm thấy ngày nhưng không có nhân sự nào báo cáo công việc (trống dữ liệu).")

    # Logic gộp ô (Rowspan)
    project_spans = calculate_spans(rows, 'project')
    hdb_spans = calculate_spans(rows, 'hdb_lead')

    for idx, row in enumerate(rows):
        row['no'] = idx + 1
        row['p_span'] = project_spans[idx]
        row['h_span'] = hdb_spans[idx]

    # Render Template
    template = jinja2.Environment(loader=jinja2.BaseLoader()).from_string(HTML_TEMPLATE)
    html_content = template.render(boss_name=BOSS_NAME, report_date=date_input, rows=rows)
    
    return html_content

# --- API ENDPOINT ---
@router.post("/generate", response_class=HTMLResponse)
async def generate_report_endpoint(
    report_date: str = Form(..., description="Ngày báo cáo (Format: MM/DD/YYYY hoặc theo format trong Excel)"),
    file: UploadFile = File(..., description="File Excel (.xlsx)")
):
    """
    API import file Excel và trả về HTML Report.
    """
    # 1. Validate file extension
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")

    # 2. Read file content
    content = await file.read()

    # 3. Process logic
    try:
        html_result = process_excel_data(content, report_date)
        return HTMLResponse(content=html_result, status_code=200)
    
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
