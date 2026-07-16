document.addEventListener('DOMContentLoaded', function() {
    console.log('EvidLens JS Loaded v2.0.0');
    
    let chatbot = document.getElementById('chatbot-container');
    if(!chatbot) {
        chatbot = document.createElement('div');
        chatbot.id = 'chatbot-container';
        document.body.appendChild(chatbot);
    }
    
    chatbot.innerHTML = `<button id="chatBtn" class="btn-primary shadow-lg">Ask EvidLens AI</button>`;
    
    document.getElementById('chatBtn').onclick = () => {
        alert('Chatbot loading...');
        console.log('Chatbot button clicked');
    };
    
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.addEventListener('click', () => console.log('Button clicked'));
    });
});
