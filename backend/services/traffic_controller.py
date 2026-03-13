"""
Traffic Controller Service
Orchestrates detection, prediction, and signal control
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import cv2
import numpy as np

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.traffic_state_builder import TrafficStateBuilder, IntersectionState
from .detection import DetectionService
from .prediction import PredictionService
from .rl_agent import RLAgentService


@dataclass
class ControllerState:
    """Current controller state"""
    is_running: bool
    current_phase: int
    current_green_time: int
    vehicle_count: int
    queue_length: int
    predicted_count: float
    emergency_active: bool
    timestamp: float


@dataclass
class TrafficMetrics:
    """Traffic metrics"""
    avg_waiting_time: float
    avg_queue_length: float
    throughput: int
    emergency_response_time: float
    vehicles_processed: int
    signals_optimized: int


class TrafficControllerService:
    """
    Main traffic controller service
    Orchestrates the complete traffic management pipeline
    """
    
    def __init__(
        self,
        detection_service: Optional[DetectionService] = None,
        prediction_service: Optional[PredictionService] = None,
        rl_service: Optional[RLAgentService] = None,
        num_lanes: int = 4,
        control_interval: float = 1.0
    ):
        """
        Initialize traffic controller
        
        Args:
            detection_service: Detection service instance
            prediction_service: Prediction service instance
            rl_service: RL agent service instance
            num_lanes: Number of lanes at intersection
            control_interval: Control loop interval (seconds)
        """
        self.detection = detection_service
        self.prediction = prediction_service
        self.rl_agent = rl_service
        self.num_lanes = num_lanes
        self.control_interval = control_interval
        
        # Traffic state builder
        self.state_builder = TrafficStateBuilder(num_lanes=num_lanes)
        
        # Controller state
        self.is_running = False
        self.current_phase = 0
        self.current_green_time = 30
        self.phase_start_time = time.time()
        
        # Metrics tracking
        self.total_vehicles = 0
        self.total_waiting_time = 0
        self.signals_changed = 0
        self.emergency_events = 0
        
        # Control thread
        self.control_thread = None
        
        # Callbacks
        self.state_callbacks: List[Callable] = []
        self.signal_callbacks: List[Callable] = []
        
        # Current data
        self.current_state: Optional[ControllerState] = None
        self.latest_detection = None
        self.latest_prediction = None
        
    async def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "default"
    ) -> Dict:
        """
        Process a single frame through the pipeline
        
        Args:
            frame: Video frame
            camera_id: Camera identifier
            
        Returns:
            Processing result with all data
        """
        result = {
            'timestamp': time.time(),
            'camera_id': camera_id
        }
        
        # 1. Detection
        if self.detection:
            detection = await self.detection.detect_from_frame(frame, camera_id)
            result['detection'] = asdict(detection)
            self.latest_detection = detection
            
            # Update state builder
            intersection_state = self.state_builder.update_from_detection(
                detections=detection.detections,
                frame_shape=frame.shape,
                emergency_detected=detection.emergency_detected,
                emergency_type=detection.emergency_type
            )
            result['intersection_state'] = {
                'total_vehicles': intersection_state.total_vehicles,
                'total_queue': intersection_state.total_queue,
                'average_density': intersection_state.average_density,
                'emergency_detected': intersection_state.emergency_detected
            }
        else:
            detection = None
        
        # 2. Prediction
        if self.prediction and detection:
            prediction = await self.prediction.predict(
                vehicle_count=detection.vehicle_count,
                queue_length=detection.queue_length,
                lane_density=detection.lane_density,
                signal_phase=self.current_phase
            )
            result['prediction'] = asdict(prediction)
            self.latest_prediction = prediction
        else:
            prediction = None
        
        # 3. Signal Decision
        if self.rl_agent and detection:
            predicted_count = prediction.predicted_vehicle_count if prediction else detection.vehicle_count
            
            signal_decision = await self.rl_agent.decide_signal(
                current_vehicle_count=detection.vehicle_count,
                predicted_vehicle_count=predicted_count,
                queue_length=detection.queue_length,
                current_signal_phase=self.current_phase,
                emergency_detected=detection.emergency_detected,
                emergency_lane=None  # Would need lane detection
            )
            result['signal_decision'] = asdict(signal_decision)
            
            # Update controller state
            self.current_green_time = signal_decision.green_time
            self.signals_changed += 1
        
        # Track metrics
        if detection:
            self.total_vehicles += detection.vehicle_count
        
        # Update current state
        self.current_state = ControllerState(
            is_running=self.is_running,
            current_phase=self.current_phase,
            current_green_time=self.current_green_time,
            vehicle_count=detection.vehicle_count if detection else 0,
            queue_length=detection.queue_length if detection else 0,
            predicted_count=prediction.predicted_vehicle_count if prediction else 0,
            emergency_active=detection.emergency_detected if detection else False,
            timestamp=time.time()
        )
        
        # Notify callbacks
        for callback in self.state_callbacks:
            try:
                callback(self.current_state)
            except Exception as e:
                print(f"Callback error: {e}")
        
        return result
    
    def start_camera_feed(self, camera_source, callback: Optional[Callable] = None):
        """
        Start processing camera feed
        
        Args:
            camera_source: Camera source (index, path, or URL)
            callback: Optional callback for each processed frame
        """
        self.is_running = True
        
        async def process_loop():
            cap = cv2.VideoCapture(camera_source)
            if not cap.isOpened():
                print(f"Failed to open camera: {camera_source}")
                return
            
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                result = await self.process_frame(frame)
                
                if callback:
                    callback(result)
                
                await asyncio.sleep(self.control_interval)
            
            cap.release()
        
        # Run in thread
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_loop())
        
        self.control_thread = threading.Thread(target=run_async)
        self.control_thread.start()
    
    def stop(self):
        """Stop the controller"""
        self.is_running = False
        if self.control_thread:
            self.control_thread.join(timeout=5)
    
    def get_current_state(self) -> Optional[ControllerState]:
        """Get current controller state"""
        return self.current_state
    
    def get_metrics(self) -> TrafficMetrics:
        """Get traffic metrics"""
        analytics = self.state_builder.get_analytics()
        
        return TrafficMetrics(
            avg_waiting_time=analytics.get('avg_queue_length', 0) * 2,  # Estimate
            avg_queue_length=analytics.get('avg_queue_length', 0),
            throughput=self.signals_changed,
            emergency_response_time=0,  # Would need tracking
            vehicles_processed=self.total_vehicles,
            signals_optimized=self.signals_changed
        )
    
    def get_live_data(self) -> Dict:
        """Get current live data"""
        state = self.current_state
        
        return {
            'timestamp': time.time(),
            'is_running': self.is_running,
            'current_phase': self.current_phase,
            'green_time': self.current_green_time,
            'vehicle_count': state.vehicle_count if state else 0,
            'queue_length': state.queue_length if state else 0,
            'predicted_count': state.predicted_count if state else 0,
            'emergency_active': state.emergency_active if state else False,
            'analytics': self.state_builder.get_analytics()
        }
    
    def get_lane_states(self) -> Dict:
        """Get per-lane state data"""
        if not self.state_builder.state_history:
            return {}
        
        latest_state = self.state_builder.state_history[-1]
        
        return {
            lane_id: {
                'vehicle_count': lane.vehicle_count,
                'queue_length': lane.queue_length,
                'density': lane.density,
                'emergency': lane.emergency_present
            }
            for lane_id, lane in latest_state.lanes.items()
        }
    
    def set_signal_phase(self, phase: int, duration: int = None):
        """
        Manually set signal phase
        
        Args:
            phase: Phase to set
            duration: Optional duration
        """
        self.current_phase = phase
        if duration:
            self.current_green_time = duration
        self.phase_start_time = time.time()
    
    def trigger_emergency_override(self, lane: int):
        """
        Trigger emergency vehicle override
        
        Args:
            lane: Lane with emergency vehicle
        """
        if self.rl_agent:
            self.rl_agent.emergency_controller.check_emergency(True, lane)
        self.emergency_events += 1
    
    def register_state_callback(self, callback: Callable):
        """Register callback for state updates"""
        self.state_callbacks.append(callback)
    
    def register_signal_callback(self, callback: Callable):
        """Register callback for signal changes"""
        self.signal_callbacks.append(callback)
