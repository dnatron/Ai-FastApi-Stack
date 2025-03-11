document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const streamToggle = document.getElementById('stream-toggle');
    const chatContainer = document.getElementById('chat-container');
    const modelSelect = document.getElementById('model-select');
    
    // Function to scroll to bottom of chat
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Scroll to bottom on page load
    scrollToBottom();
    
    // Handle form submission
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        const model = modelSelect.value;
        const isStreaming = streamToggle.checked;
        
        // Create FormData
        const formData = new FormData();
        formData.append('message', message);
        formData.append('model', model);
        
        // Clear input
        messageInput.value = '';
        
        if (isStreaming) {
            // Handle streaming response
            handleStreamingMessage(formData);
        } else {
            // Handle regular response
            handleRegularMessage(formData);
        }
    });
    
    // Handle regular message submission
    function handleRegularMessage(formData) {
        fetch('/send-message', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(html => {
            chatContainer.innerHTML += html;
            scrollToBottom();
        })
        .catch(error => {
            console.error('Error:', error);
            chatContainer.innerHTML += `
                <div class="message system-message">
                    <div class="message-content">
                        <div class="message-text">Error: ${error.message}</div>
                    </div>
                </div>
            `;
            scrollToBottom();
        });
    }
    
    // Handle streaming message
    function handleStreamingMessage(formData) {
        // First add the user message
        const userMessage = `
            <div class="message user-message">
                <div class="message-content">
                    <div class="message-text">${formData.get('message')}</div>
                    <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
            </div>
        `;
        chatContainer.innerHTML += userMessage;
        scrollToBottom();
        
        // Create and configure EventSource for SSE
        const eventSource = new EventSource(`/send-message-stream?message=${encodeURIComponent(formData.get('message'))}&model=${encodeURIComponent(formData.get('model'))}`);
        
        let assistantMessageId = null;
        let streamingContent = null;
        
        // Handle different event types
        eventSource.addEventListener('user_message', function(e) {
            // User message already added manually, so we can ignore this
        });
        
        eventSource.addEventListener('assistant_start', function(e) {
            // Add the assistant message container
            chatContainer.innerHTML += e.data;
            scrollToBottom();
            
            // Find the message ID from the container
            const messageContainer = chatContainer.querySelector('.message.assistant-message:last-child');
            assistantMessageId = messageContainer.id.replace('message-', '');
            streamingContent = document.getElementById(`streaming-content-${assistantMessageId}`);
        });
        
        eventSource.addEventListener('token', function(e) {
            if (streamingContent) {
                // Append the token to the streaming content
                streamingContent.innerHTML += formatToken(e.data);
                scrollToBottom();
            }
        });
        
        eventSource.addEventListener('error', function(e) {
            // Handle errors
            if (streamingContent) {
                streamingContent.innerHTML += `<span class="text-danger">Error: ${e.data}</span>`;
            }
            eventSource.close();
            scrollToBottom();
        });
        
        eventSource.addEventListener('done', function(e) {
            // Remove typing indicator when done
            const typingIndicator = document.querySelector(`#message-${assistantMessageId} .typing-indicator`);
            if (typingIndicator) {
                typingIndicator.remove();
            }
            eventSource.close();
            scrollToBottom();
        });
    }
    
    // Format token for display (handle code blocks, etc.)
    function formatToken(token) {
        // Simple formatting - in a real app, you might want more sophisticated formatting
        return token
            .replace(/\n/g, '<br>')
            .replace(/ /g, '&nbsp;');
    }
    
    // Auto-resize textarea as user types
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Focus input on page load
    messageInput.focus();
});
