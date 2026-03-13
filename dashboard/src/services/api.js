import axios from 'axios';

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check
export const TrafficService = {
  // Health check
  async getHealth() {
    const response = await api.get('/health');
    return response.data;
  },

  // Traffic endpoints
  async getLiveTraffic() {
    const response = await api.get('/traffic/live');
    return response.data;
  },

  async getLaneData() {
    const response = await api.get('/traffic/lanes');
    return response.data;
  },

  async getControllerState() {
    const response = await api.get('/traffic/state');
    return response.data;
  },

  async getTrafficMetrics() {
    const response = await api.get('/traffic/metrics');
    return response.data;
  },

  async triggerEmergency(lane) {
    const response = await api.post(`/traffic/emergency?lane=${lane}`);
    return response.data;
  },
};

// Prediction endpoints
export const PredictionService = {
  async getCurrentPrediction() {
    const response = await api.get('/prediction');
    return response.data;
  },

  async getPredictionHistory(limit = 100) {
    const response = await api.get(`/prediction/history?limit=${limit}`);
    return response.data;
  },

  async getPredictionStatistics() {
    const response = await api.get('/prediction/statistics');
    return response.data;
  },
};

// Signal endpoints
export const SignalService = {
  async getCurrentSignals() {
    const response = await api.get('/signals');
    return response.data;
  },

  async overrideSignal(phase, duration) {
    const response = await api.post('/signals/override', { phase, duration });
    return response.data;
  },

  async getSignalHistory(limit = 100) {
    const response = await api.get(`/signals/history?limit=${limit}`);
    return response.data;
  },

  async getAgentStats() {
    const response = await api.get('/signals/agent/stats');
    return response.data;
  },

  async startTraining() {
    const response = await api.post('/signals/agent/train/start');
    return response.data;
  },

  async stopTraining() {
    const response = await api.post('/signals/agent/train/stop');
    return response.data;
  },
};

