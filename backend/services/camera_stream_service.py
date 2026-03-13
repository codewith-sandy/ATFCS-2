"""
Camera Stream Service
Handles real-time video streaming from multiple traffic cameras with YOLO detection
"""

import asyncio
import cv2
import numpy as np
from typing import Dict, List, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, asdict
import time
import threading
from queue import Queue
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_models.yolo_detector import YOLOVehicleDetector


@dataclass
class LaneMetrics:
    """Metrics for a single lane"""
    lane_id: int
    vehicle_count: int
    queue_length: int
    congestion_level: str  # 'low', 'medium', 'high', 'critical'
    density: float
    signal_state: str  # 'red', 'yellow', 'green'
    emergency_detected: bool


@dataclass
class CameraFeed:
    """Camera feed configuration"""
    camera_id: str
    lane_id: int
    source: str  # RTSP URL, video file path, or device index
    name: str
    is_active: bool
    resolution: Tuple[int, int]


class CameraStreamService:
    """
    Service for managing multiple camera feeds with real-time YOLO detection
    
    Features:
    - Multi-camera support (4+ lanes)
    - Real-time YOLO vehicle detection
    - Bounding box annotation
    - Vehicle counting per lane
    - Congestion level estimation
    - MJPEG/WebSocket streaming
    """
    
    CONGESTION_THRESHOLDS = {
        'low': (0, 5),
        'medium': (5, 15),
        'high': (15, 25),
        'critical': (25, float('inf'))
    }
    
    def __init__(
        self,
        detector: Optional[YOLOVehicleDetector] = None,
        model_path: str = 'yolov8n.pt',
        confidence_threshold: float = 0.25
    ):
        """
        Initialize camera stream service
        
        Args:
            detector: Optional shared YOLO detector
            model_path: Path to YOLO model if detector not provided
            confidence_threshold: Detection confidence threshold
        """
        # Initialize detector
        if detector:
            self.detector = detector
        else:
            try:
                self.detector = YOLOVehicleDetector(
                    model_path=model_path,
                    confidence_threshold=confidence_threshold
                )
            except Exception as e:
                print(f"Failed to initialize YOLO detector: {e}")
                self.detector = None
        
        # Camera feeds storage
        self.cameras: Dict[str, CameraFeed] = {}
        self.captures: Dict[str, cv2.VideoCapture] = {}
        self.lane_metrics: Dict[int, LaneMetrics] = {}
        
        # Thread management
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.running = False
        self.frame_queues: Dict[str, Queue] = {}
        self.annotated_queues: Dict[str, Queue] = {}
        
        # Signal states (updated externally)
        self.signal_states: Dict[int, str] = {
            0: 'red', 1: 'red', 2: 'red', 3: 'red'
        }
        
        # Statistics
        self.fps_stats: Dict[str, float] = {}
        self.processing_times: Dict[str, List[float]] = {}
        
        # Default camera configuration for 4 lanes
        self._setup_default_cameras()
        
    def _setup_default_cameras(self):
        """Setup default camera configuration for 4 lanes"""
        default_cameras = [
            CameraFeed("cam_lane_1", 0, "0", "Lane 1 - North", True, (640, 480)),
            CameraFeed("cam_lane_2", 1, "0", "Lane 2 - East", True, (640, 480)),
            CameraFeed("cam_lane_3", 2, "0", "Lane 3 - South", True, (640, 480)),
            CameraFeed("cam_lane_4", 3, "0", "Lane 4 - West", True, (640, 480)),
        ]
        
        for cam in default_cameras:
            self.cameras[cam.camera_id] = cam
            self.lane_metrics[cam.lane_id] = LaneMetrics(
                lane_id=cam.lane_id,
                vehicle_count=0,
                queue_length=0,
                congestion_level='low',
                density=0.0,
                signal_state='red',
                emergency_detected=False
            )
            self.frame_queues[cam.camera_id] = Queue(maxsize=5)
            self.annotated_queues[cam.camera_id] = Queue(maxsize=5)
            self.processing_times[cam.camera_id] = []
    
    def add_camera(
        self,
        camera_id: str,
        lane_id: int,
        source: str,
        name: str,
        resolution: Tuple[int, int] = (640, 480)
    ) -> bool:
        """
        Add a new camera to the system
        
        Args:
            camera_id: Unique camera identifier
            lane_id: Associated lane number
            source: Camera source (RTSP URL, file path, or device index)
            name: Human-readable camera name
            resolution: Camera resolution
            
        Returns:
            Success status
        """
        if camera_id in self.cameras:
            return False
            
        camera = CameraFeed(
            camera_id=camera_id,
            lane_id=lane_id,
            source=source,
            name=name,
            is_active=True,
            resolution=resolution
        )
        
        self.cameras[camera_id] = camera
        self.lane_metrics[lane_id] = LaneMetrics(
            lane_id=lane_id,
            vehicle_count=0,
            queue_length=0,
            congestion_level='low',
            density=0.0,
            signal_state='red',
            emergency_detected=False
        )
        self.frame_queues[camera_id] = Queue(maxsize=5)
        self.annotated_queues[camera_id] = Queue(maxsize=5)
        self.processing_times[camera_id] = []
        
        return True
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera from the system"""
        if camera_id not in self.cameras:
            return False
            
        # Stop capture if running
        if camera_id in self.captures:
            self.captures[camera_id].release()
            del self.captures[camera_id]
        
        # Remove camera and related data
        lane_id = self.cameras[camera_id].lane_id
        del self.cameras[camera_id]
        
        if lane_id in self.lane_metrics:
            del self.lane_metrics[lane_id]
            
        if camera_id in self.frame_queues:
            del self.frame_queues[camera_id]
            
        if camera_id in self.annotated_queues:
            del self.annotated_queues[camera_id]
            
        return True
    
    def _open_camera(self, camera: CameraFeed) -> Optional[cv2.VideoCapture]:
        """Open camera capture source"""
        try:
            # Determine source type
            if camera.source.isdigit():
                # Webcam device
                cap = cv2.VideoCapture(int(camera.source))
            elif camera.source.startswith(('rtsp://', 'http://', 'https://')):
                # Network stream
                cap = cv2.VideoCapture(camera.source, cv2.CAP_FFMPEG)
            else:
                # File path
                cap = cv2.VideoCapture(camera.source)
            
            if not cap.isOpened():
                return None
                
            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera.resolution[1])
            
            return cap
        except Exception as e:
            print(f"Failed to open camera {camera.camera_id}: {e}")
            return None
    
    def _calculate_congestion_level(self, vehicle_count: int) -> str:
        """Calculate congestion level based on vehicle count"""
        for level, (low, high) in self.CONGESTION_THRESHOLDS.items():
            if low <= vehicle_count < high:
                return level
        return 'critical'
    
    def _estimate_queue_length(self, detections: List[Dict], frame_height: int) -> int:
        """Estimate queue length from detections"""
        if not detections:
            return 0
        
        # Sort detections by y-coordinate (bottom to top)
        sorted_detections = sorted(detections, key=lambda d: d.get('bbox', [0, 0, 0, 0])[3], reverse=True)
        
        # Count vehicles in the lower 60% of the frame (queue area)
        queue_threshold = frame_height * 0.4
        queue_vehicles = [d for d in sorted_detections if d.get('bbox', [0, 0, 0, 0])[1] > queue_threshold]
        
        return len(queue_vehicles)
    
    def _annotate_frame(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        lane_id: int,
        metrics: LaneMetrics
    ) -> np.ndarray:
        """
        Annotate frame with detection boxes and metrics overlay
        
        Args:
            frame: Original frame
            detections: Detection results
            lane_id: Lane identifier
            metrics: Current lane metrics
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        
        # Color mapping for congestion levels
        congestion_colors = {
            'low': (0, 255, 0),       # Green
            'medium': (0, 255, 255),   # Yellow
            'high': (0, 165, 255),     # Orange
            'critical': (0, 0, 255)    # Red
        }
        
        # Draw bounding boxes
        for det in detections:
            bbox = det.get('bbox', [])
            if len(bbox) >= 4:
                x1, y1, x2, y2 = map(int, bbox[:4])
                class_name = det.get('class_name', 'vehicle')
                confidence = det.get('confidence', 0)
                is_emergency = det.get('is_emergency', False)
                
                # Color based on vehicle type
                if is_emergency:
                    color = (255, 0, 255)  # Magenta for emergency
                    thickness = 3
                else:
                    color = (0, 255, 0)  # Green for normal
                    thickness = 2
                
                # Draw box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
                
                # Draw label
                label = f"{class_name}: {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(annotated, (x1, y1 - 20), (x1 + label_size[0], y1), color, -1)
                cv2.putText(annotated, label, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw metrics overlay
        overlay = annotated.copy()
        
        # Semi-transparent background for metrics
        cv2.rectangle(overlay, (10, 10), (250, 130), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)
        
        # Congestion indicator
        cong_color = congestion_colors.get(metrics.congestion_level, (255, 255, 255))
        cv2.putText(annotated, f"Lane {lane_id + 1}", (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(annotated, f"Vehicles: {metrics.vehicle_count}", (20, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(annotated, f"Queue: {metrics.queue_length}", (20, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(annotated, f"Congestion: {metrics.congestion_level.upper()}", (20, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, cong_color, 2)
        
        # Signal indicator
        signal_color = {'green': (0, 255, 0), 'yellow': (0, 255, 255), 'red': (0, 0, 255)}
        cv2.circle(annotated, (230, 70), 15, signal_color.get(metrics.signal_state, (128, 128, 128)), -1)
        
        # Emergency alert
        if metrics.emergency_detected:
            cv2.putText(annotated, "EMERGENCY DETECTED!", (20, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return annotated
    
    def process_frame(self, camera_id: str, frame: np.ndarray) -> Tuple[np.ndarray, LaneMetrics]:
        """
        Process a single frame with YOLO detection
        
        Args:
            camera_id: Camera identifier
            frame: Input frame
            
        Returns:
            Tuple of (annotated_frame, lane_metrics)
        """
        camera = self.cameras.get(camera_id)
        if not camera:
            return frame, None
            
        lane_id = camera.lane_id
        start_time = time.time()
        
        # Run detection
        if self.detector:
            result = self.detector.detect(frame)
            detections = result.detections
            vehicle_count = result.vehicle_count
            emergency_detected = result.emergency_detected
        else:
            # Mock data if no detector
            detections = []
            vehicle_count = np.random.randint(0, 20)
            emergency_detected = False
        
        # Calculate metrics
        queue_length = self._estimate_queue_length(detections, frame.shape[0])
        congestion_level = self._calculate_congestion_level(vehicle_count)
        density = min(vehicle_count / 30.0, 1.0)  # Normalize to 0-1
        
        # Update lane metrics
        metrics = LaneMetrics(
            lane_id=lane_id,
            vehicle_count=vehicle_count,
            queue_length=queue_length,
            congestion_level=congestion_level,
            density=density,
            signal_state=self.signal_states.get(lane_id, 'red'),
            emergency_detected=emergency_detected
        )
        self.lane_metrics[lane_id] = metrics
        
        # Annotate frame
        annotated_frame = self._annotate_frame(frame, detections, lane_id, metrics)
        
        # Track processing time
        processing_time = time.time() - start_time
        self.processing_times[camera_id].append(processing_time)
        if len(self.processing_times[camera_id]) > 100:
            self.processing_times[camera_id] = self.processing_times[camera_id][-100:]
        
        return annotated_frame, metrics
    
    def _generate_demo_frame(self, camera_id: str) -> np.ndarray:
        """Generate a demo frame with simulated traffic"""
        camera = self.cameras.get(camera_id)
        width, height = camera.resolution if camera else (640, 480)
        lane_id = camera.lane_id if camera else 0
        
        # Create a dark road-like background
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # Dark gray
        
        # Draw lane markings
        cv2.line(frame, (width // 2, 0), (width // 2, height), (255, 255, 255), 2)
        
        # Draw some simulated vehicles (rectangles)
        np.random.seed(int(time.time() * 1000) % 10000 + lane_id)
        num_vehicles = np.random.randint(3, 15)
        
        for _ in range(num_vehicles):
            x = np.random.randint(50, width - 100)
            y = np.random.randint(50, height - 80)
            w = np.random.randint(40, 80)
            h = np.random.randint(30, 60)
            color = (np.random.randint(100, 255), np.random.randint(100, 255), np.random.randint(100, 255))
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 0), 2)
        
        # Add lane label
        lane_names = ['North', 'East', 'South', 'West']
        lane_name = lane_names[lane_id] if lane_id < 4 else f"Lane {lane_id + 1}"
        cv2.putText(frame, f"{lane_name} Camera", (10, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    async def generate_frames(self, camera_id: str) -> AsyncGenerator[bytes, None]:
        """
        Generate MJPEG stream for a specific camera
        
        Args:
            camera_id: Camera identifier
            
        Yields:
            JPEG-encoded frames as bytes
        """
        camera = self.cameras.get(camera_id)
        if not camera:
            # Generate error frame
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Camera not found", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, jpeg = cv2.imencode('.jpg', error_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            return
        
        # Try to open camera
        cap = self._open_camera(camera)
        use_demo = cap is None or not cap.isOpened()
        
        try:
            frame_time = 1.0 / 30  # Target 30 FPS
            
            while True:
                start_time = time.time()
                
                if use_demo:
                    # Generate demo frame
                    frame = self._generate_demo_frame(camera_id)
                else:
                    ret, frame = cap.read()
                    if not ret:
                        # Loop video or switch to demo
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                
                # Process frame with detection
                annotated_frame, metrics = self.process_frame(camera_id, frame)
                
                # Encode as JPEG
                _, jpeg = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                try:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                except (GeneratorExit, asyncio.CancelledError):
                    # Client disconnected, exit gracefully
                    break
                
                # Maintain frame rate
                elapsed = time.time() - start_time
                if elapsed < frame_time:
                    await asyncio.sleep(frame_time - elapsed)
                    
        except (GeneratorExit, asyncio.CancelledError):
            # Client disconnected during processing
            pass
        finally:
            if cap and cap.isOpened():
                cap.release()
    
    def get_lane_metrics(self, lane_id: int) -> Optional[LaneMetrics]:
        """Get current metrics for a specific lane"""
        return self.lane_metrics.get(lane_id)
    
    def get_all_lane_metrics(self) -> Dict[int, LaneMetrics]:
        """Get metrics for all lanes"""
        return self.lane_metrics
    
    def get_all_lane_metrics_dict(self) -> List[Dict]:
        """Get all lane metrics as a list of dictionaries"""
        return [asdict(m) for m in self.lane_metrics.values()]
    
    def update_signal_state(self, lane_id: int, state: str):
        """Update signal state for a lane"""
        if state in ['red', 'yellow', 'green']:
            self.signal_states[lane_id] = state
            if lane_id in self.lane_metrics:
                self.lane_metrics[lane_id].signal_state = state
    
    def get_camera_list(self) -> List[Dict]:
        """Get list of all configured cameras"""
        return [
            {
                'camera_id': cam.camera_id,
                'lane_id': cam.lane_id,
                'name': cam.name,
                'is_active': cam.is_active,
                'resolution': cam.resolution,
                'source': cam.source
            }
            for cam in self.cameras.values()
        ]
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        stats = {
            'total_cameras': len(self.cameras),
            'active_cameras': sum(1 for c in self.cameras.values() if c.is_active),
            'detector_available': self.detector is not None,
            'fps_per_camera': {},
            'total_vehicles': sum(m.vehicle_count for m in self.lane_metrics.values()),
            'emergency_count': sum(1 for m in self.lane_metrics.values() if m.emergency_detected)
        }
        
        # Calculate FPS for each camera
        for cam_id, times in self.processing_times.items():
            if times:
                avg_time = sum(times) / len(times)
                stats['fps_per_camera'][cam_id] = round(1.0 / avg_time if avg_time > 0 else 0, 2)
        
        return stats
    
    def configure_camera_source(self, camera_id: str, source: str) -> bool:
        """Update camera source (RTSP URL, file path, etc.)"""
        if camera_id not in self.cameras:
            return False
        
        camera = self.cameras[camera_id]
        # Create new camera feed with updated source
        self.cameras[camera_id] = CameraFeed(
            camera_id=camera.camera_id,
            lane_id=camera.lane_id,
            source=source,
            name=camera.name,
            is_active=camera.is_active,
            resolution=camera.resolution
        )
        return True
    
    def detect_available_cameras(self, max_cameras: int = 10) -> List[Dict]:
        """
        Detect available cameras connected to the system
        
        Args:
            max_cameras: Maximum number of camera indices to check
            
        Returns:
            List of available camera information
        """
        available_cameras = []
        
        for index in range(max_cameras):
            try:
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # Use DirectShow on Windows
                if cap.isOpened():
                    # Get camera properties
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    # Try to read a frame to verify camera works
                    ret, frame = cap.read()
                    if ret:
                        camera_info = {
                            'index': index,
                            'name': f'Camera {index}',
                            'source': str(index),
                            'resolution': (width, height),
                            'fps': fps if fps > 0 else 30.0,
                            'available': True,
                            'backend': 'DirectShow'
                        }
                        available_cameras.append(camera_info)
                    
                    cap.release()
            except Exception as e:
                print(f"Error checking camera {index}: {e}")
                continue
        
        # Also check using default backend for cross-platform support
        if not available_cameras:
            for index in range(max_cameras):
                try:
                    cap = cv2.VideoCapture(index)
                    if cap.isOpened():
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        ret, frame = cap.read()
                        if ret:
                            camera_info = {
                                'index': index,
                                'name': f'Camera {index}',
                                'source': str(index),
                                'resolution': (width, height),
                                'fps': fps if fps > 0 else 30.0,
                                'available': True,
                                'backend': 'Default'
                            }
                            available_cameras.append(camera_info)
                        
                        cap.release()
                except Exception as e:
                    continue
        
        return available_cameras
    
    def assign_camera_to_lane(self, camera_index: int, lane_id: int, name: str = None) -> bool:
        """
        Assign a detected camera to a specific lane
        
        Args:
            camera_index: The camera device index
            lane_id: The lane to assign the camera to
            name: Optional custom name for the camera
            
        Returns:
            Success status
        """
        camera_id = f"cam_lane_{lane_id + 1}"
        
        # Update existing camera or create new one
        if camera_id in self.cameras:
            self.configure_camera_source(camera_id, str(camera_index))
            if name:
                camera = self.cameras[camera_id]
                self.cameras[camera_id] = CameraFeed(
                    camera_id=camera.camera_id,
                    lane_id=camera.lane_id,
                    source=str(camera_index),
                    name=name,
                    is_active=camera.is_active,
                    resolution=camera.resolution
                )
        else:
            lane_names = ['North', 'East', 'South', 'West']
            default_name = f"Lane {lane_id + 1} - {lane_names[lane_id] if lane_id < 4 else 'Custom'}"
            self.add_camera(
                camera_id=camera_id,
                lane_id=lane_id,
                source=str(camera_index),
                name=name or default_name
            )
        
        return True


# Singleton instance
_camera_service_instance: Optional[CameraStreamService] = None


def get_camera_service() -> CameraStreamService:
    """Get or create camera service instance"""
    global _camera_service_instance
    if _camera_service_instance is None:
        _camera_service_instance = CameraStreamService()
    return _camera_service_instance
