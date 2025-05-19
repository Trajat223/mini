document.addEventListener('DOMContentLoaded', function () {
    const messageContainer = document.getElementById('messageContainer');
    const messageForm = document.querySelector('.message-form');
    const messageInput = document.querySelector('.message-input');
    const recipientInput = document.querySelector('.message-select');
    const faceLockedCheckbox = document.querySelector('#faceLockedCheckbox');
    const fileInput = document.querySelector('.message-file');
    const currentUserId = document.body.dataset.userId;

    if (messageContainer) {
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }

    let socket;
    try {
        socket = io();
        socket.emit('join_room', currentUserId);

        socket.on('new_message', function (message) {
            addMessageToUI(message);
        });

        socket.on('connect_error', function (error) {
            console.error('Socket connection error:', error);
            console.log('Falling back to HTTP polling');
        });
    } catch (e) {
        console.error('Socket.IO not available:', e);
    }

    if (messageForm) {
        messageForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const content = messageInput.value.trim();
            const recipientId = recipientInput ? recipientInput.value : null;
            const isFaceLocked = faceLockedCheckbox?.checked || false;
            const file = fileInput?.files[0];

            if (!content && !file) return;
            if (!recipientId) return;

            const now = new Date();
            const time = now.toTimeString().slice(0, 5);
            const tempId = 'temp-' + Date.now();

            const messageDiv = document.createElement('div');
            messageDiv.className = 'message sent';
            messageDiv.dataset.messageId = tempId;

            const contentHtml = isFaceLocked
                ? `<span class="locked-message">🔒 Face-locked message</span>`
                : content;

            messageDiv.innerHTML = `
                <div class="message-user">You</div>
                ${contentHtml}
                ${file ? `<div>📎 ${file.name}</div>` : ''}
                <div class="message-time">${time}</div>
            `;

            messageContainer.appendChild(messageDiv);
            messageContainer.scrollTop = messageContainer.scrollHeight;

            // Encrypt the message content before sending
            const encryptedContent = encryptMessage(content, recipientId);

            if (socket && socket.connected && !file) {
                socket.emit('send_message', {
                    content: encryptedContent,
                    recipient_id: recipientId,
                    is_face_locked: isFaceLocked,
                    is_encrypted: true
                });
            } else {
                const formData = new FormData();
                formData.append('content', encryptedContent);
                formData.append('recipient_id', recipientId);
                formData.append('is_face_locked', isFaceLocked);
                formData.append('is_encrypted', true);
                if (file) formData.append('file', file);

                fetch('/send_message', {
                    method: 'POST',
                    body: formData
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            fetchMessages(recipientId);
                        } else {
                            console.error('Failed to send message:', data.message);
                            alert('Failed to send message.');
                        }
                    })
                    .catch(error => {
                        console.error('Error sending message:', error);
                        alert('Message could not be sent.');
                    });
            }

            messageInput.value = '';
            if (faceLockedCheckbox) faceLockedCheckbox.checked = false;
            if (fileInput) fileInput.value = '';
        });
    }

    function addMessageToUI(message) {
        const existing = document.querySelector(`[data-message-id="${message.id}"]`);
        if (existing) return;

        const timestamp = new Date(message.timestamp);
        const time = timestamp.toTimeString().slice(0, 5);

        const isLocked = message.is_face_locked;
        const isCurrentUser = message.user_id == currentUserId;
        const isEncrypted = message.is_encrypted;

        // Decrypt the message content if it's encrypted
        let messageContent = message.content;
        if (isEncrypted && !isLocked) {
            const senderId = isCurrentUser ? currentUserId : message.user_id;
            messageContent = decryptMessage(messageContent, senderId);
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isCurrentUser ? 'sent' : 'received'}`;
        messageDiv.dataset.messageId = message.id;

        // Store the original encrypted content for face-locked messages
        if (isLocked && isEncrypted) {
            messageDiv.dataset.encryptedContent = message.content;
        }

        let contentHtml = '';
        if (isLocked) {
            contentHtml = `<div class="locked-message" data-locked="true" data-message-id="${message.id}">
                🔒 Face-locked message (click to unlock)
            </div>`;
        } else {
            contentHtml = `<div>${messageContent}</div>`;
        }

        const fileHtml = message.file_path
            ? `<div>📎 <a href="/uploads/${message.file_path.split('/').pop()}" target="_blank">${message.file_path.split('/').pop()}</a></div>`
            : '';

        messageDiv.innerHTML = `
            <div class="message-user">${isCurrentUser ? 'You' : message.author.username}</div>
            ${contentHtml}
            ${fileHtml}
            <div class="message-time">${time}</div>
        `;

        messageContainer.appendChild(messageDiv);
        messageContainer.scrollTop = messageContainer.scrollHeight;

        // Remove temp message if matching
        const tempMessages = document.querySelectorAll('[data-message-id^="temp-"]');
        tempMessages.forEach(temp => {
            if (
                temp.textContent.includes(message.content) ||
                (isLocked && temp.querySelector('.locked-message'))
            ) {
                temp.remove();
            }
        });

        // Face unlock click handler
        if (isLocked) {
            const lockedDiv = messageDiv.querySelector('.locked-message');
            lockedDiv.addEventListener('click', function () {
                fetch('/face_verification_api')
                    .then(response => response.json())
                    .then(data => {
                        if (data.verified) {
                            // Get the message content, decrypt if needed
                            let content = message.content;
                            if (message.is_encrypted || messageDiv.dataset.encryptedContent) {
                                const encryptedContent = messageDiv.dataset.encryptedContent || message.content;
                                const senderId = isCurrentUser ? currentUserId : message.user_id;
                                content = decryptMessage(encryptedContent, senderId);
                            }
                            lockedDiv.outerHTML = `<div>${content}</div>`;
                        } else {
                            alert('Face verification failed. Cannot unlock message.');
                        }
                    })
                    .catch(error => {
                        console.error('Face verification error:', error);
                        alert('Error during face verification.');
                    });
            });
        }
    }

    function fetchMessages(recipientId) {
        const url = recipientId ? `/get_messages?recipient_id=${recipientId}` : '/get_messages';

        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.messages) updateMessages(data.messages);
            })
            .catch(error => console.error('Error fetching messages:', error));
    }

    function updateMessages(messages) {
        const displayed = new Set();
        document.querySelectorAll('[data-message-id]').forEach(el => {
            const id = el.dataset.messageId;
            if (!id.startsWith('temp-')) displayed.add(id);
        });

        messages.forEach(message => {
            if (!displayed.has(message.id.toString())) {
                addMessageToUI(message);
            }
        });
    }

    const recipientId = recipientInput ? recipientInput.value : null;
    if (recipientId) fetchMessages(recipientId);

    // Inactivity lock
    let inactivityTimeout;
    const inactivityLimit = 5 * 60 * 1000;

    function resetInactivityTimer() {
        clearTimeout(inactivityTimeout);
        inactivityTimeout = setTimeout(() => {
            window.location.href = '/face_verification';
        }, inactivityLimit);
    }

    document.addEventListener('mousemove', resetInactivityTimer);
    document.addEventListener('keypress', resetInactivityTimer);
    document.addEventListener('click', resetInactivityTimer);
    resetInactivityTimer();

    const pollingInterval = setInterval(() => {
        if (!socket || !socket.connected) {
            fetchMessages(recipientInput ? recipientInput.value : null);
        }
    }, 5000);

    window.addEventListener('beforeunload', () => {
        clearInterval(pollingInterval);
        if (socket) socket.disconnect();
    });
});
