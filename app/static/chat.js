const socket = io({ query: { username: username } }); // Assume username is defined globally

// Generate a unique message ID
function generateMessageId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// ========== TYPING INDICATOR ========== 
let typing = false;
let typingTimeout;
const messageInput = document.getElementById("msg");
const typingIndicator = document.getElementById("typing-indicator");

messageInput.addEventListener("input", () => {
    const message = messageInput.value.trim();

    if (message !== "") {
        if (!typing) {
            socket.emit("typing", { sender: username });
            typing = true;
        }

        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {
            socket.emit("stop_typing", { sender: username });
            typing = false;
        }, 1000); // stop typing after 1s of inactivity
    } else {
        if (typing) {
            socket.emit("stop_typing", { sender: username });
            typing = false;
        }
        clearTimeout(typingTimeout);
    }
});

// Show/hide "typing" indicator only when someone else is typing
socket.on("typing", ({ sender }) => {
    if (sender !== username) {
        typingIndicator.innerText = `${sender} is typing...`;
        typingIndicator.style.display = "block";
    }
});

socket.on("stop_typing", ({ sender }) => {
    if (sender !== username) {
        typingIndicator.style.display = "none";
    }
});





// ========== READ RECEIPTS ========== 
document.getElementById("messages").addEventListener("click", (event) => {
    if (event.target.tagName === "LI" && event.target.dataset.messageId) {
        socket.emit("message_read", {
            message_id: event.target.dataset.messageId,
            sender: username,
            reader: username
        });
    }
});

// ========== PUBLIC MESSAGE ========== 
document.getElementById("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (message && message.length <= 1000) { // Limit message length to 1000 characters
        const messageId = generateMessageId();
        const timestamp = new Date().toISOString();
        socket.emit("send_message", {
            sender: username,
            message,
            timestamp,
            message_id: messageId,
        });
        messageInput.value = ""; // Clear input after sending
    } else {
        alert("Message is too long or empty.");
    }
});

socket.on("receive_message", (data) => {
    const { sender, message, timestamp, message_id } = data;
    const messages = document.getElementById("messages");
    const li = document.createElement("li");
    li.textContent = `[${timestamp}] ${sender}: ${message}`;
    li.dataset.messageId = message_id;
    messages.appendChild(li);
});

// ========== PRIVATE MESSAGE ========== 
document.getElementById("send-private-message").addEventListener("click", () => {
    const recipient = document.getElementById("recipient").value.trim();
    const message = document.getElementById("private-message-input").value.trim();
    if (recipient && message && message.length <= 1000) { // Limit private message length
        const messageId = generateMessageId();
        const timestamp = new Date().toISOString();
        socket.emit("private_message", {
            sender: username,
            recipient,
            message,
            timestamp,
            message_id: messageId,
        });

        const li = document.createElement("li");
        li.textContent = `[PRIVATE] [To ${recipient}] ${message}`;
        li.style.color = "green";
        li.dataset.messageId = messageId;
        document.getElementById("messages").appendChild(li);

        document.getElementById("recipient").value = "";
        document.getElementById("private-message-input").value = "";
    } else {
        alert("Please provide a recipient and a valid message.");
    }
});

socket.on("private_message", (data) => {
    const { sender, message, timestamp, message_id } = data;
    const li = document.createElement("li");
    li.textContent = `[PRIVATE] [${timestamp}] ${sender}: ${message}`;
    li.style.color = "blue";
    li.dataset.messageId = message_id;
    document.getElementById("messages").appendChild(li);
});

// ========== PUBLIC FILE UPLOAD ========== 
document.getElementById("send-file").addEventListener("click", async () => {
    const file = document.getElementById("file-input").files[0];
    if (!file) return alert("Please select a file.");
    if (file.size > 5 * 1024 * 1024) return alert("File exceeds 5MB.");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("sender", username);

    try {
        const response = await fetch("/upload_public", { method: "POST", body: formData });
        const result = await response.json();
        if (response.ok) {
            alert(`File uploaded: ${result.fileName}`);
        } else {
            alert("Failed to upload file.");
        }
    } catch (err) {
        console.error("Upload error:", err);
        alert("An error occurred during file upload.");
    }
});

socket.on("receive_file", (data) => {
    const { sender, fileName, fileUrl } = data;
    const li = document.createElement("li");
    li.innerHTML = `[FILE] [${sender}] <a href="${fileUrl}" download="${fileName}">${fileName}</a>`;
    document.getElementById("messages").appendChild(li);
});

// ========== PRIVATE FILE UPLOAD ========== 
document.getElementById("send-private-file").addEventListener("click", async () => {
    const recipient = document.getElementById("recipient").value.trim();
    const file = document.getElementById("private-file-input").files[0];
    if (!file || !recipient) return alert("Select a file and specify recipient.");
    if (file.size > 5 * 1024 * 1024) return alert("File exceeds 5MB.");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("sender", username);
    formData.append("recipient", recipient);

    try {
        const response = await fetch("/upload_private", { method: "POST", body: formData });
        const result = await response.json();
        if (response.ok) {
            const li = document.createElement("li");
            li.innerHTML = `[FILE] [To ${recipient}] <a href="${result.fileUrl}" download="${result.fileName}">${result.fileName}</a>`;
            li.style.color = "green";
            document.getElementById("messages").appendChild(li);
        } else {
            alert("Failed to upload private file.");
        }
    } catch (err) {
        console.error("Upload error:", err);
        alert("Error uploading private file.");
    }
});

socket.on("private_file", (data) => {
    const { sender, fileName, fileUrl } = data;
    const li = document.createElement("li");
    li.innerHTML = `[FILE] [PRIVATE] [${sender}] <a href="${fileUrl}" download="${fileName}">${fileName}</a>`;
    li.style.color = "blue";
    document.getElementById("messages").appendChild(li);
});

// ========== ONLINE USERS ========== 
socket.on("user_list", (users) => {
    const ul = document.getElementById("online-users");
    ul.innerHTML = "";
    users.forEach((user) => {
        const li = document.createElement("li");
        li.textContent = user;
        ul.appendChild(li);
    });
});

// ========== TYPING INDICATOR ========== 
socket.on("typing", (data) => {
    document.getElementById("typing-indicator").textContent = `${data.sender} is typing...`;
});

socket.on("stop_typing", () => {
    document.getElementById("typing-indicator").textContent = "";
});

// ========== MESSAGE READ ACK ========== 
socket.on("message_read_ack", (data) => {
    const { message_id, reader } = data;
    const messageElement = document.querySelector(`[data-message-id="${message_id}"]`);
    if (messageElement) {
        messageElement.style.fontStyle = "italic";
        messageElement.title = `Read by ${reader}`;
    }
});

// ========== ERROR HANDLER ========== 
socket.on("error", (data) => {
    alert(data.message || "An error occurred.");
});
