# ==========================
# 1️⃣ Imagen base liviana con Python
# ==========================
FROM python:3.10-slim

# ==========================
# 2️⃣ Directorio de trabajo
# ==========================
WORKDIR /app

# ==========================
# 3️⃣ Copiar archivos del proyecto
# ==========================
COPY . /app

# ==========================
# 4️⃣ Instalar dependencias del sistema necesarias para OpenCV + GUI
# ==========================
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libxcb1 \
    qt5-qmake \
    qtbase5-dev \
 && rm -rf /var/lib/apt/lists/*

# ==========================
# 5️⃣ Instalar dependencias de Python
# ==========================
RUN pip install --no-cache-dir mediapipe opencv-python-headless matplotlib

# ==========================
# 6️⃣ Comando por defecto
# ==========================
CMD ["python3", "gestos.py"]
