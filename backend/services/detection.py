"""
Detection Service
Handles vehicle detection using YOLOv8
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import time
import cv2
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_models.yolo_detector import YOLOVehicleDetector, DetectionResult


@dataclass
class DetectionResponse:
    """API response for detection results"""
    vehicle_count: int
    lane_density: float
    queue_length: int
    detections: List[Dict]
    emergency_detected: bool
    emergency_type: Optional[str]
    timestamp: float
    processing_time: float


class DetectionService:
    """
    Service for vehicle detection operations
    """
    
    def __init__(
        self,
        model_path: str = 'yolov8n.pt',
        confidence_threshold: float = 0.25,
        device: str = 'auto'
    ):
        """
        Initialize detection service
        
        Args:
            model_path: Path to YOLO model
            confidence_threshold: Detection confidence threshold
            device: Device for inference
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        
        # Initialize detector
        try:
            self.detector = YOLOVehicleDetector(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                device=device
            )
            self.is_ready = True
        except Exception as e:
            print(f"Failed to initialize YOLO detector: {e}")
            self.detector = None
            self.is_ready = False
        
        # Cache for recent detections
        self.detection_cache = {}
        self.cache_duration = 1.0  # seconds
        
        # Statistics
        self.total_detections = 0
        self.total_vehicles_detected = 0
        self.emergency_count = 0
        
    async def detect_from_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "default"
    ) -> DetectionResponse:
        """
        Run detection on a single frame
        
        Args:
            frame: Image frame (BGR format)
            camera_id: Camera identifier
            
        Returns:
            DetectionResponse with results
        """
        if not self.is_ready:
            return DetectionResponse(
                vehicle_count=0,
                lane_density=0.0,
                queue_length=0,
                detections=[],
                emergency_detected=False,
                emergency_type=None,
                timestamp=time.time(),
                processing_time=0.0
            )
        
        start_time = time.time()
        
        # Run detection in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.detector.detect,
            frame
        )
        
        processing_time = time.time() - start_time
        
        # Update statistics
        self.total_detections += 1
        self.total_vehicles_detected += result.vehicle_count
        if result.emergency_detected:
            self.emergency_count += 1
        
        # Cache result
        self.detection_cache[camera_id] = {
            'result': result,
            'timestamp': time.time()
        }
        
        return DetectionResponse(
            vehicle_count=result.vehicle_count,
            lane_density=result.lane_density,
            queue_length=result.queue_length,
            detections=result.detections,
            emergency_detected=result.emergency_detected,
            emergency_type=result.emergency_type,
            timestamp=time.time(),
            processing_time=processing_time
        )
    
    async def detect_from_video(
        self,
        video_path: str,
        skip_frames: int = 5,
        max_frames: Optional[int] = None
    ) -> List[DetectionResponse]:
        """
        Process video file and return detections
        
        Args:
            video_path: Path to video file
            skip_frames: Process every nth frame
            max_frames: Maximum frames to process
            
        Returns:
            List of DetectionResponse
        """
        if not self.is_ready:
            return []
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        
        results = []
        frame_idx = 0
        processed = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % skip_frames == 0:
                response = await self.detect_from_frame(frame, f"video_{frame_idx}")
                results.append(response)
                processed += 1
                
                if max_frames and processed >= max_frames:
                    break
            
            frame_idx += 1
        
        cap.release()
        return results
    
    async def detect_from_image(self, image_path: str) -> DetectionResponse:
        """
        Run detection on an image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            DetectionResponse
        """
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        return await self.detect_from_frame(frame)
    
    def get_cached_detection(self, camera_id: str = "default") -> Optional[Dict]:
        """
        Get cached detection result
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Cached result or None
        """
        if camera_id not in self.detection_cache:
            return None
        
        cached = self.detection_cache[camera_id]
        
        # Check if cache is still valid
        if time.time() - cached['timestamp'] > self.cache_duration:
            del self.detection_cache[camera_id]
            return None
        
        return asdict(cached['result']) if hasattr(cached['result'], '__dataclass_fields__') else cached['result'].__dict__
    
    def get_statistics(self) -> Dict:
        """Get detection statistics"""
        return {
            'total_detections': self.total_detections,
            'total_vehicles_detected': self.total_vehicles_detected,
            'emergency_count': self.emergency_count,
            'is_ready': self.is_ready,
            'model_path': self.model_path,
            'confidence_threshold': self.confidence_threshold
        }
    
    def update_confidence(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = threshold
        if self.detector:
            self.detector.confidence_threshold = threshold
