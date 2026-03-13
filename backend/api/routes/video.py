"""
Video API Routes
Endpoints for video upload and processing
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, List, Optional
from pydantic import BaseModel
import aiofiles
import os
import uuid
from pathlib import Path
import cv2
import asyncio

router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("data/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class VideoUploadResponse(BaseModel):
    """Response for video upload"""
    video_id: str
    filename: str
    status: str
    message: str


class ProcessingStatus(BaseModel):
    """Video processing status"""
    video_id: str
    status: str
    progress: float
    frames_processed: int
    total_frames: int


# In-memory processing status tracker
processing_status = {}


@router.post("/upload")
async def upload_video(
    video: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
) -> VideoUploadResponse:
    """
    Upload a traffic video for processing
    
    Supports: MP4, AVI, MOV, MKV formats
    
    The video will be saved and queued for processing.
    Use the returned video_id to check processing status.
    """
    # Validate file type
    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    ext = Path(video.filename).suffix.lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique ID
    video_id = str(uuid.uuid4())
    
    # Save file
    filename = f"{video_id}{ext}"
    filepath = UPLOAD_DIR / filename
    
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            content = await video.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")
    
    # Initialize processing status
    processing_status[video_id] = {
        'status': 'uploaded',
        'progress': 0.0,
        'frames_processed': 0,
        'total_frames': 0,
        'filepath': str(filepath)
    }
    
    # Queue background processing
    if background_tasks:
        background_tasks.add_task(process_video_task, video_id, str(filepath))
    
    return VideoUploadResponse(
        video_id=video_id,
        filename=video.filename,
        status="uploaded",
        message="Video uploaded successfully. Processing will begin shortly."
    )


async def process_video_task(video_id: str, filepath: str):
    """Background task to process uploaded video"""
    from main import detection_service
    
    processing_status[video_id]['status'] = 'processing'
    
    try:
        # Get video info
        cap = cv2.VideoCapture(filepath)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        processing_status[video_id]['total_frames'] = total_frames
        cap.release()
        
        # Process video
        if detection_service:
            results = await detection_service.detect_from_video(
                filepath,
                skip_frames=5,
                max_frames=1000
            )
            
            processing_status[video_id]['frames_processed'] = len(results)
            processing_status[video_id]['progress'] = 100.0
            processing_status[video_id]['status'] = 'completed'
            processing_status[video_id]['results_count'] = len(results)
        else:
            processing_status[video_id]['status'] = 'error'
            processing_status[video_id]['error'] = 'Detection service not available'
            
    except Exception as e:
        processing_status[video_id]['status'] = 'error'
        processing_status[video_id]['error'] = str(e)


@router.get("/status/{video_id}")
async def get_processing_status(video_id: str) -> Dict:
    """
    Get processing status for an uploaded video
    
    Args:
        video_id: The video ID returned from upload
        
    Returns:
        Processing status including progress and frame count
    """
    if video_id not in processing_status:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return processing_status[video_id]


@router.get("/list")
async def list_videos() -> List[Dict]:
    """
    List all uploaded videos and their status
    """
    videos = []
    
    for video_id, status in processing_status.items():
        videos.append({
            'video_id': video_id,
            'status': status['status'],
            'progress': status['progress'],
            'frames_processed': status['frames_processed']
        })
    
    return videos


@router.delete("/{video_id}")
async def delete_video(video_id: str) -> Dict:
    """
    Delete an uploaded video
    
    Args:
        video_id: The video ID to delete
    """
    if video_id not in processing_status:
        raise HTTPException(status_code=404, detail="Video not found")
    
    filepath = processing_status[video_id].get('filepath')
    
    # Delete file
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
    
    # Remove from status
    del processing_status[video_id]
    
    return {"status": "deleted", "video_id": video_id}


@router.post("/stream/start")
async def start_camera_stream(camera_source: str = "0") -> Dict:
    """
    Start processing camera feed
    
    Args:
        camera_source: Camera index (0, 1, etc.) or RTSP URL
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Controller not available")
    
    try:
        source = int(camera_source)
    except ValueError:
        source = camera_source
    
    controller_service.start_camera_feed(source)
    
    return {
        "status": "started",
        "camera_source": camera_source,
        "message": "Camera feed processing started"
    }


@router.post("/stream/stop")
async def stop_camera_stream() -> Dict:
    """Stop camera feed processing"""
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Controller not available")
    
    controller_service.stop()
    
    return {
        "status": "stopped",
        "message": "Camera feed processing stopped"
    }
