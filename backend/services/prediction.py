"""
Prediction Service
Handles traffic prediction using LSTM model
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_models.lstm_model import TrafficPredictor, PredictionResult


@dataclass
class PredictionResponse:
    """API response for prediction results"""
    predicted_vehicle_count: float
    confidence: float
    trend: str  # 'increasing', 'decreasing', 'stable'
    prediction_horizon: str
    timestamp: float


class PredictionService:
    """
    Service for traffic prediction operations
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        sequence_length: int = 15
    ):
        """
        Initialize prediction service
        
        Args:
            model_path: Path to trained LSTM model
            sequence_length: Input sequence length
        """
        self.sequence_length = sequence_length
        
        # Initialize predictor
        try:
            self.predictor = TrafficPredictor(
                model_path=model_path,
                sequence_length=sequence_length
            )
            self.is_ready = True
        except Exception as e:
            print(f"Failed to initialize predictor: {e}")
            self.predictor = None
            self.is_ready = False
        
        # Statistics
        self.total_predictions = 0
        self.prediction_history = []
        
    async def predict(
        self,
        vehicle_count: int,
        queue_length: int,
        lane_density: float,
        signal_phase: int
    ) -> PredictionResponse:
        """
        Update history and get prediction
        
        Args:
            vehicle_count: Current vehicle count
            queue_length: Current queue length
            lane_density: Current lane density
            signal_phase: Current signal phase
            
        Returns:
            PredictionResponse with predicted values
        """
        if not self.is_ready:
            return PredictionResponse(
                predicted_vehicle_count=float(vehicle_count),
                confidence=0.0,
                trend='stable',
                prediction_horizon='next_timestep',
                timestamp=time.time()
            )
        
        # Update history
        self.predictor.update_history(
            vehicle_count, queue_length, lane_density, signal_phase
        )
        
        # Get prediction
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.predictor.predict
        )
        
        self.total_predictions += 1
        
        # Determine trend
        trend = self._calculate_trend(vehicle_count, result.predicted_vehicle_count)
        
        # Store in history
        self.prediction_history.append({
            'actual': vehicle_count,
            'predicted': result.predicted_vehicle_count,
            'timestamp': time.time()
        })
        
        # Keep only recent history
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-500:]
        
        return PredictionResponse(
            predicted_vehicle_count=result.predicted_vehicle_count,
            confidence=result.confidence,
            trend=trend,
            prediction_horizon='next_timestep',
            timestamp=time.time()
        )
    
    async def predict_from_sequence(
        self,
        sequence: List[Dict]
    ) -> PredictionResponse:
        """
        Predict from provided sequence
        
        Args:
            sequence: List of observation dicts with keys:
                     vehicle_count, queue_length, lane_density, signal_phase
            
        Returns:
            PredictionResponse
        """
        if not self.is_ready:
            return PredictionResponse(
                predicted_vehicle_count=0.0,
                confidence=0.0,
                trend='stable',
                prediction_horizon='next_timestep',
                timestamp=time.time()
            )
        
        # Convert to numpy array
        data = []
        for obs in sequence:
            data.append([
                obs.get('vehicle_count', 0),
                obs.get('queue_length', 0),
                obs.get('lane_density', 0.5),
                obs.get('signal_phase', 0)
            ])
        
        # Pad if necessary
        while len(data) < self.sequence_length:
            data.insert(0, data[0] if data else [0, 0, 0.5, 0])
        
        sequence_array = np.array(data[-self.sequence_length:])
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.predictor.predict,
            sequence_array
        )
        
        trend = self._calculate_trend(
            sequence[-1].get('vehicle_count', 0) if sequence else 0,
            result.predicted_vehicle_count
        )
        
        return PredictionResponse(
            predicted_vehicle_count=result.predicted_vehicle_count,
            confidence=result.confidence,
            trend=trend,
            prediction_horizon='next_timestep',
            timestamp=time.time()
        )
    
    def _calculate_trend(self, current: float, predicted: float) -> str:
        """Calculate trend direction"""
        diff = predicted - current
        if diff > 2:
            return 'increasing'
        elif diff < -2:
            return 'decreasing'
        return 'stable'
    
    def get_statistics(self) -> Dict:
        """Get prediction statistics"""
        accuracy = 0.0
        if len(self.prediction_history) > 1:
            errors = []
            for i in range(1, len(self.prediction_history)):
                actual = self.prediction_history[i]['actual']
                predicted = self.prediction_history[i-1]['predicted']
                if actual > 0:
                    errors.append(abs(actual - predicted) / actual)
            if errors:
                accuracy = 1 - np.mean(errors)
        
        return {
            'total_predictions': self.total_predictions,
            'is_ready': self.is_ready,
            'sequence_length': self.sequence_length,
            'recent_accuracy': float(accuracy),
            'history_size': len(self.prediction_history)
        }
    
    def get_prediction_history(self, limit: int = 100) -> List[Dict]:
        """Get recent prediction history"""
        return self.prediction_history[-limit:]
