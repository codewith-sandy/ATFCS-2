"""
Signals API Routes
Endpoints for traffic signal control
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel

router = APIRouter()


class SignalState(BaseModel):
    """Signal state model"""
    phase: int
    green_time: int
    time_remaining: float
    is_emergency: bool


class SignalOverride(BaseModel):
    """Manual signal override request"""
    phase: int
    duration: int = 30


class SignalDecisionRequest(BaseModel):
    """Request signal decision"""
    current_vehicle_count: int
    predicted_vehicle_count: float
    queue_length: int
    current_signal_phase: int
    emergency_detected: bool = False
    emergency_lane: Optional[int] = None


@router.get("")
async def get_current_signals() -> Dict:
    """
    Get current signal states for all phases
    
    Returns:
        Current signal configuration and timing
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Controller not available")
    
    state = controller_service.get_current_state()
    
    if state is None:
        return {
            "status": "no_data",
            "phases": [
                {"phase": 0, "state": "unknown", "description": "North-South"},
                {"phase": 1, "state": "unknown", "description": "North-South Yellow"},
                {"phase": 2, "state": "unknown", "description": "East-West"},
                {"phase": 3, "state": "unknown", "description": "East-West Yellow"}
            ]
        }
    
    # Map phases to signal states
    phases = []
    for i in range(4):
        phase_state = "green" if i == state.current_phase else "red"
        if i == (state.current_phase + 1) % 4:
            phase_state = "yellow"
            
        phases.append({
            "phase": i,
            "state": phase_state,
            "description": ["North-South", "N-S Yellow", "East-West", "E-W Yellow"][i]
        })
    
    return {
        "current_phase": state.current_phase,
        "green_time": state.current_green_time,
        "emergency_active": state.emergency_active,
        "phases": phases,
        "timestamp": state.timestamp
    }


@router.post("/override")
async def override_signal(request: SignalOverride) -> Dict:
    """
    Manually override signal phase
    
    Args:
        request: Phase and duration to set
        
    Returns:
        Confirmation of override
    """
    from main import controller_service
    
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Controller not available")
    
    if request.phase < 0 or request.phase > 3:
        raise HTTPException(status_code=400, detail="Phase must be 0-3")
    
    if request.duration < 10 or request.duration > 60:
        raise HTTPException(status_code=400, detail="Duration must be 10-60 seconds")
    
    controller_service.set_signal_phase(request.phase, request.duration)
    
    return {
        "status": "success",
        "phase": request.phase,
        "duration": request.duration,
        "message": f"Signal set to phase {request.phase} for {request.duration}s"
    }


@router.post("/decide")
async def get_signal_decision(request: SignalDecisionRequest) -> Dict:
    """
    Get RL agent's signal decision for given state
    
    Args:
        request: Current traffic state
        
    Returns:
        Recommended signal timing
    """
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    decision = await rl_service.decide_signal(
        current_vehicle_count=request.current_vehicle_count,
        predicted_vehicle_count=request.predicted_vehicle_count,
        queue_length=request.queue_length,
        current_signal_phase=request.current_signal_phase,
        emergency_detected=request.emergency_detected,
        emergency_lane=request.emergency_lane
    )
    
    return {
        "green_time": decision.green_time,
        "phase": decision.phase,
        "is_emergency_override": decision.is_emergency_override,
        "confidence": decision.confidence,
        "q_values": decision.q_values,
        "timestamp": decision.timestamp
    }


@router.get("/history")
async def get_signal_history(limit: int = 100) -> List[Dict]:
    """
    Get signal decision history
    
    Args:
        limit: Maximum number of decisions to return
        
    Returns:
        List of recent signal decisions
    """
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    history = rl_service.get_decision_history(limit)
    
    # Simplify for API response
    return [
        {
            "timestamp": h.get("timestamp"),
            "state": h.get("state"),
            "green_time": h.get("decision").green_time if h.get("decision") else None,
            "phase": h.get("decision").phase if h.get("decision") else None
        }
        for h in history
    ]


@router.get("/agent/stats")
async def get_agent_statistics() -> Dict:
    """
    Get RL agent statistics
    
    Returns training metrics and performance data.
    """
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    return rl_service.get_statistics()


@router.post("/agent/train/start")
async def start_training() -> Dict:
    """Start RL agent training mode"""
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    rl_service.start_training()
    
    return {"status": "training_started", "message": "Agent is now in training mode"}


@router.post("/agent/train/stop")
async def stop_training() -> Dict:
    """Stop RL agent training mode"""
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    rl_service.stop_training()
    
    return {"status": "training_stopped", "message": "Agent training mode disabled"}


@router.post("/agent/save")
async def save_agent(path: str = "data/models/rl_agent.pkl") -> Dict:
    """Save RL agent to file"""
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    try:
        rl_service.save_agent(path)
        return {"status": "saved", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/load")
async def load_agent(path: str) -> Dict:
    """Load RL agent from file"""
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    try:
        rl_service.load_agent(path)
        return {"status": "loaded", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
