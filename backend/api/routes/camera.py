"""
Camera API Routes
Endpoints for camera streaming and management
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
import asyncio

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.camera_stream_service import get_camera_service, CameraStreamService


router = APIRouter()


# ==================== Request/Response Models ====================

class CameraConfig(BaseModel):
    """Camera configuration model"""
    camera_id: str
    lane_id: int
    source: str
    name: str
    resolution: tuple = (640, 480)


class CameraUpdateRequest(BaseModel):
    """Camera update request"""
    source: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class SignalStateUpdate(BaseModel):
    """Signal state update"""
    lane_id: int
    state: str  # 'red', 'yellow', 'green'


class LaneMetricsResponse(BaseModel):
    """Lane metrics response"""
    lane_id: int
    vehicle_count: int
    queue_length: int
    congestion_level: str
    density: float
    signal_state: str
    emergency_detected: bool


# ==================== Streaming Endpoints ====================

@router.get("/lane/{lane_id}/stream")
async def stream_lane_camera(lane_id: int):
    """
    Stream live video feed from a lane camera
    
    Returns MJPEG stream with:
    - Vehicle detection bounding boxes
    - Vehicle count overlay
    - Congestion level indicator
    - Signal state indicator
    
    Usage: <img src="/camera/lane/1/stream" />
    """
    camera_service = get_camera_service()
    
    # Find camera for this lane
    camera_id = f"cam_lane_{lane_id + 1}"
    
    if camera_id not in camera_service.cameras:
        raise HTTPException(status_code=404, detail=f"Camera for lane {lane_id} not found")
    
    return StreamingResponse(
        camera_service.generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/camera/{camera_id}/stream")
async def stream_camera(camera_id: str):
    """
    Stream live video feed from a specific camera
    
    Returns MJPEG stream with annotations
    """
    camera_service = get_camera_service()
    
    if camera_id not in camera_service.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    return StreamingResponse(
        camera_service.generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==================== Metrics Endpoints ====================

@router.get("/lane/{lane_id}/metrics", response_model=LaneMetricsResponse)
async def get_lane_metrics(lane_id: int):
    """
    Get current metrics for a specific lane
    
    Returns:
    - Vehicle count
    - Queue length
    - Congestion level
    - Density
    - Signal state
    - Emergency status
    """
    camera_service = get_camera_service()
    
    metrics = camera_service.get_lane_metrics(lane_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for lane {lane_id} not found")
    
    return LaneMetricsResponse(
        lane_id=metrics.lane_id,
        vehicle_count=metrics.vehicle_count,
        queue_length=metrics.queue_length,
        congestion_level=metrics.congestion_level,
        density=metrics.density,
        signal_state=metrics.signal_state,
        emergency_detected=metrics.emergency_detected
    )


@router.get("/lanes/metrics")
async def get_all_lane_metrics() -> List[Dict]:
    """
    Get metrics for all lanes
    
    Returns list of all lane metrics
    """
    camera_service = get_camera_service()
    return camera_service.get_all_lane_metrics_dict()


# ==================== Camera Management Endpoints ====================

@router.get("/cameras")
async def list_cameras() -> List[Dict]:
    """
    List all configured cameras
    """
    camera_service = get_camera_service()
    return camera_service.get_camera_list()


@router.post("/cameras")
async def add_camera(config: CameraConfig):
    """
    Add a new camera to the system
    """
    camera_service = get_camera_service()
    
    success = camera_service.add_camera(
        camera_id=config.camera_id,
        lane_id=config.lane_id,
        source=config.source,
        name=config.name,
        resolution=config.resolution
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Camera ID already exists")
    
    return {"status": "success", "message": f"Camera {config.camera_id} added"}


@router.put("/cameras/{camera_id}")
async def update_camera(camera_id: str, update: CameraUpdateRequest):
    """
    Update camera configuration
    """
    camera_service = get_camera_service()
    
    if camera_id not in camera_service.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    if update.source:
        camera_service.configure_camera_source(camera_id, update.source)
    
    return {"status": "success", "message": f"Camera {camera_id} updated"}


@router.delete("/cameras/{camera_id}")
async def remove_camera(camera_id: str):
    """
    Remove a camera from the system
    """
    camera_service = get_camera_service()
    
    success = camera_service.remove_camera(camera_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    return {"status": "success", "message": f"Camera {camera_id} removed"}


# ==================== Available Cameras Detection ====================

class CameraAssignRequest(BaseModel):
    """Request to assign a detected camera to a lane"""
    camera_index: int
    lane_id: int
    name: Optional[str] = None


@router.get("/available")
async def get_available_cameras(max_cameras: int = Query(10, ge=1, le=20)):
    """
    Detect and list all available cameras connected to the system
    
    This scans for connected webcams and video capture devices.
    
    Args:
        max_cameras: Maximum number of camera indices to check (default: 10)
        
    Returns:
        List of available cameras with their properties
    """
    camera_service = get_camera_service()
    available = camera_service.detect_available_cameras(max_cameras)
    
    return {
        "status": "success",
        "count": len(available),
        "cameras": available
    }


@router.post("/assign")
async def assign_camera_to_lane(request: CameraAssignRequest):
    """
    Assign a detected camera to a specific lane
    
    Args:
        camera_index: The camera device index from available cameras
        lane_id: The lane number to assign the camera to (0-3)
        name: Optional custom name for the camera
        
    Returns:
        Success status
    """
    camera_service = get_camera_service()
    
    success = camera_service.assign_camera_to_lane(
        camera_index=request.camera_index,
        lane_id=request.lane_id,
        name=request.name
    )
    
    if success:
        return {
            "status": "success",
            "message": f"Camera {request.camera_index} assigned to lane {request.lane_id}"
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to assign camera")


@router.get("/scan")
async def scan_cameras():
    """
    Quick scan to check camera availability
    
    Returns a summary of available cameras without detailed probing
    """
    camera_service = get_camera_service()
    available = camera_service.detect_available_cameras(max_cameras=5)
    
    return {
        "status": "success",
        "available_count": len(available),
        "cameras": [
            {
                "index": cam["index"],
                "name": cam["name"],
                "resolution": f"{cam['resolution'][0]}x{cam['resolution'][1]}"
            }
            for cam in available
        ]
    }


# ==================== Signal State Endpoints ====================

@router.post("/signals/update")
async def update_signal_state(update: SignalStateUpdate):
    """
    Update signal state for a lane
    
    This is typically called by the traffic controller
    """
    camera_service = get_camera_service()
    
    if update.state not in ['red', 'yellow', 'green']:
        raise HTTPException(status_code=400, detail="Invalid signal state")
    
    camera_service.update_signal_state(update.lane_id, update.state)
    
    return {"status": "success", "message": f"Signal state updated for lane {update.lane_id}"}


# ==================== System Stats ====================

@router.get("/stats")
async def get_camera_stats():
    """
    Get camera system statistics
    
    Returns:
    - Total cameras
    - Active cameras
    - Detector status
    - FPS per camera
    - Total vehicles detected
    - Emergency count
    """
    camera_service = get_camera_service()
    return camera_service.get_system_stats()


# ==================== Multi-Intersection Support ====================

@router.get("/intersections")
async def list_intersections():
    """
    List all configured intersections
    
    For multi-intersection support
    """
    # For now, return a single intersection
    # This would be expanded for multi-intersection support
    return [
        {
            "intersection_id": "main",
            "name": "Main Intersection",
            "lanes": [0, 1, 2, 3],
            "cameras": ["cam_lane_1", "cam_lane_2", "cam_lane_3", "cam_lane_4"],
            "location": {"lat": 0.0, "lng": 0.0}
        }
    ]


@router.get("/intersections/{intersection_id}")
async def get_intersection(intersection_id: str):
    """
    Get details for a specific intersection
    """
    camera_service = get_camera_service()
    
    if intersection_id == "main":
        return {
            "intersection_id": "main",
            "name": "Main Intersection", 
            "lanes": camera_service.get_all_lane_metrics_dict(),
            "cameras": camera_service.get_camera_list(),
            "stats": camera_service.get_system_stats()
        }
    
    raise HTTPException(status_code=404, detail=f"Intersection {intersection_id} not found")
