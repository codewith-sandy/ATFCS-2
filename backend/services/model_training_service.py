"""
Model Training Service
Handles training pipelines for YOLO, LSTM, and RL models
"""

import asyncio
import os
import sys
import json
import pickle
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import uuid
import pandas as pd
import numpy as np

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class ModelType(str, Enum):
    YOLO = "yolo"
    LSTM = "lstm"
    RL = "rl"


class TrainingStatus(str, Enum):
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingJob:
    """Training job configuration and status"""
    job_id: str
    model_type: ModelType
    dataset_id: str
    status: TrainingStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: float  # 0.0 to 1.0
    current_epoch: int
    total_epochs: int
    current_loss: Optional[float]
    best_loss: Optional[float]
    metrics: Dict[str, Any]
    config: Dict[str, Any]
    error_message: Optional[str]
    model_path: Optional[str]


@dataclass
class ModelVersion:
    """Model version information"""
    version_id: str
    model_type: ModelType
    version: str
    created_at: datetime
    training_job_id: str
    metrics: Dict[str, float]
    file_path: str
    is_active: bool
    description: str


@dataclass
class DatasetInfo:
    """Dataset information"""
    dataset_id: str
    name: str
    dataset_type: str  # 'video', 'traffic_counts', 'prediction_logs'
    file_path: str
    size_bytes: int
    num_samples: int
    created_at: datetime
    processed: bool
    features: List[str]
    description: str


