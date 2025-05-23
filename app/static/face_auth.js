// Face Authentication using face-api.js

// DOM elements
let video, canvas, captureBtn, loginForm, faceUnlockContainer, faceStatus, unlockBtn;

// Face detection state
let isFaceDetectionInitialized = false;
let isFaceDetected = false;
let detectionInterval;

// Get CSRF token
function getCSRFToken() {
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (!tokenMeta) {
        console.warn("CSRF token meta tag not found.");
        return '';
    }
    return tokenMeta.getAttribute('content');
}

// On document load
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize UI elements
    video = document.getElementById('faceVideo');
    canvas = document.getElementById('faceCanvas');
    captureBtn = document.getElementById('captureBtn');
    faceUnlockContainer = document.getElementById('faceUnlockContainer');
    faceStatus = document.getElementById('faceStatus');
    unlockBtn = document.getElementById('unlockBtn');
    loginForm = document.getElementById('loginForm');

    await loadFaceDetectionModels();

    if (unlockBtn) {
        unlockBtn.addEventListener('click', async () => {
            const success = await setupCamera();
            if (success) {
                startFaceDetection();
                loginForm.style.display = 'none';
                faceUnlockContainer.style.display = 'block';
            }
        });
    }

    if (captureBtn) {
        captureBtn.addEventListener('click', captureAndVerifyFace);
    }

    const registerFaceBtn = document.getElementById('registerFaceBtn');
    if (registerFaceBtn) {
        registerFaceBtn.addEventListener('click', async () => {
            const success = await setupCamera();
            if (success) {
                startFaceDetection();
                document.getElementById('faceRegistration').style.display = 'block';
            }
        });
    }

    const saveFaceBtn = document.getElementById('saveFaceBtn');
    if (saveFaceBtn) {
        saveFaceBtn.addEventListener('click', captureFaceForRegistration);
    }
});

// Load face-api.js models
async function loadFaceDetectionModels() {
    try {
        const modelPath = '/static/face-api-models';
        await Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(modelPath),
            faceapi.nets.faceLandmark68Net.loadFromUri(modelPath),
            faceapi.nets.faceRecognitionNet.loadFromUri(modelPath)
        ]);
        console.log('Face detection models loaded.');
        isFaceDetectionInitialized = true;
    } catch (err) {
        console.error('Error loading models:', err);
        if (faceStatus) {
            faceStatus.innerText = 'Model loading failed.';
            faceStatus.className = 'error';
        }
    }
}

// Set up camera
async function setupCamera() {
    if (!video) return false;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' },
            audio: false
        });
        video.srcObject = stream;

        return new Promise(resolve => {
            video.onloadedmetadata = () => {
                video.play();
                video.style.display = 'block';
                canvas.style.display = 'block';
                resolve(true);
            };
        });
    } catch (err) {
        console.error('Camera access denied or failed:', err);
        if (faceStatus) {
            faceStatus.innerText = 'Camera access denied.';
            faceStatus.className = 'error';
        }
        stopVideo();
        return false;
    }
}

// Stop video stream
function stopVideo() {
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    video.style.display = 'none';
    canvas.style.display = 'none';
    clearInterval(detectionInterval);
}

// Start real-time detection
function startFaceDetection() {
    if (!isFaceDetectionInitialized || !video) return;

    clearInterval(detectionInterval);

    const displaySize = { width: video.width, height: video.height };
    faceapi.matchDimensions(canvas, displaySize);

    detectionInterval = setInterval(async () => {
        if (video.paused || video.ended) return;

        const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks()
            .withFaceDescriptors();
        const resized = faceapi.resizeResults(detections, displaySize);

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        faceapi.draw.drawDetections(canvas, resized);
        faceapi.draw.drawFaceLandmarks(canvas, resized);

        if (resized.length > 0) {
            isFaceDetected = true;
            faceStatus.innerText = 'Face detected! Click capture.';
            faceStatus.className = 'success';
            captureBtn.disabled = false;
        } else {
            isFaceDetected = false;
            faceStatus.innerText = 'No face detected.';
            faceStatus.className = 'warning';
            captureBtn.disabled = true;
        }
    }, 100);
}

// Login: Capture and verify
async function captureAndVerifyFace() {
    if (!isFaceDetected) return;

    clearInterval(detectionInterval);

    const detection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor();

    if (!detection) {
        faceStatus.innerText = 'Detection failed.';
        faceStatus.className = 'error';
        return;
    }

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    tempCanvas.getContext('2d').drawImage(video, 0, 0);
    const imageData = tempCanvas.toDataURL('image/jpeg', 0.8);

    faceStatus.innerText = 'Verifying...';

    try {
        const response = await fetch('/verify_face', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                faceImage: imageData,
                username: document.getElementById('username').value || ''
            })
        });

        const result = await response.json();
        if (result.success) {
            document.getElementById('face_verified').value = 'true';
            faceStatus.innerText = 'Verified! Redirecting...';
            faceStatus.className = 'success';
            stopVideo();
            setTimeout(() => window.location.href = '/chat', 1000);
        } else {
            faceStatus.innerText = result.message || 'Verification failed.';
            faceStatus.className = 'error';
            startFaceDetection();
        }
    } catch (err) {
        console.error('Verify error:', err);
        faceStatus.innerText = 'Verification error.';
        faceStatus.className = 'error';
        startFaceDetection();
    }
}

// Registration: Capture face
async function captureFaceForRegistration() {
    if (!isFaceDetected) return;

    try {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = video.videoWidth;
        tempCanvas.height = video.videoHeight;
        tempCanvas.getContext('2d').drawImage(video, 0, 0);
        const imageData = tempCanvas.toDataURL('image/jpeg', 0.8);

        document.getElementById('faceData').value = imageData;

        const preview = document.getElementById('facePreview');
        preview.src = imageData;
        preview.style.display = 'block';

        const status = document.getElementById('faceDataStatus');
        status.innerText = 'Face captured! Complete registration.';
        status.className = 'success';

        stopVideo();
    } catch (err) {
        console.error('Capture error:', err);
        const status = document.getElementById('faceDataStatus');
        status.innerText = 'Capture failed. Try again.';
        status.className = 'error';
    }
}
