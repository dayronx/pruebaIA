document.addEventListener("DOMContentLoaded", () => {
    // Referencias principales del Chatbot
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSend = document.getElementById('chatbotSend');
    const chatbotBody = document.querySelector('.chatbot-body');
    
    // Referencias del nuevo Selector de Modo (Switch)
    const outputModeToggle = document.getElementById('outputModeToggle');
    const modeTxtChat = document.getElementById('modeTxtChat');
    const modeTxtVoice = document.getElementById('modeTxtVoice');

    // Referencias Multimedia
    const btnBrowseImage = document.getElementById('btnBrowseImage');
    const imageInput = document.getElementById('imageInput');
    const btnAudioAction = document.getElementById('btnAudioAction');
    const previewArea = document.getElementById('previewArea');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const removeImage = document.getElementById('removeImage');
    const voicePreviewContainer = document.getElementById('voicePreviewContainer');

    const BACKEND_URL = 'http://127.0.0.1:8000/api/chat';
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 11);

    let selectedImageBase64 = null;
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    // --- LOGICA DEL SWITCH ---
    outputModeToggle.addEventListener('change', () => {
        if (outputModeToggle.checked) {
            modeTxtVoice.classList.add('active');
            modeTxtChat.classList.remove('active');
        } else {
            modeTxtChat.classList.add('active');
            modeTxtVoice.classList.remove('active');
        }
    });

    // --- UI BASICA ---
    chatbotToggle.addEventListener('click', () => {
        chatbotToggle.style.display = 'none';
        chatbotWindow.style.display = 'flex';
        chatbotInput.focus();
    });

    chatbotClose.addEventListener('click', (e) => {
        e.stopPropagation();
        chatbotWindow.style.display = 'none';
        chatbotToggle.style.display = 'flex';
    });

    // --- PIPELINE DE IMÁGENES ---
    btnBrowseImage.addEventListener('click', () => imageInput.click());
    
    imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                selectedImageBase64 = event.target.result;
                imagePreview.src = selectedImageBase64;
                previewArea.style.display = 'flex';
                imagePreviewContainer.style.display = 'inline-block';
            };
            reader.readAsDataURL(file);
        }
    });

    removeImage.addEventListener('click', () => {
        selectedImageBase64 = null;
        imageInput.value = '';
        imagePreviewContainer.style.display = 'none';
        checkPreviewAreaState();
    });

    // --- PIPELINE DE AUDIO ---
    btnAudioAction.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    reader.onloadend = async () => {
                        const base64Audio = reader.result;
                        appendMessage('🎤 Nota de voz enviada', 'user');
                        await sendChatMessage('', null, base64Audio);
                    };
                    stream.getTracks().forEach(track => track.stop());
                };
                mediaRecorder.start();
                isRecording = true;
                btnAudioAction.classList.add('recording');
                previewArea.style.display = 'flex';
                voicePreviewContainer.style.display = 'flex';
            } catch (err) { alert("Permiso de micrófono denegado."); }
        } else {
            mediaRecorder.stop();
            isRecording = false;
            btnAudioAction.classList.remove('recording');
            voicePreviewContainer.style.display = 'none';
            checkPreviewAreaState();
        }
    });

    // --- ENVÍO UNIFICADO ---
    async function handleTextSubmit() {
        const text = chatbotInput.value.trim();
        if (!text && !selectedImageBase64) return;

        appendMessage(text, 'user', selectedImageBase64);
        const imageToSend = selectedImageBase64;
        
        chatbotInput.value = '';
        selectedImageBase64 = null;
        imageInput.value = '';
        imagePreviewContainer.style.display = 'none';
        checkPreviewAreaState();

        await sendChatMessage(text, imageToSend, null);
    }

    async function sendChatMessage(text, base64Image = null, base64Audio = null) {
        const loadingId = 'loading_' + Date.now();
        appendMessage('FinBot está procesando...', 'system', null, loadingId);
        
        // Aquí capturamos el modo seleccionado en el Switch
        const outputMode = outputModeToggle.checked ? "audio" : "text";

        const requestBody = {
            session_id: sessionId,
            message: text || "",
            image_base64: base64Image,
            audio_base64: base64Audio,
            output_mode: outputMode // <- Se envía la preferencia al servidor
        };

        try {
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            const data = await response.json();
            document.getElementById(loadingId)?.remove();
            
            appendMessage(data.response, 'system');
            
            // Si el servidor devuelve audio, lo reproducimos
            if (data.audioUrl) {
                new Audio(`http://127.0.0.1:8000${data.audioUrl}`).play();
            }
        } catch (error) {
            document.getElementById(loadingId)?.remove();
            appendMessage('Error de conexión con el servidor.', 'system');
        }
    }

    // --- FUNCIONES AUXILIARES ---
    function appendMessage(text, sender, imageSrc = null, uniqueId = null) {
        if (!text && !imageSrc) return;
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', sender);
        if (uniqueId) messageDiv.id = uniqueId;
        
        if (imageSrc) {
            const img = document.createElement('img');
            img.src = imageSrc;
            img.classList.add('chat-image-attachment');
            messageDiv.appendChild(img);
        }
        if (text) {
            const span = document.createElement('span');
            span.innerText = text;
            messageDiv.appendChild(span);
        }
        chatbotBody.appendChild(messageDiv);
        chatbotBody.scrollTop = chatbotBody.scrollHeight;
    }

    function checkPreviewAreaState() {
        if (imagePreviewContainer.style.display === 'none' && voicePreviewContainer.style.display === 'none') {
            previewArea.style.display = 'none';
        }
    }

    chatbotSend.addEventListener('click', handleTextSubmit);
    chatbotInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleTextSubmit(); });
});