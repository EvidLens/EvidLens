document.addEventListener('DOMContentLoaded', function() {
    console.log('EvidLens JS Loaded v2.0.0');
    const chatbot = document.getElementById('chatbot-container');
    if(chatbot) {
        chatbot.innerHTML = `<button id="chatBtn" class="btn-primary shadow-lg">Ask EvidLens AI</button>`;
        document.getElementById('chatBtn').onclick = () => alert('Chatbot loading...');
    }
});
