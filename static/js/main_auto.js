// main_auto.js - Detección automática de marcadores

let selectedFiles = [];
let detectedMarkers = [];

// Elementos DOM
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const selectFilesBtn = document.getElementById('select-files-btn');
const filesList = document.getElementById('files-list');
const filesContainer = document.getElementById('files-container');
const fileCount = document.getElementById('file-count');

const detectBtn = document.getElementById('detect-btn');
const maskBtn = document.getElementById('mask-btn');
const mosaicBtn = document.getElementById('mosaic-btn');

const step1 = document.getElementById('step-1');
const step2 = document.getElementById('step-2');
const step3 = document.getElementById('step-3');
const step4 = document.getElementById('step-4');

const logs = document.getElementById('logs');
const previewContainer = document.getElementById('preview-container');

const markersSection = document.getElementById('markers-section');
const markersTableBody = document.getElementById('markers-table-body');

const statLoaded = document.getElementById('stat-loaded');
const statMarkers = document.getElementById('stat-markers');
const statFlowers = document.getElementById('stat-flowers');

// ✅ EVENT LISTENERS PARA SELECCIÓN DE ARCHIVOS

// Botón de selección
selectFilesBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

// Drag & Drop en toda la zona
dropZone.addEventListener('click', (e) => {
    if (e.target === dropZone || e.target.closest('#drop-zone')) {
        fileInput.click();
    }
});

dropZone.addEventListener('dragover', (e) => { 
    e.preventDefault(); 
    dropZone.classList.add('border-blue-500', 'bg-blue-50'); 
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-blue-500', 'bg-blue-50');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-blue-500', 'bg-blue-50');
    handleFiles(Array.from(e.dataTransfer.files));
});

// Cambio en input file
fileInput.addEventListener('change', (e) => {
    handleFiles(Array.from(e.target.files));
});

function handleFiles(files) {
    // Filtrar solo imágenes
    selectedFiles = files.filter(f => {
        const ext = f.name.split('.').pop().toLowerCase();
        return ['jpg', 'jpeg', 'png'].includes(ext);
    });
    
    if (selectedFiles.length === 0) {
        addLog('⚠️ No se seleccionaron imágenes válidas', 'warning');
        return;
    }
    
    filesList.classList.remove('hidden');
    filesContainer.innerHTML = selectedFiles.map((f, i) => 
        `<div class="text-sm p-2 bg-white rounded border border-gray-200 flex justify-between items-center">
            <span class="flex-1 truncate">📄 ${f.name}</span>
            <span class="text-gray-500 text-xs ml-2">${formatSize(f.size)}</span>
        </div>`
    ).join('');
    
    fileCount.textContent = `${selectedFiles.length} archivo${selectedFiles.length > 1 ? 's' : ''}`;
    statLoaded.textContent = selectedFiles.length;
    
    // Habilitar botón de detección
    detectBtn.disabled = false;
    
    // Activar paso 1
    activateStep(1);
    
    addLog(`📤 ${selectedFiles.length} imagen${selectedFiles.length > 1 ? 'es' : ''} seleccionada${selectedFiles.length > 1 ? 's' : ''}`, 'success');
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function activateStep(stepNum) {
    [step1, step2, step3, step4].forEach((el, i) => {
        el.classList.remove('active', 'completed');
        if (i + 1 === stepNum) {
            el.classList.add('active');
        } else if (i + 1 < stepNum) {
            el.classList.add('completed');
        }
    });
}

function addLog(msg, level = 'info') {
    const time = new Date().toLocaleTimeString();
    let icon = 'ℹ️';
    let color = 'text-cyan-400';
    
    if (level === 'success') { icon = '✅'; color = 'text-green-400'; }
    if (level === 'warning') { icon = '⚠️'; color = 'text-yellow-400'; }
    if (level === 'error') { icon = '❌'; color = 'text-red-400'; }
    
    logs.innerHTML += `<p><span class="text-gray-500">${time}</span> <span class="${color}">${icon}</span> ${msg}</p>`;
    logs.scrollTop = logs.scrollHeight;
}

function showSpinner(btn) {
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<div class="spinner mx-auto"></div>';
    btn.disabled = true;
    return originalContent;
}

function hideSpinner(btn, originalContent) {
    btn.innerHTML = originalContent;
    btn.disabled = false;
}

// PASO 1: Detectar Marcadores
detectBtn.addEventListener('click', async () => {
    const originalContent = showSpinner(detectBtn);
    
    try {
        addLog('📤 Subiendo archivos al servidor...');
        
        // Subir archivos
        const formData = new FormData();
        selectedFiles.forEach(f => formData.append('files[]', f));
        
        const uploadRes = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadRes.ok) throw new Error('Error al subir archivos');
        
        const uploadData = await uploadRes.json();
        addLog(`✅ ${uploadData.count} archivo${uploadData.count > 1 ? 's' : ''} subido${uploadData.count > 1 ? 's' : ''}`, 'success');
        
        // Detectar marcadores
        addLog('🔍 Analizando imágenes y detectando marcadores...');
        
        const detectRes = await fetch('/detect_markers', {
            method: 'POST'
        });
        
        if (!detectRes.ok) throw new Error('Error al detectar marcadores');
        
        const detectData = await detectRes.json();
        detectedMarkers = detectData.markers;
        
        addLog(`✅ ${detectData.count} marcador${detectData.count > 1 ? 'es' : ''} detectado${detectData.count > 1 ? 's' : ''}`, 'success');
        
        // Mostrar tabla de marcadores
        displayMarkers(detectedMarkers);
        
        // Actualizar estadísticas
        statMarkers.textContent = detectData.count;
        
        // Activar paso 2 y habilitar botón de máscaras
        activateStep(2);
        maskBtn.disabled = false;
        
    } catch (error) {
        addLog(`❌ Error: ${error.message}`, 'error');
    } finally {
        hideSpinner(detectBtn, originalContent);
    }
});

