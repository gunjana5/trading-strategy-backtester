# flask api behind gunicorn; workers=1 keeps sqlite simple
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5050
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --access-logfile - --error-logfile -
