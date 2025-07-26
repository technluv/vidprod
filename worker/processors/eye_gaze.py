"""
Eye gaze correction using MediaPipe
"""
import cv2
import numpy as np
import mediapipe as mp
import asyncio
from typing import Tuple, Optional

import structlog

logger = structlog.get_logger()


class EyeGazeCorrector:
    """Eye gaze correction using MediaPipe Face Mesh"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Eye landmark indices
        self.LEFT_EYE_INDICES = [33, 133, 157, 158, 159, 160, 161, 163, 144, 145, 153, 154, 155]
        self.RIGHT_EYE_INDICES = [362, 263, 387, 388, 389, 390, 391, 393, 373, 374, 380, 381, 382]
        self.IRIS_INDICES = [468, 469, 470, 471, 472]  # If refine_landmarks is True
    
    async def process_video(self, input_path: str, output_path: str, intensity: float = 0.7):
        """Process video with eye gaze correction"""
        # Run processing in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._process_video_sync, input_path, output_path, intensity)
    
    def _process_video_sync(self, input_path: str, output_path: str, intensity: float):
        """Synchronous video processing"""
        cap = cv2.VideoCapture(input_path)
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                corrected_frame = self._correct_eye_gaze(frame, intensity)
                
                # Write frame
                out.write(corrected_frame)
                
                frame_count += 1
                if frame_count % 30 == 0:  # Log progress every 30 frames
                    logger.debug("Processing frame", frame=frame_count)
            
            logger.info("Eye gaze correction completed", frames=frame_count)
            
        finally:
            cap.release()
            out.release()
            cv2.destroyAllWindows()
    
    def _correct_eye_gaze(self, frame: np.ndarray, intensity: float) -> np.ndarray:
        """Correct eye gaze in a single frame"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return frame  # No face detected, return original
        
        face_landmarks = results.multi_face_landmarks[0]
        h, w, _ = frame.shape
        
        # Get eye centers
        left_eye_center = self._get_eye_center(face_landmarks, self.LEFT_EYE_INDICES, w, h)
        right_eye_center = self._get_eye_center(face_landmarks, self.RIGHT_EYE_INDICES, w, h)
        
        if left_eye_center is None or right_eye_center is None:
            return frame
        
        # Calculate gaze correction
        # This is a simplified approach - in production, you'd use more sophisticated methods
        face_center_x = (left_eye_center[0] + right_eye_center[0]) // 2
        face_center_y = (left_eye_center[1] + right_eye_center[1]) // 2
        
        # Target is camera center
        target_x = w // 2
        target_y = h // 2
        
        # Calculate shift needed
        shift_x = int((target_x - face_center_x) * intensity * 0.1)
        shift_y = int((target_y - face_center_y) * intensity * 0.1)
        
        # Apply subtle warping to redirect gaze
        corrected_frame = self._apply_gaze_warp(frame, left_eye_center, right_eye_center, shift_x, shift_y, intensity)
        
        return corrected_frame
    
    def _get_eye_center(self, landmarks, indices: list, w: int, h: int) -> Optional[Tuple[int, int]]:
        """Get the center point of an eye"""
        points = []
        for idx in indices:
            if idx < len(landmarks.landmark):
                landmark = landmarks.landmark[idx]
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                points.append((x, y))
        
        if not points:
            return None
        
        center_x = sum(p[0] for p in points) // len(points)
        center_y = sum(p[1] for p in points) // len(points)
        
        return (center_x, center_y)
    
    def _apply_gaze_warp(self, frame: np.ndarray, left_eye: Tuple[int, int], 
                        right_eye: Tuple[int, int], shift_x: int, shift_y: int, 
                        intensity: float) -> np.ndarray:
        """Apply warping to redirect gaze"""
        h, w = frame.shape[:2]
        
        # Create mesh grid
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        
        # Calculate distance from eyes
        left_dist = np.sqrt((x - left_eye[0])**2 + (y - left_eye[1])**2)
        right_dist = np.sqrt((x - right_eye[0])**2 + (y - right_eye[1])**2)
        
        # Create gaussian weights around eyes
        eye_radius = 30
        left_weight = np.exp(-(left_dist**2) / (2 * eye_radius**2))
        right_weight = np.exp(-(right_dist**2) / (2 * eye_radius**2))
        
        # Combine weights
        weight = np.maximum(left_weight, right_weight) * intensity
        
        # Apply shift with falloff
        map_x = (x + shift_x * weight).astype(np.float32)
        map_y = (y + shift_y * weight).astype(np.float32)
        
        # Remap the image
        corrected = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        
        return corrected