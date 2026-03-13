"""
LSTM Traffic Prediction Model
Predicts future traffic volume based on historical time series data
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
import pickle
from pathlib import Path


@dataclass
class PredictionResult:
    """Data class for prediction results"""
    predicted_vehicle_count: float
    confidence: float
    sequence_used: List[float]
    timestamp: int


class LSTMTrafficPredictor(nn.Module):
    """
    LSTM-based traffic prediction model
    
    Architecture:
        Input Layer → LSTM(64) → LSTM(32) → Dense → Output
    
    Features:
        - vehicle_count
        - queue_length
        - lane_density
        - signal_phase
    """
    
    def __init__(
        self,
        input_size: int = 4,
        hidden_size_1: int = 64,
        hidden_size_2: int = 32,
        num_layers: int = 2,
        output_size: int = 1,
        dropout: float = 0.2
    ):
        """
        Initialize LSTM model
        
        Args:
            input_size: Number of input features
            hidden_size_1: First LSTM layer hidden size
            hidden_size_2: Second LSTM layer hidden size
            num_layers: Number of LSTM layers
            output_size: Number of output features
            dropout: Dropout rate
        """
        super(LSTMTrafficPredictor, self).__init__()
        
        self.input_size = input_size
        self.hidden_size_1 = hidden_size_1
        self.hidden_size_2 = hidden_size_2
        self.num_layers = num_layers
        
        # First LSTM layer
        self.lstm1 = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size_1,
            num_layers=1,
            batch_first=True,
            dropout=0
        )
        
        # Second LSTM layer
        self.lstm2 = nn.LSTM(
            input_size=hidden_size_1,
            hidden_size=hidden_size_2,
            num_layers=1,
            batch_first=True,
            dropout=0
        )
        
        # Dropout layer
        self.dropout = nn.Dropout(dropout)
        
        # Fully connected layers
        self.fc1 = nn.Linear(hidden_size_2, 16)
        self.fc2 = nn.Linear(16, output_size)
        
        # Activation
        self.relu = nn.ReLU()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            
        Returns:
            Output tensor of shape (batch_size, output_size)
        """
        # First LSTM layer
        lstm_out1, _ = self.lstm1(x)
        lstm_out1 = self.dropout(lstm_out1)
        
        # Second LSTM layer
        lstm_out2, _ = self.lstm2(lstm_out1)
        lstm_out2 = self.dropout(lstm_out2)
        
        # Take the last time step output
        last_output = lstm_out2[:, -1, :]
        
        # Fully connected layers
        out = self.relu(self.fc1(last_output))
        out = self.fc2(out)
        
        return out


