import React, { useState, useEffect, useRef } from 'react';
import { CameraService } from '../services/api';

// Camera Feed Component for a single lane
function CameraFeed({ laneId, laneName }) {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);
  const imgRef = useRef(null);

  const streamUrl = CameraService.getStreamUrl(laneId);

  // Fetch metrics periodically
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await CameraService.getLaneMetrics(laneId);
        setMetrics(data);
        setError(null);
      } catch (err) {
        console.error(`Failed to fetch metrics for lane ${laneId}:`, err);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 2000);
    return () => clearInterval(interval);
  }, [laneId]);

  const getCongestionColor = (level) => {
    const colors = {
      low: 'bg-green-500',
      medium: 'bg-yellow-500',
      high: 'bg-orange-500',
      critical: 'bg-red-500',
    };
    return colors[level] || 'bg-gray-500';
  };

  const getSignalColor = (state) => {
    const colors = {
      green: 'bg-green-500',
      yellow: 'bg-yellow-500',
      red: 'bg-red-500',
    };
    return colors[state] || 'bg-gray-500';
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      {/* Camera Feed */}
      <div className="relative">
        <img
          ref={imgRef}
          src={streamUrl}
          alt={`${laneName} Camera Feed`}
          className="w-full h-48 object-cover bg-gray-900"
          onError={() => setError('Stream unavailable')}
        />
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75">
            <span className="text-red-400">{error}</span>
          </div>
        )}

        {/* Overlay: Signal Indicator */}
        <div className="absolute top-2 right-2">
          <div className={`w-6 h-6 rounded-full ${getSignalColor(metrics?.signal_state)} shadow-lg`}></div>
        </div>

        {/* Overlay: Emergency Alert */}
        {metrics?.emergency_detected && (
          <div className="absolute top-2 left-2 bg-red-600 text-white px-2 py-1 rounded text-xs animate-pulse">
            EMERGENCY
          </div>
        )}
      </div>

      {/* Metrics Panel */}
      <div className="p-3">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-white font-semibold">{laneName}</h3>
          <span className={`px-2 py-1 rounded text-xs text-white ${getCongestionColor(metrics?.congestion_level)}`}>
            {metrics?.congestion_level?.toUpperCase() || 'N/A'}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-sm">
          <div className="text-center">
            <p className="text-gray-400">Vehicles</p>
            <p className="text-white font-bold text-lg">{metrics?.vehicle_count || 0}</p>
          </div>
          <div className="text-center">
            <p className="text-gray-400">Queue</p>
            <p className="text-white font-bold text-lg">{metrics?.queue_length || 0}</p>
          </div>
          <div className="text-center">
            <p className="text-gray-400">Density</p>
            <p className="text-white font-bold text-lg">{((metrics?.density || 0) * 100).toFixed(0)}%</p>
          </div>
        </div>

        {/* Density Bar */}
        <div className="mt-2">
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${getCongestionColor(metrics?.congestion_level)}`}
              style={{ width: `${(metrics?.density || 0) * 100}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Multi-Lane Camera Grid
