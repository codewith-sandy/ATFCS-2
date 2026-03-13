# Datasets Directory

This directory stores uploaded datasets for model training.

## Directory Structure

```
datasets/
├── datasets.json          # Metadata about uploaded datasets
├── {uuid}.csv             # Uploaded CSV files
├── {uuid}.json            # Uploaded JSON files
├── {uuid}.mp4             # Uploaded video files
└── {uuid}_cleaned.csv     # Preprocessed datasets
```

## Supported Dataset Types

### 1. Traffic Count Data (CSV/JSON)
Used for LSTM model training.

Example CSV format:
```csv
timestamp,vehicle_count,queue_length,lane_id,density
2024-01-01 10:00:00,14,6,1,0.35
2024-01-01 10:05:00,22,10,1,0.55
2024-01-01 10:10:00,18,8,1,0.45
```

### 2. Prediction Logs (CSV/JSON)
Used for model evaluation and retraining.

Example CSV format:
```csv
timestamp,predicted_count,actual_count,lane_id
2024-01-01 10:00:00,20,18,1
2024-01-01 10:05:00,25,23,1
```

### 3. Traffic Videos (MP4/AVI/MOV)
Used for YOLO model training and vehicle detection.

Supported formats: .mp4, .avi, .mov, .mkv, .webm

## API Endpoints

- `POST /dataset/upload` - Upload new dataset
- `GET /dataset/` - List all datasets
- `GET /dataset/{id}` - Get dataset details
- `DELETE /dataset/{id}` - Delete dataset
- `GET /dataset/{id}/download` - Download dataset
- `POST /dataset/{id}/preprocess` - Preprocess dataset
- `GET /dataset/{id}/preview` - Preview dataset rows
