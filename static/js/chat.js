// Add this to your chat.js file

// Store conversation keys
const conversationKeys = {};

// Generate or retrieve encryption key for a conversation
function getConversationKey(otherUserId) {
    if (!conversationKeys[otherUserId]) {
        // For a simple implementation, we'll use a derived key from both user IDs
        // In a real implementation, you would use proper key exchange protocols
        const combinedIds = [currentUser.id, otherUserId].sort().join('_');
        conversationKeys[otherUserId] = CryptoJS.SHA256(combinedIds).toString();
    }
    return conversationKeys[otherUserId];
}

// Encrypt message content
function encryptMessage(content, recipientId) {
    const key = getConversationKey(recipientId);
    return CryptoJS.AES.encrypt(content, key).toString();
}

// Decrypt message content
function decryptMessage(encryptedContent, senderId) {
    const key = getConversationKey(senderId);
    const bytes = CryptoJS.AES.decrypt(encryptedContent, key);
    return bytes.toString(CryptoJS.enc.Utf8);
}