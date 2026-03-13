"""
Model Training API Routes
Endpoints for model training and versioning
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.model_training_service import (
    get_training_service, 
    ModelType, 
    TrainingStatus,
    TrainingJob,
    ModelVersion
)


router = APIRouter()


# ==================== Request/Response Models ====================

class TrainingStartRequest(BaseModel):
    """Request to start training"""
    model_type: str  # 'yolo', 'lstm', 'rl'
    dataset_id: str
    config: Dict[str, Any] = {}


class TrainingJobResponse(BaseModel):
    """Training job response"""
    job_id: str
    model_type: str
    dataset_id: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: float
    current_epoch: int
    total_epochs: int
    current_loss: Optional[float]
    best_loss: Optional[float]
    metrics: Dict[str, Any]
    error_message: Optional[str]
    model_path: Optional[str]


class ModelVersionResponse(BaseModel):
    """Model version response"""
    version_id: str
    model_type: str
    version: str
    created_at: str
    training_job_id: str
    metrics: Dict[str, float]
    file_path: str
    is_active: bool
    description: str


class TrainingConfigLSTM(BaseModel):
    """LSTM training configuration"""
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    sequence_length: int = 10
    hidden_size: int = 64


class TrainingConfigYOLO(BaseModel):
    """YOLO training configuration"""
    epochs: int = 10
    batch_size: int = 16
    learning_rate: float = 0.001
    base_model: str = "yolov8n.pt"
    image_size: int = 640


class TrainingConfigRL(BaseModel):
    """RL training configuration"""
    episodes: int = 1000
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    state_size: int = 16
    action_size: int = 4


# ==================== Helper Functions ====================

def job_to_response(job: TrainingJob) -> TrainingJobResponse:
    """Convert TrainingJob to response model"""
    return TrainingJobResponse(
        job_id=job.job_id,
        model_type=job.model_type.value,
        dataset_id=job.dataset_id,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        progress=job.progress,
        current_epoch=job.current_epoch,
        total_epochs=job.total_epochs,
        current_loss=job.current_loss,
        best_loss=job.best_loss,
        metrics=job.metrics,
        error_message=job.error_message,
        model_path=job.model_path
    )


def version_to_response(version: ModelVersion) -> ModelVersionResponse:
    """Convert ModelVersion to response model"""
    return ModelVersionResponse(
        version_id=version.version_id,
        model_type=version.model_type.value,
        version=version.version,
        created_at=version.created_at.isoformat(),
        training_job_id=version.training_job_id,
        metrics=version.metrics,
        file_path=version.file_path,
        is_active=version.is_active,
        description=version.description
    )


# ==================== Training Endpoints ====================

@router.post("/train/lstm")
async def start_lstm_training(
    dataset_id: str,
    config: TrainingConfigLSTM = TrainingConfigLSTM()
):
    """
    Start LSTM model training
    
    The LSTM model predicts future traffic volume based on historical data.
    
    Required dataset format (CSV):
    - timestamp: Time of observation
    - vehicle_count: Number of vehicles
    - queue_length: Length of traffic queue
    - lane_id: Lane identifier (optional)
    """
    training_service = get_training_service()
    
    try:
        job = await training_service.start_training(
            model_type=ModelType.LSTM,
            dataset_id=dataset_id,
            config=config.dict()
        )
        return job_to_response(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


@router.post("/train/yolo")
async def start_yolo_training(
    dataset_id: str,
    config: TrainingConfigYOLO = TrainingConfigYOLO()
):
    """
    Start YOLO model training/fine-tuning
    
    Fine-tunes the vehicle detection model on traffic videos.
    
    Required dataset format:
    - Video file (.mp4, .avi, etc.)
    """
    training_service = get_training_service()
    
    try:
        job = await training_service.start_training(
            model_type=ModelType.YOLO,
            dataset_id=dataset_id,
            config=config.dict()
        )
        return job_to_response(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


@router.post("/train/rl")
async def start_rl_training(
    dataset_id: str,
    config: TrainingConfigRL = TrainingConfigRL()
):
    """
    Start RL agent training
    
    Trains the Q-learning agent for traffic signal optimization.
    
    Dataset can contain historical traffic data for offline training.
    """
    training_service = get_training_service()
    
    try:
        job = await training_service.start_training(
            model_type=ModelType.RL,
            dataset_id=dataset_id,
            config=config.dict()
        )
        return job_to_response(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")


# ==================== Training Job Management ====================

@router.get("/training/status")
async def get_all_training_status():
    """
    Get status of all training jobs
    """
    training_service = get_training_service()
    
    jobs = training_service.get_all_training_jobs()
    
    return {
        "total": len(jobs),
        "active": len([j for j in jobs if j.status in 
                      [TrainingStatus.PENDING, TrainingStatus.PREPROCESSING,
                       TrainingStatus.TRAINING, TrainingStatus.EVALUATING]]),
        "completed": len([j for j in jobs if j.status == TrainingStatus.COMPLETED]),
        "failed": len([j for j in jobs if j.status == TrainingStatus.FAILED]),
        "jobs": [job_to_response(j) for j in jobs]
    }


@router.get("/training/{job_id}")
async def get_training_status(job_id: str):
    """
    Get status of a specific training job
    """
    training_service = get_training_service()
    
    job = training_service.get_training_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    
    return job_to_response(job)


@router.post("/training/{job_id}/cancel")
async def cancel_training(job_id: str):
    """
    Cancel a running training job
    """
    training_service = get_training_service()
    
    success = training_service.cancel_training(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")
    
    return {"status": "success", "message": f"Training job {job_id} cancelled"}


@router.get("/training/active")
async def get_active_training():
    """
    Get currently active training jobs
    """
    training_service = get_training_service()
    
    jobs = training_service.get_active_jobs()
    
    return {
        "count": len(jobs),
        "jobs": [job_to_response(j) for j in jobs]
    }


# ==================== Model Version Management ====================

@router.get("/versions")
async def list_model_versions(model_type: Optional[str] = None):
    """
    List all model versions
    
    Optionally filter by model type (yolo, lstm, rl)
    """
    training_service = get_training_service()
    
    filter_type = None
    if model_type:
        try:
            filter_type = ModelType(model_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}")
    
    versions = training_service.get_model_versions(filter_type)
    
    return {
        "total": len(versions),
        "versions": [version_to_response(v) for v in versions]
    }


@router.get("/versions/{version_id}")
async def get_model_version(version_id: str):
    """
    Get specific model version details
    """
    training_service = get_training_service()
    
    version = training_service.get_model_version(version_id)
    
    if not version:
        raise HTTPException(status_code=404, detail=f"Model version {version_id} not found")
    
    return version_to_response(version)


@router.post("/versions/{version_id}/activate")
async def activate_model_version(version_id: str):
    """
    Activate a model version for use in the system
    
    This sets the specified version as the active version for its model type.
    """
    training_service = get_training_service()
    
    success = training_service.activate_model_version(version_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Model version {version_id} not found")
    
    return {"status": "success", "message": f"Model version {version_id} activated"}


@router.delete("/versions/{version_id}")
async def delete_model_version(version_id: str):
    """
    Delete a model version
    """
    training_service = get_training_service()
    
    success = training_service.delete_model_version(version_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Model version {version_id} not found")
    
    return {"status": "success", "message": f"Model version {version_id} deleted"}


@router.get("/active/{model_type}")
async def get_active_model(model_type: str):
    """
    Get the currently active model version for a model type
    """
    training_service = get_training_service()
    
    try:
        mtype = ModelType(model_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}")
    
    version = training_service.get_active_model(mtype)
    
    if not version:
        return {"active": False, "message": f"No active {model_type} model"}
    
    return {
        "active": True,
        "version": version_to_response(version)
    }


# ==================== Default Configs ====================

@router.get("/config/default/{model_type}")
async def get_default_config(model_type: str):
    """
    Get default training configuration for a model type
    """
    configs = {
        'lstm': TrainingConfigLSTM().dict(),
        'yolo': TrainingConfigYOLO().dict(),
        'rl': TrainingConfigRL().dict()
    }
    
    if model_type not in configs:
        raise HTTPException(status_code=400, detail=f"Invalid model type: {model_type}")
    
    return {
        "model_type": model_type,
        "config": configs[model_type]
    }
