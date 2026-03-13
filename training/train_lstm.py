"""
LSTM Traffic Prediction Model Training Script

This script trains the LSTM model for traffic flow prediction.
It can use either real collected data or synthetic data for training.
"""

import os
import sys
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_models.lstm_model import TrafficPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_data(
    num_samples: int = 10000,
    sequence_length: int = 15,
    num_features: int = 4,
    seed: int = 42
) -> tuple:
    """
    Generate synthetic traffic data for training.
    
    Features: [vehicle_count, queue_length, avg_speed, time_of_day]
    """
    np.random.seed(seed)
    
    # Time-based patterns
    hours = np.tile(np.arange(24), num_samples // 24 + 1)[:num_samples]
    
    # Rush hour patterns (higher traffic at 8-9 AM and 5-6 PM)
    rush_hour_factor = np.where(
        ((hours >= 8) & (hours <= 9)) | ((hours >= 17) & (hours <= 18)),
        1.5,
        np.where(((hours >= 7) & (hours <= 10)) | ((hours >= 16) & (hours <= 19)), 1.2, 1.0)
    )
    
    # Base traffic patterns
    base_vehicle_count = 15 + 10 * rush_hour_factor + np.random.randn(num_samples) * 3
    queue_length = base_vehicle_count * 0.3 + np.random.randn(num_samples) * 2
    avg_speed = 50 - base_vehicle_count * 0.5 + np.random.randn(num_samples) * 5
    time_normalized = hours / 24.0
    
    # Stack features
    features = np.stack([
        base_vehicle_count,
        np.maximum(0, queue_length),
        np.clip(avg_speed, 5, 80),
        time_normalized
    ], axis=1)
    
    # Create sequences
    X, y = [], []
    for i in range(len(features) - sequence_length - 1):
        X.append(features[i:i + sequence_length])
        y.append(features[i + sequence_length, 0])  # Predict next vehicle count
    
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)
    
    # Split data
    train_size = int(0.8 * len(X))
    X_train, X_val = X[:train_size], X[train_size:]
    y_train, y_val = y[:train_size], y[train_size:]
    
    return (X_train, y_train), (X_val, y_val)


def load_real_data(data_path: str, sequence_length: int = 15) -> tuple:
    """Load real traffic data from JSON or CSV files."""
    data_path = Path(data_path)
    
    if data_path.suffix == '.json':
        with open(data_path, 'r') as f:
            data = json.load(f)
        features = np.array([[
            d['vehicle_count'],
            d['queue_length'],
            d.get('avg_speed', 30),
            d.get('hour', 12) / 24.0
        ] for d in data], dtype=np.float32)
    elif data_path.suffix == '.csv':
        import pandas as pd
        df = pd.read_csv(data_path)
        features = df[['vehicle_count', 'queue_length', 'avg_speed', 'hour']].values.astype(np.float32)
        features[:, 3] = features[:, 3] / 24.0  # Normalize hour
    else:
        raise ValueError(f"Unsupported file format: {data_path.suffix}")
    
    # Create sequences
    X, y = [], []
    for i in range(len(features) - sequence_length - 1):
        X.append(features[i:i + sequence_length])
        y.append(features[i + sequence_length, 0])
    
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)
    
    # Split data
    train_size = int(0.8 * len(X))
    X_train, X_val = X[:train_size], X[train_size:]
    y_train, y_val = y[:train_size], y[train_size:]
    
    return (X_train, y_train), (X_val, y_val)


