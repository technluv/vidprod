# VidProd Frontend

A minimal, upload-only frontend for the VidProd video processing system.

## Features

- **Simple HTML5 Interface**: Clean, modern design with no heavy frameworks
- **Drag and Drop Support**: Drag video files directly onto the upload area
- **Upload Progress Tracking**: Real-time progress bars with speed indicators
- **Queue Management**: View pending, uploading, completed, and failed uploads
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices
- **Multiple File Support**: Upload multiple videos simultaneously
- **Concurrent Upload Control**: Configurable number of parallel uploads

## File Structure

```
frontend/
├── index.html          # Main HTML file
├── css/
│   └── styles.css      # All styling
├── js/
│   ├── config.js       # Configuration settings
│   └── upload.js       # Upload functionality
└── README.md          # This file
```

## Configuration

Edit `js/config.js` to configure:

- `uploadUrl`: The API endpoint for video uploads (default: `/api/upload`)
- `maxConcurrentUploads`: Number of simultaneous uploads (default: 2)
- `supportedFormats`: Array of accepted video MIME types
- `maxFileSize`: Maximum file size in bytes (default: 5GB)

## Usage

1. Open `index.html` in a web browser
2. Click the upload area or drag files to upload
3. Monitor progress in real-time
4. View completed uploads at the bottom

## Supported Video Formats

- MP4 (video/mp4)
- MOV (video/quicktime)
- AVI (video/x-msvideo)
- MKV (video/x-matroska)
- WebM (video/webm)

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Android)

## Integration

To integrate with your backend:

1. Update the `uploadUrl` in `config.js`
2. Ensure your backend accepts multipart/form-data POST requests
3. The file field name is `video`

## No Dependencies

This frontend uses only vanilla JavaScript, HTML5, and CSS3 - no external libraries or frameworks required.