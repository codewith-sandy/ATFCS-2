"""
Q-Learning Reinforcement Learning Agent
Adaptive traffic signal controller using Q-Learning
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import pickle
from pathlib import Path
import random
from collections import defaultdict


@dataclass
class TrafficState:
    """Traffic state representation"""
    current_vehicle_count: int
    predicted_vehicle_count: float
    queue_length: int
    current_signal_phase: int
    
    def to_discrete(self, bins: Dict[str, List[float]]) -> Tuple:
        """Convert continuous state to discrete for Q-table"""
        vehicle_bin = np.digitize(self.current_vehicle_count, bins['vehicle_count'])
        predicted_bin = np.digitize(self.predicted_vehicle_count, bins['predicted_count'])
        queue_bin = np.digitize(self.queue_length, bins['queue_length'])
        
        return (vehicle_bin, predicted_bin, queue_bin, self.current_signal_phase)


@dataclass
class SignalAction:
    """Signal action representation"""
    green_time: int
    phase: int


class QLearningAgent:
    """
    Q-Learning agent for adaptive traffic signal control
    
    State Space:
        S = {current_vehicle_count, predicted_vehicle_count, queue_length, current_signal_phase}
    
    Action Space:
        A = {green_time: 10, 20, 30, 40 seconds}
    
    Reward Function:
        R = -(α₁ * queue_length + α₂ * waiting_time)
    """
    
    # Available green time durations (seconds)
    GREEN_TIMES = [10, 20, 30, 40]
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.1,
        epsilon_decay: float = 0.995,
        alpha_queue: float = 1.0,
        alpha_waiting: float = 0.5,
        num_phases: int = 4
    ):
        """
        Initialize Q-Learning agent
        
        Args:
            learning_rate: Learning rate (α)
            discount_factor: Discount factor (γ)
            epsilon_start: Initial exploration rate
            epsilon_end: Final exploration rate
            epsilon_decay: Decay rate for epsilon
            alpha_queue: Weight for queue length in reward
            alpha_waiting: Weight for waiting time in reward
            num_phases: Number of signal phases
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon_start
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.alpha_queue = alpha_queue
        self.alpha_waiting = alpha_waiting
        self.num_phases = num_phases
        
        # State discretization bins
        self.state_bins = {
            'vehicle_count': [5, 10, 15, 20, 30],
            'predicted_count': [5, 10, 15, 20, 30],
            'queue_length': [2, 5, 8, 12, 15]
        }
        
        # Q-table: maps (state, action) -> value
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        # Training statistics
        self.total_episodes = 0
        self.total_steps = 0
        self.rewards_history = []
        self.avg_rewards = []
        
    @property
    def action_space(self) -> List[int]:
        """Get available actions (green times)"""
        return self.GREEN_TIMES
    
    def get_state_key(self, state: TrafficState) -> Tuple:
        """Convert state to hashable key for Q-table"""
        return state.to_discrete(self.state_bins)
    
    def choose_action(self, state: TrafficState, training: bool = True) -> int:
        """
        Choose action using epsilon-greedy policy
        
        Args:
            state: Current traffic state
            training: Whether in training mode
            
        Returns:
            Selected green time (action)
        """
        state_key = self.get_state_key(state)
        
        # Epsilon-greedy exploration
        if training and random.random() < self.epsilon:
            # Explore: random action
            return random.choice(self.action_space)
        
        # Exploit: best known action
        q_values = self.q_table[state_key]
        
        if not q_values:
            # No experience for this state, choose randomly
            return random.choice(self.action_space)
        
        # Find action with maximum Q-value
        best_action = max(q_values.keys(), key=lambda a: q_values[a])
        return best_action
    
    def calculate_reward(
        self,
        queue_length: int,
        waiting_time: float,
        emergency_penalty: float = 0.0
    ) -> float:
        """
        Calculate reward for the current state
        
        Reward = -(α₁ * queue_length + α₂ * waiting_time) - emergency_penalty
        
        Args:
            queue_length: Current queue length
            waiting_time: Current average waiting time
            emergency_penalty: Additional penalty for blocking emergency vehicles
            
        Returns:
            Reward value (negative, minimize congestion)
        """
        reward = -(self.alpha_queue * queue_length + 
                   self.alpha_waiting * waiting_time +
                   emergency_penalty)
        return reward
    
    def update(
        self,
        state: TrafficState,
        action: int,
        reward: float,
        next_state: TrafficState
    ) -> float:
        """
        Update Q-value using Q-Learning update rule
        
        Q(s,a) = Q(s,a) + α[r + γ·max(Q(s',a')) - Q(s,a)]
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Resulting state
            
        Returns:
            TD error for monitoring
        """
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # Current Q-value
        current_q = self.q_table[state_key][action]
        
        # Maximum Q-value for next state
        next_q_values = self.q_table[next_state_key]
        max_next_q = max(next_q_values.values()) if next_q_values else 0.0
        
        # TD target
        td_target = reward + self.discount_factor * max_next_q
        
        # TD error
        td_error = td_target - current_q
        
        # Update Q-value
        new_q = current_q + self.learning_rate * td_error
        self.q_table[state_key][action] = new_q
        
        # Update statistics
        self.total_steps += 1
        self.rewards_history.append(reward)
        
        return td_error
    
    def decay_epsilon(self):
        """Decay exploration rate"""
        self.epsilon = max(
            self.epsilon_end,
            self.epsilon * self.epsilon_decay
        )
    
    def train_episode(
        self,
        initial_state: TrafficState,
        environment,  # SUMO environment
        max_steps: int = 100
    ) -> Dict:
        """
        Train for one episode
        
        Args:
            initial_state: Starting state
            environment: Traffic simulation environment
            max_steps: Maximum steps per episode
            
        Returns:
            Episode statistics
        """
        state = initial_state
        total_reward = 0
        steps = 0
        
        for step in range(max_steps):
            # Choose action
            action = self.choose_action(state, training=True)
            
            # Execute action in environment
            next_state, reward, done, info = environment.step(action)
            
            # Update Q-table
            self.update(state, action, reward, next_state)
            
            total_reward += reward
            steps += 1
            state = next_state
            
            if done:
                break
        
        # Decay epsilon after episode
        self.decay_epsilon()
        self.total_episodes += 1
        
        # Calculate average reward for this episode
        avg_reward = total_reward / steps if steps > 0 else 0
        self.avg_rewards.append(avg_reward)
        
        return {
            'episode': self.total_episodes,
            'total_reward': total_reward,
            'avg_reward': avg_reward,
            'steps': steps,
            'epsilon': self.epsilon
        }
    
    def get_best_action(self, state: TrafficState) -> int:
        """
        Get the best action for a state (no exploration)
        
        Args:
            state: Current traffic state
            
        Returns:
            Best green time (action)
        """
        return self.choose_action(state, training=False)
    
    def get_q_values(self, state: TrafficState) -> Dict[int, float]:
        """Get Q-values for all actions in a state"""
        state_key = self.get_state_key(state)
        return dict(self.q_table[state_key])
    
    def save(self, path: str):
        """Save agent to file"""
        save_data = {
            'q_table': dict(self.q_table),
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'epsilon': self.epsilon,
            'epsilon_start': self.epsilon_start,
            'epsilon_end': self.epsilon_end,
            'epsilon_decay': self.epsilon_decay,
            'alpha_queue': self.alpha_queue,
            'alpha_waiting': self.alpha_waiting,
            'state_bins': self.state_bins,
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
            'avg_rewards': self.avg_rewards
        }
        
        with open(path, 'wb') as f:
            pickle.dump(save_data, f)
        print(f"Agent saved to {path}")
    
    def load(self, path: str):
        """Load agent from file"""
        with open(path, 'rb') as f:
            save_data = pickle.load(f)
        
        self.q_table = defaultdict(lambda: defaultdict(float), save_data['q_table'])
        self.learning_rate = save_data['learning_rate']
        self.discount_factor = save_data['discount_factor']
        self.epsilon = save_data['epsilon']
        self.epsilon_start = save_data['epsilon_start']
        self.epsilon_end = save_data['epsilon_end']
        self.epsilon_decay = save_data['epsilon_decay']
        self.alpha_queue = save_data['alpha_queue']
        self.alpha_waiting = save_data['alpha_waiting']
        self.state_bins = save_data['state_bins']
        self.total_episodes = save_data['total_episodes']
        self.total_steps = save_data['total_steps']
        self.avg_rewards = save_data.get('avg_rewards', [])
        
        print(f"Agent loaded from {path}")
        print(f"Episodes: {self.total_episodes}, Steps: {self.total_steps}")
    
    def get_training_stats(self) -> Dict:
        """Get training statistics"""
        return {
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
            'current_epsilon': self.epsilon,
            'q_table_size': sum(len(actions) for actions in self.q_table.values()),
            'recent_avg_reward': np.mean(self.avg_rewards[-100:]) if self.avg_rewards else 0
        }
    
    def reset_exploration(self):
        """Reset exploration rate to initial value"""
        self.epsilon = self.epsilon_start


