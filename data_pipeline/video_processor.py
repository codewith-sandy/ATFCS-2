"""
Video Processor Module
Handles video input, frame extraction, and preprocessing
"""

import cv2
import numpy as np
from typing import Generator, List, Tuple, Optional, Dict, Callable
from dataclasses import dataclass
from pathlib import Path
import time
import threading
from queue import Queue
import asyncio


@dataclass
class FrameData:
    """Data class for processed frame"""
    frame: np.ndarray
    timestamp: float
    frame_id: int
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]


class VideoProcessor:
    """
    Video processor for traffic camera feeds
    Supports video files, webcams, and RTSP streams
    """
    
    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        skip_frames: int = 1,
        buffer_size: int = 30
    ):
        """
        Initialize video processor
        
        Args:
            target_size: Target frame size (width, height)
            skip_frames: Process every nth frame
            buffer_size: Frame buffer size for async processing
        """
        self.target_size = target_size
        self.skip_frames = skip_frames
        self.buffer_size = buffer_size
        
        self.capture = None
        self.is_running = False
        self.frame_buffer = Queue(maxsize=buffer_size)
        
        self.total_frames = 0
        self.processed_frames = 0
        self.fps = 0
        
    def open(self, source) -> bool:
        """
        Open video source
        
        Args:
            source: Video file path, camera index, or RTSP URL
            
        Returns:
            True if successful
        """
        if isinstance(source, str) and not source.isdigit():
            # File path or RTSP URL
            self.capture = cv2.VideoCapture(source)
        else:
            # Camera index
            self.capture = cv2.VideoCapture(int(source))
            
        if not self.capture.isOpened():
            print(f"Failed to open video source: {source}")
            return False
            
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"Opened video source: {source}")
        print(f"FPS: {self.fps}, Total frames: {self.total_frames}")
        
        return True
    
    def close(self):
        """Close video source"""
        self.is_running = False
        if self.capture:
            self.capture.release()
            self.capture = None
            
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for detection
        
        Args:
            frame: Input frame (BGR)
            
        Returns:
            Preprocessed frame
        """
        # Resize
        resized = cv2.resize(frame, self.target_size)
        
        return resized
    
    def read_frame(self) -> Optional[FrameData]:
        """
        Read and preprocess a single frame
        
        Returns:
            FrameData or None if no more frames
        """
        if not self.capture or not self.capture.isOpened():
            return None
            
        ret, frame = self.capture.read()
        if not ret:
            return None
            
        original_size = (frame.shape[1], frame.shape[0])
        processed = self.preprocess_frame(frame)
        
        self.processed_frames += 1
        
        return FrameData(
            frame=processed,
            timestamp=time.time(),
            frame_id=self.processed_frames,
            original_size=original_size,
            processed_size=self.target_size
        )
    
    def stream_frames(
        self,
        callback: Optional[Callable] = None,
        max_frames: Optional[int] = None
    ) -> Generator[FrameData, None, None]:
        """
        Stream frames from video source
        
        Args:
            callback: Optional callback function for each frame
            max_frames: Maximum frames to process
            
        Yields:
            FrameData for each frame
        """
        if not self.capture or not self.capture.isOpened():
            return
            
        frame_count = 0
        
        while True:
            # Skip frames
            for _ in range(self.skip_frames - 1):
                self.capture.read()
                
            frame_data = self.read_frame()
            
            if frame_data is None:
                break
                
            frame_count += 1
            
            if callback:
                callback(frame_data)
                
            yield frame_data
            
            if max_frames and frame_count >= max_frames:
                break
    
    def start_async_capture(self, callback: Callable):
        """
        Start asynchronous frame capture
        
        Args:
            callback: Callback function to process frames
        """
        self.is_running = True
        
        def capture_thread():
            while self.is_running:
                frame_data = self.read_frame()
                if frame_data is None:
                    break
                    
                if not self.frame_buffer.full():
                    self.frame_buffer.put(frame_data)
                    
        def process_thread():
            while self.is_running:
                try:
                    frame_data = self.frame_buffer.get(timeout=1)
                    callback(frame_data)
                except:
                    continue
                    
        # Start threads
        self.capture_thread = threading.Thread(target=capture_thread)
        self.process_thread = threading.Thread(target=process_thread)
        
        self.capture_thread.start()
        self.process_thread.start()
        
    def stop_async_capture(self):
        """Stop asynchronous capture"""
        self.is_running = False
        
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join()
        if hasattr(self, 'process_thread'):
            self.process_thread.join()
            
    def extract_frames_to_disk(
        self,
        video_path: str,
        output_dir: str,
        frame_interval: int = 30
    ) -> List[str]:
        """
        Extract frames from video to disk
        
        Args:
            video_path: Path to video file
            output_dir: Output directory for frames
            frame_interval: Extract every nth frame
            
        Returns:
            List of extracted frame paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if not self.open(video_path):
            return []
            
        frame_paths = []
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = self.capture.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                filename = output_path / f"frame_{saved_count:06d}.jpg"
                cv2.imwrite(str(filename), frame)
                frame_paths.append(str(filename))
                saved_count += 1
                
            frame_count += 1
            
        self.close()
        print(f"Extracted {saved_count} frames to {output_dir}")
        
        return frame_paths
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get video file information
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video info
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {}
            
        info = {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)),
            'codec': int(cap.get(cv2.CAP_PROP_FOURCC))
        }
        
        cap.release()
        return info


