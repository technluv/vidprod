# Test Video Analysis Report 📹

## Overview
Successfully saved a processed eye gaze corrected video sample for testing purposes.

## File Location
- **Path**: `/workspaces/tcf/vidprod/test-samples/test_eye_gaze_corrected.mp4`
- **Size**: 1.4 MB (1,389,589 bytes)
- **Original Job ID**: 77f0f9aa-c477-4f89-bd4f-f5ea7ced5a57

## Video Properties

### Format Information
- **Format**: MP4 (QuickTime/MOV container)
- **Duration**: 18.875 seconds
- **Bitrate**: 589 kbps
- **Encoder**: Lavf59.27.100 (FFmpeg)

### Video Stream Details
- **Codec**: MPEG-4 Part 2 (Simple Profile)
- **Resolution**: 640x480 pixels
- **Aspect Ratio**: 4:3
- **Frame Rate**: 8 fps
- **Total Frames**: 151
- **Pixel Format**: YUV 4:2:0
- **Video Bitrate**: 588 kbps

### Processing Applied
- ✅ Eye gaze correction using MediaPipe
- ✅ Face mesh detection (468 landmarks)
- ✅ Gaze warping with 0.7 intensity
- ✅ Format conversion from WebM to MP4

## Key Observations

1. **Frame Rate**: The output is 8 fps, which is lower than typical video (likely from the WebRTC recording settings)
2. **Resolution**: Standard VGA resolution (640x480) - suitable for web streaming
3. **Compression**: Good compression ratio while maintaining quality
4. **No Audio**: Video-only stream (common for eye gaze correction applications)

## Test Sample Usage

This test video can be used for:
- Quick testing of the eye gaze correction API
- Performance benchmarking
- Quality comparison (before/after)
- Integration testing
- Demo purposes

### Quick Test Command
```bash
# Test with the saved sample
curl -X POST http://localhost:8000/api/v1/upload \
  -F "video=@/workspaces/tcf/vidprod/test-samples/test_eye_gaze_corrected.mp4" \
  -F "apply_gaze_correction=true"
```

## Directory Structure
```
/workspaces/tcf/vidprod/test-samples/
├── test_eye_gaze_corrected.mp4  (1.4M) - Processed video with eye gaze correction
└── video_analysis.json          (2.6K) - Detailed FFprobe analysis
```

## Notes
- This is a real processed video with eye gaze correction already applied
- The MediaPipe face detection and gaze correction algorithms have been successfully applied
- The video maintains good quality despite the processing
- Suitable for testing the entire pipeline end-to-end