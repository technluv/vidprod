// WebRTC Video Recorder for VidProd
class VideoRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.stream = null;
        this.isRecording = false;
        this.startTime = null;
        this.timerInterval = null;
        
        this.preview = document.getElementById('preview');
        this.recorded = document.getElementById('recorded');
        this.recordBtn = document.getElementById('record-btn');
        this.processBtn = document.getElementById('process-btn');
        this.startCameraBtn = document.getElementById('start-camera');
        this.cameraSelect = document.getElementById('camera-select');
        this.qualitySelect = document.getElementById('quality-select');
        this.timer = document.getElementById('timer');
        this.uploadStatus = document.getElementById('upload-status');
        this.downloadSection = document.getElementById('download-section');
        this.videoList = document.getElementById('video-list');
        
        this.initializeEventListeners();
        this.loadCameras();
    }
    
    initializeEventListeners() {
        this.startCameraBtn.addEventListener('click', () => this.startCamera());
        this.recordBtn.addEventListener('click', () => this.toggleRecording());
        this.processBtn.addEventListener('click', () => this.processVideo());
        this.cameraSelect.addEventListener('change', () => this.switchCamera());
    }
    
    async loadCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            
            this.cameraSelect.innerHTML = '';
            videoDevices.forEach((device, index) => {
                const option = document.createElement('option');
                option.value = device.deviceId;
                option.text = device.label || `Camera ${index + 1}`;
                this.cameraSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading cameras:', error);
            this.showStatus('Failed to load cameras', 'error');
        }
    }
    
    async startCamera() {
        try {
            const quality = this.qualitySelect.value;
            const constraints = {
                video: {
                    deviceId: this.cameraSelect.value ? { exact: this.cameraSelect.value } : undefined,
                    width: { ideal: quality === '1080' ? 1920 : (quality === '720' ? 1280 : 640) },
                    height: { ideal: quality === '1080' ? 1080 : (quality === '720' ? 720 : 480) },
                    facingMode: 'user'
                },
                audio: true
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.preview.srcObject = this.stream;
            
            this.startCameraBtn.disabled = true;
            this.recordBtn.disabled = false;
            this.showStatus('Camera started successfully', 'success');
        } catch (error) {
            console.error('Error accessing camera:', error);
            this.showStatus('Failed to access camera. Please check permissions.', 'error');
        }
    }
    
    async switchCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            await this.startCamera();
        }
    }
    
    toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }
    
    startRecording() {
        this.recordedChunks = [];
        
        const options = {
            mimeType: 'video/webm;codecs=vp9,opus'
        };
        
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'video/webm;codecs=vp8,opus';
        }
        
        try {
            this.mediaRecorder = new MediaRecorder(this.stream, options);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.handleRecordingComplete();
            };
            
            this.mediaRecorder.start(1000); // Collect data every second
            this.isRecording = true;
            this.startTime = Date.now();
            
            // Update UI
            this.recordBtn.classList.add('recording');
            this.recordBtn.querySelector('.record-text').textContent = 'Stop Recording';
            this.processBtn.disabled = true;
            
            // Start timer
            this.startTimer();
            
            this.showStatus('Recording started...', 'info');
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showStatus('Failed to start recording', 'error');
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // Update UI
            this.recordBtn.classList.remove('recording');
            this.recordBtn.querySelector('.record-text').textContent = 'Start Recording';
            
            // Stop timer
            this.stopTimer();
            
            this.showStatus('Recording stopped', 'info');
        }
    }
    
    handleRecordingComplete() {
        const blob = new Blob(this.recordedChunks, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        this.recorded.src = url;
        
        // Store the blob for processing
        this.recordedBlob = blob;
        this.processBtn.disabled = false;
        
        this.showStatus('Recording complete. You can now process the video.', 'success');
    }
    
    startTimer() {
        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            this.timer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 100);
    }
    
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    async processVideo() {
        if (!this.recordedBlob) {
            this.showStatus('No video to process', 'error');
            return;
        }
        
        this.showStatus('Uploading video for processing...', 'info');
        this.processBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('video', this.recordedBlob, 'recording.webm');
        formData.append('apply_gaze_correction', 'true');
        formData.append('split_duration', '60'); // Split if longer than 60 seconds
        
        try {
            const response = await fetch('/api/v1/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showStatus('Video uploaded successfully! Processing...', 'success');
                this.pollJobStatus(result.job_id);
            } else {
                throw new Error(result.detail || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading video:', error);
            this.showStatus(`Upload failed: ${error.message}`, 'error');
            this.processBtn.disabled = false;
        }
    }
    
    async pollJobStatus(jobId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/v1/jobs/${jobId}`);
                const job = await response.json();
                
                if (job.status === 'completed') {
                    clearInterval(pollInterval);
                    this.showStatus('Processing complete!', 'success');
                    this.displayProcessedVideos(job.result);
                    this.processBtn.disabled = false;
                } else if (job.status === 'failed') {
                    clearInterval(pollInterval);
                    this.showStatus(`Processing failed: ${job.error}`, 'error');
                    this.processBtn.disabled = false;
                } else {
                    this.showStatus(`Processing: ${job.progress}% complete`, 'info');
                }
            } catch (error) {
                console.error('Error checking job status:', error);
            }
        }, 2000);
    }
    
    displayProcessedVideos(result) {
        this.downloadSection.classList.add('show');
        this.videoList.innerHTML = '';
        
        if (result.processed_videos && result.processed_videos.length > 0) {
            result.processed_videos.forEach((video, index) => {
                const videoItem = document.createElement('div');
                videoItem.className = 'video-item';
                videoItem.innerHTML = `
                    <div>
                        <strong>Clip ${index + 1}</strong>
                        <span> - ${video.duration}s</span>
                    </div>
                    <a href="${video.download_url}" class="download-btn" download="vidprod_clip_${index + 1}.mp4">
                        📥 Download
                    </a>
                `;
                this.videoList.appendChild(videoItem);
            });
        }
    }
    
    showStatus(message, type = 'info') {
        const statusClass = {
            'info': 'status-info',
            'success': 'status-success',
            'error': 'status-error'
        };
        
        this.uploadStatus.className = `upload-status ${statusClass[type]} show`;
        this.uploadStatus.textContent = message;
        
        if (type !== 'info') {
            setTimeout(() => {
                this.uploadStatus.classList.remove('show');
            }, 5000);
        }
    }
}

// Initialize the recorder when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const recorder = new VideoRecorder();
});

// Check WebRTC support
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('WebRTC is not supported in your browser. Please use a modern browser like Chrome, Firefox, or Edge.');
}