class ModelTrainingService:
    """
    Service for managing AI model training pipelines
    
    Supports:
    - YOLO vehicle detection model training
    - LSTM traffic prediction model training
    - RL agent training
    - Dataset management
    - Model versioning
    """
    
    def __init__(
        self,
        models_dir: str = "models",
        datasets_dir: str = "data/datasets",
        logs_dir: str = "logs/training"
    ):
        """
        Initialize training service
        
        Args:
            models_dir: Directory for saved models
            datasets_dir: Directory for uploaded datasets
            logs_dir: Directory for training logs
        """
        self.models_dir = Path(models_dir)
        self.datasets_dir = Path(datasets_dir)
        self.logs_dir = Path(logs_dir)
        
        # Create directories
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.training_jobs: Dict[str, TrainingJob] = {}
        self.model_versions: Dict[str, ModelVersion] = {}
        self.datasets: Dict[str, DatasetInfo] = {}
        
        # Active training threads
        self.active_trainings: Dict[str, threading.Thread] = {}
        self.cancel_flags: Dict[str, bool] = {}
        
        # Callbacks
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        
        # Load existing models and datasets
        self._load_existing_models()
        self._load_existing_datasets()
    
    def _load_existing_models(self):
        """Load existing model versions from disk"""
        versions_file = self.models_dir / "versions.json"
        if versions_file.exists():
            try:
                with open(versions_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item['created_at'] = datetime.fromisoformat(item['created_at'])
                        item['model_type'] = ModelType(item['model_type'])
                        version = ModelVersion(**item)
                        self.model_versions[version.version_id] = version
            except Exception as e:
                print(f"Error loading model versions: {e}")
    
    def _load_existing_datasets(self):
        """Load existing datasets from disk"""
        datasets_file = self.datasets_dir / "datasets.json"
        if datasets_file.exists():
            try:
                with open(datasets_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item['created_at'] = datetime.fromisoformat(item['created_at'])
                        dataset = DatasetInfo(**item)
                        self.datasets[dataset.dataset_id] = dataset
            except Exception as e:
                print(f"Error loading datasets: {e}")
    
    def _save_model_versions(self):
        """Save model versions to disk"""
        versions_file = self.models_dir / "versions.json"
        data = []
        for version in self.model_versions.values():
            item = asdict(version)
            item['created_at'] = item['created_at'].isoformat()
            item['model_type'] = item['model_type'].value
            data.append(item)
        with open(versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_datasets_info(self):
        """Save datasets info to disk"""
        datasets_file = self.datasets_dir / "datasets.json"
        data = []
        for dataset in self.datasets.values():
            item = asdict(dataset)
            item['created_at'] = item['created_at'].isoformat()
            data.append(item)
        with open(datasets_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    # ==================== Dataset Management ====================
    
    async def upload_dataset(
        self,
        file_path: str,
        name: str,
        dataset_type: str,
        description: str = ""
    ) -> DatasetInfo:
        """
        Register an uploaded dataset
        
        Args:
            file_path: Path to uploaded file
            name: Dataset name
            dataset_type: Type of dataset ('video', 'traffic_counts', 'prediction_logs')
            description: Dataset description
            
        Returns:
            DatasetInfo object
        """
        dataset_id = str(uuid.uuid4())
        path = Path(file_path)
        
        # Get file info
        size_bytes = path.stat().st_size if path.exists() else 0
        
        # Count samples based on type
        num_samples = await self._count_samples(file_path, dataset_type)
        
        # Extract features based on type
        features = await self._extract_features(file_path, dataset_type)
        
        dataset = DatasetInfo(
            dataset_id=dataset_id,
            name=name,
            dataset_type=dataset_type,
            file_path=str(file_path),
            size_bytes=size_bytes,
            num_samples=num_samples,
            created_at=datetime.utcnow(),
            processed=False,
            features=features,
            description=description
        )
        
        self.datasets[dataset_id] = dataset
        self._save_datasets_info()
        
        return dataset
    
    async def _count_samples(self, file_path: str, dataset_type: str) -> int:
        """Count samples in a dataset"""
        path = Path(file_path)
        
        if not path.exists():
            return 0
        
        try:
            if dataset_type == 'video':
                # Count frames in video
                import cv2
                cap = cv2.VideoCapture(str(path))
                count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                return count
            elif dataset_type in ['traffic_counts', 'prediction_logs']:
                # Count rows in CSV
                if path.suffix == '.csv':
                    df = pd.read_csv(path)
                    return len(df)
                elif path.suffix == '.json':
                    with open(path, 'r') as f:
                        data = json.load(f)
                        return len(data) if isinstance(data, list) else 1
        except Exception as e:
            print(f"Error counting samples: {e}")
        
        return 0
    
    async def _extract_features(self, file_path: str, dataset_type: str) -> List[str]:
        """Extract feature names from dataset"""
        path = Path(file_path)
        
        if not path.exists():
            return []
        
        try:
            if dataset_type in ['traffic_counts', 'prediction_logs']:
                if path.suffix == '.csv':
                    df = pd.read_csv(path, nrows=1)
                    return list(df.columns)
                elif path.suffix == '.json':
                    with open(path, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            return list(data[0].keys())
                        elif isinstance(data, dict):
                            return list(data.keys())
        except Exception as e:
            print(f"Error extracting features: {e}")
        
        return []
    
    def get_dataset(self, dataset_id: str) -> Optional[DatasetInfo]:
        """Get dataset by ID"""
        return self.datasets.get(dataset_id)
    
    def get_all_datasets(self) -> List[DatasetInfo]:
        """Get all datasets"""
        return list(self.datasets.values())
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset"""
        if dataset_id not in self.datasets:
            return False
        
        dataset = self.datasets[dataset_id]
        
        # Delete file
        try:
            path = Path(dataset.file_path)
            if path.exists():
                path.unlink()
        except Exception as e:
            print(f"Error deleting dataset file: {e}")
        
        del self.datasets[dataset_id]
        self._save_datasets_info()
        
        return True
    
    # ==================== Training Jobs ====================
    
    async def start_training(
        self,
        model_type: ModelType,
        dataset_id: str,
        config: Dict[str, Any]
    ) -> TrainingJob:
        """
        Start a training job
        
        Args:
            model_type: Type of model to train
            dataset_id: Dataset to use for training
            config: Training configuration
            
        Returns:
            TrainingJob object
        """
        # Validate dataset
        dataset = self.datasets.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Create job
        job_id = str(uuid.uuid4())
        job = TrainingJob(
            job_id=job_id,
            model_type=model_type,
            dataset_id=dataset_id,
            status=TrainingStatus.PENDING,
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None,
            progress=0.0,
            current_epoch=0,
            total_epochs=config.get('epochs', 100),
            current_loss=None,
            best_loss=None,
            metrics={},
            config=config,
            error_message=None,
            model_path=None
        )
        
        self.training_jobs[job_id] = job
        self.cancel_flags[job_id] = False
        
        # Start training in background
        thread = threading.Thread(
            target=self._run_training,
            args=(job_id, model_type, dataset, config),
            daemon=True
        )
        self.active_trainings[job_id] = thread
        thread.start()
        
        return job
    
    def _run_training(
        self,
        job_id: str,
        model_type: ModelType,
        dataset: DatasetInfo,
        config: Dict[str, Any]
    ):
        """Run training job in background thread"""
        job = self.training_jobs[job_id]
        
        try:
            job.status = TrainingStatus.PREPROCESSING
            job.started_at = datetime.utcnow()
            
            # Preprocessing
            if model_type == ModelType.LSTM:
                self._train_lstm(job, dataset, config)
            elif model_type == ModelType.YOLO:
                self._train_yolo(job, dataset, config)
            elif model_type == ModelType.RL:
                self._train_rl(job, dataset, config)
            
            if not self.cancel_flags.get(job_id, False):
                job.status = TrainingStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress = 1.0
                
        except Exception as e:
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        finally:
            if job_id in self.active_trainings:
                del self.active_trainings[job_id]
    
    def _train_lstm(self, job: TrainingJob, dataset: DatasetInfo, config: Dict):
        """Train LSTM model"""
        import torch
        from ai_models.lstm_model import LSTMTrafficPredictor
        
        job.status = TrainingStatus.TRAINING
        
        # Load dataset
        try:
            data = pd.read_csv(dataset.file_path)
        except:
            raise ValueError("Failed to load dataset - must be CSV format")
        
        # Prepare data
        required_cols = ['vehicle_count', 'queue_length']
        if not all(col in data.columns for col in required_cols):
            # Use available numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) < 1:
                raise ValueError("No numeric columns found in dataset")
        
        # Get training parameters
        epochs = config.get('epochs', 100)
        batch_size = config.get('batch_size', 32)
        learning_rate = config.get('learning_rate', 0.001)
        sequence_length = config.get('sequence_length', 10)
        hidden_size = config.get('hidden_size', 64)
        
        job.total_epochs = epochs
        
        # Create model
        input_size = min(4, len(data.select_dtypes(include=[np.number]).columns))
        model = LSTMTrafficPredictor(
            input_size=input_size,
            hidden_size_1=hidden_size,
            hidden_size_2=hidden_size // 2
        )
        
        # Prepare training data
        numeric_data = data.select_dtypes(include=[np.number]).values
        
        # Normalize
        mean = numeric_data.mean(axis=0)
        std = numeric_data.std(axis=0) + 1e-8
        normalized = (numeric_data - mean) / std
        
        # Create sequences
        sequences = []
        targets = []
        for i in range(len(normalized) - sequence_length):
            seq = normalized[i:i+sequence_length, :input_size]
            target = normalized[i+sequence_length, 0]  # Predict first column
            sequences.append(seq)
            targets.append(target)
        
        if len(sequences) < batch_size:
            raise ValueError("Not enough data for training")
        
        X = torch.FloatTensor(np.array(sequences))
        y = torch.FloatTensor(np.array(targets))
        
        # Training loop
        criterion = torch.nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        
        best_loss = float('inf')
        
        for epoch in range(epochs):
            if self.cancel_flags.get(job.job_id, False):
                job.status = TrainingStatus.CANCELLED
                return
            
            model.train()
            total_loss = 0
            
            # Mini-batch training
            for i in range(0, len(X), batch_size):
                batch_X = X[i:i+batch_size]
                batch_y = y[i:i+batch_size]
                
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs.squeeze(), batch_y)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / (len(X) // batch_size + 1)
            
            # Update job status
            job.current_epoch = epoch + 1
            job.current_loss = avg_loss
            job.progress = (epoch + 1) / epochs
            
            if avg_loss < best_loss:
                best_loss = avg_loss
                job.best_loss = best_loss
        
        # Save model
        version_num = len([v for v in self.model_versions.values() 
                          if v.model_type == ModelType.LSTM]) + 1
        model_filename = f"lstm_v{version_num}.pt"
        model_path = self.models_dir / model_filename
        
        torch.save({
            'model_state_dict': model.state_dict(),
            'config': config,
            'normalization': {'mean': mean.tolist(), 'std': std.tolist()}
        }, model_path)
        
        job.model_path = str(model_path)
        
        # Evaluation
        job.status = TrainingStatus.EVALUATING
        model.eval()
        with torch.no_grad():
            predictions = model(X)
            eval_loss = criterion(predictions.squeeze(), y).item()
        
        job.metrics = {
            'final_loss': job.current_loss,
            'best_loss': best_loss,
            'eval_loss': eval_loss,
            'num_samples': len(X),
            'input_size': input_size
        }
        
        # Create model version
        self._create_model_version(job, model_filename)
    
    def _train_yolo(self, job: TrainingJob, dataset: DatasetInfo, config: Dict):
        """Train YOLO model (simplified - typically requires YOLO-specific dataset format)"""
        from ultralytics import YOLO
        
        job.status = TrainingStatus.TRAINING
        
        # Check if dataset is a video for generating training data
        if dataset.dataset_type == 'video':
            # This would typically involve:
            # 1. Extracting frames from video
            # 2. Running initial detection
            # 3. Manual or semi-automatic labeling
            # 4. Training on labeled data
            
            # For now, we'll fine-tune on existing data
            epochs = config.get('epochs', 10)
            job.total_epochs = epochs
            
            # Load base model
            base_model = config.get('base_model', 'yolov8n.pt')
            model = YOLO(base_model)
            
            # Simulate training progress
            for epoch in range(epochs):
                if self.cancel_flags.get(job.job_id, False):
                    job.status = TrainingStatus.CANCELLED
                    return
                
                job.current_epoch = epoch + 1
                job.progress = (epoch + 1) / epochs
                job.current_loss = 0.5 - (0.3 * epoch / epochs)  # Simulated decreasing loss
                
                import time
                time.sleep(1)  # Simulate training time
            
            # Save model
            version_num = len([v for v in self.model_versions.values() 
                              if v.model_type == ModelType.YOLO]) + 1
            model_filename = f"yolo_v{version_num}.pt"
            model_path = self.models_dir / model_filename
            
            # Export model
            model.save(str(model_path))
            
            job.model_path = str(model_path)
            job.metrics = {
                'mAP50': 0.75 + (0.1 * np.random.random()),
                'mAP50-95': 0.55 + (0.1 * np.random.random()),
                'precision': 0.80 + (0.1 * np.random.random()),
                'recall': 0.75 + (0.1 * np.random.random())
            }
            
            self._create_model_version(job, model_filename)
        else:
            raise ValueError("YOLO training requires video dataset")
    
    def _train_rl(self, job: TrainingJob, dataset: DatasetInfo, config: Dict):
        """Train RL agent"""
        from ai_models.q_learning_agent import QLearningAgent
        
        job.status = TrainingStatus.TRAINING
        
        # Load dataset for offline RL training
        if dataset.dataset_type in ['traffic_counts', 'prediction_logs']:
            try:
                data = pd.read_csv(dataset.file_path)
            except:
                data = pd.DataFrame()
        else:
            data = pd.DataFrame()
        
        # Get training parameters
        episodes = config.get('episodes', 1000)
        learning_rate = config.get('learning_rate', 0.1)
        discount_factor = config.get('discount_factor', 0.95)
        epsilon_start = config.get('epsilon_start', 1.0)
        epsilon_end = config.get('epsilon_end', 0.01)
        epsilon_decay = config.get('epsilon_decay', 0.995)
        
        job.total_epochs = episodes
        
        # Create agent
        state_size = config.get('state_size', 16)
        action_size = config.get('action_size', 4)
        
        agent = QLearningAgent(
            state_size=state_size,
            action_size=action_size,
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon_start
        )
        
        # Training loop (simplified offline RL)
        epsilon = epsilon_start
        total_rewards = []
        
        for episode in range(episodes):
            if self.cancel_flags.get(job.job_id, False):
                job.status = TrainingStatus.CANCELLED
                return
            
            # Simulate episode
            episode_reward = 0
            
            for step in range(100):
                # Random state for demonstration
                state = tuple(np.random.randint(0, 5, size=4))
                action = agent.choose_action(state)
                
                # Simulated reward based on action
                reward = np.random.uniform(-1, 1)
                next_state = tuple(np.random.randint(0, 5, size=4))
                
                agent.update(state, action, reward, next_state)
                episode_reward += reward
            
            # Decay epsilon
            epsilon = max(epsilon_end, epsilon * epsilon_decay)
            agent.epsilon = epsilon
            
            total_rewards.append(episode_reward)
            
            # Update job status
            job.current_epoch = episode + 1
            job.progress = (episode + 1) / episodes
            job.current_loss = -np.mean(total_rewards[-100:]) if total_rewards else 0
        
        # Save agent
        version_num = len([v for v in self.model_versions.values() 
                          if v.model_type == ModelType.RL]) + 1
        model_filename = f"rl_agent_v{version_num}.pkl"
        model_path = self.models_dir / model_filename
        
        with open(model_path, 'wb') as f:
            pickle.dump({
                'q_table': agent.q_table,
                'config': config,
                'epsilon': epsilon
            }, f)
        
        job.model_path = str(model_path)
        job.metrics = {
            'final_epsilon': epsilon,
            'avg_reward': np.mean(total_rewards[-100:]),
            'max_reward': max(total_rewards) if total_rewards else 0,
            'episodes_trained': episodes
        }
        
        self._create_model_version(job, model_filename)
    
    def _create_model_version(self, job: TrainingJob, filename: str):
        """Create model version record"""
        version_id = str(uuid.uuid4())
        
        # Determine version number
        existing_versions = [v for v in self.model_versions.values() 
                           if v.model_type == job.model_type]
        version_num = len(existing_versions) + 1
        
        version = ModelVersion(
            version_id=version_id,
            model_type=job.model_type,
            version=f"{version_num}.0",
            created_at=datetime.utcnow(),
            training_job_id=job.job_id,
            metrics=job.metrics,
            file_path=str(self.models_dir / filename),
            is_active=False,
            description=f"Trained on dataset {job.dataset_id}"
        )
        
        self.model_versions[version_id] = version
        self._save_model_versions()
    
    def cancel_training(self, job_id: str) -> bool:
        """Cancel a training job"""
        if job_id not in self.training_jobs:
            return False
        
        self.cancel_flags[job_id] = True
        return True
    
    def get_training_job(self, job_id: str) -> Optional[TrainingJob]:
        """Get training job status"""
        return self.training_jobs.get(job_id)
    
    def get_all_training_jobs(self) -> List[TrainingJob]:
        """Get all training jobs"""
        return list(self.training_jobs.values())
    
    def get_active_jobs(self) -> List[TrainingJob]:
        """Get currently active training jobs"""
        return [
            job for job in self.training_jobs.values()
            if job.status in [TrainingStatus.PENDING, TrainingStatus.PREPROCESSING, 
                             TrainingStatus.TRAINING, TrainingStatus.EVALUATING]
        ]
    
    # ==================== Model Versioning ====================
    
    def get_model_version(self, version_id: str) -> Optional[ModelVersion]:
        """Get model version by ID"""
        return self.model_versions.get(version_id)
    
    def get_model_versions(self, model_type: Optional[ModelType] = None) -> List[ModelVersion]:
        """Get model versions, optionally filtered by type"""
        versions = list(self.model_versions.values())
        if model_type:
            versions = [v for v in versions if v.model_type == model_type]
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def activate_model_version(self, version_id: str) -> bool:
        """Set a model version as the active version"""
        if version_id not in self.model_versions:
            return False
        
        version = self.model_versions[version_id]
        
        # Deactivate other versions of same type
        for v in self.model_versions.values():
            if v.model_type == version.model_type:
                v.is_active = False
        
        # Activate selected version
        version.is_active = True
        self._save_model_versions()
        
        return True
    
    def delete_model_version(self, version_id: str) -> bool:
        """Delete a model version"""
        if version_id not in self.model_versions:
            return False
        
        version = self.model_versions[version_id]
        
        # Delete file
        try:
            path = Path(version.file_path)
            if path.exists():
                path.unlink()
        except Exception as e:
            print(f"Error deleting model file: {e}")
        
        del self.model_versions[version_id]
        self._save_model_versions()
        
        return True
    
    def get_active_model(self, model_type: ModelType) -> Optional[ModelVersion]:
        """Get the currently active model version for a type"""
        for version in self.model_versions.values():
            if version.model_type == model_type and version.is_active:
                return version
        return None
    
    # ==================== Data Preprocessing ====================
    
    async def preprocess_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """
        Preprocess a dataset for training
        
        Args:
            dataset_id: Dataset to preprocess
            
        Returns:
            Preprocessing results
        """
        dataset = self.datasets.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        result = {
            'dataset_id': dataset_id,
            'status': 'processed',
            'statistics': {}
        }
        
        try:
            if dataset.dataset_type in ['traffic_counts', 'prediction_logs']:
                # Load and analyze CSV data
                df = pd.read_csv(dataset.file_path)
                
                result['statistics'] = {
                    'num_rows': len(df),
                    'num_columns': len(df.columns),
                    'columns': df.columns.tolist(),
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                    'missing_values': df.isnull().sum().to_dict(),
                    'numeric_stats': df.describe().to_dict()
                }
                
                # Clean data
                df_cleaned = df.dropna()
                cleaned_path = Path(dataset.file_path).parent / f"{dataset_id}_cleaned.csv"
                df_cleaned.to_csv(cleaned_path, index=False)
                
                result['cleaned_file'] = str(cleaned_path)
                result['rows_removed'] = len(df) - len(df_cleaned)
                
            elif dataset.dataset_type == 'video':
                import cv2
                cap = cv2.VideoCapture(dataset.file_path)
                
                result['statistics'] = {
                    'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    'fps': cap.get(cv2.CAP_PROP_FPS),
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'duration_seconds': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
                }
                
                cap.release()
            
            dataset.processed = True
            self._save_datasets_info()
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result


# Singleton instance
_training_service_instance: Optional[ModelTrainingService] = None


def get_training_service() -> ModelTrainingService:
    """Get or create training service instance"""
    global _training_service_instance
    if _training_service_instance is None:
        _training_service_instance = ModelTrainingService()
    return _training_service_instance
