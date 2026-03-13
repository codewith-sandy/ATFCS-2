"""
Training Data Generation Script

This script generates synthetic training data or processes real video data
for training the LSTM prediction model.
"""

import os
import sys
import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_traffic_pattern(
    start_time: datetime,
    duration_hours: int,
    interval_minutes: int = 5,
    pattern_type: str = 'urban'
) -> List[Dict]:
    """
    Generate realistic traffic patterns based on time of day.
    
    Args:
        start_time: Starting timestamp
        duration_hours: Duration in hours
        interval_minutes: Data collection interval
        pattern_type: 'urban', 'suburban', or 'highway'
    """
    data = []
    current_time = start_time
    
    # Pattern parameters based on location type
    patterns = {
        'urban': {
            'base_count': 20,
            'rush_multiplier': 2.5,
            'night_multiplier': 0.3,
            'variability': 0.25
        },
        'suburban': {
            'base_count': 12,
            'rush_multiplier': 2.0,
            'night_multiplier': 0.2,
            'variability': 0.20
        },
        'highway': {
            'base_count': 30,
            'rush_multiplier': 1.8,
            'night_multiplier': 0.4,
            'variability': 0.15
        }
    }
    
    params = patterns.get(pattern_type, patterns['urban'])
    
    total_intervals = (duration_hours * 60) // interval_minutes
    
    for i in range(total_intervals):
        hour = current_time.hour
        minute = current_time.minute
        day_of_week = current_time.weekday()
        
        # Time-based multiplier
        if 7 <= hour <= 9:  # Morning rush
            time_mult = params['rush_multiplier'] * (1 - 0.3 * abs(hour - 8))
        elif 16 <= hour <= 19:  # Evening rush
            time_mult = params['rush_multiplier'] * (1 - 0.2 * abs(hour - 17.5))
        elif 11 <= hour <= 14:  # Lunch time
            time_mult = 1.3
        elif 0 <= hour <= 5:  # Night
            time_mult = params['night_multiplier']
        else:
            time_mult = 1.0
        
        # Weekend adjustment
        if day_of_week >= 5:
            time_mult *= 0.7
        
        # Calculate vehicle count
        variability = np.random.normal(1, params['variability'])
        vehicle_count = max(0, int(params['base_count'] * time_mult * variability))
        
        # Calculate related metrics
        queue_length = max(0, int(vehicle_count * np.random.uniform(0.2, 0.5)))
        avg_speed = max(5, 60 - vehicle_count * 1.5 + np.random.normal(0, 5))
        density = min(1.0, vehicle_count / 50)
        
        # Lane distribution (4 lanes)
        total = vehicle_count
        lane_counts = []
        for j in range(3):
            count = np.random.binomial(total, 1 / (4 - j))
            lane_counts.append(count)
            total -= count
        lane_counts.append(total)
        
        data_point = {
            'timestamp': current_time.isoformat(),
            'vehicle_count': vehicle_count,
            'queue_length': queue_length,
            'avg_speed': round(avg_speed, 1),
            'density': round(density, 3),
            'hour': hour,
            'minute': minute,
            'day_of_week': day_of_week,
            'is_weekend': day_of_week >= 5,
            'lanes': {
                'north': {'count': lane_counts[0], 'queue': max(0, lane_counts[0] // 3)},
                'east': {'count': lane_counts[1], 'queue': max(0, lane_counts[1] // 3)},
                'south': {'count': lane_counts[2], 'queue': max(0, lane_counts[2] // 3)},
                'west': {'count': lane_counts[3], 'queue': max(0, lane_counts[3] // 3)}
            }
        }
        
        data.append(data_point)
        current_time += timedelta(minutes=interval_minutes)
    
    return data


def generate_emergency_events(
    data: List[Dict],
    frequency: float = 0.01
) -> List[Dict]:
    """Add emergency vehicle events to the data."""
    for i, point in enumerate(data):
        if np.random.random() < frequency:
            point['emergency_vehicle'] = True
            point['emergency_type'] = np.random.choice(['ambulance', 'fire_truck', 'police'])
            point['emergency_direction'] = np.random.choice(['north', 'south', 'east', 'west'])
        else:
            point['emergency_vehicle'] = False
    
    return data


def add_anomalies(
    data: List[Dict],
    anomaly_rate: float = 0.02
) -> List[Dict]:
    """Add anomalous events (accidents, road closures, etc.)."""
    i = 0
    while i < len(data):
        if np.random.random() < anomaly_rate:
            # Anomaly duration (30 min to 2 hours)
            duration = np.random.randint(6, 24)
            anomaly_type = np.random.choice(['accident', 'road_work', 'event', 'weather'])
            
            for j in range(i, min(i + duration, len(data))):
                data[j]['anomaly'] = True
                data[j]['anomaly_type'] = anomaly_type
                
                # Increase congestion during anomaly
                multiplier = np.random.uniform(1.3, 2.0)
                data[j]['vehicle_count'] = int(data[j]['vehicle_count'] * multiplier)
                data[j]['queue_length'] = int(data[j]['queue_length'] * multiplier * 1.5)
                data[j]['avg_speed'] = max(5, data[j]['avg_speed'] / multiplier)
            
            i += duration
        else:
            if 'anomaly' not in data[i]:
                data[i]['anomaly'] = False
            i += 1
    
    return data


def process_video_data(
    video_path: str,
    output_path: str,
    interval_seconds: int = 5
) -> Optional[List[Dict]]:
    """
    Process real video data using YOLOv8 detector.
    Requires ai_models module.
    """
    try:
        from ai_models.yolo_detector import YOLOVehicleDetector
        import cv2
        
        detector = YOLOVehicleDetector()
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * interval_seconds)
        
        data = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                # Detect vehicles
                detections = detector.detect(frame)
                
                timestamp = datetime.now() + timedelta(seconds=frame_count / fps)
                
                data_point = {
                    'timestamp': timestamp.isoformat(),
                    'vehicle_count': len(detections),
                    'queue_length': detector.calculate_queue_length(detections),
                    'hour': timestamp.hour,
                    'minute': timestamp.minute,
                    'detections': detections
                }
                
                data.append(data_point)
                logger.info(f"Processed frame {frame_count}: {len(detections)} vehicles")
            
            frame_count += 1
        
        cap.release()
        
        # Save processed data
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Processed {len(data)} data points from video")
        return data
        
    except ImportError as e:
        logger.error(f"Required modules not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return None


def save_data(
    data: List[Dict],
    output_path: str,
    format: str = 'json'
) -> None:
    """Save generated data to file."""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    if format == 'json':
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    elif format == 'csv':
        import csv
        
        # Flatten nested data for CSV
        flat_data = []
        for point in data:
            flat_point = {k: v for k, v in point.items() if not isinstance(v, dict)}
            if 'lanes' in point:
                for lane, lane_data in point['lanes'].items():
                    flat_point[f'{lane}_count'] = lane_data['count']
                    flat_point[f'{lane}_queue'] = lane_data['queue']
            flat_data.append(flat_point)
        
        if flat_data:
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=flat_data[0].keys())
                writer.writeheader()
                writer.writerows(flat_data)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    logger.info(f"Data saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Generate or Process Training Data')
    parser.add_argument('--mode', type=str, choices=['generate', 'process'], default='generate',
                       help='Mode: generate synthetic data or process video')
    parser.add_argument('--duration', type=int, default=168, help='Duration in hours (default: 1 week)')
    parser.add_argument('--interval', type=int, default=5, help='Data interval in minutes')
    parser.add_argument('--pattern', type=str, choices=['urban', 'suburban', 'highway'], 
                       default='urban', help='Traffic pattern type')
    parser.add_argument('--output', type=str, default='data/training_data.json', help='Output file path')
    parser.add_argument('--format', type=str, choices=['json', 'csv'], default='json', help='Output format')
    parser.add_argument('--video', type=str, help='Video file path for processing mode')
    parser.add_argument('--add-emergencies', action='store_true', help='Add emergency vehicle events')
    parser.add_argument('--add-anomalies', action='store_true', help='Add traffic anomalies')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    np.random.seed(args.seed)
    
    logger.info("=" * 60)
    logger.info("Training Data Generation")
    logger.info("=" * 60)
    logger.info(f"Configuration: {vars(args)}")
    
    if args.mode == 'generate':
        # Generate synthetic data
        start_time = datetime.now() - timedelta(hours=args.duration)
        
        logger.info(f"Generating {args.duration} hours of {args.pattern} traffic data...")
        data = generate_traffic_pattern(
            start_time=start_time,
            duration_hours=args.duration,
            interval_minutes=args.interval,
            pattern_type=args.pattern
        )
        
        if args.add_emergencies:
            logger.info("Adding emergency vehicle events...")
            data = generate_emergency_events(data)
        
        if args.add_anomalies:
            logger.info("Adding traffic anomalies...")
            data = add_anomalies(data)
        
    else:  # process mode
        if not args.video:
            logger.error("Video path required for process mode")
            return
        
        logger.info(f"Processing video: {args.video}")
        data = process_video_data(
            video_path=args.video,
            output_path=args.output
        )
        
        if data is None:
            logger.error("Video processing failed")
            return
    
    # Save data
    save_data(data, args.output, args.format)
    
    # Print statistics
    vehicle_counts = [d['vehicle_count'] for d in data]
    logger.info(f"\nData Statistics:")
    logger.info(f"  Total data points: {len(data)}")
    logger.info(f"  Average vehicle count: {np.mean(vehicle_counts):.1f}")
    logger.info(f"  Max vehicle count: {np.max(vehicle_counts)}")
    logger.info(f"  Min vehicle count: {np.min(vehicle_counts)}")
    
    if args.add_emergencies:
        emergency_count = sum(1 for d in data if d.get('emergency_vehicle', False))
        logger.info(f"  Emergency events: {emergency_count}")
    
    if args.add_anomalies:
        anomaly_count = sum(1 for d in data if d.get('anomaly', False))
        logger.info(f"  Anomaly periods: {anomaly_count}")
    
    logger.info("\nData generation completed!")


if __name__ == '__main__':
    main()
