"""
CRUD Operations
Database create, read, update, delete operations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from .models import (
    TrafficFrame, 
    VehicleDetection, 
    VehicleCount,
    Prediction, 
    SignalDecision, 
    SimulationResult,
    SystemMetrics,
    EmergencyEvent
)


# ==================== Traffic Frames ====================

async def create_traffic_frame(
    db: AsyncSession,
    camera_id: str,
    vehicle_count: int,
    queue_length: int,
    lane_density: float,
    emergency_detected: bool = False,
    emergency_type: str = None,
    processing_time: float = None
) -> TrafficFrame:
    """Create a new traffic frame record"""
    frame = TrafficFrame(
        camera_id=camera_id,
        vehicle_count=vehicle_count,
        queue_length=queue_length,
        lane_density=lane_density,
        emergency_detected=emergency_detected,
        emergency_type=emergency_type,
        processing_time=processing_time
    )
    db.add(frame)
    await db.commit()
    await db.refresh(frame)
    return frame


async def get_traffic_frames(
    db: AsyncSession,
    camera_id: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = 100
) -> List[TrafficFrame]:
    """Get traffic frames with optional filters"""
    query = select(TrafficFrame)
    
    conditions = []
    if camera_id:
        conditions.append(TrafficFrame.camera_id == camera_id)
    if start_time:
        conditions.append(TrafficFrame.timestamp >= start_time)
    if end_time:
        conditions.append(TrafficFrame.timestamp <= end_time)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(TrafficFrame.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


# ==================== Vehicle Detections ====================

async def create_vehicle_detection(
    db: AsyncSession,
    frame_id: int,
    class_id: int,
    class_name: str,
    confidence: float,
    bbox: List[float],
    lane_id: int = None,
    is_emergency: bool = False
) -> VehicleDetection:
    """Create a vehicle detection record"""
    detection = VehicleDetection(
        frame_id=frame_id,
        class_id=class_id,
        class_name=class_name,
        confidence=confidence,
        bbox_x1=bbox[0],
        bbox_y1=bbox[1],
        bbox_x2=bbox[2],
        bbox_y2=bbox[3],
        lane_id=lane_id,
        is_emergency=is_emergency
    )
    db.add(detection)
    await db.commit()
    return detection


async def get_vehicle_type_counts(
    db: AsyncSession,
    start_time: datetime = None,
    end_time: datetime = None
) -> Dict[str, int]:
    """Get counts of each vehicle type"""
    query = select(
        VehicleDetection.class_name,
        func.count(VehicleDetection.id).label('count')
    ).group_by(VehicleDetection.class_name)
    
    if start_time:
        query = query.where(VehicleDetection.frame.has(
            TrafficFrame.timestamp >= start_time
        ))
    
    result = await db.execute(query)
    return {row.class_name: row.count for row in result}


# ==================== Vehicle Counts ====================

async def save_vehicle_count(
    db: AsyncSession,
    camera_id: str,
    lane_counts: List[int],
    total_count: int,
    total_queue: int,
    average_density: float
) -> VehicleCount:
    """Save vehicle count time series data"""
    count = VehicleCount(
        camera_id=camera_id,
        lane_0_count=lane_counts[0] if len(lane_counts) > 0 else 0,
        lane_1_count=lane_counts[1] if len(lane_counts) > 1 else 0,
        lane_2_count=lane_counts[2] if len(lane_counts) > 2 else 0,
        lane_3_count=lane_counts[3] if len(lane_counts) > 3 else 0,
        total_count=total_count,
        total_queue=total_queue,
        average_density=average_density
    )
    db.add(count)
    await db.commit()
    return count


async def get_vehicle_count_history(
    db: AsyncSession,
    camera_id: str = None,
    hours: int = 24,
    limit: int = 1000
) -> List[VehicleCount]:
    """Get vehicle count history"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(VehicleCount).where(
        VehicleCount.timestamp >= cutoff
    )
    
    if camera_id:
        query = query.where(VehicleCount.camera_id == camera_id)
    
    query = query.order_by(VehicleCount.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


# ==================== Predictions ====================

async def save_prediction(
    db: AsyncSession,
    predicted_count: float,
    confidence: float,
    trend: str,
    sequence_length: int,
    actual_count: float = None
) -> Prediction:
    """Save a prediction record"""
    prediction = Prediction(
        predicted_vehicle_count=predicted_count,
        actual_vehicle_count=actual_count,
        confidence=confidence,
        trend=trend,
        sequence_length=sequence_length
    )
    db.add(prediction)
    await db.commit()
    return prediction


async def update_prediction_actual(
    db: AsyncSession,
    prediction_id: int,
    actual_count: float
):
    """Update prediction with actual value"""
    query = select(Prediction).where(Prediction.id == prediction_id)
    result = await db.execute(query)
    prediction = result.scalar_one_or_none()
    
    if prediction:
        prediction.actual_vehicle_count = actual_count
        await db.commit()


async def get_prediction_accuracy(
    db: AsyncSession,
    hours: int = 24
) -> Dict:
    """Calculate prediction accuracy metrics"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(Prediction).where(
        and_(
            Prediction.timestamp >= cutoff,
            Prediction.actual_vehicle_count.isnot(None)
        )
    )
    
    result = await db.execute(query)
    predictions = result.scalars().all()
    
    if not predictions:
        return {
            'count': 0,
            'mae': 0,
            'mape': 0
        }
    
    errors = []
    percentage_errors = []
    
    for p in predictions:
        error = abs(p.predicted_vehicle_count - p.actual_vehicle_count)
        errors.append(error)
        if p.actual_vehicle_count > 0:
            percentage_errors.append(error / p.actual_vehicle_count)
    
    return {
        'count': len(predictions),
        'mae': sum(errors) / len(errors),
        'mape': sum(percentage_errors) / len(percentage_errors) if percentage_errors else 0
    }


# ==================== Signal Decisions ====================

async def save_signal_decision(
    db: AsyncSession,
    vehicle_count: int,
    predicted_count: float,
    queue_length: int,
    previous_phase: int,
    new_phase: int,
    green_time: int,
    is_emergency: bool = False,
    emergency_lane: int = None,
    q_values: Dict = None,
    epsilon: float = None,
    confidence: float = None
) -> SignalDecision:
    """Save a signal decision record"""
    decision = SignalDecision(
        vehicle_count=vehicle_count,
        predicted_count=predicted_count,
        queue_length=queue_length,
        previous_phase=previous_phase,
        new_phase=new_phase,
        green_time=green_time,
        is_emergency_override=is_emergency,
        emergency_lane=emergency_lane,
        q_values=q_values,
        epsilon=epsilon,
        confidence=confidence
    )
    db.add(decision)
    await db.commit()
    return decision


async def update_signal_outcome(
    db: AsyncSession,
    decision_id: int,
    resulting_queue: int,
    resulting_wait_time: float,
    reward: float
):
    """Update signal decision with outcome"""
    query = select(SignalDecision).where(SignalDecision.id == decision_id)
    result = await db.execute(query)
    decision = result.scalar_one_or_none()
    
    if decision:
        decision.resulting_queue = resulting_queue
        decision.resulting_wait_time = resulting_wait_time
        decision.reward = reward
        await db.commit()


# ==================== Simulation Results ====================

async def save_simulation_result(
    db: AsyncSession,
    simulation_id: str,
    config_file: str,
    duration: int,
    vehicles_per_hour: int,
    metrics: Dict
) -> SimulationResult:
    """Save simulation result"""
    result = SimulationResult(
        simulation_id=simulation_id,
        config_file=config_file,
        duration_seconds=duration,
        vehicles_per_hour=vehicles_per_hour,
        total_vehicles=metrics.get('total_vehicles', 0),
        total_throughput=metrics.get('throughput', 0),
        average_waiting_time=metrics.get('avg_waiting_time', 0),
        average_queue_length=metrics.get('avg_queue_length', 0),
        average_speed=metrics.get('avg_speed', 0),
        total_episodes=metrics.get('episodes', 0),
        final_epsilon=metrics.get('epsilon', 0),
        average_reward=metrics.get('avg_reward', 0)
    )
    db.add(result)
    await db.commit()
    return result


# ==================== System Metrics ====================

async def save_system_metrics(
    db: AsyncSession,
    avg_waiting_time: float,
    avg_queue_length: float,
    throughput: int,
    detection_ok: bool,
    prediction_ok: bool,
    rl_ok: bool,
    frames_processed: int,
    predictions_made: int,
    signals_optimized: int
) -> SystemMetrics:
    """Save system metrics snapshot"""
    metrics = SystemMetrics(
        avg_waiting_time=avg_waiting_time,
        avg_queue_length=avg_queue_length,
        throughput=throughput,
        detection_service_ok=detection_ok,
        prediction_service_ok=prediction_ok,
        rl_service_ok=rl_ok,
        frames_processed=frames_processed,
        predictions_made=predictions_made,
        signals_optimized=signals_optimized
    )
    db.add(metrics)
    await db.commit()
    return metrics


# ==================== Emergency Events ====================

async def log_emergency_event(
    db: AsyncSession,
    emergency_type: str,
    lane_detected: int,
    override_triggered: bool
) -> EmergencyEvent:
    """Log an emergency vehicle event"""
    event = EmergencyEvent(
        emergency_type=emergency_type,
        lane_detected=lane_detected,
        override_triggered=override_triggered
    )
    db.add(event)
    await db.commit()
    return event


async def update_emergency_cleared(
    db: AsyncSession,
    event_id: int,
    response_time: float,
    clearance_time: float
):
    """Update emergency event when cleared"""
    query = select(EmergencyEvent).where(EmergencyEvent.id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if event:
        event.response_time = response_time
        event.cleared_timestamp = datetime.utcnow()
        event.total_clearance_time = clearance_time
        await db.commit()


async def get_emergency_statistics(
    db: AsyncSession,
    hours: int = 24
) -> Dict:
    """Get emergency response statistics"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(EmergencyEvent).where(
        EmergencyEvent.timestamp >= cutoff
    )
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    if not events:
        return {
            'total_events': 0,
            'avg_response_time': 0,
            'avg_clearance_time': 0
        }
    
    response_times = [e.response_time for e in events if e.response_time]
    clearance_times = [e.total_clearance_time for e in events if e.total_clearance_time]
    
    return {
        'total_events': len(events),
        'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
        'avg_clearance_time': sum(clearance_times) / len(clearance_times) if clearance_times else 0,
        'by_type': {
            e.emergency_type: sum(1 for ev in events if ev.emergency_type == e.emergency_type)
            for e in events
        }
    }
