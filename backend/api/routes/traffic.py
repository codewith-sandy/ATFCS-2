"""
Traffic API Routes
Endpoints for live traffic data
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel

router = APIRouter()


class TrafficData(BaseModel):
    """Traffic data response model"""
    timestamp: float
    vehicle_count: int
    queue_length: int
    lane_density: float
    current_phase: int
    emergency_detected: bool


class LaneData(BaseModel):
    """Per-lane traffic data"""
    lane_id: int
    vehicle_count: int
    queue_length: int
    density: float
    emergency: bool


@router.get("/live")
async def get_live_traffic() -> Dict:
    """
    Get live traffic data
    
    Returns current traffic state including:
    - Vehicle count
    - Queue length
    - Lane density
    - Signal phase
    - Emergency status
    """
    # Import here to avoid circular imports
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Traffic controller not available")
    
    return controller_service.get_live_data()


@router.get("/lanes")
async def get_lane_data() -> Dict:
    """
    Get per-lane traffic data
    
    Returns traffic state for each lane at the intersection
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Traffic controller not available")
    
    return controller_service.get_lane_states()


@router.get("/state")
async def get_controller_state() -> Dict:
    """
    Get current controller state
    
    Returns complete controller state including:
    - Running status
    - Current phase and timing
    - Vehicle metrics
    - Predictions
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Traffic controller not available")
    
    state = controller_service.get_current_state()
    if state is None:
        return {"status": "no_data", "message": "No traffic data available yet"}
    
    return {
        "is_running": state.is_running,
        "current_phase": state.current_phase,
        "current_green_time": state.current_green_time,
        "vehicle_count": state.vehicle_count,
        "queue_length": state.queue_length,
        "predicted_count": state.predicted_count,
        "emergency_active": state.emergency_active,
        "timestamp": state.timestamp
    }


@router.get("/metrics")
async def get_traffic_metrics() -> Dict:
    """
    Get traffic performance metrics
    
    Returns:
    - Average waiting time
    - Average queue length
    - Throughput
    - Emergency response metrics
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Traffic controller not available")
    
    metrics = controller_service.get_metrics()
    
    return {
        "avg_waiting_time": metrics.avg_waiting_time,
        "avg_queue_length": metrics.avg_queue_length,
        "throughput": metrics.throughput,
        "emergency_response_time": metrics.emergency_response_time,
        "vehicles_processed": metrics.vehicles_processed,
        "signals_optimized": metrics.signals_optimized
    }


@router.post("/emergency")
async def trigger_emergency(lane: int) -> Dict:
    """
    Trigger emergency vehicle override
    
    Args:
        lane: Lane number where emergency vehicle is detected
        
    Returns:
        Confirmation of emergency override
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Traffic controller not available")
    
    if lane < 0 or lane > 3:
        raise HTTPException(status_code=400, detail="Invalid lane number (0-3)")
    
    controller_service.trigger_emergency_override(lane)
    
    return {
        "status": "success",
        "message": f"Emergency override triggered for lane {lane}",
        "lane": lane
    }
