"""
Analytics API Routes
Endpoints for traffic analytics and reporting
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import time

router = APIRouter()


class AnalyticsTimeRange(BaseModel):
    """Time range for analytics queries"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_hours: Optional[int] = 24


class PerformanceMetrics(BaseModel):
    """Performance metrics model"""
    waiting_time_reduction: float
    queue_length_reduction: float
    throughput_improvement: float
    emergency_response_improvement: float


@router.get("")
async def get_analytics() -> Dict:
    """
    Get comprehensive traffic analytics
    
    Returns aggregated analytics including:
    - Traffic patterns
    - Performance metrics
    - System statistics
    """
    from main import controller_service, detection_service, prediction_service, rl_service
    
    analytics = {
        "timestamp": time.time(),
        "traffic": {},
        "detection": {},
        "prediction": {},
        "rl_agent": {},
        "performance": {}
    }
    
    # Traffic analytics
    if controller_service:
        metrics = controller_service.get_metrics()
        analytics["traffic"] = {
            "avg_waiting_time": metrics.avg_waiting_time,
            "avg_queue_length": metrics.avg_queue_length,
            "throughput": metrics.throughput,
            "emergency_response_time": metrics.emergency_response_time,
            "vehicles_processed": metrics.vehicles_processed,
            "signals_optimized": metrics.signals_optimized
        }
    
    # Detection analytics
    if detection_service:
        analytics["detection"] = detection_service.get_statistics()
    
    # Prediction analytics
    if prediction_service:
        analytics["prediction"] = prediction_service.get_statistics()
    
    # RL agent analytics
    if rl_service:
        analytics["rl_agent"] = rl_service.get_statistics()
    
    # Performance improvements (compared to baseline)
    analytics["performance"] = calculate_performance_improvements(analytics)
    
    return analytics


def calculate_performance_improvements(analytics: Dict) -> Dict:
    """Calculate performance improvements compared to baseline"""
    # Baseline values (typical fixed-time signals)
    baseline = {
        "avg_waiting_time": 45.0,  # seconds
        "avg_queue_length": 12.0,  # vehicles
        "throughput": 100,  # vehicles per hour
        "emergency_response": 60.0  # seconds
    }
    
    traffic = analytics.get("traffic", {})
    
    # Calculate improvements
    waiting_reduction = 0.0
    queue_reduction = 0.0
    throughput_improvement = 0.0
    emergency_improvement = 0.0
    
    if traffic.get("avg_waiting_time"):
        waiting_reduction = (baseline["avg_waiting_time"] - traffic["avg_waiting_time"]) / baseline["avg_waiting_time"] * 100
    
    if traffic.get("avg_queue_length"):
        queue_reduction = (baseline["avg_queue_length"] - traffic["avg_queue_length"]) / baseline["avg_queue_length"] * 100
    
    if traffic.get("throughput"):
        throughput_improvement = (traffic["throughput"] - baseline["throughput"]) / baseline["throughput"] * 100
    
    if traffic.get("emergency_response_time"):
        emergency_improvement = (baseline["emergency_response"] - traffic["emergency_response_time"]) / baseline["emergency_response"] * 100
    
    return {
        "waiting_time_reduction_percent": max(0, waiting_reduction),
        "queue_length_reduction_percent": max(0, queue_reduction),
        "throughput_improvement_percent": max(0, throughput_improvement),
        "emergency_response_improvement_percent": max(0, emergency_improvement),
        "targets": {
            "waiting_time": "32-45% reduction",
            "queue_length": "28-40% reduction",
            "throughput": "19% improvement",
            "emergency_response": "40% faster"
        }
    }


@router.get("/traffic/hourly")
async def get_hourly_traffic() -> List[Dict]:
    """
    Get hourly traffic patterns
    
    Returns traffic data aggregated by hour for the last 24 hours.
    """
    from main import controller_service
    
    # Generate sample hourly data (in production, would query database)
    hours = []
    current_hour = datetime.now().hour
    
    for i in range(24):
        hour = (current_hour - 23 + i) % 24
        
        # Simulate traffic patterns
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            # Rush hour
            base_count = 45
        elif 22 <= hour or hour <= 5:
            # Night
            base_count = 10
        else:
            # Normal
            base_count = 25
        
        hours.append({
            "hour": hour,
            "avg_vehicle_count": base_count + (i % 5),
            "avg_queue_length": base_count // 3,
            "avg_waiting_time": base_count * 1.2
        })
    
    return hours