function displayMarkers(markers) {
    markersSection.classList.remove('hidden');
    markersTableBody.innerHTML = markers.map((m, i) => `
        <tr class="hover:bg-gray-50">
            <td class="px-4 py-2 font-semibold">${i + 1}</td>
            <td class="px-4 py-2 font-mono text-xs">${m.filename}</td>
            <td class="px-4 py-2">
                <span class="px-3 py-1 rounded-full bg-blue-100 text-blue-700 font-bold text-sm">${m.marcador}</span>
            </td>
            <td class="px-4 py-2">
                <span class="text-green-600 font-semibold">✓ Detectado</span>
            </td>
        </tr>
    `).join('');
}

// PASO 2: Crear Máscaras
maskBtn.addEventListener('click', async () => {
    const originalContent = showSpinner(maskBtn);
    
    try {
        addLog('🎭 Generando máscaras binarias...');
        
        const maskRes = await fetch('/create_masks', {
            method: 'POST'
        });
        
        if (!maskRes.ok) throw new Error('Error al crear máscaras');
        
        const maskData = await maskRes.json();
        addLog(`✅ ${maskData.count} máscara${maskData.count > 1 ? 's' : ''} creada${maskData.count > 1 ? 's' : ''}`, 'success');
        
        // Activar paso 3 y habilitar botón de mosaico
        activateStep(3);
        mosaicBtn.disabled = false;
        
    } catch (error) {
        addLog(`❌ Error: ${error.message}`, 'error');
    } finally {
        hideSpinner(maskBtn, originalContent);
    }
});

// PASO 3: Generar Mosaico
mosaicBtn.addEventListener('click', async () => {
    const originalContent = showSpinner(mosaicBtn);
    
    try {
        addLog('🗺️ Ensamblando mosaico vertical...');
        
        const mosaicRes = await fetch('/create_mosaic', {
            method: 'POST'
        });
        
        if (!mosaicRes.ok) throw new Error('Error al generar mosaico');
        
        const mosaicData = await mosaicRes.json();
        
        addLog(`✅ Mosaico generado con ${mosaicData.images_loaded} imágenes`, 'success');
        addLog(`🌼 ${mosaicData.flower_count} flores amarillas detectadas`, 'success');
        
        // Actualizar estadísticas
        statFlowers.textContent = mosaicData.flower_count;
        
        // Activar paso 4
        activateStep(4);
        
        // Habilitar descargas
        document.getElementById('download-mask').disabled = false;
        document.getElementById('download-color').disabled = false;
        
        // Cargar preview automáticamente
        loadPreview('mask');
        
        addLog('🎉 ¡Proceso completado!', 'success');
        
    } catch (error) {
        addLog(`❌ Error: ${error.message}`, 'error');
    } finally {
        hideSpinner(mosaicBtn, originalContent);
    }
});

// Preview
document.getElementById('preview-mask').addEventListener('click', () => {
    loadPreview('mask');
    document.getElementById('preview-mask').classList.add('bg-blue-100', 'text-blue-700');
    document.getElementById('preview-mask').classList.remove('bg-gray-100', 'text-gray-700');
    document.getElementById('preview-color').classList.add('bg-gray-100', 'text-gray-700');
    document.getElementById('preview-color').classList.remove('bg-blue-100', 'text-blue-700');
});

document.getElementById('preview-color').addEventListener('click', () => {
    loadPreview('color');
    document.getElementById('preview-color').classList.add('bg-blue-100', 'text-blue-700');
    document.getElementById('preview-color').classList.remove('bg-gray-100', 'text-gray-700');
    document.getElementById('preview-mask').classList.add('bg-gray-100', 'text-gray-700');
    document.getElementById('preview-mask').classList.remove('bg-blue-100', 'text-blue-700');
});

function loadPreview(type) {
    addLog(`📸 Cargando preview ${type}...`);
    previewContainer.innerHTML = `
        <img src="/preview/${type}?t=${Date.now()}" 
             class="max-w-full max-h-full object-contain rounded" 
             onerror="this.parentElement.innerHTML='<p class=text-red-500>❌ Preview no disponible</p>'"
             onload="console.log('Preview cargado')"
        />
    `;
}

// Downloads
document.getElementById('download-mask').addEventListener('click', () => {
    addLog('⬇️ Descargando mosaico máscara...');
    window.location.href = '/download/mask';
});

document.getElementById('download-color').addEventListener('click', () => {
    addLog('⬇️ Descargando mosaico color...');
    window.location.href = '/download/color';
});

// Inicialización
addLog('🤖 Sistema de detección automática iniciado');
addLog('📝 Selecciona tus imágenes DJI para comenzar');