class EmergencyOverrideController:
    """
    Emergency vehicle priority controller
    Overrides RL decisions when emergency vehicles are detected
    """
    
    def __init__(self, priority_duration: int = 30):
        """
        Initialize emergency controller
        
        Args:
            priority_duration: Duration of priority green signal (seconds)
        """
        self.priority_duration = priority_duration
        self.active_emergency = False
        self.emergency_lane = None
        self.override_timer = 0
        
    def check_emergency(
        self,
        emergency_detected: bool,
        emergency_lane: Optional[int] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if emergency override should be active
        
        Args:
            emergency_detected: Whether emergency vehicle detected
            emergency_lane: Lane where emergency vehicle is detected
            
        Returns:
            Tuple of (override_active, override_green_time)
        """
        if emergency_detected and emergency_lane is not None:
            self.active_emergency = True
            self.emergency_lane = emergency_lane
            self.override_timer = self.priority_duration
            return True, self.priority_duration
        
        if self.active_emergency:
            self.override_timer -= 1
            if self.override_timer <= 0:
                self.active_emergency = False
                self.emergency_lane = None
                return False, None
            return True, self.override_timer
        
        return False, None
    
    def get_override_action(self) -> Optional[Dict]:
        """
        Get emergency override action
        
        Returns:
            Override action or None if not active
        """
        if self.active_emergency:
            return {
                'emergency_active': True,
                'priority_lane': self.emergency_lane,
                'green_time': self.priority_duration,
                'remaining_time': self.override_timer
            }
        return None


class AdaptiveTrafficController:
    """
    Main adaptive traffic controller combining RL agent and emergency override
    """
    
    def __init__(
        self,
        rl_agent: Optional[QLearningAgent] = None,
        emergency_controller: Optional[EmergencyOverrideController] = None
    ):
        """
        Initialize adaptive controller
        
        Args:
            rl_agent: Q-Learning agent instance
            emergency_controller: Emergency override controller
        """
        self.rl_agent = rl_agent or QLearningAgent()
        self.emergency_controller = emergency_controller or EmergencyOverrideController()
        
        self.current_phase = 0
        self.decision_history = []
        
    def decide_signal(
        self,
        traffic_state: TrafficState,
        emergency_detected: bool = False,
        emergency_lane: Optional[int] = None,
        training: bool = False
    ) -> Dict:
        """
        Decide signal timing based on traffic state
        
        Args:
            traffic_state: Current traffic state
            emergency_detected: Whether emergency vehicle detected
            emergency_lane: Lane of emergency vehicle
            training: Whether in training mode
            
        Returns:
            Signal decision dictionary
        """
        # Check for emergency override
        override_active, override_time = self.emergency_controller.check_emergency(
            emergency_detected, emergency_lane
        )
        
        if override_active:
            decision = {
                'action_type': 'emergency_override',
                'green_time': override_time,
                'phase': emergency_lane if emergency_lane is not None else self.current_phase,
                'emergency': True,
                'confidence': 1.0
            }
        else:
            # Use RL agent
            green_time = self.rl_agent.choose_action(traffic_state, training=training)
            
            # Get Q-values for debugging
            q_values = self.rl_agent.get_q_values(traffic_state)
            
            decision = {
                'action_type': 'rl_decision',
                'green_time': green_time,
                'phase': self.current_phase,
                'emergency': False,
                'q_values': q_values,
                'epsilon': self.rl_agent.epsilon if training else 0.0,
                'confidence': 1.0 - (self.rl_agent.epsilon if training else 0.0)
            }
        
        # Update current phase
        self.current_phase = (self.current_phase + 1) % self.rl_agent.num_phases
        
        # Record decision
        self.decision_history.append(decision)
        
        return decision
    
    def update_from_feedback(
        self,
        state: TrafficState,
        action: int,
        next_state: TrafficState,
        queue_length: int,
        waiting_time: float,
        emergency_blocked: bool = False
    ) -> float:
        """
        Update RL agent based on feedback
        
        Args:
            state: State when action was taken
            action: Action that was taken
            next_state: Resulting state
            queue_length: Resulting queue length
            waiting_time: Resulting waiting time
            emergency_blocked: Whether emergency vehicle was blocked
            
        Returns:
            TD error from update
        """
        # Calculate reward
        emergency_penalty = 100.0 if emergency_blocked else 0.0
        reward = self.rl_agent.calculate_reward(queue_length, waiting_time, emergency_penalty)
        
        # Update Q-table
        td_error = self.rl_agent.update(state, action, reward, next_state)
        
        return td_error
    
    def save_controller(self, path: str):
        """Save controller state"""
        self.rl_agent.save(path)
        
    def load_controller(self, path: str):
        """Load controller state"""
        self.rl_agent.load(path)


if __name__ == '__main__':
    # Test the agent
    print("Initializing Q-Learning Agent...")
    agent = QLearningAgent()
    
    # Create some test states
    states = [
        TrafficState(current_vehicle_count=5, predicted_vehicle_count=6.5, queue_length=2, current_signal_phase=0),
        TrafficState(current_vehicle_count=15, predicted_vehicle_count=20.0, queue_length=8, current_signal_phase=1),
        TrafficState(current_vehicle_count=25, predicted_vehicle_count=22.0, queue_length=12, current_signal_phase=2),
    ]
    
    print("\nTest actions (with exploration):")
    for state in states:
        action = agent.choose_action(state, training=True)
        print(f"State: count={state.current_vehicle_count}, queue={state.queue_length} -> Action: {action}s green")
    
    # Simulate some training
    print("\nSimulating training updates...")
    for i in range(100):
        state = states[i % len(states)]
        action = agent.choose_action(state, training=True)
        
        # Simulate next state
        next_state = TrafficState(
            current_vehicle_count=state.current_vehicle_count + random.randint(-3, 3),
            predicted_vehicle_count=state.predicted_vehicle_count + random.random(),
            queue_length=max(0, state.queue_length + random.randint(-2, 2)),
            current_signal_phase=(state.current_signal_phase + 1) % 4
        )
        
        # Calculate reward
        reward = agent.calculate_reward(next_state.queue_length, next_state.queue_length * 2)
        
        # Update
        agent.update(state, action, reward, next_state)
        agent.decay_epsilon()
    
    print(f"\nTraining stats: {agent.get_training_stats()}")
    
    # Test without exploration
    print("\nTest actions (no exploration):")
    for state in states:
        action = agent.get_best_action(state)
        q_values = agent.get_q_values(state)
        print(f"State: count={state.current_vehicle_count}, queue={state.queue_length} -> Best action: {action}s")
        print(f"  Q-values: {q_values}")
    
    # Save and load test
    agent.save('test_agent.pkl')
    
    new_agent = QLearningAgent()
    new_agent.load('test_agent.pkl')
    print(f"\nLoaded agent stats: {new_agent.get_training_stats()}")