@router.get("/traffic/daily")
async def get_daily_traffic() -> List[Dict]:
    """
    Get daily traffic patterns
    
    Returns traffic data aggregated by day for the last 30 days.
    """
    days = []
    
    for i in range(30):
        date = datetime.now() - timedelta(days=29-i)
        
        # Simulate daily patterns
        if date.weekday() < 5:
            # Weekday
            base_count = 35
        else:
            # Weekend
            base_count = 20
        
        days.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_name": date.strftime("%A"),
            "total_vehicles": base_count * 24 * 60 // 10,
            "avg_vehicle_count": base_count,
            "peak_hour_count": base_count * 2
        })
    
    return days


@router.get("/detection/summary")
async def get_detection_summary() -> Dict:
    """
    Get detection statistics summary
    
    Returns breakdown of detected vehicle types.
    """
    from main import detection_service
    
    if detection_service is None:
        raise HTTPException(status_code=503, detail="Detection service not available")
    
    stats = detection_service.get_statistics()
    
    # Simulated vehicle type breakdown
    total = stats.get("total_vehicles_detected", 0)
    
    return {
        "total_detections": stats.get("total_detections", 0),
        "total_vehicles": total,
        "vehicle_types": {
            "car": int(total * 0.65),
            "motorcycle": int(total * 0.15),
            "bus": int(total * 0.05),
            "truck": int(total * 0.08),
            "auto_rickshaw": int(total * 0.07)
        },
        "emergency_vehicles": stats.get("emergency_count", 0),
        "model_info": {
            "model": "YOLOv8n",
            "confidence_threshold": stats.get("confidence_threshold", 0.25)
        }
    }


@router.get("/prediction/accuracy")
async def get_prediction_accuracy() -> Dict:
    """
    Get prediction model accuracy metrics
    """
    from main import prediction_service
    
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    
    stats = prediction_service.get_statistics()
    history = prediction_service.get_prediction_history(100)
    
    # Calculate accuracy metrics
    if len(history) > 1:
        errors = []
        for i in range(1, len(history)):
            actual = history[i].get('actual', 0)
            predicted = history[i-1].get('predicted', 0)
            if actual > 0:
                errors.append(abs(actual - predicted) / actual)
        
        mae = sum(abs(h.get('actual', 0) - history[max(0, i-1)].get('predicted', 0)) 
                 for i, h in enumerate(history[1:])) / max(1, len(history)-1)
    else:
        errors = []
        mae = 0
    
    return {
        "total_predictions": stats.get("total_predictions", 0),
        "recent_accuracy": stats.get("recent_accuracy", 0),
        "mean_absolute_error": mae,
        "model_info": {
            "architecture": "LSTM (64) -> LSTM (32) -> Dense",
            "sequence_length": stats.get("sequence_length", 15)
        }
    }


@router.get("/rl/training")
async def get_rl_training_metrics() -> Dict:
    """
    Get RL agent training metrics
    """
    from main import rl_service
    
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent not available")
    
    stats = rl_service.get_statistics()
    
    return {
        "total_episodes": stats.get("total_episodes", 0),
        "total_steps": stats.get("total_steps", 0),
        "current_epsilon": stats.get("current_epsilon", 1.0),
        "q_table_size": stats.get("q_table_size", 0),
        "recent_avg_reward": stats.get("recent_avg_reward", 0),
        "is_training": stats.get("is_training", False),
        "hyperparameters": {
            "learning_rate": 0.1,
            "discount_factor": 0.9,
            "epsilon_decay": 0.995
        }
    }


@router.get("/system")
async def get_system_analytics() -> Dict:
    """
    Get overall system analytics and health
    """
    from main import detection_service, prediction_service, rl_service, controller_service
    
    return {
        "status": "operational",
        "uptime": time.time(),  # Would track actual uptime
        "services": {
            "detection": {
                "status": "healthy" if detection_service else "unavailable",
                "ready": detection_service.is_ready if detection_service else False
            },
            "prediction": {
                "status": "healthy" if prediction_service else "unavailable",
                "ready": prediction_service.is_ready if prediction_service else False
            },
            "rl_agent": {
                "status": "healthy" if rl_service else "unavailable",
                "ready": rl_service.is_ready if rl_service else False
            },
            "controller": {
                "status": "healthy" if controller_service else "unavailable",
                "running": controller_service.is_running if controller_service else False
            }
        },
        "performance_targets": {
            "waiting_time_reduction": "32-45%",
            "queue_length_reduction": "28-40%",
            "throughput_improvement": "19%",
            "emergency_response_improvement": "40%"
        }
    }