class TrafficPredictor:
    """
    Wrapper class for LSTM traffic prediction
    Handles preprocessing, prediction, and postprocessing
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        sequence_length: int = 15,
        device: str = 'auto'
    ):
        """
        Initialize the traffic predictor
        
        Args:
            model_path: Path to saved model weights
            sequence_length: Length of input sequence (10-20 recommended)
            device: Device to run inference on
        """
        self.sequence_length = sequence_length
        
        # Determine device
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
            
        # Initialize model
        self.model = LSTMTrafficPredictor().to(self.device)
        
        # Load weights if provided
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        
        # Normalization parameters (will be set during training or loaded)
        self.scaler_params = {
            'vehicle_count': {'mean': 10.0, 'std': 5.0},
            'queue_length': {'mean': 5.0, 'std': 3.0},
            'lane_density': {'mean': 0.5, 'std': 0.25},
            'signal_phase': {'mean': 1.5, 'std': 1.0}
        }
        
        # History buffer for online prediction
        self.history_buffer = []
        
        self.prediction_count = 0
        
    def normalize(self, data: np.ndarray) -> np.ndarray:
        """
        Normalize input data
        
        Args:
            data: Input array of shape (sequence_length, 4)
            
        Returns:
            Normalized data
        """
        normalized = np.zeros_like(data, dtype=np.float32)
        
        feature_names = ['vehicle_count', 'queue_length', 'lane_density', 'signal_phase']
        
        for i, name in enumerate(feature_names):
            mean = self.scaler_params[name]['mean']
            std = self.scaler_params[name]['std']
            normalized[:, i] = (data[:, i] - mean) / (std + 1e-8)
            
        return normalized
    
    def denormalize(self, value: float, feature: str = 'vehicle_count') -> float:
        """
        Denormalize output value
        
        Args:
            value: Normalized value
            feature: Feature name
            
        Returns:
            Denormalized value
        """
        mean = self.scaler_params[feature]['mean']
        std = self.scaler_params[feature]['std']
        return value * std + mean
    
    def update_history(
        self,
        vehicle_count: int,
        queue_length: int,
        lane_density: float,
        signal_phase: int
    ):
        """
        Update history buffer with new observation
        
        Args:
            vehicle_count: Current vehicle count
            queue_length: Current queue length
            lane_density: Current lane density
            signal_phase: Current signal phase (0-3)
        """
        observation = [vehicle_count, queue_length, lane_density, signal_phase]
        self.history_buffer.append(observation)
        
        # Keep only recent history
        if len(self.history_buffer) > self.sequence_length * 2:
            self.history_buffer = self.history_buffer[-self.sequence_length:]
    
    def predict(
        self,
        sequence: Optional[np.ndarray] = None
    ) -> PredictionResult:
        """
        Predict next timestep vehicle count
        
        Args:
            sequence: Input sequence of shape (sequence_length, 4)
                     If None, uses history buffer
                     
        Returns:
            PredictionResult with predicted vehicle count
        """
        self.prediction_count += 1
        
        # Use history buffer if sequence not provided
        if sequence is None:
            if len(self.history_buffer) < self.sequence_length:
                # Not enough history, return current value
                return PredictionResult(
                    predicted_vehicle_count=self.history_buffer[-1][0] if self.history_buffer else 0,
                    confidence=0.0,
                    sequence_used=[],
                    timestamp=self.prediction_count
                )
            sequence = np.array(self.history_buffer[-self.sequence_length:])
        
        # Normalize
        normalized = self.normalize(sequence)
        
        # Convert to tensor
        input_tensor = torch.FloatTensor(normalized).unsqueeze(0).to(self.device)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(input_tensor)
            
        # Denormalize
        predicted_value = self.denormalize(prediction.item())
        
        # Ensure non-negative
        predicted_value = max(0, predicted_value)
        
        # Calculate confidence based on prediction variance
        # This is a simplified confidence measure
        confidence = self._calculate_confidence(sequence[:, 0])
        
        return PredictionResult(
            predicted_vehicle_count=predicted_value,
            confidence=confidence,
            sequence_used=sequence[:, 0].tolist(),
            timestamp=self.prediction_count
        )
    
    def _calculate_confidence(self, sequence: np.ndarray) -> float:
        """
        Calculate prediction confidence based on sequence stability
        
        Args:
            sequence: Vehicle count sequence
            
        Returns:
            Confidence score (0-1)
        """
        if len(sequence) < 2:
            return 0.5
            
        # Lower variance = higher confidence
        variance = np.var(sequence)
        confidence = 1.0 / (1.0 + variance / 10.0)
        return min(max(confidence, 0.0), 1.0)
    
    def train_model(
        self,
        train_data: np.ndarray,
        val_data: Optional[np.ndarray] = None,
        epochs: int = 10,
        batch_size: int = 32,
        learning_rate: float = 0.001
    ) -> Dict:
        """
        Train the LSTM model
        
        Args:
            train_data: Training data of shape (n_samples, sequence_length, features)
            val_data: Validation data (optional)
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            
        Returns:
            Training history dictionary
        """
        # Update scaler params from training data
        self._fit_scaler(train_data)
        
        # Create data loader
        train_loader = self._create_dataloader(train_data, batch_size)
        val_loader = self._create_dataloader(val_data, batch_size) if val_data is not None else None
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        
        history = {
            'train_loss': [],
            'val_loss': []
        }
        
        self.model.train()
        
        for epoch in range(epochs):
            train_losses = []
            
            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                # Forward pass
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                train_losses.append(loss.item())
            
            avg_train_loss = np.mean(train_losses)
            history['train_loss'].append(avg_train_loss)
            
            # Validation
            if val_loader:
                val_loss = self._validate(val_loader, criterion)
                history['val_loss'].append(val_loss)
                print(f"Epoch {epoch+1}/{epochs}, Train Loss: {avg_train_loss:.4f}, Val Loss: {val_loss:.4f}")
            else:
                print(f"Epoch {epoch+1}/{epochs}, Train Loss: {avg_train_loss:.4f}")
                
        return history
    
    def _validate(self, val_loader, criterion) -> float:
        """Validate model on validation set"""
        self.model.eval()
        val_losses = []
        
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                val_losses.append(loss.item())
                
        self.model.train()
        return np.mean(val_losses)
    
    def _fit_scaler(self, data: np.ndarray):
        """Fit normalization parameters from data"""
        # data shape: (n_samples, sequence_length, features)
        features = ['vehicle_count', 'queue_length', 'lane_density', 'signal_phase']
        
        for i, feature in enumerate(features):
            feature_data = data[:, :, i].flatten()
            self.scaler_params[feature] = {
                'mean': float(np.mean(feature_data)),
                'std': float(np.std(feature_data))
            }
    
    def _create_dataloader(
        self,
        data: np.ndarray,
        batch_size: int
    ) -> torch.utils.data.DataLoader:
        """Create PyTorch DataLoader from data"""
        # Split into sequences and targets
        X = data[:, :-1, :]  # All but last timestep
        y = data[:, -1:, 0]  # Last timestep, vehicle count only
        
        # Normalize
        X_normalized = np.array([self.normalize(seq) for seq in X])
        y_normalized = (y - self.scaler_params['vehicle_count']['mean']) / \
                       (self.scaler_params['vehicle_count']['std'] + 1e-8)
        
        # Create tensors
        X_tensor = torch.FloatTensor(X_normalized)
        y_tensor = torch.FloatTensor(y_normalized)
        
        # Create dataset
        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        
        # Create dataloader
        return torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True
        )
    
    def save_model(self, path: str):
        """Save model weights and scaler parameters"""
        save_dict = {
            'model_state_dict': self.model.state_dict(),
            'scaler_params': self.scaler_params
        }
        torch.save(save_dict, path)
        print(f"Model saved to {path}")
        
    def load_model(self, path: str):
        """Load model weights and scaler parameters"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        if 'scaler_params' in checkpoint:
            self.scaler_params = checkpoint['scaler_params']
            
        print(f"Model loaded from {path}")


