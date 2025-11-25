FROM python:3.12-slim

# dependencias de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# instalar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copiar el resto del código
COPY . .

# asegurar que Python encuentre /app
ENV PYTHONPATH=/app

# variables útiles para flask
ENV FLASK_ENV=development
ENV FLASK_APP=manage:app

EXPOSE 5000

# iniciar con gunicorn
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "manage:app"]
