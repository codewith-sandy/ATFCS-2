"""
FastAPI Backend Main Application
Adaptive Traffic Flow Management System
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

# Suppress socket.send() exceptions from uvicorn (benign when clients disconnect)
class SocketExceptionFilter(logging.Filter):
    def filter(self, record):
        return "socket.send()" not in record.getMessage()

# Apply filter to uvicorn error logger
logging.getLogger("uvicorn.error").addFilter(SocketExceptionFilter())

# Import routers
from api.routes import traffic, video, prediction, signals, analytics
from api.routes import camera, dataset, training

# Import services
from services.detection import DetectionService
from services.prediction import PredictionService
from services.rl_agent import RLAgentService
from services.traffic_controller import TrafficControllerService
from services.camera_stream_service import get_camera_service
from services.model_training_service import get_training_service

# Import database
from database.connection import init_db, close_db


# Global service instances
detection_service: DetectionService = None
prediction_service: PredictionService = None
rl_service: RLAgentService = None
controller_service: TrafficControllerService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global detection_service, prediction_service, rl_service, controller_service
    
    logger.info("Starting Adaptive Traffic Flow Management System...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
    
    # Initialize services
    try:
        detection_service = DetectionService()
        logger.info("Detection service initialized")
    except Exception as e:
        logger.warning(f"Detection service initialization failed: {e}")
        detection_service = None
    
    try:
        prediction_service = PredictionService()
        logger.info("Prediction service initialized")
    except Exception as e:
        logger.warning(f"Prediction service initialization failed: {e}")
        prediction_service = None
    
    try:
        rl_service = RLAgentService()
        logger.info("RL agent service initialized")
    except Exception as e:
        logger.warning(f"RL agent service initialization failed: {e}")
        rl_service = None
    
    try:
        controller_service = TrafficControllerService(
            detection_service=detection_service,
            prediction_service=prediction_service,
            rl_service=rl_service
        )
        logger.info("Traffic controller service initialized")
    except Exception as e:
        logger.warning(f"Traffic controller initialization failed: {e}")
        controller_service = None
    
    logger.info("All services initialized. System ready.")
    
    yield
    
    # Cleanup
    logger.info("Shutting down services...")
    
    if controller_service:
        controller_service.stop()
    
    try:
        await close_db()
    except:
        pass
    
    logger.info("Shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title="Adaptive Traffic Flow Management System",
    description="""
    AI-powered adaptive traffic signal control system using:
    - YOLOv8 for real-time vehicle detection
    - LSTM for traffic prediction
    - Q-Learning for signal optimization
    - SUMO for traffic simulation
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(traffic.router, prefix="/traffic", tags=["Traffic"])
app.include_router(video.router, prefix="/video", tags=["Video"])
app.include_router(prediction.router, prefix="/prediction", tags=["Prediction"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(camera.router, prefix="/camera", tags=["Camera"])
app.include_router(dataset.router, prefix="/dataset", tags=["Dataset"])
app.include_router(training.router, prefix="/model", tags=["Model Training"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "services": {
            "detection": detection_service is not None,
            "prediction": prediction_service is not None,
            "rl_agent": rl_service is not None,
            "controller": controller_service is not None
        }
    }


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Adaptive Traffic Flow Management System",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "traffic": "/traffic/live",
            "video": "/video/upload",
            "prediction": "/prediction",
            "signals": "/signals",
            "analytics": "/analytics"
        }
    }


# Dependency injection functions
def get_detection_service() -> DetectionService:
    """Get detection service instance"""
    if detection_service is None:
        raise HTTPException(status_code=503, detail="Detection service not available")
    return detection_service


def get_prediction_service() -> PredictionService:
    """Get prediction service instance"""
    if prediction_service is None:
        raise HTTPException(status_code=503, detail="Prediction service not available")
    return prediction_service


def get_rl_service() -> RLAgentService:
    """Get RL agent service instance"""
    if rl_service is None:
        raise HTTPException(status_code=503, detail="RL agent service not available")
    return rl_service


def get_controller_service() -> TrafficControllerService:
    """Get traffic controller service instance"""
    if controller_service is None:
        raise HTTPException(status_code=503, detail="Traffic controller not available")
    return controller_service


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
