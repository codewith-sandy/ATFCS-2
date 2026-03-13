# Adaptive Traffic Flow Management System

An AI-powered adaptive traffic signal control system using computer vision, time-series prediction, and reinforcement learning.

## 🎯 System Overview

This system combines:

- **YOLOv8** → Real-time vehicle detection
- **LSTM** → Short-term traffic prediction
- **Q-Learning RL Agent** → Adaptive signal optimization
- **SUMO Simulation** → Traffic environment testing
- **FastAPI Backend** → RESTful API services
- **React Dashboard** → Real-time analytics visualization

## 🏗️ Architecture

```
Camera Feed
     ↓
Frame Processing (OpenCV)
     ↓
YOLOv8 Vehicle Detection
     ↓
Vehicle Count + Queue Length
     ↓
Traffic State Builder
     ↓
LSTM Prediction Model
     ↓
Predicted Traffic Density
     ↓
RL State Representation
     ↓
Q-Learning Agent
     ↓
Optimal Signal Phase Decision
     ↓
Traffic Signal Controller
     ↓
SUMO Simulation / Hardware Signals
     ↓
Dashboard Visualization
```

## 📁 Project Structure

```
adaptive-traffic-ai/
│
├── backend/
│   ├── main.py                 # FastAPI application entry
│   ├── api/                    # API routes
│   │   ├── routes/
│   │   │   ├── traffic.py      # Traffic data endpoints
│   │   │   ├── video.py        # Video upload endpoints
│   │   │   ├── prediction.py   # Prediction endpoints
│   │   │   ├── signals.py      # Signal control endpoints
│   │   │   ├── analytics.py    # Analytics endpoints
│   │   │   ├── camera.py       # Camera streaming endpoints (NEW)
│   │   │   ├── dataset.py      # Dataset management endpoints (NEW)
│   │   │   └── training.py     # Model training endpoints (NEW)
│   ├── services/               # Business logic
│   │   ├── detection.py
│   │   ├── prediction.py
│   │   ├── rl_agent.py
│   │   ├── traffic_controller.py
│   │   ├── camera_stream_service.py    # Multi-camera streaming (NEW)
│   │   └── model_training_service.py   # Model training pipeline (NEW)
│   ├── database/               # Database models & connection
│   │   ├── models.py           # SQLAlchemy models (extended)
│   │   ├── connection.py
│   │   └── crud.py
│   └── utils/                  # Utility functions
│
├── ai_models/
│   ├── yolo_detector.py        # YOLOv8 vehicle detection
│   ├── lstm_model.py           # LSTM traffic prediction
│   └── q_learning_agent.py     # Q-Learning RL agent
│
├── simulation/
│   ├── sumo_environment.py     # SUMO integration
│   └── configs/                # SUMO network files
│
├── dashboard/                  # React frontend (extended)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.js
│   │   │   ├── Analytics.js
│   │   │   ├── LiveTrafficFeed.js      # Multi-lane camera grid (NEW)
│   │   │   ├── PredictionVisualization.js  # AI predictions (NEW)
│   │   │   ├── DatasetUpload.js        # Dataset & training UI (NEW)
│   │   │   ├── AdminPanel.js           # Admin dashboard (NEW)
│   │   │   ├── Simulation.js
│   │   │   └── Settings.js
│   │   ├── services/
│   │   │   └── api.js          # API services (extended)
│   │   └── App.js              # Main app with new routes
│   ├── public/
│   └── package.json
│
├── data_pipeline/
│   ├── video_processor.py      # Video frame extraction
│   └── traffic_state_builder.py
│
├── training/
│   ├── train_lstm.py
│   ├── train_rl_agent.py
│   └── generate_training_data.py
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.dashboard
│   └── nginx.conf
│
├── data/                       # Data storage
│   ├── videos/
│   ├── datasets/               # Uploaded datasets (NEW)
│   └── logs/
│
├── models/                     # Trained models
│   ├── yolo_v1.pt
│   ├── lstm_v1.pt
│   └── rl_agent_v1.pkl
│
├── logs/                       # System logs
│   └── training/               # Training logs (NEW)
│
├── docker-compose.yml          # Docker orchestration (updated)
├── requirements.txt
└── README.md
```

│ └── logs/
│
├── requirements.txt
└── README.md

````

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- SUMO (Simulation of Urban Mobility)
- PostgreSQL

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/adaptive-traffic-ai.git
cd adaptive-traffic-ai
````

2. **Set up Python environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

3. **Set up the database**

```bash
# Create PostgreSQL database
createdb traffic_db

# Run migrations
cd backend
alembic upgrade head
```

4. **Install SUMO**

```bash
# Ubuntu/Debian
sudo apt-get install sumo sumo-tools sumo-doc

# Windows: Download from https://sumo.dlr.de/docs/Downloads.php
```

5. **Start the backend**

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. **Start the dashboard**

```bash
cd dashboard
npm install
npm start
```

### Docker Deployment

```bash
docker-compose -f docker/docker-compose.yml up --build
```

## 📊 API Endpoints

### Core Traffic APIs