def train_model(
    model: TrafficPredictor,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 100,
    learning_rate: float = 0.001,
    save_path: str = "models/lstm_traffic.pth",
    early_stopping_patience: int = 15
) -> dict:
    """
    Train the LSTM model with early stopping and learning rate scheduling.
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Training on device: {device}")
    
    model.model.to(device)
    optimizer = Adam(model.model.parameters(), lr=learning_rate)
    scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5, verbose=True)
    criterion = torch.nn.MSELoss()
    
    best_val_loss = float('inf')
    patience_counter = 0
    history = {'train_loss': [], 'val_loss': [], 'lr': []}
    
    for epoch in range(epochs):
        # Training phase
        model.model.train()
        train_losses = []
        
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            predictions = model.model(batch_X).squeeze()
            loss = criterion(predictions, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.model.parameters(), max_norm=1.0)
            optimizer.step()
            
            train_losses.append(loss.item())
        
        # Validation phase
        model.model.eval()
        val_losses = []
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                predictions = model.model(batch_X).squeeze()
                loss = criterion(predictions, batch_y)
                val_losses.append(loss.item())
        
        avg_train_loss = np.mean(train_losses)
        avg_val_loss = np.mean(val_losses)
        current_lr = optimizer.param_groups[0]['lr']
        
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)
        history['lr'].append(current_lr)
        
        scheduler.step(avg_val_loss)
        
        logger.info(
            f"Epoch {epoch + 1}/{epochs} - "
            f"Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}, "
            f"LR: {current_lr:.6f}"
        )
        
        # Early stopping check
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            # Save best model
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            model.save_model(save_path)
            logger.info(f"Model saved to {save_path}")
        else:
            patience_counter += 1
            if patience_counter >= early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
    
    return history


def evaluate_model(model: TrafficPredictor, test_loader: DataLoader) -> dict:
    """Evaluate the trained model on test data."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.model.to(device)
    model.model.eval()
    
    all_predictions = []
    all_targets = []
    
    with torch.no_grad():
        for batch_X, batch_y in test_loader:
            batch_X = batch_X.to(device)
            predictions = model.model(batch_X).squeeze().cpu().numpy()
            all_predictions.extend(predictions)
            all_targets.extend(batch_y.numpy())
    
    predictions = np.array(all_predictions)
    targets = np.array(all_targets)
    
    # Calculate metrics
    mae = np.mean(np.abs(predictions - targets))
    mse = np.mean((predictions - targets) ** 2)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((targets - predictions) / (targets + 1e-8))) * 100
    
    metrics = {
        'mae': float(mae),
        'mse': float(mse),
        'rmse': float(rmse),
        'mape': float(mape)
    }
    
    logger.info(f"Evaluation Metrics:")
    logger.info(f"  MAE: {mae:.4f}")
    logger.info(f"  RMSE: {rmse:.4f}")
    logger.info(f"  MAPE: {mape:.2f}%")
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description='Train LSTM Traffic Prediction Model')
    parser.add_argument('--data', type=str, default=None, help='Path to training data file')
    parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--sequence-length', type=int, default=15, help='Sequence length')
    parser.add_argument('--hidden-size', type=int, default=64, help='LSTM hidden size')
    parser.add_argument('--num-layers', type=int, default=2, help='Number of LSTM layers')
    parser.add_argument('--save-path', type=str, default='models/lstm_traffic.pth', help='Model save path')
    parser.add_argument('--synthetic-samples', type=int, default=10000, help='Number of synthetic samples')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("LSTM Traffic Prediction Model Training")
    logger.info("=" * 60)
    logger.info(f"Configuration: {vars(args)}")
    
    # Load or generate data
    if args.data and os.path.exists(args.data):
        logger.info(f"Loading real data from {args.data}")
        (X_train, y_train), (X_val, y_val) = load_real_data(args.data, args.sequence_length)
    else:
        logger.info(f"Generating {args.synthetic_samples} synthetic samples")
        (X_train, y_train), (X_val, y_val) = generate_synthetic_data(
            num_samples=args.synthetic_samples,
            sequence_length=args.sequence_length
        )
    
    logger.info(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")
    
    # Create data loaders
    train_dataset = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
    val_dataset = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)
    
    # Initialize model
    input_size = X_train.shape[2]
    model = TrafficPredictor(
        input_size=input_size,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        sequence_length=args.sequence_length
    )
    
    logger.info(f"Model initialized with input_size={input_size}, hidden_size={args.hidden_size}")
    
    # Train model
    history = train_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=args.epochs,
        learning_rate=args.lr,
        save_path=args.save_path
    )
    
    # Evaluate model
    logger.info("\nFinal Evaluation:")
    metrics = evaluate_model(model, val_loader)
    
    # Save training history
    history_path = args.save_path.replace('.pth', '_history.json')
    with open(history_path, 'w') as f:
        json.dump({
            'history': {k: [float(v) for v in vals] for k, vals in history.items()},
            'metrics': metrics,
            'config': vars(args),
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    logger.info(f"Training history saved to {history_path}")
    logger.info("Training completed!")


if __name__ == '__main__':
    main()
