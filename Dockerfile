FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
EXPOSE ${PORT}
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT} --workers 1 --timeout 10"]
