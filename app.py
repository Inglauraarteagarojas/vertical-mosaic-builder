cd ~/Desktop/WEBmarcadores

# Crear app.py corregido (sin duplicados)
cat > app.py << 'EOFAPP'
#!/usr/bin/env python3
"""
Vertical Mosaic Builder - Versión Inteligente
Detecta automáticamente marcadores en imágenes DJI
Optimizado para despliegue en Render
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from datetime import datetime
import re
import pytesseract
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'vertical_mosaic_auto_2024')

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MASKS_FOLDER = os.path.join(BASE_DIR, 'masks')
MOSAICS_FOLDER = os.path.join(BASE_DIR, 'mosaics')
RESULTS_FOLDER = os.path.join(BASE_DIR, 'results')

# Crear carpetas
for folder in [UPLOAD_FOLDER, MASKS_FOLDER, MOSAICS_FOLDER, RESULTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'JPG', 'PNG'}

# Estado global
processing_state = {
    'status': 'idle',
    'progress': 0,
    'logs': [],
    'images_loaded': 0,
    'images_total': 0,
    'detected_markers': [],
    'flower_count': 0
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def add_log(message, level='info'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message
    }
    processing_state['logs'].append(log_entry)
    print(f"[{level.upper()}] {message}")

def detectar_marcador_en_imagen(imagen_path):
    """Detecta el marcador en la imagen usando OCR"""
    try:
        img = cv2.imread(imagen_path)
        if img is None:
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        regiones = [
            gray[0:int(h*0.2), int(w*0.8):w],
            gray[int(h*0.8):h, int(w*0.8):w],
            gray[0:int(h*0.2), 0:int(w*0.2)],
            gray[int(h*0.8):h, 0:int(w*0.2)],
        ]
        
        marcadores_encontrados = []
        
        for region in regiones:
            _, thresh = cv2.threshold(region, 150, 255, cv2.THRESH_BINARY)
            
            try:
                texto = pytesseract.image_to_string(thresh, config='--psm 6')
                patron_numero = re.findall(r'\b([1-9]|[1-3][0-9])\b', texto)
                patron_letra = re.findall(r'\b([A-J]\d{1,2})\b', texto)
                patron_especial = re.findall(r'\b(4[35])\b', texto)
                
                marcadores_encontrados.extend(patron_numero)
                marcadores_encontrados.extend(patron_letra)
                marcadores_encontrados.extend(patron_especial)
            except:
                continue
        
        if marcadores_encontrados:
            for m in marcadores_encontrados:
                if any(c.isalpha() for c in str(m)):
                    return m
            return marcadores_encontrados[0]
        
        filename = os.path.basename(imagen_path)
        match = re.search(r'DJI_(\d+)', filename)
        if match:
            numero_archivo = int(match.group(1))
            if 535 <= numero_archivo <= 543:
                return str(numero_archivo - 534)
            elif numero_archivo == 544:
                return 'A41'
            elif 545 <= numero_archivo <= 553:
                letras = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
                idx = numero_archivo - 545
                return f"{letras[idx]}{11 + idx}"
            elif numero_archivo == 554:
                return '45'
            elif 555 <= numero_archivo <= 563:
                return str(numero_archivo - 534)
            elif numero_archivo == 565:
                return '43'
            elif 566 <= numero_archivo <= 574:
                return str(numero_archivo - 535)
        
        return None
    except Exception as e:
        add_log(f"Error detectando marcador: {str(e)}", 'error')
        return None

def ordenar_marcadores(lista_marcadores):
    """Ordena los marcadores"""
    def clave_orden(item):
        marcador = item['marcador']
        if marcador.isdigit():
            num = int(marcador)
            if 1 <= num <= 9:
                return (1, num)
            elif 21 <= num <= 29:
                return (4, num)
            elif 31 <= num <= 38:
                return (6, num)
            elif num == 45:
                return (3, 20)
            elif num == 43:
                return (5, 30)
        if marcador == 'A41':
            return (2, 10)
        if len(marcador) == 3 and marcador[0].isalpha():
            orden_letra = ord(marcador[0]) - ord('B') + 11
            return (2, orden_letra)
        return (99, 0)
    return sorted(lista_marcadores, key=clave_orden)

def crear_mascara(imagen_path, output_path):
    """Crea máscara binaria"""
    try:
        img = cv2.imread(imagen_path)
        if img is None:
            return False
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        cv2.imwrite(output_path, mask)
        return True
    except Exception as e:
        add_log(f"Error creando máscara: {str(e)}", 'error')
        return False

def recortar_seccion(imagen, pct_inicio, pct_fin):
    """Recorta sección vertical"""
    altura = imagen.shape[0]
    pixel_inicio = int(altura * pct_inicio)
    pixel_fin = int(altura * pct_fin)
    if pixel_fin <= pixel_inicio:
        pixel_fin = altura
    return imagen[pixel_inicio:pixel_fin, :]

def crear_mosaico_automatico(imagenes_ordenadas, folder, output_path):
    """Crea mosaico con las imágenes ordenadas"""
    add_log("Creando mosaico...", 'info')
    secciones = []
    cargadas = 0
    
    for idx, item in enumerate(imagenes_ordenadas):
        filepath = item['filepath']
        marcador = item['marcador']
        
        if idx == 0:
            pct_inicio, pct_fin = 0.66, 1.0
        elif idx == len(imagenes_ordenadas) - 1:
            pct_inicio, pct_fin = 0.5, 1.0
        else:
            pct_inicio, pct_fin = 0.5, 1.0
        
        archivo_base = os.path.basename(filepath)
        posibles_rutas = [
            os.path.join(folder, f"mask_total_{archivo_base}"),
            os.path.join(folder, archivo_base),
            filepath
        ]
        
        img = None
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                img = cv2.imread(ruta)
                if img is not None:
                    break
        
        if img is not None:
            seccion = recortar_seccion(img, pct_inicio, pct_fin)
            secciones.append(seccion)
            cargadas += 1
            add_log(f"✓ Marcador {marcador} ({idx+1}/{len(imagenes_ordenadas)})", 'info')
        else:
            add_log(f"✗ Marcador {marcador} no encontrado", 'warning')
    
    processing_state['images_loaded'] = cargadas
    processing_state['images_total'] = len(imagenes_ordenadas)
    
    if not secciones:
        return False
    
    ancho_max = max(s.shape[1] for s in secciones)
    secciones_ajustadas = []
    
    for sec in secciones:
        if sec.shape[1] != ancho_max:
            factor = float(ancho_max) / float(sec.shape[1])
            nueva_altura = int(sec.shape[0] * factor)
            secciones_ajustadas.append(cv2.resize(sec, (ancho_max, nueva_altura)))
        else:
            secciones_ajustadas.append(sec)
    
    mosaico = np.vstack(secciones_ajustadas)
    cv2.imwrite(output_path, mosaico)
    add_log(f"✓ Mosaico guardado: {cargadas} marcadores", 'success')
    return True

def contar_flores(imagen_path):
    """Cuenta flores amarillas"""
    try:
        img = cv2.imread(imagen_path)
        if img is None:
            return 0
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower = np.array([20, 100, 100])
        upper = np.array([30, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        flores = [c for c in contours if cv2.contourArea(c) > 50]
        resultado = img.copy()
        cv2.drawContours(resultado, flores, -1, (0, 255, 0), 2)
        output = os.path.join(RESULTS_FOLDER, 'flores_detectadas.jpg')
        cv2.imwrite(output, resultado)
        return len(flores)
    except Exception as e:
        add_log(f"Error: {str(e)}", 'error')
        return 0

# RUTAS
@app.route('/')
def index():
    return render_template('index_auto.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        files = request.files.getlist('files[]')
        uploaded = []
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                uploaded.append({'filename': filename, 'path': filepath})
                add_log(f"📤 Subido: {filename}", 'info')
        return jsonify({'success': True, 'files': uploaded, 'count': len(uploaded)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detect_markers', methods=['POST'])
def detect_markers():
    try:
        add_log("🔍 Detectando marcadores...", 'info')
        files = os.listdir(UPLOAD_FOLDER)
        imagenes_con_marcadores = []
        
        for filename in files:
            if allowed_file(filename):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                marcador = detectar_marcador_en_imagen(filepath)
                if marcador:
                    imagenes_con_marcadores.append({
                        'filename': filename,
                        'filepath': filepath,
                        'marcador': marcador
                    })
                    add_log(f"  ✓ {filename} → {marcador}", 'info')
                else:
                    add_log(f"  ✗ {filename} → No detectado", 'warning')
        
        imagenes_ordenadas = ordenar_marcadores(imagenes_con_marcadores)
        processing_state['detected_markers'] = imagenes_ordenadas
        add_log(f"✅ {len(imagenes_ordenadas)} marcadores detectados", 'success')
        
        return jsonify({'success': True, 'markers': imagenes_ordenadas, 'count': len(imagenes_ordenadas)})
    except Exception as e:
        add_log(f"Error: {str(e)}", 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/create_masks', methods=['POST'])
def create_masks():
    try:
        add_log("🎭 Creando máscaras...", 'info')
        imagenes = processing_state.get('detected_markers', [])
        if not imagenes:
            files = os.listdir(UPLOAD_FOLDER)
            imagenes = [{'filepath': os.path.join(UPLOAD_FOLDER, f), 'filename': f} 
                       for f in files if allowed_file(f)]
        
        mascaras_creadas = 0
        for item in imagenes:
            filepath = item['filepath']
            filename = item.get('filename', os.path.basename(filepath))
            output_path = os.path.join(MASKS_FOLDER, f"mask_total_{filename}")
            if crear_mascara(filepath, output_path):
                mascaras_creadas += 1
                add_log(f"  ✓ Máscara: {filename}", 'info')
        
        add_log(f"✅ {mascaras_creadas} máscaras creadas", 'success')
        return jsonify({'success': True, 'count': mascaras_creadas})
    except Exception as e:
        add_log(f"Error: {str(e)}", 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/create_mosaic', methods=['POST'])
def create_mosaic():
    try:
        add_log("🗺️ Generando mosaico...", 'info')
        imagenes_ordenadas = processing_state.get('detected_markers', [])
        if not imagenes_ordenadas:
            return jsonify({'success': False, 'error': 'Primero detecta marcadores'}), 400
        
        mask_mosaic = os.path.join(MOSAICS_FOLDER, 'mosaico_masks.png')
        crear_mosaico_automatico(imagenes_ordenadas, MASKS_FOLDER, mask_mosaic)
        
        color_mosaic = os.path.join(MOSAICS_FOLDER, 'mosaico_color.png')
        crear_mosaico_automatico(imagenes_ordenadas, UPLOAD_FOLDER, color_mosaic)
        
        flower_count = contar_flores(color_mosaic)
        processing_state['flower_count'] = flower_count
        add_log("✅ Mosaico completado", 'success')
        
        return jsonify({
            'success': True,
            'flower_count': flower_count,
            'images_loaded': processing_state['images_loaded'],
            'images_total': processing_state['images_total']
        })
    except Exception as e:
        add_log(f"Error: {str(e)}", 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/status')
def status():
    return jsonify(processing_state)

@app.route('/logs')
def logs():
    return jsonify({'logs': processing_state['logs']})

@app.route('/preview/<tipo>')
def preview(tipo):
    try:
        if tipo == 'mask':
            path = os.path.join(MOSAICS_FOLDER, 'mosaico_masks.png')
        else:
            path = os.path.join(MOSAICS_FOLDER, 'mosaico_color.png')
        if os.path.exists(path):
            return send_file(path, mimetype='image/png')
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<tipo>')
def download(tipo):
    try:
        if tipo == 'mask':
            path = os.path.join(MOSAICS_FOLDER, 'mosaico_masks.png')
        elif tipo == 'color':
            path = os.path.join(MOSAICS_FOLDER, 'mosaico_color.png')
        else:
            path = os.path.join(RESULTS_FOLDER, 'flores_detectadas.jpg')
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'vertical-mosaic-builder'})

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 VERTICAL MOSAIC BUILDER")
    print("=" * 70)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
EOFAPP