class RTSPStreamProcessor(VideoProcessor):
    """
    Specialized processor for RTSP camera streams
    """
    
    def __init__(
        self,
        target_size: Tuple[int, int] = (640, 640),
        reconnect_delay: int = 5,
        max_retries: int = 3
    ):
        """
        Initialize RTSP processor
        
        Args:
            target_size: Target frame size
            reconnect_delay: Delay between reconnection attempts
            max_retries: Maximum reconnection attempts
        """
        super().__init__(target_size)
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries
        self.rtsp_url = None
        
    def connect(self, rtsp_url: str) -> bool:
        """
        Connect to RTSP stream
        
        Args:
            rtsp_url: RTSP stream URL
            
        Returns:
            True if connected
        """
        self.rtsp_url = rtsp_url
        
        for attempt in range(self.max_retries):
            if self.open(rtsp_url):
                return True
                
            print(f"Connection attempt {attempt + 1} failed, retrying...")
            time.sleep(self.reconnect_delay)
            
        return False
    
    def read_frame_with_reconnect(self) -> Optional[FrameData]:
        """
        Read frame with automatic reconnection
        
        Returns:
            FrameData or None
        """
        frame_data = self.read_frame()
        
        if frame_data is None and self.rtsp_url:
            # Try to reconnect
            print("Stream disconnected, attempting reconnection...")
            if self.connect(self.rtsp_url):
                frame_data = self.read_frame()
                
        return frame_data


class MultiCameraProcessor:
    """
    Process multiple camera feeds simultaneously
    """
    
    def __init__(self, target_size: Tuple[int, int] = (640, 640)):
        """
        Initialize multi-camera processor
        
        Args:
            target_size: Target frame size for all cameras
        """
        self.target_size = target_size
        self.processors: Dict[str, VideoProcessor] = {}
        self.is_running = False
        
    def add_camera(self, camera_id: str, source) -> bool:
        """
        Add camera to processor
        
        Args:
            camera_id: Unique camera identifier
            source: Video source
            
        Returns:
            True if successful
        """
        processor = VideoProcessor(self.target_size)
        
        if processor.open(source):
            self.processors[camera_id] = processor
            return True
            
        return False
    
    def remove_camera(self, camera_id: str):
        """Remove camera from processor"""
        if camera_id in self.processors:
            self.processors[camera_id].close()
            del self.processors[camera_id]
            
    def read_all_frames(self) -> Dict[str, Optional[FrameData]]:
        """
        Read frames from all cameras
        
        Returns:
            Dictionary of camera_id to FrameData
        """
        frames = {}
        
        for camera_id, processor in self.processors.items():
            frames[camera_id] = processor.read_frame()
            
        return frames
    
    def close_all(self):
        """Close all cameras"""
        for processor in self.processors.values():
            processor.close()
        self.processors.clear()


if __name__ == '__main__':
    # Test video processor
    processor = VideoProcessor()
    
    # Test with webcam
    if processor.open(0):
        print("Webcam opened successfully")
        
        for i, frame_data in enumerate(processor.stream_frames(max_frames=30)):
            print(f"Frame {frame_data.frame_id}: shape={frame_data.frame.shape}")
            
            # Display frame
            cv2.imshow('Frame', frame_data.frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        processor.close()
        cv2.destroyAllWindows()
    else:
        print("No webcam available")