// Video endpoints
export const VideoService = {
  async uploadVideo(file, onProgress) {
    const formData = new FormData();
    formData.append('video', file);

    const response = await api.post('/video/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return response.data;
  },

  async getProcessingStatus(videoId) {
    const response = await api.get(`/video/status/${videoId}`);
    return response.data;
  },

  async listVideos() {
    const response = await api.get('/video/list');
    return response.data;
  },

  async startCameraStream(cameraSource) {
    const response = await api.post(`/video/stream/start?camera_source=${cameraSource}`);
    return response.data;
  },

  async stopCameraStream() {
    const response = await api.post('/video/stream/stop');
    return response.data;
  },
};

// Analytics endpoints
export const AnalyticsService = {
  async getAnalytics() {
    const response = await api.get('/analytics');
    return response.data;
  },

  async getHourlyTraffic() {
    const response = await api.get('/analytics/traffic/hourly');
    return response.data;
  },

  async getDailyTraffic() {
    const response = await api.get('/analytics/traffic/daily');
    return response.data;
  },

  async getDetectionSummary() {
    const response = await api.get('/analytics/detection/summary');
    return response.data;
  },

  async getPredictionAccuracy() {
    const response = await api.get('/analytics/prediction/accuracy');
    return response.data;
  },

  async getRLTrainingMetrics() {
    const response = await api.get('/analytics/rl/training');
    return response.data;
  },

  async getSystemAnalytics() {
    const response = await api.get('/analytics/system');
    return response.data;
  },
};

// Camera Streaming Service (NEW)
export const CameraService = {
  // Get stream URL for a lane
  getStreamUrl(laneId) {
    return `${API_BASE_URL}/camera/lane/${laneId}/stream`;
  },

  // Get all lane metrics
  async getAllLaneMetrics() {
    const response = await api.get('/camera/lanes/metrics');
    return response.data;
  },

  // Get specific lane metrics
  async getLaneMetrics(laneId) {
    const response = await api.get(`/camera/lane/${laneId}/metrics`);
    return response.data;
  },

  // List all cameras
  async listCameras() {
    const response = await api.get('/camera/cameras');
    return response.data;
  },

  // Detect available cameras connected to the system
  async getAvailableCameras(maxCameras = 10) {
    const response = await api.get(`/camera/available?max_cameras=${maxCameras}`);
    return response.data;
  },

  // Quick scan for available cameras
  async scanCameras() {
    const response = await api.get('/camera/scan');
    return response.data;
  },

  // Assign a detected camera to a lane
  async assignCameraToLane(cameraIndex, laneId, name = null) {
    const response = await api.post('/camera/assign', {
      camera_index: cameraIndex,
      lane_id: laneId,
      name: name
    });
    return response.data;
  },

  // Add camera
  async addCamera(config) {
    const response = await api.post('/camera/cameras', config);
    return response.data;
  },

  // Remove camera
  async removeCamera(cameraId) {
    const response = await api.delete(`/camera/cameras/${cameraId}`);
    return response.data;
  },

  // Update signal state
  async updateSignalState(laneId, state) {
    const response = await api.post('/camera/signals/update', { lane_id: laneId, state });
    return response.data;
  },

  // Get camera stats
  async getStats() {
    const response = await api.get('/camera/stats');
    return response.data;
  },

  // Get intersections
  async getIntersections() {
    const response = await api.get('/camera/intersections');
    return response.data;
  },

  // Get intersection details
  async getIntersection(intersectionId) {
    const response = await api.get(`/camera/intersections/${intersectionId}`);
    return response.data;
  },
};

// Dataset Service (NEW)
export const DatasetService = {
  // Upload dataset
  async uploadDataset(file, name, datasetType, description, onProgress) {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams({
      name: name || file.name,
      dataset_type: datasetType,
      description: description || ''
    });

    const response = await api.post(`/dataset/upload?${params}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return response.data;
  },

  // List datasets
  async listDatasets(datasetType = null) {
    const params = datasetType ? `?dataset_type=${datasetType}` : '';
    const response = await api.get(`/dataset/${params}`);
    return response.data;
  },

  // Get dataset
  async getDataset(datasetId) {
    const response = await api.get(`/dataset/${datasetId}`);
    return response.data;
  },

  // Delete dataset
  async deleteDataset(datasetId) {
    const response = await api.delete(`/dataset/${datasetId}`);
    return response.data;
  },

  // Preview dataset
  async previewDataset(datasetId, rows = 10) {
    const response = await api.get(`/dataset/${datasetId}/preview?rows=${rows}`);
    return response.data;
  },

  // Preprocess dataset
  async preprocessDataset(datasetId) {
    const response = await api.post(`/dataset/${datasetId}/preprocess`);
    return response.data;
  },

  // Download URL
  getDownloadUrl(datasetId) {
    return `${API_BASE_URL}/dataset/${datasetId}/download`;
  },
};

// Model Training Service (NEW)
export const ModelTrainingService = {
  // Start LSTM training
  async trainLSTM(datasetId, config = {}) {
    const response = await api.post(`/model/train/lstm?dataset_id=${datasetId}`, config);
    return response.data;
  },

  // Start YOLO training
  async trainYOLO(datasetId, config = {}) {
    const response = await api.post(`/model/train/yolo?dataset_id=${datasetId}`, config);
    return response.data;
  },

  // Start RL training
  async trainRL(datasetId, config = {}) {
    const response = await api.post(`/model/train/rl?dataset_id=${datasetId}`, config);
    return response.data;
  },

  // Get training status
  async getTrainingStatus(jobId) {
    const response = await api.get(`/model/training/${jobId}`);
    return response.data;
  },

  // Get all training jobs
  async getAllTrainingJobs() {
    const response = await api.get('/model/training/status');
    return response.data;
  },

  // Cancel training
  async cancelTraining(jobId) {
    const response = await api.post(`/model/training/${jobId}/cancel`);
    return response.data;
  },

  // Get active training jobs
  async getActiveJobs() {
    const response = await api.get('/model/training/active');
    return response.data;
  },

  // List model versions
  async listVersions(modelType = null) {
    const params = modelType ? `?model_type=${modelType}` : '';
    const response = await api.get(`/model/versions${params}`);
    return response.data;
  },

  // Activate model version
  async activateVersion(versionId) {
    const response = await api.post(`/model/versions/${versionId}/activate`);
    return response.data;
  },

  // Delete model version
  async deleteVersion(versionId) {
    const response = await api.delete(`/model/versions/${versionId}`);
    return response.data;
  },

  // Get active model
  async getActiveModel(modelType) {
    const response = await api.get(`/model/active/${modelType}`);
    return response.data;
  },

  // Get default config
  async getDefaultConfig(modelType) {
    const response = await api.get(`/model/config/default/${modelType}`);
    return response.data;
  },
};

export default api;
