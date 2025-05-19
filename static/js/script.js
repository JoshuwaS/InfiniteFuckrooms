// DOM elements
const chatBox = document.getElementById('chat-box');
const statusIndicator = document.getElementById('status-indicator');

// State
let lastMessageId = -1;
let isInitialLoad = true;
const pollInterval = 2000; // Poll for new messages every 2 seconds
let isNearBottom = true; // Track if user is at bottom of chat

// Check if user is near bottom of chat
function checkNearBottom() {
    const scrollPosition = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight;
    isNearBottom = scrollPosition < 100; // Within 100px of bottom is considered "near bottom"
}

// Add scroll event listener to track user position
chatBox.addEventListener('scroll', checkNearBottom);

// Scroll to bottom only if user was already at bottom
function scrollToBottomIfNeeded() {
    if (isNearBottom) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

/**
 * Format a timestamp to a readable time
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Create a message element
 */
function createMessageElement(message) {
    const messageEl = document.createElement('div');
    messageEl.className = 'message';
    messageEl.setAttribute('data-agent', message.agent);
    messageEl.setAttribute('data-id', message.id !== undefined ? message.id : 0);
    
    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    
    const agentName = document.createElement('strong');
    agentName.textContent = message.agent;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = formatTimestamp(message.timestamp);
    
    messageHeader.appendChild(agentName);
    messageHeader.appendChild(timestamp);
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = message.content;
    
    messageEl.appendChild(messageHeader);
    messageEl.appendChild(messageContent);
    
    return messageEl;
}

/**
 * Fetch all messages
 */
async function fetchAllMessages() {
    try {
        statusIndicator.textContent = 'Loading messages...';
        const response = await fetch('/api/messages');
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const messages = await response.json();
        
        // Clear chat box first if this is initial load
        if (isInitialLoad) {
            chatBox.innerHTML = '';
            isInitialLoad = false;
        }
        
        // Add all messages
        messages.forEach(message => {
            const messageEl = createMessageElement(message);
            chatBox.appendChild(messageEl);
            // Update lastMessageId if this message has a higher ID
            if (message.id !== undefined && message.id > lastMessageId) {
                lastMessageId = message.id;
            }
        });
        
        // Always scroll to bottom on initial load
        chatBox.scrollTop = chatBox.scrollHeight;
        
        statusIndicator.textContent = 'Connected';
    } catch (error) {
        console.error('Error fetching messages:', error);
        statusIndicator.textContent = 'Connection error. Retrying...';
    }
}

/**
 * Fetch new messages since last check
 */
async function fetchNewMessages() {
    try {
        const response = await fetch(`/api/new_messages/${lastMessageId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const messages = await response.json();
        
        if (messages.length > 0) {
            // Check if user is near bottom before adding new messages
            checkNearBottom();
            
            // Add new messages
            messages.forEach(message => {
                const messageEl = createMessageElement(message);
                chatBox.appendChild(messageEl);
                // Update lastMessageId if this message has a higher ID
                if (message.id !== undefined && message.id > lastMessageId) {
                    lastMessageId = message.id;
                }
            });
            
            // Only scroll to bottom if user was already at bottom
            scrollToBottomIfNeeded();
            
            // Update the status indicator to show new message count
            if (!isNearBottom) {
                statusIndicator.textContent = `${messages.length} new message(s) below`;
                statusIndicator.classList.add('new-messages');
            } else {
                statusIndicator.textContent = 'Connected';
                statusIndicator.classList.remove('new-messages');
            }
        } else {
            statusIndicator.textContent = 'Connected';
            statusIndicator.classList.remove('new-messages');
        }
    } catch (error) {
        console.error('Error fetching new messages:', error);
        statusIndicator.textContent = 'Connection error. Retrying...';
    }
}

/**
 * Initialize the chat
 */
function initChat() {
    fetchAllMessages();
    
    // Add click event to status indicator to scroll to bottom when clicked
    statusIndicator.addEventListener('click', () => {
        chatBox.scrollTop = chatBox.scrollHeight;
        statusIndicator.textContent = 'Connected';
        statusIndicator.classList.remove('new-messages');
    });
    
    // Set up polling for new messages
    setInterval(fetchNewMessages, pollInterval);
}

// Load messages when the page is loaded
window.addEventListener('load', initChat);