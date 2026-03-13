"""
Q-Learning Agent Training Script

This script trains the Q-Learning agent for traffic signal optimization
using either SUMO simulation or a mock environment.
"""

import os
import sys
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.q_learning_agent import QLearningAgent, AdaptiveTrafficController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockTrafficEnvironment:
    """
    Mock traffic environment for training without SUMO.
    Simulates traffic flow and signal interactions.
    """
    
    def __init__(self, num_lanes: int = 4):
        self.num_lanes = num_lanes
        self.reset()
    
    def reset(self) -> Dict:
        """Reset environment to initial state."""
        self.step_count = 0
        self.vehicle_counts = np.random.randint(5, 25, self.num_lanes)
        self.queue_lengths = self.vehicle_counts * np.random.uniform(0.2, 0.4, self.num_lanes)
        self.waiting_times = np.zeros(self.num_lanes)
        self.current_phase = 0
        self.phase_duration = 30
        
        return self._get_state()
    
    def _get_state(self) -> Dict:
        """Get current state representation."""
        return {
            'vehicle_counts': self.vehicle_counts.tolist(),
            'queue_lengths': self.queue_lengths.tolist(),
            'waiting_times': self.waiting_times.tolist(),
            'current_phase': self.current_phase,
            'total_vehicles': int(np.sum(self.vehicle_counts))
        }
    
    def step(self, action: int) -> tuple:
        """
        Execute action and return (next_state, reward, done).
        
        Action: green time duration index (maps to [10, 20, 30, 40] seconds)
        """
        green_times = [10, 20, 30, 40]
        green_time = green_times[action]
        
        self.step_count += 1
        
        # Simulate traffic flow based on action
        # Lanes in green phase get cleared
        green_lanes = [0, 2] if self.current_phase == 0 else [1, 3]
        red_lanes = [1, 3] if self.current_phase == 0 else [0, 2]
        
        # Green lane vehicles decrease
        for lane in green_lanes:
            cleared = min(self.vehicle_counts[lane], green_time // 3)
            self.vehicle_counts[lane] = max(0, self.vehicle_counts[lane] - cleared)
            self.queue_lengths[lane] = max(0, self.queue_lengths[lane] - cleared * 0.5)
            self.waiting_times[lane] = max(0, self.waiting_times[lane] - green_time * 0.3)
        
        # Red lane vehicles accumulate
        for lane in red_lanes:
            arrivals = np.random.poisson(2)
            self.vehicle_counts[lane] = min(50, self.vehicle_counts[lane] + arrivals)
            self.queue_lengths[lane] = min(30, self.queue_lengths[lane] + arrivals * 0.5)
            self.waiting_times[lane] += green_time * 0.5
        
        # Calculate reward
        reward = self._calculate_reward(green_time)
        
        # Switch phase
        self.current_phase = 1 - self.current_phase
        
        # Random arrivals
        self.vehicle_counts += np.random.poisson(1, self.num_lanes)
        
        done = self.step_count >= 100
        
        return self._get_state(), reward, done
    
    def _calculate_reward(self, green_time: int) -> float:
        """Calculate reward based on current state."""
        # Penalty for waiting vehicles
        waiting_penalty = -np.sum(self.vehicle_counts) * 0.1
        
        # Penalty for queue length
        queue_penalty = -np.sum(self.queue_lengths) * 0.05
        
        # Penalty for accumulated waiting time
        time_penalty = -np.sum(self.waiting_times) * 0.02
        
        # Bonus for balanced traffic
        std_penalty = -np.std(self.vehicle_counts) * 0.1
        
        # Small penalty for extreme green times
        if green_time <= 10 or green_time >= 40:
            time_penalty -= 1
        
        reward = waiting_penalty + queue_penalty + time_penalty + std_penalty + 10  # Base reward
        
        return reward


def train_q_learning(
    agent: QLearningAgent,
    env: MockTrafficEnvironment,
    episodes: int = 5000,
    save_path: str = "models/q_learning_agent.json",
    log_interval: int = 100
) -> Dict:
    """
    Train Q-Learning agent.
    """
    history = {
        'episode_rewards': [],
        'episode_lengths': [],
        'epsilon_values': [],
        'avg_rewards': []
    }
    
    best_avg_reward = float('-inf')
    
    for episode in range(episodes):
        state = env.reset()
        total_vehicles = state['total_vehicles']
        
        episode_reward = 0
        episode_length = 0
        done = False
        
        while not done:
            # Get action from agent
            action = agent.get_action(total_vehicles)
            
            # Take action
            next_state, reward, done = env.step(action)
            
            # Update agent
            next_total = next_state['total_vehicles']
            agent.update(total_vehicles, action, reward, next_total)
            
            total_vehicles = next_total
            episode_reward += reward
            episode_length += 1
        
        # Record history
        history['episode_rewards'].append(episode_reward)
        history['episode_lengths'].append(episode_length)
        history['epsilon_values'].append(agent.epsilon)
        
        # Calculate running average
        avg_reward = np.mean(history['episode_rewards'][-100:])
        history['avg_rewards'].append(avg_reward)
        
        # Logging
        if (episode + 1) % log_interval == 0:
            logger.info(
                f"Episode {episode + 1}/{episodes} - "
                f"Reward: {episode_reward:.2f}, "
                f"Avg Reward (100): {avg_reward:.2f}, "
                f"Epsilon: {agent.epsilon:.4f}"
            )
        
        # Save best model
        if avg_reward > best_avg_reward and episode > 100:
            best_avg_reward = avg_reward
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            agent.save_q_table(save_path)
    
    return history


def evaluate_agent(
    agent: QLearningAgent,
    env: MockTrafficEnvironment,
    episodes: int = 100
) -> Dict:
    """Evaluate trained agent."""
    rewards = []
    lengths = []
    
    # Disable exploration
    original_epsilon = agent.epsilon
    agent.epsilon = 0
    
    for _ in range(episodes):
        state = env.reset()
        total_vehicles = state['total_vehicles']
        episode_reward = 0
        episode_length = 0
        done = False
        
        while not done:
            action = agent.get_action(total_vehicles)
            next_state, reward, done = env.step(action)
            total_vehicles = next_state['total_vehicles']
            episode_reward += reward
            episode_length += 1
        
        rewards.append(episode_reward)
        lengths.append(episode_length)
    
    agent.epsilon = original_epsilon
    
    metrics = {
        'mean_reward': float(np.mean(rewards)),
        'std_reward': float(np.std(rewards)),
        'max_reward': float(np.max(rewards)),
        'min_reward': float(np.min(rewards)),
        'mean_length': float(np.mean(lengths))
    }
    
    return metrics


def compare_with_fixed_timing(env: MockTrafficEnvironment, episodes: int = 100) -> Dict:
    """Compare Q-Learning with fixed timing baseline."""
    fixed_rewards = []
    
    for _ in range(episodes):
        state = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            # Fixed timing: always use 30 seconds (action index 2)
            _, reward, done = env.step(2)
            episode_reward += reward
        
        fixed_rewards.append(episode_reward)
    
    return {
        'mean_reward': float(np.mean(fixed_rewards)),
        'std_reward': float(np.std(fixed_rewards))
    }


def main():
    parser = argparse.ArgumentParser(description='Train Q-Learning Traffic Signal Agent')
    parser.add_argument('--episodes', type=int, default=5000, help='Number of training episodes')
    parser.add_argument('--learning-rate', type=float, default=0.1, help='Learning rate (alpha)')
    parser.add_argument('--discount', type=float, default=0.9, help='Discount factor (gamma)')
    parser.add_argument('--epsilon-start', type=float, default=1.0, help='Initial epsilon')
    parser.add_argument('--epsilon-end', type=float, default=0.1, help='Final epsilon')
    parser.add_argument('--epsilon-decay', type=float, default=0.995, help='Epsilon decay rate')
    parser.add_argument('--save-path', type=str, default='models/q_learning_agent.json', help='Model save path')
    parser.add_argument('--eval-episodes', type=int, default=100, help='Evaluation episodes')
    parser.add_argument('--log-interval', type=int, default=100, help='Logging interval')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Q-Learning Traffic Signal Agent Training")
    logger.info("=" * 60)
    logger.info(f"Configuration: {vars(args)}")
    
    # Initialize environment
    env = MockTrafficEnvironment(num_lanes=4)
    
    # Initialize agent
    agent = QLearningAgent(
        n_states=10,  # Discretized vehicle count bins
        n_actions=4,  # Green time options: [10, 20, 30, 40]
        learning_rate=args.learning_rate,
        discount_factor=args.discount,
        epsilon=args.epsilon_start,
        epsilon_decay=args.epsilon_decay,
        epsilon_min=args.epsilon_end
    )
    
    logger.info(f"Agent initialized with {agent.n_states} states, {agent.n_actions} actions")
    
    # Compare with fixed timing baseline
    logger.info("\nBaseline (Fixed Timing) Performance:")
    baseline_metrics = compare_with_fixed_timing(env, args.eval_episodes)
    logger.info(f"  Mean Reward: {baseline_metrics['mean_reward']:.2f} ± {baseline_metrics['std_reward']:.2f}")
    
    # Train agent
    logger.info("\nStarting training...")
    history = train_q_learning(
        agent=agent,
        env=env,
        episodes=args.episodes,
        save_path=args.save_path,
        log_interval=args.log_interval
    )
    
    # Final evaluation
    logger.info("\nFinal Evaluation:")
    eval_metrics = evaluate_agent(agent, env, args.eval_episodes)
    logger.info(f"  Mean Reward: {eval_metrics['mean_reward']:.2f} ± {eval_metrics['std_reward']:.2f}")
    logger.info(f"  Max Reward: {eval_metrics['max_reward']:.2f}")
    logger.info(f"  Mean Episode Length: {eval_metrics['mean_length']:.1f}")
    
    # Calculate improvement
    improvement = (eval_metrics['mean_reward'] - baseline_metrics['mean_reward']) / abs(baseline_metrics['mean_reward']) * 100
    logger.info(f"\nImprovement over fixed timing: {improvement:.1f}%")
    
    # Save training results
    results_path = args.save_path.replace('.json', '_results.json')
    with open(results_path, 'w') as f:
        json.dump({
            'config': vars(args),
            'baseline_metrics': baseline_metrics,
            'final_metrics': eval_metrics,
            'improvement_percent': improvement,
            'history_summary': {
                'final_avg_reward': history['avg_rewards'][-1] if history['avg_rewards'] else 0,
                'final_epsilon': agent.epsilon,
                'total_episodes': len(history['episode_rewards'])
            },
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    logger.info(f"Results saved to {results_path}")
    logger.info("Training completed!")


if __name__ == '__main__':
    main()
