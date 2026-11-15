# PERISAI-RESPON demo publik (Hugging Face Spaces / Render). Data contoh sintetis saja; unggah log ditolak.
# Build dari AKAR repo (butuh prototype/perisai):
#   docker build -f app/Dockerfile -t perisai-respon-demo:1.1.0 .
#   docker run --rm -p 7860:7860 perisai-respon-demo:1.1.0
FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PERISAI_MODE=demo \
    PERISAI_DATA_DIR=/tmp/perisai-demo \
    PERISAI_ENGINE_DIR=/opt/perisai/prototype \
    OTEL_SDK_DISABLED=true \
    PORT=7860

# Spaces menjalankan kontainer sebagai UID 1000
RUN useradd -m -u 1000 user
WORKDIR /opt/perisai/app
COPY app/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Mesin (tidak diubah) + aplikasi
COPY prototype/perisai /opt/perisai/prototype/perisai
COPY app/perisai_app /opt/perisai/app/perisai_app
COPY app/frontend /opt/perisai/app/frontend

USER user
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"7860\")}/api/ping',timeout=4)"
CMD ["python", "-m", "perisai_app.server"]
