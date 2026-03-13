"""
Traffic State Builder
Aggregates detection results into traffic state for RL agent
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class LaneState:
    """State for a single lane"""
    lane_id: int
    vehicle_count: int
    queue_length: int
    density: float
    average_speed: float = 0.0
    emergency_present: bool = False
    emergency_type: Optional[str] = None


@dataclass
class IntersectionState:
    """Complete intersection state"""
    timestamp: float
    lanes: Dict[int, LaneState]
    total_vehicles: int
    total_queue: int
    average_density: float
    current_phase: int
    emergency_detected: bool
    emergency_lane: Optional[int]
    predicted_count: Optional[float] = None


class TrafficStateBuilder:
    """
    Builds traffic state from detection results
    Aggregates data across time steps for stable state representation
    """
    
    def __init__(
        self,
        num_lanes: int = 4,
        history_size: int = 30,
        smoothing_window: int = 5
    ):
        """
        Initialize traffic state builder
        
        Args:
            num_lanes: Number of lanes at intersection
            history_size: Size of state history buffer
            smoothing_window: Window size for temporal smoothing
        """
        self.num_lanes = num_lanes
        self.history_size = history_size
        self.smoothing_window = smoothing_window
        
        # Detection history per lane
        self.lane_histories = {
            i: deque(maxlen=history_size)
            for i in range(num_lanes)
        }
        
        # Global state history
        self.state_history = deque(maxlen=history_size)
        
        # Signal phase tracking
        self.current_phase = 0
        self.phase_start_time = time.time()
        
    def update_from_detection(
        self,
        detections: List[Dict],
        frame_shape: Tuple[int, int],
        emergency_detected: bool = False,
        emergency_type: Optional[str] = None
    ) -> IntersectionState:
        """
        Update state from detection results
        
        Args:
            detections: List of detection dictionaries from YOLO
            frame_shape: Shape of the frame (height, width)
            emergency_detected: Whether emergency vehicle detected
            emergency_type: Type of emergency vehicle
            
        Returns:
            Updated IntersectionState
        """
        timestamp = time.time()
        
        # Assign detections to lanes based on position
        lane_detections = self._assign_detections_to_lanes(detections, frame_shape)
        
        # Calculate per-lane states
        lane_states = {}
        emergency_lane = None
        
        for lane_id in range(self.num_lanes):
            lane_dets = lane_detections.get(lane_id, [])
            
            # Count vehicles
            vehicle_count = len(lane_dets)
            
            # Calculate queue (stationary/slow vehicles)
            queue_length = self._calculate_queue(lane_dets, frame_shape)
            
            # Calculate density
            density = min(vehicle_count / 10.0, 1.0)  # Normalize to max 10 vehicles
            
            # Check for emergency in this lane
            lane_emergency = any(d.get('is_emergency', False) for d in lane_dets)
            lane_emergency_type = None
            if lane_emergency:
                emergency_lane = lane_id
                for d in lane_dets:
                    if d.get('is_emergency', False):
                        lane_emergency_type = d.get('class_name')
                        break
            
            lane_state = LaneState(
                lane_id=lane_id,
                vehicle_count=vehicle_count,
                queue_length=queue_length,
                density=density,
                emergency_present=lane_emergency,
                emergency_type=lane_emergency_type
            )
            
            lane_states[lane_id] = lane_state
            
            # Update history
            self.lane_histories[lane_id].append({
                'vehicle_count': vehicle_count,
                'queue_length': queue_length,
                'density': density,
                'timestamp': timestamp
            })
        
        # Aggregate totals
        total_vehicles = sum(ls.vehicle_count for ls in lane_states.values())
        total_queue = sum(ls.queue_length for ls in lane_states.values())
        average_density = np.mean([ls.density for ls in lane_states.values()])
        
        # Create intersection state
        state = IntersectionState(
            timestamp=timestamp,
            lanes=lane_states,
            total_vehicles=total_vehicles,
            total_queue=total_queue,
            average_density=average_density,
            current_phase=self.current_phase,
            emergency_detected=emergency_detected,
            emergency_lane=emergency_lane
        )
        
        # Add to history
        self.state_history.append(state)
        
        return state
    
    def _assign_detections_to_lanes(
        self,
        detections: List[Dict],
        frame_shape: Tuple[int, int]
    ) -> Dict[int, List[Dict]]:
        """
        Assign detections to lanes based on position
        
        Args:
            detections: List of detection dictionaries
            frame_shape: Frame shape (height, width)
            
        Returns:
            Dictionary mapping lane_id to list of detections
        """
        height, width = frame_shape[:2]
        lane_width = width // 2
        lane_height = height // 2
        
        lane_detections = {i: [] for i in range(self.num_lanes)}
        
        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            
            # Determine lane based on position (quadrant-based for 4-way intersection)
            if cx < lane_width:
                if cy < lane_height:
                    lane_id = 0  # Top-left
                else:
                    lane_id = 2  # Bottom-left
            else:
                if cy < lane_height:
                    lane_id = 1  # Top-right
                else:
                    lane_id = 3  # Bottom-right
                    
            lane_detections[lane_id].append(det)
            
        return lane_detections
    
    def _calculate_queue(
        self,
        detections: List[Dict],
        frame_shape: Tuple[int, int]
    ) -> int:
        """
        Calculate queue length (vehicles waiting at stop line)
        
        Args:
            detections: Detections in this lane
            frame_shape: Frame shape
            
        Returns:
            Queue length (number of vehicles)
        """
        if not detections:
            return 0
            
        height = frame_shape[0]
        queue_zone = height * 0.7  # Lower 30% of frame is queue zone
        
        queue_count = 0
        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            if bbox[3] > queue_zone:  # Bottom of bbox in queue zone
                queue_count += 1
                
        return queue_count
    
    def get_smoothed_state(self, lane_id: int = None) -> Dict:
        """
        Get temporally smoothed state
        
        Args:
            lane_id: Optional specific lane, None for global
            
        Returns:
            Smoothed state dictionary
        """
        if lane_id is not None:
            history = list(self.lane_histories[lane_id])[-self.smoothing_window:]
        else:
            history = [
                {
                    'vehicle_count': s.total_vehicles,
                    'queue_length': s.total_queue,
                    'density': s.average_density
                }
                for s in list(self.state_history)[-self.smoothing_window:]
            ]
        
        if not history:
            return {
                'vehicle_count': 0,
                'queue_length': 0,
                'density': 0.0
            }
        
        return {
            'vehicle_count': np.mean([h['vehicle_count'] for h in history]),
            'queue_length': np.mean([h['queue_length'] for h in history]),
            'density': np.mean([h['density'] for h in history])
        }
    
    def get_time_series(
        self,
        feature: str = 'vehicle_count',
        length: int = 15
    ) -> np.ndarray:
        """
        Get time series data for prediction
        
        Args:
            feature: Feature to extract
            length: Length of time series
            
        Returns:
            Numpy array of feature values
        """
        history = list(self.state_history)[-length:]
        
        if not history:
            return np.zeros(length)
        
        values = []
        for state in history:
            if feature == 'vehicle_count':
                values.append(state.total_vehicles)
            elif feature == 'queue_length':
                values.append(state.total_queue)
            elif feature == 'density':
                values.append(state.average_density)
            else:
                values.append(0)
        
        # Pad if necessary
        if len(values) < length:
            values = [values[0]] * (length - len(values)) + values
            
        return np.array(values)
    
    def get_prediction_input(self, sequence_length: int = 15) -> np.ndarray:
        """
        Get formatted input for LSTM prediction model
        
        Args:
            sequence_length: Required sequence length
            
        Returns:
            Array of shape (sequence_length, 4) with features:
            [vehicle_count, queue_length, density, signal_phase]
        """
        history = list(self.state_history)[-sequence_length:]
        
        if not history:
            return np.zeros((sequence_length, 4))
        
        data = []
        for state in history:
            data.append([
                state.total_vehicles,
                state.total_queue,
                state.average_density,
                state.current_phase
            ])
        
        # Pad if necessary
        while len(data) < sequence_length:
            data.insert(0, data[0] if data else [0, 0, 0, 0])
            
        return np.array(data)
    
    def update_signal_phase(self, phase: int):
        """
        Update current signal phase
        
        Args:
            phase: New signal phase (0-3)
        """
        self.current_phase = phase
        self.phase_start_time = time.time()
    
    def get_rl_state(self, predicted_count: float = None):
        """
        Get state representation for RL agent
        
        Args:
            predicted_count: Predicted vehicle count from LSTM
            
        Returns:
            TrafficState object for RL agent
        """
        from ai_models.q_learning_agent import TrafficState
        
        smoothed = self.get_smoothed_state()
        
        return TrafficState(
            current_vehicle_count=int(smoothed['vehicle_count']),
            predicted_vehicle_count=predicted_count or smoothed['vehicle_count'],
            queue_length=int(smoothed['queue_length']),
            current_signal_phase=self.current_phase
        )
    
    def get_analytics(self) -> Dict:
        """
        Get traffic analytics
        
        Returns:
            Dictionary with analytics data
        """
        if not self.state_history:
            return {}
        
        recent_states = list(self.state_history)[-60:]  # Last minute
        
        return {
            'avg_vehicle_count': np.mean([s.total_vehicles for s in recent_states]),
            'max_vehicle_count': max(s.total_vehicles for s in recent_states),
            'min_vehicle_count': min(s.total_vehicles for s in recent_states),
            'avg_queue_length': np.mean([s.total_queue for s in recent_states]),
            'max_queue_length': max(s.total_queue for s in recent_states),
            'avg_density': np.mean([s.average_density for s in recent_states]),
            'emergency_events': sum(1 for s in recent_states if s.emergency_detected),
            'current_phase': self.current_phase,
            'states_collected': len(self.state_history)
        }


class MultiIntersectionStateBuilder:
    """
    Manages traffic state for multiple intersections
    """
    
    def __init__(self, intersection_ids: List[str]):
        """
        Initialize multi-intersection builder
        
        Args:
            intersection_ids: List of intersection IDs
        """
        self.builders = {
            iid: TrafficStateBuilder()
            for iid in intersection_ids
        }
        
    def update_intersection(
        self,
        intersection_id: str,
        detections: List[Dict],
        frame_shape: Tuple[int, int],
        emergency_detected: bool = False,
        emergency_type: Optional[str] = None
    ) -> Optional[IntersectionState]:
        """
        Update state for a specific intersection
        
        Args:
            intersection_id: Intersection identifier
            detections: Detection results
            frame_shape: Frame shape
            emergency_detected: Emergency flag
            emergency_type: Emergency type
            
        Returns:
            IntersectionState or None
        """
        if intersection_id not in self.builders:
            return None
            
        return self.builders[intersection_id].update_from_detection(
            detections, frame_shape, emergency_detected, emergency_type
        )
    
    def get_all_states(self) -> Dict[str, IntersectionState]:
        """Get current state for all intersections"""
        states = {}
        for iid, builder in self.builders.items():
            if builder.state_history:
                states[iid] = builder.state_history[-1]
        return states


if __name__ == '__main__':
    # Test traffic state builder
    builder = TrafficStateBuilder(num_lanes=4)
    
    # Simulate some detections
    for i in range(30):
        # Generate random detections
        num_vehicles = np.random.randint(5, 15)
        detections = []
        
        for j in range(num_vehicles):
            det = {
                'class_id': 2,
                'class_name': 'car',
                'confidence': 0.8,
                'bbox': [
                    np.random.randint(0, 600),
                    np.random.randint(0, 400),
                    np.random.randint(20, 100),
                    np.random.randint(20, 60)
                ],
                'is_emergency': j == 0 and i == 15  # One emergency at step 15
            }
            detections.append(det)
        
        state = builder.update_from_detection(
            detections,
            (480, 640),
            emergency_detected=any(d['is_emergency'] for d in detections)
        )
        
        print(f"Step {i}: Vehicles={state.total_vehicles}, Queue={state.total_queue}, Emergency={state.emergency_detected}")
    
    # Get analytics
    print("\nAnalytics:", builder.get_analytics())
    
    # Get prediction input
    pred_input = builder.get_prediction_input()
    print(f"\nPrediction input shape: {pred_input.shape}")
    
    # Get RL state
    rl_state = builder.get_rl_state(predicted_count=12.5)
    print(f"\nRL State: {rl_state}")