| Method | Endpoint        | Description                         |
| ------ | --------------- | ----------------------------------- |
| POST   | `/video/upload` | Upload traffic video for processing |
| GET    | `/traffic/live` | Get live traffic data               |
| GET    | `/prediction`   | Get traffic predictions             |
| GET    | `/signals`      | Get current signal states           |
| GET    | `/analytics`    | Get traffic analytics               |

### Camera Streaming APIs

| Method | Endpoint                        | Description                        |
| ------ | ------------------------------- | ---------------------------------- |
| GET    | `/camera/lane/{lane_id}/stream` | MJPEG stream with YOLO annotations |
| GET    | `/camera/lanes/metrics`         | Get all lane metrics               |
| GET    | `/camera/cameras`               | List all cameras                   |
| POST   | `/camera/cameras`               | Add new camera                     |
| DELETE | `/camera/cameras/{id}`          | Remove camera                      |

### Dataset & Training APIs

| Method | Endpoint                        | Description             |
| ------ | ------------------------------- | ----------------------- |
| POST   | `/dataset/upload`               | Upload training dataset |
| GET    | `/dataset/`                     | List all datasets       |
| DELETE | `/dataset/{id}`                 | Delete dataset          |
| POST   | `/model/train/lstm`             | Start LSTM training     |
| POST   | `/model/train/yolo`             | Start YOLO training     |
| POST   | `/model/train/rl`               | Start RL training       |
| GET    | `/model/training/status`        | Get training status     |
| GET    | `/model/versions`               | List model versions     |
| POST   | `/model/versions/{id}/activate` | Activate model version  |

## 🎬 Advanced Features

### Live Multi-Lane Traffic Camera Feed

- 4+ lane camera support with RTSP/WebRTC streaming
- Real-time YOLO detection overlay with bounding boxes
- Vehicle count, queue length, and congestion level per lane
- Signal state indicator on each feed
- Emergency vehicle detection alerts

### AI Prediction Visualization

- Time-series prediction vs actual charts
- Traffic heatmap showing congestion patterns
- Lane load prediction bar charts
- Congestion forecast animation
- AI decision explanation panel

### Dataset Upload & Model Retraining

- Upload traffic videos (.mp4, .avi, .mov)
- Upload traffic counts (.csv, .json)
- Upload prediction logs for evaluation
- Real-time preprocessing and feature extraction

### Model Training Pipeline

- LSTM traffic prediction training
- YOLO vehicle detection fine-tuning
- RL agent training with custom rewards
- Model versioning and activation
- Training progress monitoring

### Admin Panel

- Camera management (add/remove/configure)
- Model version management
- System logs viewer
- AI decision history
- Alert configuration
- Multi-intersection support

## 🧠 AI Models

### YOLOv8 Vehicle Detection

- Detects: car, motorcycle, bus, truck, auto-rickshaw, ambulance, police, fire_truck
- Confidence threshold: 0.25
- Input resolution: 640×640

### LSTM Traffic Prediction

- Architecture: LSTM(64) → LSTM(32) → Dense
- Sequence window: 10-20 timesteps
- Predicts: Next timestep vehicle count

### Q-Learning RL Agent

- State: {current_count, predicted_count, queue_length, signal_phase}
- Actions: Green time = {10, 20, 30, 40} seconds
- Reward: -(α₁ × queue_length + α₂ × waiting_time)

## 🚨 Emergency Vehicle Priority

The system automatically detects emergency vehicles (ambulance, police, fire truck) and overrides normal signal timing to provide immediate green signals.

## 📈 Performance Targets

- 32-45% reduction in waiting time
- 28-40% reduction in queue length
- 19% improvement in throughput
- 40% faster emergency response

## Starting the Adaptive Traffic Management Dashboard

To start the dashboard, use the provided batch script:

1. Open a terminal (Command Prompt) in the project root directory.
2. Run the following command:

   ```
   start_dashboard.bat
   ```

This script will:

- Display a message indicating the dashboard is starting.
- Change the directory to the `dashboard` folder.
- Start the dashboard using `npm start`.
- Pause so you can see any output or errors.

**Note:**
Make sure you have Node.js and npm installed, and that all dependencies in the `dashboard` folder are installed (`npm install`).

## �️ Dashboard Views

### Main Dashboard

- Real-time traffic metrics overview
- 4-lane traffic light visualization
- Vehicle count charts
- System health status

### Live Traffic Feed (`/live`)

- Grid view of all 4 camera feeds
- YOLO detection overlays with bounding boxes
- Per-lane metrics (vehicle count, queue, congestion)
- Single camera expanded view option

### AI Predictions (`/predictions`)

- Prediction vs Actual time-series charts
- Lane load prediction bar charts
- Traffic heatmap (hourly/weekly patterns)
- Congestion forecast animation
- AI decision explanation panel

### Training (`/training`)

- Dataset upload interface
- Dataset management (view, delete, preview)
- Model training configuration
- Training job monitoring
- Model version management

### Admin Panel (`/admin`)

- Camera configuration
- Model activation
- System logs
- AI decision history
- Alert settings

## �🔧 Configuration

Edit `config/settings.py` to customize:

- Detection confidence thresholds
- LSTM model parameters
- RL hyperparameters
- Signal timing ranges
- Database connection

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines.
