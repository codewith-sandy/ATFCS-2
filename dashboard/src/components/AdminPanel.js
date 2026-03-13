import React, { useState, useEffect } from 'react';
import { CameraService, ModelTrainingService, TrafficService, DatasetService } from '../services/api';

// System Status Card
function SystemStatusCard({ title, status, details, icon }) {
  const statusColors = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    warning: 'bg-yellow-500',
    loading: 'bg-gray-500',
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{icon}</span>
          <h4 className="text-white font-medium">{title}</h4>
        </div>
        <span className={`w-3 h-3 rounded-full ${statusColors[status] || statusColors.loading}`}></span>
      </div>
      <p className="text-gray-400 text-sm">{details}</p>
    </div>
  );
}

// Camera Management Section
function CameraManagement() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newCamera, setNewCamera] = useState({
    camera_id: '',
    lane_id: 0,
    source: '',
    name: '',
    resolution: [640, 480],
  });

  const fetchCameras = async () => {
    try {
      const data = await CameraService.listCameras();
      setCameras(data);
    } catch (err) {
      console.error('Failed to fetch cameras:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const handleAddCamera = async () => {
    try {
      await CameraService.addCamera({
        ...newCamera,
        resolution: [newCamera.resolution[0], newCamera.resolution[1]],
      });
      setShowAddForm(false);
      setNewCamera({ camera_id: '', lane_id: 0, source: '', name: '', resolution: [640, 480] });
      fetchCameras();
    } catch (err) {
      console.error('Failed to add camera:', err);
      alert('Failed to add camera: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleRemoveCamera = async (cameraId) => {
    if (window.confirm('Are you sure you want to remove this camera?')) {
      try {
        await CameraService.removeCamera(cameraId);
        fetchCameras();
      } catch (err) {
        console.error('Failed to remove camera:', err);
      }
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-white font-medium">Camera Management</h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
        >
          + Add Camera
        </button>
      </div>

      {/* Add Camera Form */}
      {showAddForm && (
        <div className="bg-gray-700 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-gray-400 text-xs">Camera ID</label>
              <input
                type="text"
                value={newCamera.camera_id}
                onChange={(e) => setNewCamera({ ...newCamera, camera_id: e.target.value })}
                placeholder="cam_lane_5"
                className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-white text-sm"
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs">Lane ID</label>
              <input
                type="number"
                value={newCamera.lane_id}
                onChange={(e) => setNewCamera({ ...newCamera, lane_id: parseInt(e.target.value) })}
                className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-white text-sm"
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs">Name</label>
              <input
                type="text"
                value={newCamera.name}
                onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                placeholder="Lane 5 - Camera"
                className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-white text-sm"
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs">Source (RTSP/File/Device)</label>
              <input
                type="text"
                value={newCamera.source}
                onChange={(e) => setNewCamera({ ...newCamera, source: e.target.value })}
                placeholder="rtsp://... or 0"
                className="w-full bg-gray-600 border border-gray-500 rounded px-2 py-1 text-white text-sm"
              />
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleAddCamera}
              className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
            >
              Save
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1 bg-gray-600 text-gray-300 rounded hover:bg-gray-500 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Camera List */}
      {loading ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      ) : (
        <div className="space-y-2">
          {cameras.map((camera) => (
            <div
              key={camera.camera_id}
              className="flex items-center justify-between bg-gray-700 rounded-lg p-3"
            >
              <div className="flex items-center space-x-3">
                <span className={`w-2 h-2 rounded-full ${camera.is_active ? 'bg-green-500' : 'bg-red-500'}`}></span>
                <div>
                  <p className="text-white text-sm font-medium">{camera.name}</p>
                  <p className="text-gray-400 text-xs">
                    Lane {camera.lane_id} | {camera.source}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleRemoveCamera(camera.camera_id)}
                className="text-red-400 hover:text-red-300 text-sm"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Model Management Section
function ModelManagement() {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchVersions = async () => {
    try {
      const data = await ModelTrainingService.listVersions();
      setVersions(data.versions || []);
    } catch (err) {
      console.error('Failed to fetch versions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVersions();
  }, []);

  const handleActivate = async (versionId) => {
    try {
      await ModelTrainingService.activateVersion(versionId);
      fetchVersions();
    } catch (err) {
      console.error('Failed to activate version:', err);
    }
  };

  const handleDelete = async (versionId) => {
    if (window.confirm('Are you sure you want to delete this model version?')) {
      try {
        await ModelTrainingService.deleteVersion(versionId);
        fetchVersions();
      } catch (err) {
        console.error('Failed to delete version:', err);
      }
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-4">
      <h3 className="text-white font-medium">Model Version Management</h3>

      {loading ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      ) : versions.length === 0 ? (
        <p className="text-gray-400 text-sm text-center py-4">No model versions available</p>
      ) : (
        <div className="space-y-2">
          {versions.map((version) => (
            <div
              key={version.version_id}
              className="flex items-center justify-between bg-gray-700 rounded-lg p-3"
            >
              <div>
                <div className="flex items-center space-x-2">
                  <p className="text-white text-sm font-medium">
                    {version.model_type.toUpperCase()} v{version.version}
                  </p>
                  {version.is_active && (
                    <span className="px-2 py-0.5 bg-green-600 text-white rounded text-xs">Active</span>
                  )}
                </div>
                <p className="text-gray-400 text-xs">
                  Created: {new Date(version.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex space-x-2">
                {!version.is_active && (
                  <button
                    onClick={() => handleActivate(version.version_id)}
                    className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                  >
                    Activate
                  </button>
                )}
                <button
                  onClick={() => handleDelete(version.version_id)}
                  className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// System Logs Section
function SystemLogs() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    // Simulated logs - in production, fetch from backend
    const mockLogs = [
      { timestamp: new Date().toISOString(), level: 'INFO', message: 'System started successfully' },
      { timestamp: new Date(Date.now() - 60000).toISOString(), level: 'INFO', message: 'Camera stream initialized' },
      { timestamp: new Date(Date.now() - 120000).toISOString(), level: 'WARNING', message: 'High congestion detected on Lane 2' },
      { timestamp: new Date(Date.now() - 180000).toISOString(), level: 'INFO', message: 'RL agent decision: Extended green for Lane 2' },
      { timestamp: new Date(Date.now() - 240000).toISOString(), level: 'INFO', message: 'YOLO detector processing at 28 FPS' },
      { timestamp: new Date(Date.now() - 300000).toISOString(), level: 'ERROR', message: 'Failed to connect to camera cam_lane_3' },
      { timestamp: new Date(Date.now() - 360000).toISOString(), level: 'INFO', message: 'Model training completed: LSTM v2.0' },
    ];
    setLogs(mockLogs);
  }, []);

  const getLevelColor = (level) => {
    const colors = {
      INFO: 'text-blue-400',
      WARNING: 'text-yellow-400',
      ERROR: 'text-red-400',
      DEBUG: 'text-gray-400',
    };
    return colors[level] || 'text-gray-400';
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="text-white font-medium">System Logs</h3>
        <button className="text-gray-400 hover:text-white text-sm">View All</button>
      </div>

      <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
        {logs.map((log, idx) => (
          <div key={idx} className="flex space-x-2">
            <span className="text-gray-500">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            <span className={`${getLevelColor(log.level)} w-16`}>[{log.level}]</span>
            <span className="text-gray-300">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// AI Decisions History
function AIDecisionHistory() {
  const [decisions, setDecisions] = useState([]);

  useEffect(() => {
    // Simulated decisions - in production, fetch from backend
    const mockDecisions = [
      {
        timestamp: new Date().toISOString(),
        action: 'Green time extended',
        lane: 2,
        duration: 45,
        reason: 'High congestion predicted',
        reward: 0.85,
      },
      {
        timestamp: new Date(Date.now() - 30000).toISOString(),
        action: 'Phase changed',
        lane: 0,
        duration: 30,
        reason: 'Normal cycle',
        reward: 0.72,
      },
      {
        timestamp: new Date(Date.now() - 60000).toISOString(),
        action: 'Emergency override',
        lane: 3,
        duration: 60,
        reason: 'Ambulance detected',
        reward: 1.0,
      },
      {
        timestamp: new Date(Date.now() - 90000).toISOString(),
        action: 'Green time reduced',
        lane: 1,
        duration: 20,
        reason: 'Low traffic detected',
        reward: 0.65,
      },
    ];
    setDecisions(mockDecisions);
  }, []);

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <h3 className="text-white font-medium">AI Decision History</h3>

      <div className="space-y-2">
        {decisions.map((decision, idx) => (
          <div key={idx} className="bg-gray-700 rounded-lg p-3">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-white text-sm font-medium">{decision.action}</p>
                <p className="text-gray-400 text-xs">{decision.reason}</p>
              </div>
              <div className="text-right">
                <span className="text-green-400 text-sm">
                  Reward: {decision.reward.toFixed(2)}
                </span>
                <p className="text-gray-500 text-xs">
                  {new Date(decision.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
            <div className="flex space-x-4 mt-2 text-xs text-gray-400">
              <span>Lane: {decision.lane + 1}</span>
              <span>Duration: {decision.duration}s</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Alert Configuration
function AlertConfiguration() {
  const [alerts, setAlerts] = useState({
    congestionThreshold: 20,
    emergencyNotification: true,
    cameraOfflineAlert: true,
    modelDegradation: true,
    emailNotifications: false,
  });

  const handleToggle = (key) => {
    setAlerts({ ...alerts, [key]: !alerts[key] });
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-4">
      <h3 className="text-white font-medium">Alert Configuration</h3>

      <div className="space-y-3">
        {/* Congestion Threshold */}
        <div>
          <label className="text-gray-400 text-sm">Congestion Alert Threshold</label>
          <div className="flex items-center space-x-3 mt-1">
            <input
              type="range"
              min="5"
              max="50"
              value={alerts.congestionThreshold}
              onChange={(e) => setAlerts({ ...alerts, congestionThreshold: parseInt(e.target.value) })}
              className="flex-1"
            />
            <span className="text-white text-sm w-12">{alerts.congestionThreshold}</span>
          </div>
        </div>

        {/* Toggle Options */}
        {[
          { key: 'emergencyNotification', label: 'Emergency Vehicle Notifications' },
          { key: 'cameraOfflineAlert', label: 'Camera Offline Alerts' },
          { key: 'modelDegradation', label: 'Model Performance Alerts' },
          { key: 'emailNotifications', label: 'Email Notifications' },
        ].map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-gray-300 text-sm">{label}</span>
            <button
              onClick={() => handleToggle(key)}
              className={`w-12 h-6 rounded-full transition-colors ${
                alerts[key] ? 'bg-blue-600' : 'bg-gray-600'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full transition-transform ${
                  alerts[key] ? 'translate-x-6' : 'translate-x-0.5'
                }`}
              ></div>
            </button>
          </div>
        ))}
      </div>

      <button className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
        Save Configuration
      </button>
    </div>
  );
}

// Main Admin Panel
function AdminPanel() {
  const [systemHealth, setSystemHealth] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [health, cameraStats] = await Promise.all([
          TrafficService.getHealth().catch(() => null),
          CameraService.getStats().catch(() => null),
        ]);
        setSystemHealth(health);
        setStats(cameraStats);
      } catch (err) {
        console.error('Failed to fetch system status:', err);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">Admin Panel</h2>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SystemStatusCard
          title="Detection Service"
          status={systemHealth?.services?.detection ? 'online' : 'offline'}
          details={systemHealth?.services?.detection ? 'Running normally' : 'Not available'}
          icon="🔍"
        />
        <SystemStatusCard
          title="Prediction Service"
          status={systemHealth?.services?.prediction ? 'online' : 'offline'}
          details={systemHealth?.services?.prediction ? 'Running normally' : 'Not available'}
          icon="📈"
        />
        <SystemStatusCard
          title="RL Agent"
          status={systemHealth?.services?.rl_agent ? 'online' : 'offline'}
          details={systemHealth?.services?.rl_agent ? 'Optimizing signals' : 'Not available'}
          icon="🤖"
        />
        <SystemStatusCard
          title="Camera System"
          status={stats?.active_cameras > 0 ? 'online' : 'warning'}
          details={`${stats?.active_cameras || 0} cameras active`}
          icon="📹"
        />
      </div>

      {/* Management Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CameraManagement />
        <ModelManagement />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SystemLogs />
        <AIDecisionHistory />
      </div>

      <AlertConfiguration />
    </div>
  );
}

export default AdminPanel;
export { CameraManagement, ModelManagement, SystemLogs, AIDecisionHistory };
