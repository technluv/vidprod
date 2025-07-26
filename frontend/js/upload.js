// Upload Manager
class UploadManager {
    constructor() {
        this.uploadQueue = [];
        this.activeUploads = new Map();
        this.completedUploads = [];
        this.maxConcurrentUploads = CONFIG.maxConcurrentUploads || 2;
        this.uploadUrl = CONFIG.uploadUrl || '/api/upload';
        this.maxFileSize = CONFIG.maxFileSize || (5 * 1024 * 1024 * 1024); // 5GB default
        this.supportedFormats = CONFIG.supportedFormats || ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm'];
        
        this.initializeElements();
        this.attachEventListeners();
        this.startQueueProcessor();
    }
    
    initializeElements() {
        // Main elements
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.browseButton = document.getElementById('browseButton');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.queueStatus = document.getElementById('queueStatus');
        this.completedUploads = document.getElementById('completedUploads');
        
        // Progress template
        this.progressTemplate = document.getElementById('progressTemplate');
        
        // Queue stats
        this.pendingCount = document.getElementById('pendingCount');
        this.uploadingCount = document.getElementById('uploadingCount');
        this.completedCount = document.getElementById('completedCount');
        this.failedCount = document.getElementById('failedCount');
        
        // Queue items container
        this.queueItems = document.getElementById('queueItems');
        this.completedItems = document.getElementById('completedItems');
    }
    
