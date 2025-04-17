// static/chat_script.js
document.addEventListener("DOMContentLoaded", () => {
    // Get elements
    const chatContainer = document.querySelector('.chat-page-container');
    const chatHistoryElement = document.getElementById("chat-history");
    const messageInputElement = document.getElementById("chat-message-input");
    const sendButton = document.getElementById("send-chat-btn");

    // --- Get character name directly from data attribute ---
    const characterName = chatContainer ? chatContainer.dataset.characterName : 'Character'; // Fallback name

    // State for chat history (to send to backend)
    // Format: [{ role: 'user'/'assistant', content: '...' }]
    // Start with an initial assistant message
    let chatHistory = [];

    // Function to add a message to the UI
    function appendMessageToUI(role, text, senderName = null) { // Role is 'user', 'assistant', or 'system'
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', `message-${role}`); // e.g., message-user, message-assistant

        const senderSpan = document.createElement('span');
        senderSpan.classList.add('message-sender');

        if (role === 'user') {
            senderSpan.textContent = 'You:';
        } else if (role === 'assistant') {
            // Use the provided senderName or extract from characterName
            const nameToShow = senderName || (characterName.match(/^([^(]+)/) ? characterName.match(/^([^(]+)/)[1].trim() : characterName);
            senderSpan.textContent = `${nameToShow}:`;
        } else { // system messages
             senderSpan.textContent = 'System:';
        }

        const textSpan = document.createElement('span');
        textSpan.classList.add('message-text');
        textSpan.textContent = text; // Use textContent for safety

        messageElement.appendChild(senderSpan);
        messageElement.appendChild(textSpan);
        chatHistoryElement.appendChild(messageElement);

        // Scroll to the bottom
        chatHistoryElement.scrollTop = chatHistoryElement.scrollHeight;
    }

    // Function to handle sending a message
    async function sendMessage() {
        const messageText = messageInputElement.value.trim();
        if (!messageText) return; // Don't send empty messages

        // 1. Add user message to UI and history state
        appendMessageToUI('user', messageText);
        chatHistory.push({ role: 'user', content: messageText });
        const userMessageToSend = messageText; // Store before clearing
        messageInputElement.value = ''; // Clear input
        sendButton.disabled = true;
        messageInputElement.disabled = true;
        messageInputElement.placeholder = "Waiting for response..."; // UX feedback

        try {
            // 2. Send message and history to backend API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_message: userMessageToSend,
                    character_name: characterName, // Send the character name for persona prompt
                    chat_history: chatHistory.slice(0, -1) // Send history *before* the latest user message
                }),
            });

            if (!response.ok) {
                let errorMsg = `Error: ${response.status}`;
                try {
                    const errData = await response.json();
                    errorMsg = errData.error || errorMsg;
                } catch (e) { /* Ignore if response body isn't JSON */ }
                throw new Error(errorMsg);
            }

            const data = await response.json();

            // 3. Add assistant response to UI and history state
            if (data.assistant_response) {
                appendMessageToUI('assistant', data.assistant_response);
                chatHistory.push({ role: 'assistant', content: data.assistant_response });
            } else {
                // Handle cases where backend might return success but empty response
                const errMsg = 'Received an empty response from the character.';
                appendMessageToUI('system', errMsg);
                // Optionally add system message to history too, or just display it
                // chatHistory.push({ role: 'system', content: errMsg });
            }

        } catch (error) {
            console.error("Chat API Fetch Error:", error);
            const displayError = error.message.includes("Groq API error:")
                ? error.message // Show Groq specific error if available
                : `Error: Could not reach the character. Please try again. (${error.message})`;
            appendMessageToUI('system', displayError);
            // Optionally remove the last user message from history on failure?
            // chatHistory.pop();
        } finally {
            // 4. Re-enable input
            sendButton.disabled = false;
            messageInputElement.disabled = false;
            messageInputElement.placeholder = `Type your message to ${characterName}...`; // Restore placeholder
            messageInputElement.focus();
        }
    }

    // --- Initial Greeting ---
    function addInitialGreeting() {
        const greeting = `Hello there! I'm ${characterName}. What's on your mind?`;
        appendMessageToUI('assistant', greeting);
        // Add the greeting to the history so the character knows it was said
        chatHistory.push({ role: 'assistant', content: greeting });
    }

    // --- Event Listeners ---
    sendButton.addEventListener('click', sendMessage);

    messageInputElement.addEventListener('keypress', (e) => {
        // Send on Enter, allow newline with Shift+Enter
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // Prevent newline in textarea
            sendMessage();
        }
    });

    // --- Initialize ---
    addInitialGreeting(); // Add the greeting when the script loads
    messageInputElement.focus(); // Focus input on page load
});