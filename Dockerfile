
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY index.html .
COPY script.js .
COPY style.css .

RUN mkdir -p uploads
EXPOSE 8000
ENV GEMINI_API_KEY=""
CMD ["python", "main.py"]