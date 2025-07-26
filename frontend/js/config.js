// Configuration for the VidProd upload frontend
const CONFIG = {
    // API endpoint for video uploads
    uploadUrl: '/api/upload',
    
    // Maximum concurrent uploads
    maxConcurrentUploads: 2,
    
    // Supported video formats
    supportedFormats: [
        'video/mp4',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-matroska',
        'video/webm'
    ],
    
    // Maximum file size (in bytes) - 5GB default
    maxFileSize: 5 * 1024 * 1024 * 1024,
    
    // Enable debug logging
    debug: false
};