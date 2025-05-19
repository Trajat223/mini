/**
 * End-to-End Encryption Utilities for SecureChatApp
 *
 * This file contains functions for secure message encryption and decryption
 * using the CryptoJS library.
 */

// Store conversation keys in memory (will be lost on page refresh)
const conversationKeys = {};

/**
 * Generate a secure random key for a new conversation
 * @returns {string} A random key in hex format
 */
function generateRandomKey() {
    // Generate a random 256-bit key
    const randomArray = new Uint8Array(32); // 32 bytes = 256 bits
    window.crypto.getRandomValues(randomArray);

    // Convert to hex string
    return Array.from(randomArray)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}

/**
 * Get or create an encryption key for a conversation
 * @param {string} otherUserId - The ID of the other user in the conversation
 * @returns {string} The encryption key for this conversation
 */
function getConversationKey(otherUserId) {
    if (!conversationKeys[otherUserId]) {
        // For a real implementation, we would use a proper key exchange protocol
        // This is a simplified version that derives a key from user IDs
        // In production, use a secure key exchange protocol like Diffie-Hellman

        const currentUserId = document.body.dataset.userId;

        // Sort IDs to ensure the same key is generated regardless of who initiates
        const combinedIds = [currentUserId, otherUserId].sort().join('_');

        // Derive a key using SHA-256
        conversationKeys[otherUserId] = CryptoJS.SHA256(combinedIds).toString();

        // In a real implementation, we would store this key securely
        console.log(`Generated new key for conversation with user ${otherUserId}`);
    }

    return conversationKeys[otherUserId];
}

/**
 * Encrypt a message
 * @param {string} plaintext - The message to encrypt
 * @param {string} recipientId - The ID of the message recipient
 * @returns {string} The encrypted message (Base64 encoded)
 */
function encryptMessage(plaintext, recipientId) {
    if (!plaintext || plaintext.trim() === '') {
        return '';
    }

    try {
        const key = getConversationKey(recipientId);

        // Generate a random IV for each message
        const iv = CryptoJS.lib.WordArray.random(16); // 128 bits

        // Encrypt the message using AES-256-CBC with the key and IV
        const encrypted = CryptoJS.AES.encrypt(plaintext, key, {
            iv: iv,
            padding: CryptoJS.pad.Pkcs7,
            mode: CryptoJS.mode.CBC
        });

        // Combine the IV and ciphertext for storage/transmission
        // Format: IV:ciphertext (both Base64 encoded)
        return iv.toString(CryptoJS.enc.Base64) + ':' + encrypted.toString();
    } catch (error) {
        console.error('Encryption error:', error);
        return plaintext; // Fallback to plaintext if encryption fails
    }
}

/**
 * Decrypt a message
 * @param {string} encryptedMessage - The encrypted message to decrypt
 * @param {string} senderId - The ID of the message sender
 * @returns {string} The decrypted message
 */
function decryptMessage(encryptedMessage, senderId) {
    if (!encryptedMessage || !encryptedMessage.includes(':')) {
        return encryptedMessage; // Not encrypted or invalid format
    }

    try {
        const key = getConversationKey(senderId);

        // Split the IV and ciphertext
        const [ivString, ciphertext] = encryptedMessage.split(':');

        // Convert the IV from Base64 to WordArray
        const iv = CryptoJS.enc.Base64.parse(ivString);

        // Decrypt the message
        const decrypted = CryptoJS.AES.decrypt(ciphertext, key, {
            iv: iv,
            padding: CryptoJS.pad.Pkcs7,
            mode: CryptoJS.mode.CBC
        });

        // Convert the result to a UTF-8 string
        return decrypted.toString(CryptoJS.enc.Utf8);
    } catch (error) {
        console.error('Decryption error:', error);
        return 'Error: Could not decrypt message';
    }
}