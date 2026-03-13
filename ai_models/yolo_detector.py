"""
YOLOv8 Vehicle Detection Module
Handles real-time vehicle detection from video frames
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import torch


@dataclass
class DetectionResult:
    """Data class for detection results"""
    vehicle_count: int
    lane_density: float
    queue_length: int
    detections: List[Dict]
    emergency_detected: bool
    emergency_type: Optional[str]
    frame_id: int


class YOLOVehicleDetector:
    """
    YOLOv8-based vehicle detector for traffic monitoring
    
    Supports detection of:
    - Standard vehicles: car, motorcycle, bus, truck, auto-rickshaw
    - Emergency vehicles: ambulance, police, fire_truck
    """
    
    # COCO classes that are vehicles
    VEHICLE_CLASSES = {
        2: 'car',
        3: 'motorcycle',
        5: 'bus',
        7: 'truck',
    }
    
    # Emergency vehicle classes (custom trained or fine-tuned model)
    EMERGENCY_CLASSES = {
        'ambulance': 80,
        'police': 81,
        'fire_truck': 82,
    }
    
    # Extended classes for Indian traffic
    EXTENDED_CLASSES = {
        'auto-rickshaw': 83,
    }
    
    def __init__(
        self,
        model_path: str = 'yolov8n.pt',
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = 'auto'
    ):
        """
        Initialize the YOLOv8 detector
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Minimum confidence for detections
            iou_threshold: IOU threshold for NMS
            device: Device to run inference on ('auto', 'cuda', 'cpu')
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        
        # Determine device
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        # Load YOLO model
        self.model = YOLO(model_path)
        self.model.to(self.device)
        
        # Combine all vehicle classes
        self.all_vehicle_classes = {
            **self.VEHICLE_CLASSES,
            **{v: k for k, v in self.EMERGENCY_CLASSES.items()},
            **{v: k for k, v in self.EXTENDED_CLASSES.items()}
        }
        
        self.frame_count = 0
        
    def preprocess_frame(self, frame: np.ndarray, target_size: int = 640) -> np.ndarray:
        """
        Preprocess frame for YOLO inference
        
        Args:
            frame: Input frame (BGR)
            target_size: Target size for resizing
            
        Returns:
            Preprocessed frame
        """
        # Resize to target size while maintaining aspect ratio
        height, width = frame.shape[:2]
        scale = target_size / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        resized = cv2.resize(frame, (new_width, new_height))
        
        # Pad to make square
        delta_w = target_size - new_width
        delta_h = target_size - new_height
        top, bottom = delta_h // 2, delta_h - (delta_h // 2)
        left, right = delta_w // 2, delta_w - (delta_w // 2)
        
        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right,
            cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
        
        return padded
    
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run vehicle detection on a frame
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            DetectionResult with vehicle counts and detections
        """
        self.frame_count += 1
        
        # Run inference
        results = self.model(
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False
        )[0]
        
        detections = []
        vehicle_count = 0
        emergency_detected = False
        emergency_type = None
        
        # Process detections
        for box in results.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].cpu().numpy()
            
            # Check if it's a vehicle
            if class_id in self.VEHICLE_CLASSES:
                vehicle_type = self.VEHICLE_CLASSES[class_id]
                vehicle_count += 1
                
                detections.append({
                    'class_id': class_id,
                    'class_name': vehicle_type,
                    'confidence': confidence,
                    'bbox': bbox.tolist(),
                    'is_emergency': False
                })
            
            # Check for emergency vehicles (if using custom model)
            elif class_id in [80, 81, 82]:
                emergency_type_map = {80: 'ambulance', 81: 'police', 82: 'fire_truck'}
                emergency_type = emergency_type_map.get(class_id)
                emergency_detected = True
                vehicle_count += 1
                
                detections.append({
                    'class_id': class_id,
                    'class_name': emergency_type,
                    'confidence': confidence,
                    'bbox': bbox.tolist(),
                    'is_emergency': True
                })
        
        # Calculate queue length based on vehicle positions
        queue_length = self._calculate_queue_length(detections, frame.shape)
        
        # Calculate lane density
        lane_density = self._calculate_lane_density(vehicle_count, frame.shape)
        
        return DetectionResult(
            vehicle_count=vehicle_count,
            lane_density=lane_density,
            queue_length=queue_length,
            detections=detections,
            emergency_detected=emergency_detected,
            emergency_type=emergency_type,
            frame_id=self.frame_count
        )
    
    def _calculate_queue_length(
        self,
        detections: List[Dict],
        frame_shape: Tuple[int, int, int]
    ) -> int:
        """
        Estimate queue length based on vehicle positions
        
        Args:
            detections: List of detection dictionaries
            frame_shape: Shape of the frame
            
        Returns:
            Estimated queue length (number of vehicles in queue)
        """
        if not detections:
            return 0
        
        height = frame_shape[0]
        
        # Vehicles in the lower half of the frame are considered in queue
        # This is a simplified heuristic - would need calibration for real deployment
        queue_threshold = height * 0.5
        
        queue_count = 0
        for det in detections:
            bbox = det['bbox']
            # Check if bottom of bounding box is in queue zone
            if bbox[3] > queue_threshold:
                queue_count += 1
                
        return queue_count
    
    def _calculate_lane_density(
        self,
        vehicle_count: int,
        frame_shape: Tuple[int, int, int]
    ) -> float:
        """
        Calculate lane density as vehicles per unit area
        
        Args:
            vehicle_count: Number of vehicles detected
            frame_shape: Shape of the frame
            
        Returns:
            Density value (normalized 0-1)
        """
        # Assuming max capacity based on frame size
        # This would need calibration for actual lane configuration
        max_capacity = 20  # Hypothetical max vehicles per frame
        density = min(vehicle_count / max_capacity, 1.0)
        return density
    
    def detect_from_video(
        self,
        video_path: str,
        skip_frames: int = 1,
        max_frames: Optional[int] = None
    ) -> List[DetectionResult]:
        """
        Process entire video file
        
        Args:
            video_path: Path to video file
            skip_frames: Process every nth frame
            max_frames: Maximum frames to process
            
        Returns:
            List of DetectionResult for each processed frame
        """
        cap = cv2.VideoCapture(video_path)
        results = []
        frame_idx = 0
        processed = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % skip_frames == 0:
                result = self.detect(frame)
                results.append(result)
                processed += 1
                
                if max_frames and processed >= max_frames:
                    break
                    
            frame_idx += 1
            
        cap.release()
        return results
    
    def draw_detections(
        self,
        frame: np.ndarray,
        result: DetectionResult
    ) -> np.ndarray:
        """
        Draw detection boxes on frame
        
        Args:
            frame: Input frame
            result: DetectionResult from detect()
            
        Returns:
            Frame with drawn detections
        """
        annotated = frame.copy()
        
        for det in result.detections:
            bbox = det['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Color based on vehicle type
            if det['is_emergency']:
                color = (0, 0, 255)  # Red for emergency
            else:
                color = (0, 255, 0)  # Green for normal vehicles
                
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            cv2.putText(
                annotated, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )
            
        # Draw stats
        stats = f"Vehicles: {result.vehicle_count} | Queue: {result.queue_length}"
        cv2.putText(
            annotated, stats, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
        )
        
        if result.emergency_detected:
            cv2.putText(
                annotated, f"EMERGENCY: {result.emergency_type}", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
            )
            
        return annotated


class EmergencyVehicleDetector:
    """
    Specialized detector for emergency vehicles
    Can be used alongside main detector for higher accuracy
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize emergency vehicle detector
        
        Args:
            model_path: Path to custom emergency vehicle model
        """
        if model_path and Path(model_path).exists():
            self.model = YOLO(model_path)
        else:
            # Use base model and detect by color/features
            self.model = None
            
    def detect_by_color(self, frame: np.ndarray) -> Tuple[bool, str]:
        """
        Detect emergency vehicles by color analysis
        (Fallback when no custom model available)
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (is_emergency, vehicle_type)
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for emergency vehicles
        # Red for ambulance/fire truck
        red_lower1 = np.array([0, 100, 100])
        red_upper1 = np.array([10, 255, 255])
        red_lower2 = np.array([160, 100, 100])
        red_upper2 = np.array([180, 255, 255])
        
        # Blue for police
        blue_lower = np.array([100, 100, 100])
        blue_upper = np.array([130, 255, 255])
        
        # Create masks
        red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
        
        # Check for significant color regions
        red_ratio = np.sum(red_mask > 0) / red_mask.size
        blue_ratio = np.sum(blue_mask > 0) / blue_mask.size
        
        # Thresholds for emergency detection
        if red_ratio > 0.1:
            return True, 'ambulance'  # or fire_truck
        elif blue_ratio > 0.1:
            return True, 'police'
            
        return False, None


if __name__ == '__main__':
    # Test the detector
    import sys
    
    detector = YOLOVehicleDetector()
    
    # Test with webcam or video
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        result = detector.detect(frame)
        annotated = detector.draw_detections(frame, result)
        
        cv2.imshow('Vehicle Detection', annotated)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