def create_synthetic_training_data(
    n_samples: int = 1000,
    sequence_length: int = 15
) -> np.ndarray:
    """
    Generate synthetic training data for testing
    
    Args:
        n_samples: Number of samples
        sequence_length: Length of each sequence
        
    Returns:
        Training data array
    """
    data = []
    
    for _ in range(n_samples):
        # Generate a sequence with temporal patterns
        base_count = np.random.randint(5, 20)
        
        sequence = []
        for t in range(sequence_length + 1):
            # Add temporal pattern (rush hour simulation)
            hour_factor = np.sin(2 * np.pi * t / 24) * 5
            
            # Add noise
            noise = np.random.randn() * 2
            
            vehicle_count = max(0, base_count + hour_factor + noise)
            queue_length = max(0, vehicle_count * 0.5 + np.random.randn())
            lane_density = min(1.0, max(0, vehicle_count / 25 + np.random.randn() * 0.1))
            signal_phase = np.random.randint(0, 4)
            
            sequence.append([vehicle_count, queue_length, lane_density, signal_phase])
            
        data.append(sequence)
        
    return np.array(data)


if __name__ == '__main__':
    # Test the predictor
    print("Creating synthetic training data...")
    train_data = create_synthetic_training_data(n_samples=500)
    val_data = create_synthetic_training_data(n_samples=100)
    
    print(f"Training data shape: {train_data.shape}")
    
    # Initialize predictor
    predictor = TrafficPredictor(sequence_length=15)
    
    # Train
    print("\nTraining model...")
    history = predictor.train_model(
        train_data,
        val_data,
        epochs=10,
        batch_size=32
    )
    
    # Test prediction
    print("\nTesting prediction...")
    test_sequence = train_data[0, :-1, :]
    result = predictor.predict(test_sequence)
    
    print(f"Predicted vehicle count: {result.predicted_vehicle_count:.2f}")
    print(f"Confidence: {result.confidence:.2f}")
    
    # Save model
    predictor.save_model('lstm_traffic_model.pth')
