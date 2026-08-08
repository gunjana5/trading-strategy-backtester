# Dockerfile - flask api behind gunicorn (single worker is fine for this demo)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5050
# workers=1 keeps sqlite simple; threads for a few concurrent paper runs
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --access-logfile - --error-logfile -