function LiveTrafficFeed() {
  const [stats, setStats] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'single'
  const [selectedLane, setSelectedLane] = useState(null);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [selectedCameraForAssign, setSelectedCameraForAssign] = useState(null);
  const [assigningCamera, setAssigningCamera] = useState(false);

  const lanes = [
    { id: 0, name: 'Lane 1 - North' },
    { id: 1, name: 'Lane 2 - East' },
    { id: 2, name: 'Lane 3 - South' },
    { id: 3, name: 'Lane 4 - West' },
  ];

  // Fetch system stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await CameraService.getStats();
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch camera stats:', err);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  // Scan for available cameras
  const scanForCameras = async () => {
    setIsScanning(true);
    try {
      const result = await CameraService.getAvailableCameras(10);
      setAvailableCameras(result.cameras || []);
      setShowCameraModal(true);
    } catch (err) {
      console.error('Failed to scan cameras:', err);
      alert('Failed to scan for cameras. Make sure the backend is running.');
    } finally {
      setIsScanning(false);
    }
  };

  // Assign camera to lane
  const assignCamera = async (cameraIndex, laneId) => {
    setAssigningCamera(true);
    try {
      await CameraService.assignCameraToLane(cameraIndex, laneId);
      alert(`Camera ${cameraIndex} assigned to Lane ${laneId + 1} successfully!`);
      setShowCameraModal(false);
      setSelectedCameraForAssign(null);
    } catch (err) {
      console.error('Failed to assign camera:', err);
      alert('Failed to assign camera. Please try again.');
    } finally {
      setAssigningCamera(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white">Live Traffic Feed</h2>
          <p className="text-gray-400 text-sm">
            {stats?.active_cameras || 0} cameras active | {stats?.total_vehicles || 0} total vehicles
          </p>
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={scanForCameras}
            disabled={isScanning}
            className={`px-3 py-1 rounded flex items-center ${
              isScanning ? 'bg-gray-600 cursor-wait' : 'bg-green-600 hover:bg-green-700'
            } text-white`}
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
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Scan Cameras
              </>
            )}
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`px-3 py-1 rounded ${viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}
          >
            Grid View
          </button>
          <button
            onClick={() => setViewMode('single')}
            className={`px-3 py-1 rounded ${viewMode === 'single' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}
          >
            Single View
          </button>
        </div>
      </div>

      {/* Camera Scanner Modal */}
      {showCameraModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-white">Available Cameras</h3>
              <button
                onClick={() => setShowCameraModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {availableCameras.length === 0 ? (
              <div className="text-center py-8">
                <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p className="text-gray-400">No cameras detected on this system.</p>
                <p className="text-gray-500 text-sm mt-2">Make sure your cameras are connected and try again.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-400 text-sm mb-4">
                  Found {availableCameras.length} camera(s). Select a camera and assign it to a lane.
                </p>
                
                {availableCameras.map((camera) => (
                  <div
                    key={camera.index}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${
                      selectedCameraForAssign === camera.index
                        ? 'border-blue-500 bg-blue-500 bg-opacity-10'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                    onClick={() => setSelectedCameraForAssign(camera.index)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="text-white font-semibold">{camera.name}</h4>
                        <p className="text-gray-400 text-sm">Device Index: {camera.index}</p>
                        <p className="text-gray-400 text-sm">
                          Resolution: {camera.resolution[0]}x{camera.resolution[1]}
                        </p>
                        <p className="text-gray-400 text-sm">FPS: {camera.fps}</p>
                        <p className="text-gray-500 text-xs">Backend: {camera.backend}</p>
                      </div>
                      <div className="flex items-center">
                        <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                        <span className="text-green-400 text-sm">Available</span>
                      </div>
                    </div>
                  </div>
                ))}

                {selectedCameraForAssign !== null && (
                  <div className="mt-6 pt-4 border-t border-gray-700">
                    <p className="text-gray-300 mb-3">Assign Camera {selectedCameraForAssign} to:</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {lanes.map((lane) => (
                        <button
                          key={lane.id}
                          onClick={() => assignCamera(selectedCameraForAssign, lane.id)}
                          disabled={assigningCamera}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded transition-colors"
                        >
                          {lane.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="mt-6 flex justify-end space-x-2">
              <button
                onClick={scanForCameras}
                disabled={isScanning}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
              >
                Rescan
              </button>
              <button
                onClick={() => setShowCameraModal(false)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Grid View */}
      {viewMode === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {lanes.map((lane) => (
            <div 
              key={lane.id} 
              onClick={() => { setSelectedLane(lane.id); setViewMode('single'); }}
              className="cursor-pointer hover:ring-2 hover:ring-blue-500 rounded-lg transition-all"
            >
              <CameraFeed laneId={lane.id} laneName={lane.name} />
            </div>
          ))}
        </div>
      )}

      {/* Single View */}
      {viewMode === 'single' && (
        <div className="space-y-4">
          {/* Lane Selector */}
          <div className="flex space-x-2">
            {lanes.map((lane) => (
              <button
                key={lane.id}
                onClick={() => setSelectedLane(lane.id)}
                className={`px-4 py-2 rounded ${
                  selectedLane === lane.id ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'
                }`}
              >
                {lane.name}
              </button>
            ))}
          </div>

          {/* Large Camera View */}
          {selectedLane !== null && (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <img
                src={CameraService.getStreamUrl(selectedLane)}
                alt={`Lane ${selectedLane + 1} Camera`}
                className="w-full h-96 object-contain bg-gray-900"
              />
            </div>
          )}
        </div>
      )}

      {/* Aggregate Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <p className="text-gray-400 text-sm">Active Cameras</p>
            <p className="text-2xl font-bold text-green-400">{stats.active_cameras}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <p className="text-gray-400 text-sm">Total Vehicles</p>
            <p className="text-2xl font-bold text-blue-400">{stats.total_vehicles}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <p className="text-gray-400 text-sm">Emergencies</p>
            <p className="text-2xl font-bold text-red-400">{stats.emergency_count}</p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <p className="text-gray-400 text-sm">Detector</p>
            <p className={`text-2xl font-bold ${stats.detector_available ? 'text-green-400' : 'text-red-400'}`}>
              {stats.detector_available ? 'Online' : 'Offline'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default LiveTrafficFeed;
export { CameraFeed };
