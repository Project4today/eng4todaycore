# Dockerfile mẫu cho FastAPI
FROM python:3.9-slim

WORKDIR /app

# Copy file requirements trước để tận dụng cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Mở cổng 8000
EXPOSE 8000

# Lệnh chạy app (Host 0.0.0.0 là bắt buộc trên Docker)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]