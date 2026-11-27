FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
RUN useradd --system --no-create-home appuser
COPY . .
USER appuser
EXPOSE 8000
CMD ["python", "-m", "sortyield.delivery", "serve"]
