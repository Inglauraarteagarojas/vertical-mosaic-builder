cd ~/Desktop/WEBmarcadores

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Puerto por defecto
ENV PORT=10000

# Comando de inicio
CMD gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120
EOF

git add Dockerfile
git commit -m "Add Dockerfile for reliable deployment"
git push origin main
