"""
Prediction API Routes
Endpoints for traffic prediction
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel

router = APIRouter()


class PredictionRequest(BaseModel):
    """Request model for prediction"""
    vehicle_count: int
    queue_length: int
    lane_density: float
    signal_phase: int


class SequencePredictionRequest(BaseModel):
    """Request model for sequence-based prediction"""
    sequence: List[Dict]


class PredictionResponse(BaseModel):
    """Prediction response model"""
    predicted_vehicle_count: float
    confidence: float
    trend: str
    prediction_horizon: str
    timestamp: float


@router.get("")
async def get_current_prediction() -> Dict:
    """
    Get the current traffic prediction
    
    Returns the latest prediction based on recent traffic data.
    """
    from main import prediction_service, controller_service
    
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    
    # Get current state from controller
    if controller_service:
        state = controller_service.get_current_state()
        if state:
            prediction = await prediction_service.predict(
                vehicle_count=state.vehicle_count,
                queue_length=state.queue_length,
                lane_density=state.queue_length / 10.0,
                signal_phase=state.current_phase
            )
            
            return {
                "predicted_vehicle_count": prediction.predicted_vehicle_count,
                "confidence": prediction.confidence,
                "trend": prediction.trend,
                "prediction_horizon": prediction.prediction_horizon,
                "timestamp": prediction.timestamp
            }
    
    return {
        "status": "no_data",
        "message": "No traffic data available for prediction"
    }


@router.post("/from_data")
async def predict_from_data(request: PredictionRequest) -> Dict:
    """
    Generate prediction from provided data
    
    Args:
        request: Current traffic state data
        
    Returns:
        Prediction for next timestep
    """
    from main import prediction_service
    
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    
    prediction = await prediction_service.predict(
        vehicle_count=request.vehicle_count,
        queue_length=request.queue_length,
        lane_density=request.lane_density,
        signal_phase=request.signal_phase
    )
    
    return {
        "predicted_vehicle_count": prediction.predicted_vehicle_count,
        "confidence": prediction.confidence,
        "trend": prediction.trend,
        "prediction_horizon": prediction.prediction_horizon,
        "timestamp": prediction.timestamp
    }


@router.post("/from_sequence")
async def predict_from_sequence(request: SequencePredictionRequest) -> Dict:
    """
    Generate prediction from a sequence of observations
    
    Args:
        request: Sequence of traffic observations
        
    Returns:
        Prediction for next timestep
    """
    from main import prediction_service
    
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    
    if len(request.sequence) < 5:
        raise HTTPException(
            status_code=400,
            detail="Sequence must have at least 5 observations"
        )
    
    prediction = await prediction_service.predict_from_sequence(request.sequence)
    
    return {
        "predicted_vehicle_count": prediction.predicted_vehicle_count,
        "confidence": prediction.confidence,
        "trend": prediction.trend,
        "prediction_horizon": prediction.prediction_horizon,
        "timestamp": prediction.timestamp
    }


@router.get("/history")
async def get_prediction_history(limit: int = 100) -> List[Dict]:
    """
    Get prediction history
    
    Args:
        limit: Maximum number of predictions to return
        
    Returns:
        List of recent predictions with actual values
    """
    from main import prediction_service
    
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    
    return prediction_service.get_prediction_history(limit)


@router.get("/statistics")
async def get_prediction_statistics() -> Dict:
    """
    Get prediction model statistics
    
    Returns model performance metrics including accuracy.
    """
    from main import prediction_service
    
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    
    return prediction_service.get_statistics()
