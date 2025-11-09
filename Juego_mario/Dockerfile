# === Etapa base ===
FROM python:3.10-slim

# Evita preguntas interactivas de apt
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias para Pygame y renderizado
RUN apt-get update && apt-get install -y \
    python3-tk \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libglu1-mesa \
    libgl1 \
    libx11-6 \
 && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos del juego
COPY . /app

# Instalar dependencias de Python
RUN pip install --no-cache-dir pygame

# Comando por defecto
CMD ["python", "mario.py"]
