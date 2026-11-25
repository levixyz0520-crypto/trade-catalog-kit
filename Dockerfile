# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY --chown=10001:10001 app.py ./
COPY --chown=10001:10001 .streamlit ./.streamlit
COPY --chown=10001:10001 examples ./examples
RUN --mount=type=secret,id=pip_cert \
    if [ -s /run/secrets/pip_cert ]; then export PIP_CERT=/run/secrets/pip_cert; fi && \
    pip install --no-cache-dir '.[web]' && useradd -m -u 10001 catalog
USER catalog
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)"]
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
