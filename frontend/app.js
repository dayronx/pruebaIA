document.addEventListener("DOMContentLoaded", () => {
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSend = document.getElementById('chatbotSend');
    const chatbotBody = document.querySelector('.chatbot-body');

    const BACKEND_URL = 'http://127.0.0.1:8000/api/chat';
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 11);

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

    async function handleTextSubmit() {
        const text = chatbotInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        chatbotInput.value = '';
        await sendChatMessage(text);
    }

    async function sendChatMessage(text) {
        const loadingId = appendMessage('FinBot está procesando...', 'system');

        const requestBody = {
            session_id: sessionId,
            message: text
        };

        try {
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) throw new Error('Status error code: ' + response.status);

            const data = await response.json();
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) loadingElement.remove();

            const botResponseText = data.response || data.output || data.text || 'Operación procesada con éxito.';
            appendMessage(botResponseText, 'system');
        } catch (error) {
            console.error('Error crítico en el pipeline:', error);
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) loadingElement.remove();
            appendMessage('Lo siento, hubo un problema al conectar con el servidor local de FinBot.', 'system');
        }
    }

    function appendMessage(text, sender) {
        if (!text) return null;

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', sender);
        messageDiv.style.alignSelf = sender === 'user' ? 'flex-end' : 'flex-start';

        const textNode = document.createElement('span');
        textNode.innerText = text;
        messageDiv.appendChild(textNode);

        chatbotBody.appendChild(messageDiv);
        chatbotBody.scrollTop = chatbotBody.scrollHeight;

        return null;
    }

    chatbotSend.addEventListener('click', handleTextSubmit);
    chatbotInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleTextSubmit();
    });
});