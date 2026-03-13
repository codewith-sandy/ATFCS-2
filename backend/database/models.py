"""
Database Models
SQLAlchemy models for traffic management system
"""

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class TrafficFrame(Base):
    """
    Stores processed video frames with detection data
    """
    __tablename__ = 'traffic_frames'
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    frame_id = Column(Integer)
    
    # Aggregated metrics
    vehicle_count = Column(Integer, default=0)
    queue_length = Column(Integer, default=0)
    lane_density = Column(Float, default=0.0)
    
    # Emergency info
    emergency_detected = Column(Boolean, default=False)
    emergency_type = Column(String(50), nullable=True)
    
    # Processing info
    processing_time = Column(Float)
    
    # Relationships
    detections = relationship("VehicleDetection", back_populates="frame")


class VehicleDetection(Base):
    """
    Individual vehicle detections within frames
    """
    __tablename__ = 'vehicle_detections'
    
    id = Column(Integer, primary_key=True, index=True)
    frame_id = Column(Integer, ForeignKey('traffic_frames.id'))
    
    # Detection data
    class_id = Column(Integer)
    class_name = Column(String(50))
    confidence = Column(Float)
    
    # Bounding box
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)
    
    # Lane assignment
    lane_id = Column(Integer, nullable=True)
    
    # Emergency flag
    is_emergency = Column(Boolean, default=False)
    
    # Relationships
    frame = relationship("TrafficFrame", back_populates="detections")


class VehicleCount(Base):
    """
    Time series of vehicle counts for analytics
    """
    __tablename__ = 'vehicle_counts'
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Per-lane counts
    lane_0_count = Column(Integer, default=0)
    lane_1_count = Column(Integer, default=0)
    lane_2_count = Column(Integer, default=0)
    lane_3_count = Column(Integer, default=0)
    
    # Aggregated
    total_count = Column(Integer, default=0)
    total_queue = Column(Integer, default=0)
    average_density = Column(Float, default=0.0)


class Prediction(Base):
    """
    Traffic predictions from LSTM model
    """
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Prediction data
    predicted_vehicle_count = Column(Float)
    actual_vehicle_count = Column(Float, nullable=True)  # Filled in later
    confidence = Column(Float)
    trend = Column(String(20))
    
    # Sequence info
    sequence_length = Column(Integer)
    
    # Model info
    model_version = Column(String(20), default='1.0')


class SignalDecision(Base):
    """
    Signal timing decisions from RL agent
    """
    __tablename__ = 'signal_decisions'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    intersection_id = Column(String(50), default='main', index=True)
    
    # State at decision time
    vehicle_count = Column(Integer)
    predicted_count = Column(Float)
    queue_length = Column(Integer)
    previous_phase = Column(Integer)
    
    # Decision
    new_phase = Column(Integer)
    green_time = Column(Integer)
    
    # Decision type
    is_emergency_override = Column(Boolean, default=False)
    emergency_lane = Column(Integer, nullable=True)
    
    # RL metrics
    q_values = Column(JSON, nullable=True)
    epsilon = Column(Float)
    confidence = Column(Float)
    
    # Outcome (filled in later)
    resulting_queue = Column(Integer, nullable=True)
    resulting_wait_time = Column(Float, nullable=True)
    reward = Column(Float, nullable=True)


class SimulationResult(Base):
    """
    Results from SUMO simulation runs
    """
    __tablename__ = 'simulation_results'
    
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String(50), unique=True, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    
    # Configuration
    config_file = Column(String(200))
    duration_seconds = Column(Integer)
    vehicles_per_hour = Column(Integer)
    
    # Results
    total_vehicles = Column(Integer)
    total_throughput = Column(Integer)
    average_waiting_time = Column(Float)
    average_queue_length = Column(Float)
    average_speed = Column(Float)
    emergency_response_time = Column(Float, nullable=True)
    
    # RL metrics
    total_episodes = Column(Integer)
    final_epsilon = Column(Float)
    average_reward = Column(Float)
    
    # Comparison to baseline
    waiting_time_improvement = Column(Float, nullable=True)
    queue_length_improvement = Column(Float, nullable=True)
    throughput_improvement = Column(Float, nullable=True)


class SystemMetrics(Base):
    """
    System performance metrics over time
    """
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Performance metrics
    avg_waiting_time = Column(Float)
    avg_queue_length = Column(Float)
    throughput = Column(Integer)
    emergency_response_time = Column(Float, nullable=True)
    
    # System health
    detection_service_ok = Column(Boolean)
    prediction_service_ok = Column(Boolean)
    rl_service_ok = Column(Boolean)
    
    # Load metrics
    frames_processed = Column(Integer)
    predictions_made = Column(Integer)
    signals_optimized = Column(Integer)


class EmergencyEvent(Base):
    """
    Emergency vehicle events
    """
    __tablename__ = 'emergency_events'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Event details
    emergency_type = Column(String(50))
    lane_detected = Column(Integer)
    
    # Response
    override_triggered = Column(Boolean)
    response_time = Column(Float, nullable=True)  # Time to green signal
    
    # Outcome
    cleared_timestamp = Column(DateTime, nullable=True)
    total_clearance_time = Column(Float, nullable=True)


class Dataset(Base):
    """
    Uploaded datasets for model training
    """
    __tablename__ = 'datasets'
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String(50), unique=True, index=True)
    name = Column(String(200))
    dataset_type = Column(String(50))  # 'video', 'traffic_counts', 'prediction_logs'
    file_path = Column(String(500))
    size_bytes = Column(Integer)
    num_samples = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed = Column(Boolean, default=False)
    features = Column(JSON, nullable=True)
    description = Column(String(1000), nullable=True)


class TrainingJob(Base):
    """
    Model training jobs
    """
    __tablename__ = 'training_jobs'
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, index=True)
    model_type = Column(String(20))  # 'yolo', 'lstm', 'rl'
    dataset_id = Column(String(50), ForeignKey('datasets.dataset_id'))
    status = Column(String(20))  # 'pending', 'training', 'completed', 'failed'
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    progress = Column(Float, default=0.0)
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer)
    current_loss = Column(Float, nullable=True)
    best_loss = Column(Float, nullable=True)
    
    config = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    error_message = Column(String(1000), nullable=True)
    model_path = Column(String(500), nullable=True)


class ModelVersion(Base):
    """
    Trained model versions
    """
    __tablename__ = 'model_versions'
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(String(50), unique=True, index=True)
    model_type = Column(String(20))
    version = Column(String(20))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    training_job_id = Column(String(50), nullable=True)
    
    metrics = Column(JSON, nullable=True)
    file_path = Column(String(500))
    is_active = Column(Boolean, default=False)
    description = Column(String(1000), nullable=True)


class CameraConfig(Base):
    """
    Camera configurations
    """
    __tablename__ = 'camera_configs'
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(50), unique=True, index=True)
    lane_id = Column(Integer)
    name = Column(String(200))
    source = Column(String(500))  # RTSP URL, file path, or device index
    resolution_width = Column(Integer, default=640)
    resolution_height = Column(Integer, default=480)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Intersection(Base):
    """
    Intersection configurations for multi-intersection support
    """
    __tablename__ = 'intersections'
    
    id = Column(Integer, primary_key=True, index=True)
    intersection_id = Column(String(50), unique=True, index=True)
    name = Column(String(200))
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    num_lanes = Column(Integer, default=4)
    created_at = Column(DateTime, default=datetime.utcnow)
    config = Column(JSON, nullable=True)
