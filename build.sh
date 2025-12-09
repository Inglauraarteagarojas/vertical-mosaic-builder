#!/bin/bash
# build.sh - Script de construcción para Render

set -e  # Salir si hay error

echo "🔧 Actualizando sistema..."
apt-get update

echo "📦 Instalando Tesseract OCR..."
apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev

echo "📦 Instalando dependencias de Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Build completado exitosamente"
```

### 4. `.gitignore`
```
# Entornos virtuales
.venv/
.venv311/
venv/
ENV/
env/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Flask
instance/
.webassets-cache

# Archivos de usuario (uploads temporales)
uploads/*
!uploads/.gitkeep
masks/*
!masks/.gitkeep
mosaics/*
!mosaics/.gitkeep
results/*
!results/.gitkeep

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Environment variables
.env
.env.local