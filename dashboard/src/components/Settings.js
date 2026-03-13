import React, { useState, useEffect } from 'react';
import { CameraService } from '../services/api';

// Settings Section Component
function SettingsSection({ title, children }) {
  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      {children}
    </div>
  );
}

// Toggle Switch Component
function Toggle({ label, description, enabled, onChange }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-700 last:border-0">
      <div>
        <p className="text-white font-medium">{label}</p>
        {description && <p className="text-sm text-gray-400">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          enabled ? 'bg-blue-600' : 'bg-gray-600'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}

// Slider Setting Component
function SliderSetting({ label, value, min, max, step, unit, onChange }) {
  return (
    <div className="py-3 border-b border-gray-700 last:border-0">
      <div className="flex justify-between mb-2">
        <span className="text-white font-medium">{label}</span>
        <span className="text-blue-400">{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

// Select Setting Component
function SelectSetting({ label, value, options, onChange }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-700 last:border-0">
      <span className="text-white font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-gray-700 text-white rounded-lg px-3 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Camera Lane Configuration Component
function CameraLaneConfiguration() {
  const [cameras, setCameras] = useState([]);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [editingLane, setEditingLane] = useState(null);
  const [customSource, setCustomSource] = useState('');

  const lanes = [
    { id: 0, name: 'Lane 1 - North', cameraId: 'cam_lane_1' },
    { id: 1, name: 'Lane 2 - East', cameraId: 'cam_lane_2' },
    { id: 2, name: 'Lane 3 - South', cameraId: 'cam_lane_3' },
    { id: 3, name: 'Lane 4 - West', cameraId: 'cam_lane_4' },
  ];

  // Load current camera configuration
  useEffect(() => {
    const loadCameras = async () => {
      try {
        const cameraList = await CameraService.listCameras();
        setCameras(cameraList);
      } catch (err) {
        console.error('Failed to load cameras:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadCameras();
  }, []);

  // Scan for available cameras
  const scanCameras = async () => {
    setIsScanning(true);
    try {
      const result = await CameraService.getAvailableCameras(10);
      setAvailableCameras(result.cameras || []);
    } catch (err) {
      console.error('Failed to scan cameras:', err);
      alert('Failed to scan for cameras');
    } finally {
      setIsScanning(false);
    }
  };

  // Assign camera to lane
  const assignCamera = async (laneId, source, name = null) => {
    try {
      // If source is a number, use assignCameraToLane
      if (!isNaN(parseInt(source))) {
        await CameraService.assignCameraToLane(parseInt(source), laneId, name);
      } else {
        // For RTSP/file paths, use addCamera or update existing
        const cameraId = `cam_lane_${laneId + 1}`;
        const laneName = lanes.find(l => l.id === laneId)?.name || `Lane ${laneId + 1}`;
        await CameraService.addCamera({
          camera_id: cameraId,
          lane_id: laneId,
          source: source,
          name: name || laneName,
          resolution: [640, 480]
        });
      }
      
      // Reload cameras
      const cameraList = await CameraService.listCameras();
      setCameras(cameraList);
      setEditingLane(null);
      setCustomSource('');
      alert(`Camera assigned to Lane ${laneId + 1} successfully!`);
    } catch (err) {
      console.error('Failed to assign camera:', err);
      alert('Failed to assign camera. Please try again.');
    }
  };

  // Get current camera for a lane
  const getCameraForLane = (laneId) => {
    return cameras.find(c => c.lane_id === laneId);
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-semibold text-white">Camera Configuration</h3>
          <p className="text-sm text-gray-400">Assign cameras to each traffic lane</p>
        </div>
        <button
          onClick={scanCameras}
          disabled={isScanning}
          className={`px-4 py-2 rounded-lg flex items-center ${
            isScanning ? 'bg-gray-600 cursor-wait' : 'bg-green-600 hover:bg-green-700'
          } text-white transition-colors`}
        >
          {isScanning ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Scanning...
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Scan for Cameras
            </>
          )}
        </button>
      </div>

      {/* Available Cameras Section */}
      {availableCameras.length > 0 && (
        <div className="mb-6 p-4 bg-gray-700 rounded-lg">
          <h4 className="text-white font-medium mb-3">Detected Cameras ({availableCameras.length})</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {availableCameras.map((cam) => (
              <div key={cam.index} className="bg-gray-600 rounded-lg p-3">
                <div className="flex items-center mb-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                  <span className="text-white text-sm font-medium">{cam.name}</span>
                </div>
                <p className="text-gray-400 text-xs">Index: {cam.index}</p>
                <p className="text-gray-400 text-xs">{cam.resolution[0]}x{cam.resolution[1]}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lane Configuration */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading camera configuration...</div>
      ) : (
        <div className="space-y-4">
          {lanes.map((lane) => {
            const currentCamera = getCameraForLane(lane.id);
            const isEditing = editingLane === lane.id;

            return (
              <div key={lane.id} className="border border-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="text-white font-medium">{lane.name}</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      Current Source: <span className="text-blue-400">{currentCamera?.source || 'Not configured'}</span>
                    </p>
                    {currentCamera && (
                      <p className="text-gray-500 text-xs">
                        Resolution: {currentCamera.resolution?.[0]}x{currentCamera.resolution?.[1]} | 
                        Active: {currentCamera.is_active ? 'Yes' : 'No'}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      setEditingLane(isEditing ? null : lane.id);
                      setCustomSource(currentCamera?.source || '');
                    }}
                    className={`px-3 py-1 rounded text-sm ${
                      isEditing ? 'bg-gray-600 text-gray-300' : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                  >
                    {isEditing ? 'Cancel' : 'Change Camera'}
                  </button>
                </div>

                {/* Edit Panel */}
                {isEditing && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <div className="space-y-4">
                      {/* Quick Select from Detected Cameras */}
                      {availableCameras.length > 0 && (
                        <div>
                          <label className="block text-sm text-gray-400 mb-2">Select Detected Camera</label>
                          <div className="flex flex-wrap gap-2">
                            {availableCameras.map((cam) => (
                              <button
                                key={cam.index}
                                onClick={() => assignCamera(lane.id, cam.index)}
                                className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm"
                              >
                                Camera {cam.index}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Manual Input */}
                      <div>
                        <label className="block text-sm text-gray-400 mb-2">Or Enter Custom Source</label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={customSource}
                            onChange={(e) => setCustomSource(e.target.value)}
                            placeholder="0, rtsp://..., or /path/to/video.mp4"
                            className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
                          />
                          <button
                            onClick={() => assignCamera(lane.id, customSource)}
                            disabled={!customSource}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg"
                          >
                            Apply
                          </button>
                        </div>
                        <p className="text-gray-500 text-xs mt-1">
                          Examples: 0 (webcam), rtsp://192.168.1.100:554/stream, C:\videos\traffic.mp4
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Main Settings Component
function Settings() {
  const [settings, setSettings] = useState({
    // Detection Settings
    yoloModel: 'yolov8n',
    confidenceThreshold: 0.25,
    inputSize: 640,
    enableGPU: true,
    
    // LSTM Settings
    sequenceLength: 15,
    predictionHorizon: 5,
    
    // Q-Learning Settings
    learningRate: 0.1,
    discountFactor: 0.9,
    epsilon: 0.1,
    enableRL: true,
    
    // Signal Settings
    minGreenTime: 10,
    maxGreenTime: 60,
    yellowTime: 3,
    allRedTime: 2,
    
    // System Settings
    emergencyOverride: true,
    dataLogging: true,
    autoSave: true,
    refreshRate: 2,
    
    // Video Settings
    videoSource: 'camera',
    frameSkip: 2,
    resolution: '640x480',
  });

  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    console.log('Saving settings:', settings);
    // In production, this would call the API to save settings
    alert('Settings saved successfully!');
  };

  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset all settings to default?')) {
      setSettings({
        yoloModel: 'yolov8n',
        confidenceThreshold: 0.25,
        inputSize: 640,
        enableGPU: true,
        sequenceLength: 15,
        predictionHorizon: 5,
        learningRate: 0.1,
        discountFactor: 0.9,
        epsilon: 0.1,
        enableRL: true,
        minGreenTime: 10,
        maxGreenTime: 60,
        yellowTime: 3,
        allRedTime: 2,
        emergencyOverride: true,
        dataLogging: true,
        autoSave: true,
        refreshRate: 2,
        videoSource: 'camera',
        frameSkip: 2,
        resolution: '640x480',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">System Settings</h2>
        <div className="flex space-x-3">
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Reset to Default
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Save Settings
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* YOLOv8 Detection Settings */}
        <SettingsSection title="YOLOv8 Detection">
          <SelectSetting
            label="Model"
            value={settings.yoloModel}
            options={[
              { value: 'yolov8n', label: 'YOLOv8n (Fast)' },
              { value: 'yolov8s', label: 'YOLOv8s (Balanced)' },
              { value: 'yolov8m', label: 'YOLOv8m (Accurate)' },
            ]}
            onChange={(v) => updateSetting('yoloModel', v)}
          />
          <SliderSetting
            label="Confidence Threshold"
            value={settings.confidenceThreshold}
            min={0.1}
            max={0.9}
            step={0.05}
            unit=""
            onChange={(v) => updateSetting('confidenceThreshold', v)}
          />
          <SelectSetting
            label="Input Size"
            value={settings.inputSize}
            options={[
              { value: 416, label: '416x416' },
              { value: 640, label: '640x640' },
              { value: 1280, label: '1280x1280' },
            ]}
            onChange={(v) => updateSetting('inputSize', parseInt(v))}
          />
          <Toggle
            label="GPU Acceleration"
            description="Use CUDA for faster inference"
            enabled={settings.enableGPU}
            onChange={(v) => updateSetting('enableGPU', v)}
          />
        </SettingsSection>

        {/* LSTM Prediction Settings */}
        <SettingsSection title="LSTM Prediction">
          <SliderSetting
            label="Sequence Length"
            value={settings.sequenceLength}
            min={5}
            max={30}
            step={1}
            unit=" steps"
            onChange={(v) => updateSetting('sequenceLength', v)}
          />
          <SliderSetting
            label="Prediction Horizon"
            value={settings.predictionHorizon}
            min={1}
            max={10}
            step={1}
            unit=" steps"
            onChange={(v) => updateSetting('predictionHorizon', v)}
          />
        </SettingsSection>

        {/* Q-Learning Settings */}
        <SettingsSection title="Q-Learning Agent">
          <Toggle
            label="Enable RL Control"
            description="Use Q-Learning for signal optimization"
            enabled={settings.enableRL}
            onChange={(v) => updateSetting('enableRL', v)}
          />
          <SliderSetting
            label="Learning Rate"
            value={settings.learningRate}
            min={0.01}
            max={0.5}
            step={0.01}
            unit=""
            onChange={(v) => updateSetting('learningRate', v)}
          />
          <SliderSetting
            label="Discount Factor"
            value={settings.discountFactor}
            min={0.5}
            max={0.99}
            step={0.01}
            unit=""
            onChange={(v) => updateSetting('discountFactor', v)}
          />
          <SliderSetting
            label="Epsilon"
            value={settings.epsilon}
            min={0}
            max={1}
            step={0.05}
            unit=""
            onChange={(v) => updateSetting('epsilon', v)}
          />
        </SettingsSection>

        {/* Signal Timing Settings */}
        <SettingsSection title="Signal Timing">
          <SliderSetting
            label="Minimum Green Time"
            value={settings.minGreenTime}
            min={5}
            max={30}
            step={1}
            unit="s"
            onChange={(v) => updateSetting('minGreenTime', v)}
          />
          <SliderSetting
            label="Maximum Green Time"
            value={settings.maxGreenTime}
            min={30}
            max={120}
            step={5}
            unit="s"
            onChange={(v) => updateSetting('maxGreenTime', v)}
          />
          <SliderSetting
            label="Yellow Time"
            value={settings.yellowTime}
            min={2}
            max={6}
            step={1}
            unit="s"
            onChange={(v) => updateSetting('yellowTime', v)}
          />
          <SliderSetting
            label="All-Red Time"
            value={settings.allRedTime}
            min={1}
            max={5}
            step={1}
            unit="s"
            onChange={(v) => updateSetting('allRedTime', v)}
          />
        </SettingsSection>

        {/* Video Source Settings */}
        <SettingsSection title="Video Source">
          <SelectSetting
            label="Source Type"
            value={settings.videoSource}
            options={[
              { value: 'camera', label: 'Webcam' },
              { value: 'file', label: 'Video File' },
              { value: 'rtsp', label: 'RTSP Stream' },
            ]}
            onChange={(v) => updateSetting('videoSource', v)}
          />
          <SelectSetting
            label="Resolution"
            value={settings.resolution}
            options={[
              { value: '320x240', label: '320x240' },
              { value: '640x480', label: '640x480' },
              { value: '1280x720', label: '1280x720 (HD)' },
              { value: '1920x1080', label: '1920x1080 (Full HD)' },
            ]}
            onChange={(v) => updateSetting('resolution', v)}
          />
          <SliderSetting
            label="Frame Skip"
            value={settings.frameSkip}
            min={0}
            max={10}
            step={1}
            unit=" frames"
            onChange={(v) => updateSetting('frameSkip', v)}
          />
        </SettingsSection>

        {/* System Settings */}
        <SettingsSection title="System">
          <Toggle
            label="Emergency Override"
            description="Enable priority signal for emergency vehicles"
            enabled={settings.emergencyOverride}
            onChange={(v) => updateSetting('emergencyOverride', v)}
          />
          <Toggle
            label="Data Logging"
            description="Log traffic data to database"
            enabled={settings.dataLogging}
            onChange={(v) => updateSetting('dataLogging', v)}
          />
          <Toggle
            label="Auto-Save"
            description="Automatically save model weights"
            enabled={settings.autoSave}
            onChange={(v) => updateSetting('autoSave', v)}
          />
          <SliderSetting
            label="Refresh Rate"
            value={settings.refreshRate}
            min={1}
            max={10}
            step={1}
            unit="s"
            onChange={(v) => updateSetting('refreshRate', v)}
          />
        </SettingsSection>
      </div>

      {/* Camera Lane Configuration - Full Width */}
      <CameraLaneConfiguration />

      {/* API Configuration */}
      <SettingsSection title="API Configuration">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Backend URL</label>
            <input
              type="text"
              defaultValue="http://localhost:8000"
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Database URL</label>
            <input
              type="text"
              defaultValue="postgresql://localhost:5432/traffic_db"
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">SUMO Binary Path</label>
            <input
              type="text"
              defaultValue="/usr/share/sumo/bin/sumo"
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Model Weights Path</label>
            <input
              type="text"
              defaultValue="./models/"
              className="w-full bg-gray-700 text-white rounded-lg px-4 py-2 border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
      </SettingsSection>
    </div>
  );
}

export default Settings;
