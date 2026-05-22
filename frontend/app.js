document.addEventListener("DOMContentLoaded", () => {
    // =========================
    // REFERENCIAS
    // =========================
    const toggle = document.getElementById('chat-toggle');
    const windowChat = document.getElementById('chat-window');
    const closeChat = document.getElementById('close-chat');
    const sendBtn = document.querySelector('.send-btn');
    const chatInput = document.getElementById('chat-input');
    const chatBody = document.getElementById('chat-body');
    const outputModeToggle = document.querySelector('.mode-toggle .switch input');
    const plusBtn = document.querySelector('.icon-btn');
    const micBtn = document.querySelector('.mic-btn');

    // =========================
    // CONFIGURACIÓN
    // =========================
    const BACKEND_URL = 'http://127.0.0.1:8000';
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 11);

    let selectedImageBase64 = null;
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    const imageInput = document.createElement('input');
    imageInput.type = 'file';
    imageInput.accept = 'image/*';
    imageInput.style.display = 'none';
    document.body.appendChild(imageInput);

    // =========================
    // FUNCIONES AUXILIARES
    // =========================
    function appendMessage(text, sender, imageSrc = null, uniqueId = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        if (uniqueId) messageDiv.id = uniqueId;

        if (imageSrc) {
            const img = document.createElement('img');
            img.src = imageSrc;
            img.style.maxWidth = '150px';
            img.style.display = 'block';
            messageDiv.appendChild(img);
        }
        if (text) {
            const span = document.createElement('span');
            span.innerText = text;
            messageDiv.appendChild(span);
        }
        chatBody.appendChild(messageDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
        return messageDiv;
    }

    async function sendChatMessage(text, base64Image = null, base64Audio = null) {
        const loadingId = 'load_' + Date.now();
        appendMessage('Ampere pensando...', 'system', null, loadingId);

        try {
            const response = await fetch(`${BACKEND_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: text || "",
                    image_base64: base64Image,
                    audio_base64: base64Audio,
                    output_mode: outputModeToggle?.checked ? "audio" : "text"
                })
            });

            const data = await response.json();
            document.getElementById(loadingId)?.remove();

            if (data.response) appendMessage(data.response, 'system');

            if (data.audioUrl) {
                const audioPath = data.audioUrl.startsWith('http') ? data.audioUrl : `${BACKEND_URL}${data.audioUrl}`;
                
                const audioContainer = document.createElement('div');
                audioContainer.style.marginTop = '10px';

                const audioElement = document.createElement('audio');
                audioElement.controls = true;
                audioElement.src = audioPath;
                audioElement.style.width = '100%';

                audioContainer.appendChild(audioElement);
                chatBody.appendChild(audioContainer);
                
                // Intento de reproducción automática (con gestión de error por política del navegador)
                audioElement.play().catch(e => console.warn("Autoplay bloqueado, el usuario debe dar play manualmente."));
                
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        } catch (error) {
            document.getElementById(loadingId)?.remove();
            appendMessage('Error de conexión con el servidor.', 'system');
        }
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text && !selectedImageBase64) return;
        appendMessage(text, 'user', selectedImageBase64);
        const imageToSend = selectedImageBase64;
        chatInput.value = '';
        selectedImageBase64 = null;
        await sendChatMessage(text, imageToSend, null);
    }

    // =========================
    // LISTENERS
    // =========================
    toggle.addEventListener('click', () => windowChat.classList.remove('hidden'));
    closeChat.addEventListener('click', () => windowChat.classList.add('hidden'));
    plusBtn.addEventListener('click', () => imageInput.click());
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

    // Micrófono con verificación de seguridad
    micBtn.addEventListener('click', async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Tu navegador no soporta grabación de audio o no estás en una conexión segura (localhost/HTTPS).");
            return;
        }

        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data && e.data.size > 0) {
                        audioChunks.push(e.data);
                    }
                };
                mediaRecorder.onstop = async () => {
                    if (audioChunks.length === 0) {
                        appendMessage('No se detectó audio.', 'system');
                        return;
                    }
                    const mimeType = mediaRecorder.mimeType || 'audio/webm';
                    const audioBlob = new Blob(audioChunks, { type: mimeType });
                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    reader.onloadend = async () => {
                        appendMessage('Enviando nota de voz...', 'user');
                        await sendChatMessage('', null, reader.result);
                    };
                    stream.getTracks().forEach(track => track.stop());
                };
                mediaRecorder.start();
                isRecording = true;
                micBtn.classList.add('recording');
            } catch (err) { alert("Error de micrófono: " + err.message); }
        } else {
            mediaRecorder.stop();
            isRecording = false;
            micBtn.classList.remove('recording');
        }
    });
});