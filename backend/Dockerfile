FROM python:3.12-slim

# Instalar dependencias del sistema necesarias para compilar extensiones
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto donde corre la app
EXPOSE 5000

# Comando de inicio
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "manage:app"]
