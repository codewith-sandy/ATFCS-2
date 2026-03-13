"""
Dataset API Routes
Endpoints for dataset upload and management
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
import aiofiles
import os
import uuid
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.model_training_service import get_training_service, DatasetInfo


router = APIRouter()


# Upload directory
UPLOAD_DIR = Path("data/datasets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================== Request/Response Models ====================

class DatasetUploadResponse(BaseModel):
    """Response for dataset upload"""
    dataset_id: str
    name: str
    dataset_type: str
    file_path: str
    size_bytes: int
    num_samples: int
    status: str
    message: str


class DatasetInfoResponse(BaseModel):
    """Dataset information response"""
    dataset_id: str
    name: str
    dataset_type: str
    size_bytes: int
    num_samples: int
    created_at: str
    processed: bool
    features: List[str]
    description: str


class DatasetListResponse(BaseModel):
    """Dataset list response"""
    total: int
    datasets: List[DatasetInfoResponse]


# ==================== Upload Endpoints ====================

@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    dataset_type: str = Query(..., description="Type: video, traffic_counts, prediction_logs"),
    description: str = ""
):
    """
    Upload a dataset for model training
    
    Supported formats:
    - Videos: .mp4, .avi, .mov, .mkv
    - Traffic counts: .csv, .json
    - Prediction logs: .csv, .json
    
    The dataset will be processed and made available for training.
    """
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    
    allowed_extensions = {
        'video': {'.mp4', '.avi', '.mov', '.mkv', '.webm'},
        'traffic_counts': {'.csv', '.json'},
        'prediction_logs': {'.csv', '.json'}
    }
    
    if dataset_type not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dataset type. Allowed: {', '.join(allowed_extensions.keys())}"
        )
    
    if ext not in allowed_extensions[dataset_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type for {dataset_type}. Allowed: {', '.join(allowed_extensions[dataset_type])}"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    filepath = UPLOAD_DIR / filename
    
    # Save file
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Register dataset with training service
    training_service = get_training_service()
    
    dataset_name = name or file.filename
    
    try:
        dataset = await training_service.upload_dataset(
            file_path=str(filepath),
            name=dataset_name,
            dataset_type=dataset_type,
            description=description
        )
    except Exception as e:
        # Clean up file on error
        filepath.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to process dataset: {str(e)}")
    
    return DatasetUploadResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        dataset_type=dataset.dataset_type,
        file_path=str(filepath),
        size_bytes=dataset.size_bytes,
        num_samples=dataset.num_samples,
        status="uploaded",
        message="Dataset uploaded successfully"
    )


# ==================== Dataset Management Endpoints ====================

@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    dataset_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List all uploaded datasets
    
    Optionally filter by dataset type
    """
    training_service = get_training_service()
    
    datasets = training_service.get_all_datasets()
    
    # Filter by type if specified
    if dataset_type:
        datasets = [d for d in datasets if d.dataset_type == dataset_type]
    
    # Paginate
    total = len(datasets)
    datasets = datasets[offset:offset + limit]
    
    return DatasetListResponse(
        total=total,
        datasets=[
            DatasetInfoResponse(
                dataset_id=d.dataset_id,
                name=d.name,
                dataset_type=d.dataset_type,
                size_bytes=d.size_bytes,
                num_samples=d.num_samples,
                created_at=d.created_at.isoformat(),
                processed=d.processed,
                features=d.features,
                description=d.description
            )
            for d in datasets
        ]
    )


@router.get("/{dataset_id}", response_model=DatasetInfoResponse)
async def get_dataset(dataset_id: str):
    """
    Get dataset details by ID
    """
    training_service = get_training_service()
    
    dataset = training_service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    return DatasetInfoResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        dataset_type=dataset.dataset_type,
        size_bytes=dataset.size_bytes,
        num_samples=dataset.num_samples,
        created_at=dataset.created_at.isoformat(),
        processed=dataset.processed,
        features=dataset.features,
        description=dataset.description
    )


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """
    Delete a dataset
    """
    training_service = get_training_service()
    
    success = training_service.delete_dataset(dataset_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    return {"status": "success", "message": f"Dataset {dataset_id} deleted"}


@router.get("/{dataset_id}/download")
async def download_dataset(dataset_id: str):
    """
    Download a dataset file
    """
    training_service = get_training_service()
    
    dataset = training_service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    filepath = Path(dataset.file_path)
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    return FileResponse(
        path=str(filepath),
        filename=f"{dataset.name}{filepath.suffix}",
        media_type="application/octet-stream"
    )


@router.post("/{dataset_id}/preprocess")
async def preprocess_dataset(dataset_id: str):
    """
    Preprocess a dataset for training
    
    Performs data cleaning, feature extraction, and analysis
    """
    training_service = get_training_service()
    
    dataset = training_service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    try:
        result = await training_service.preprocess_dataset(dataset_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing failed: {str(e)}")


@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, rows: int = 10):
    """
    Preview first N rows of a dataset
    """
    import pandas as pd
    
    training_service = get_training_service()
    
    dataset = training_service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    if dataset.dataset_type == 'video':
        return {
            "message": "Video preview not supported through API",
            "info": {
                "file_path": dataset.file_path,
                "num_frames": dataset.num_samples
            }
        }
    
    try:
        filepath = Path(dataset.file_path)
        
        if filepath.suffix == '.csv':
            df = pd.read_csv(filepath, nrows=rows)
            return {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient='records'),
                "total_rows": dataset.num_samples
            }
        elif filepath.suffix == '.json':
            import json
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {
                        "data": data[:rows],
                        "total_items": len(data)
                    }
                return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview dataset: {str(e)}")