    attachEventListeners() {
        // File input
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Browse button
        this.browseButton.addEventListener('click', () => this.fileInput.click());
        
        // Drag and drop
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Prevent default drag behavior on document
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('drop', (e) => e.preventDefault());
    }
    
    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        this.addFilesToQueue(files);
        event.target.value = ''; // Reset input
    }
    
    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        this.uploadArea.classList.remove('dragover');
    }
    
    handleDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.uploadArea.classList.remove('dragover');
        
        const files = Array.from(event.dataTransfer.files).filter(file => 
            file.type.startsWith('video/')
        );
        
        if (files.length > 0) {
            this.addFilesToQueue(files);
        } else {
            alert('Please drop only video files');
        }
    }
    
    addFilesToQueue(files) {
        const videoFiles = files.filter(file => {
            // Check file size
            if (file.size > this.maxFileSize) {
                alert(`${file.name} is too large. Maximum size is ${this.formatFileSize(this.maxFileSize)}`);
                return false;
            }
            // Check file type
            return this.supportedFormats.includes(file.type) || file.type.startsWith('video/');
        });
        
        if (videoFiles.length === 0) {
            alert('Please select valid video files');
            return;
        }
        
        videoFiles.forEach(file => {
            const queueItem = {
                id: Date.now() + Math.random(),
                file: file,
                status: 'pending',
                progress: 0,
                speed: 0,
                startTime: null,
                xhr: null
            };
            
            this.uploadQueue.push(queueItem);
            this.addQueueItemToUI(queueItem);
        });
        
        this.updateQueueStats();
        this.showQueueStatus();
    }
    
    addQueueItemToUI(item) {
        const queueElement = document.createElement('div');
        queueElement.className = 'queue-item';
        queueElement.id = `queue-item-${item.id}`;
        queueElement.innerHTML = `
            <span class="queue-item-name" title="${item.file.name}">${item.file.name}</span>
            <span class="queue-item-status status-${item.status}">${this.formatStatus(item.status)}</span>
        `;
        
        this.queueItems.appendChild(queueElement);
    }
    
    updateQueueItemStatus(item) {
        const queueElement = document.getElementById(`queue-item-${item.id}`);
        if (queueElement) {
            const statusElement = queueElement.querySelector('.queue-item-status');
            statusElement.className = `queue-item-status status-${item.status}`;
            statusElement.textContent = this.formatStatus(item.status);
        }
    }
    
    formatStatus(status) {
        const statusMap = {
            'pending': 'Pending',
            'uploading': 'Uploading',
            'completed': 'Completed',
            'failed': 'Failed'
        };
        return statusMap[status] || status;
    }
    
    startQueueProcessor() {
        setInterval(() => {
            if (this.activeUploads.size < this.maxConcurrentUploads) {
                const nextItem = this.uploadQueue.find(item => item.status === 'pending');
                if (nextItem) {
                    this.startUpload(nextItem);
                }
            }
        }, 500);
    }
    
    startUpload(item) {
        item.status = 'uploading';
        item.startTime = Date.now();
        this.activeUploads.set(item.id, item);
        
        this.updateQueueItemStatus(item);
        this.updateQueueStats();
        this.showUploadProgress();
        
        const progressElement = this.createProgressElement(item);
        this.uploadProgress.appendChild(progressElement);
        
        this.uploadFile(item, progressElement);
    }
    
    createProgressElement(item) {
        const element = this.progressTemplate.cloneNode(true);
        element.id = `progress-${item.id}`;
        element.style.display = 'block';
        
        element.querySelector('.file-name').textContent = item.file.name;
        element.querySelector('.file-size').textContent = this.formatFileSize(item.file.size);
        
        const cancelButton = element.querySelector('.cancel-button');
        cancelButton.addEventListener('click', () => this.cancelUpload(item));
        
        return element;
    }
    
    uploadFile(item, progressElement) {
        const formData = new FormData();
        formData.append('video', item.file);
        
        const xhr = new XMLHttpRequest();
        item.xhr = xhr;
        
        // Progress tracking
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                this.updateProgress(item, progressElement, percentComplete, e.loaded);
            }
        });
        
        // Completion handling
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                this.handleUploadComplete(item, progressElement);
            } else {
                this.handleUploadError(item, progressElement, 'Upload failed');
            }
        });
        
        // Error handling
        xhr.addEventListener('error', () => {
            this.handleUploadError(item, progressElement, 'Network error');
        });
        
        xhr.addEventListener('abort', () => {
            this.handleUploadCancel(item, progressElement);
        });
        
        // Send request
        xhr.open('POST', this.uploadUrl);
        xhr.send(formData);
    }
    
    updateProgress(item, progressElement, percent, loaded) {
        item.progress = percent;
        
        const progressFill = progressElement.querySelector('.progress-fill');
        const progressPercent = progressElement.querySelector('.progress-percent');
        const progressSpeed = progressElement.querySelector('.progress-speed');
        
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        
        // Calculate upload speed
        const elapsed = (Date.now() - item.startTime) / 1000;
        const speed = loaded / elapsed;
        progressSpeed.textContent = `${this.formatSpeed(speed)}`;
    }
    
    handleUploadComplete(item, progressElement) {
        item.status = 'completed';
        this.activeUploads.delete(item.id);
        this.completedUploads.push(item);
        
        // Remove from progress view
        progressElement.remove();
        
        // Update queue status
        this.updateQueueItemStatus(item);
        this.updateQueueStats();
        
        // Add to completed section
        this.addCompletedItem(item);
        
        // Check if all uploads are done
        if (this.uploadProgress.querySelectorAll('.progress-item:not(#progressTemplate)').length === 0) {
            this.uploadProgress.classList.add('hidden');
        }
    }
    
    handleUploadError(item, progressElement, error) {
        item.status = 'failed';
        item.error = error;
        this.activeUploads.delete(item.id);
        
        // Remove from progress view
        progressElement.remove();
        
        // Update queue status
        this.updateQueueItemStatus(item);
        this.updateQueueStats();
        
        // Check if all uploads are done
        if (this.uploadProgress.querySelectorAll('.progress-item:not(#progressTemplate)').length === 0) {
            this.uploadProgress.classList.add('hidden');
        }
        
        alert(`Upload failed for ${item.file.name}: ${error}`);
    }
    
    handleUploadCancel(item, progressElement) {
        item.status = 'pending';
        this.activeUploads.delete(item.id);
        
        // Remove from progress view
        progressElement.remove();
        
        // Update queue status
        this.updateQueueItemStatus(item);
        this.updateQueueStats();
        
        // Check if all uploads are done
        if (this.uploadProgress.querySelectorAll('.progress-item:not(#progressTemplate)').length === 0) {
            this.uploadProgress.classList.add('hidden');
        }
    }
    
    cancelUpload(item) {
        if (item.xhr) {
            item.xhr.abort();
        }
    }
    
    addCompletedItem(item) {
        const completedElement = document.createElement('div');
        completedElement.className = 'completed-item';
        completedElement.innerHTML = `
            <svg class="completed-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 6L9 17l-5-5"></path>
            </svg>
            <div class="completed-info">
                <span class="completed-name" title="${item.file.name}">${item.file.name}</span>
                <span class="completed-time">Completed ${this.formatTime(new Date())}</span>
            </div>
        `;
        
        this.completedItems.insertBefore(completedElement, this.completedItems.firstChild);
        this.showCompletedUploads();
    }
    
    updateQueueStats() {
        const stats = {
            pending: 0,
            uploading: 0,
            completed: 0,
            failed: 0
        };
        
        this.uploadQueue.forEach(item => {
            stats[item.status]++;
        });
        
        this.pendingCount.textContent = stats.pending;
        this.uploadingCount.textContent = stats.uploading;
        this.completedCount.textContent = stats.completed;
        this.failedCount.textContent = stats.failed;
    }
    
    showUploadProgress() {
        this.uploadProgress.classList.remove('hidden');
    }
    
    showQueueStatus() {
        this.queueStatus.classList.remove('hidden');
    }
    
    showCompletedUploads() {
        this.completedUploads.classList.remove('hidden');
    }
    
    formatFileSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }
    
    formatSpeed(bytesPerSecond) {
        return `${this.formatFileSize(bytesPerSecond)}/s`;
    }
    
    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) {
            return 'just now';
        } else if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleTimeString();
        }
    }
}

// Initialize upload manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new UploadManager();
});