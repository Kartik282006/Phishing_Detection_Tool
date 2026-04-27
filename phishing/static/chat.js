// Chatbot Frontend Logic

const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('chat-send-btn');
// Note: toggle-chat-btn and .chat-section removed in v2.0 redesign
const voiceBtn = document.getElementById('voice-btn');

// Speech Recognition Setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let isListening = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = function() {
        isListening = true;
        if(voiceBtn) voiceBtn.classList.add('listening');
        if(userInput) userInput.placeholder = "Listening...";
    };

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        if(userInput) userInput.value = transcript;
        sendMessage(); // Auto send after recording
    };

    recognition.onerror = function(event) {
        console.error("Speech recognition error", event.error);
        stopListening();
    };

    recognition.onend = function() {
        stopListening();
    };
} else {
    // Hide or disable voice btn if not supported
    if(voiceBtn) voiceBtn.style.display = 'none';
}

function stopListening() {
    isListening = false;
    if(voiceBtn) {
        voiceBtn.classList.remove('listening');
        if(userInput) userInput.placeholder = "Type a message or say 'Scan example.com'...";
    }
}

// Text to Speech
function speakResponse(text) {
    if (!window.speechSynthesis) return;
    
    // Remove markdown symbols for better speech
    const cleanText = text.replace(/[*_#]/g, '').replace(/\[.*?\]\(.*?\)/g, 'link');
    
    window.speechSynthesis.cancel(); // Cancel ongoing speech
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    
    window.speechSynthesis.speak(utterance);
}


// Markdown parser (marked.js) is expected to be loaded in dashboard.html

function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message');
    msgDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');

    if (sender === 'bot') {
        // Use marked for safe HTML rendering if available, else text
        if (typeof marked !== 'undefined') {
            msgDiv.innerHTML = marked.parse(text);
        } else {
            msgDiv.innerText = text;
        }
    } else {
        msgDiv.innerText = text;
    }

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    userInput.value = '';
    userInput.style.height = 'auto'; // Reset height

    // Show typing
    const loadingDiv = document.createElement('div');
    loadingDiv.classList.add('message', 'bot-message', 'loading');
    loadingDiv.innerText = 'Analyzing...';
    chatBox.appendChild(loadingDiv);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        chatBox.removeChild(loadingDiv);

        appendMessage(data.response, 'bot');
        speakResponse(data.response);

    } catch (error) {
        if (chatBox.contains(loadingDiv)) chatBox.removeChild(loadingDiv);
        appendMessage("Error: Could not reach the server.", 'bot');
        console.error(error);
    }
}

// Event Listeners
if (userInput) {
    userInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    userInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
}

if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
        if (!recognition) return;
        if (isListening) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
}
