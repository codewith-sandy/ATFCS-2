"""
RL Agent Service
Handles reinforcement learning agent operations
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from ai_models.q_learning_agent import (
    QLearningAgent,
    TrafficState,
    AdaptiveTrafficController,
    EmergencyOverrideController
)


@dataclass
class SignalDecision:
    """Signal decision response"""
    green_time: int
    phase: int
    is_emergency_override: bool
    confidence: float
    q_values: Dict[int, float]
    timestamp: float


class RLAgentService:
    """
    Service for RL agent operations
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9
    ):
        """
        Initialize RL agent service
        
        Args:
            model_path: Path to saved agent
            learning_rate: Learning rate
            discount_factor: Discount factor
        """
        # Initialize controller
        self.agent = QLearningAgent(
            learning_rate=learning_rate,
            discount_factor=discount_factor
        )
        
        self.emergency_controller = EmergencyOverrideController()
        
        self.controller = AdaptiveTrafficController(
            rl_agent=self.agent,
            emergency_controller=self.emergency_controller
        )
        
        # Load saved model if available
        if model_path and Path(model_path).exists():
            try:
                self.agent.load(model_path)
            except Exception as e:
                print(f"Failed to load agent: {e}")
        
        self.is_ready = True
        self.is_training = False
        
        # Decision history
        self.decision_history = []
        
    async def decide_signal(
        self,
        current_vehicle_count: int,
        predicted_vehicle_count: float,
        queue_length: int,
        current_signal_phase: int,
        emergency_detected: bool = False,
        emergency_lane: Optional[int] = None
    ) -> SignalDecision:
        """
        Get signal timing decision from RL agent
        
        Args:
            current_vehicle_count: Current vehicle count
            predicted_vehicle_count: Predicted vehicle count
            queue_length: Current queue length
            current_signal_phase: Current signal phase
            emergency_detected: Emergency vehicle flag
            emergency_lane: Lane with emergency vehicle
            
        Returns:
            SignalDecision with timing recommendation
        """
        # Create traffic state
        state = TrafficState(
            current_vehicle_count=current_vehicle_count,
            predicted_vehicle_count=predicted_vehicle_count,
            queue_length=queue_length,
            current_signal_phase=current_signal_phase
        )
        
        # Get decision
        decision = self.controller.decide_signal(
            traffic_state=state,
            emergency_detected=emergency_detected,
            emergency_lane=emergency_lane,
            training=self.is_training
        )
        
        # Create response
        response = SignalDecision(
            green_time=decision['green_time'],
            phase=decision['phase'],
            is_emergency_override=decision['emergency'],
            confidence=decision.get('confidence', 1.0),
            q_values=decision.get('q_values', {}),
            timestamp=time.time()
        )
        
        # Store in history
        self.decision_history.append({
            'state': {
                'vehicle_count': current_vehicle_count,
                'predicted': predicted_vehicle_count,
                'queue': queue_length,
                'phase': current_signal_phase
            },
            'decision': response,
            'timestamp': time.time()
        })
        
        # Keep history bounded
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]
        
        return response
    
    async def update_from_feedback(
        self,
        state: Dict,
        action: int,
        next_state: Dict,
        queue_length: int,
        waiting_time: float,
        emergency_blocked: bool = False
    ) -> Dict:
        """
        Update agent from feedback
        
        Args:
            state: Previous state dict
            action: Action taken
            next_state: Resulting state dict
            queue_length: Resulting queue length
            waiting_time: Resulting waiting time
            emergency_blocked: Whether emergency was blocked
            
        Returns:
            Update info
        """
        # Convert to TrafficState
        prev_state = TrafficState(
            current_vehicle_count=state.get('vehicle_count', 0),
            predicted_vehicle_count=state.get('predicted', 0),
            queue_length=state.get('queue', 0),
            current_signal_phase=state.get('phase', 0)
        )
        
        new_state = TrafficState(
            current_vehicle_count=next_state.get('vehicle_count', 0),
            predicted_vehicle_count=next_state.get('predicted', 0),
            queue_length=next_state.get('queue', 0),
            current_signal_phase=next_state.get('phase', 0)
        )
        
        # Update controller
        td_error = self.controller.update_from_feedback(
            state=prev_state,
            action=action,
            next_state=new_state,
            queue_length=queue_length,
            waiting_time=waiting_time,
            emergency_blocked=emergency_blocked
        )
        
        return {
            'td_error': td_error,
            'epsilon': self.agent.epsilon,
            'updated': True
        }
    
    def start_training(self):
        """Enable training mode"""
        self.is_training = True
        
    def stop_training(self):
        """Disable training mode"""
        self.is_training = False
        
    def save_agent(self, path: str):
        """Save agent to file"""
        self.agent.save(path)
        
    def load_agent(self, path: str):
        """Load agent from file"""
        self.agent.load(path)
        
    def get_statistics(self) -> Dict:
        """Get agent statistics"""
        stats = self.agent.get_training_stats()
        stats['is_ready'] = self.is_ready
        stats['is_training'] = self.is_training
        stats['decisions_made'] = len(self.decision_history)
        return stats
    
    def get_decision_history(self, limit: int = 100) -> List[Dict]:
        """Get recent decision history"""
        return self.decision_history[-limit:]
    
    def reset_exploration(self):
        """Reset exploration rate"""
        self.agent.reset_exploration()
