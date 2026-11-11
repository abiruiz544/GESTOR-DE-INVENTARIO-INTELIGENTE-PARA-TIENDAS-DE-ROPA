FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY demo demo
COPY datos_iniciales datos_iniciales
# En la nube los datos van en /var/data (con disco persistente si el plan lo permite)
ENV DATA_DIR=/var/data
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
