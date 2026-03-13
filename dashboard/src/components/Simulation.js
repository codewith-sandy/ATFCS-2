import React, { useState, useEffect } from 'react';
import { SignalService, TrafficService } from '../services/api';

// Intersection Visualization Component
function IntersectionVisualization({ trafficState, signalPhase }) {
  const getLaneColor = (density) => {
    if (density > 0.7) return 'bg-red-500';
    if (density > 0.4) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getSignalColor = (direction, phase) => {
    // Phase 0: N-S green, Phase 1: E-W green
    if (phase % 2 === 0 && (direction === 'N' || direction === 'S')) {
      return 'bg-green-500 animate-pulse';
    }
    if (phase % 2 === 1 && (direction === 'E' || direction === 'W')) {
      return 'bg-green-500 animate-pulse';
    }
    return 'bg-red-500';
  };

  return (
    <div className="relative w-full h-96 bg-gray-800 rounded-xl overflow-hidden">
      {/* Road Background */}
      <svg className="w-full h-full" viewBox="0 0 400 400">
        {/* Vertical Road */}
        <rect x="150" y="0" width="100" height="400" fill="#374151" />
        {/* Horizontal Road */}
        <rect x="0" y="150" width="400" height="100" fill="#374151" />
        {/* Intersection Center */}
        <rect x="150" y="150" width="100" height="100" fill="#4B5563" />
        
        {/* Lane Markings - Vertical */}
        <line x1="200" y1="0" x2="200" y2="150" stroke="#FFF" strokeWidth="2" strokeDasharray="10,10" />
        <line x1="200" y1="250" x2="200" y2="400" stroke="#FFF" strokeWidth="2" strokeDasharray="10,10" />
        
        {/* Lane Markings - Horizontal */}
        <line x1="0" y1="200" x2="150" y2="200" stroke="#FFF" strokeWidth="2" strokeDasharray="10,10" />
        <line x1="250" y1="200" x2="400" y2="200" stroke="#FFF" strokeWidth="2" strokeDasharray="10,10" />
        
        {/* Stop Lines */}
        <line x1="150" y1="145" x2="195" y2="145" stroke="#FFF" strokeWidth="3" />
        <line x1="205" y1="255" x2="250" y2="255" stroke="#FFF" strokeWidth="3" />
        <line x1="145" y1="205" x2="145" y2="250" stroke="#FFF" strokeWidth="3" />
        <line x1="255" y1="150" x2="255" y2="195" stroke="#FFF" strokeWidth="3" />
        
        {/* Crosswalks */}
        <g fill="#FFF" opacity="0.7">
          <rect x="152" y="140" width="8" height="4" />
          <rect x="165" y="140" width="8" height="4" />
          <rect x="178" y="140" width="8" height="4" />
          <rect x="191" y="140" width="8" height="4" />
        </g>
      </svg>
      
      {/* Traffic Signals */}
      <div className="absolute top-32 left-32">
        <div className={`w-4 h-4 rounded-full ${getSignalColor('W', signalPhase)}`}></div>
      </div>
      <div className="absolute top-32 right-32">
        <div className={`w-4 h-4 rounded-full ${getSignalColor('E', signalPhase)}`}></div>
      </div>
      <div className="absolute top-8 left-1/2 transform -translate-x-1/2">
        <div className={`w-4 h-4 rounded-full ${getSignalColor('N', signalPhase)}`}></div>
      </div>
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">
        <div className={`w-4 h-4 rounded-full ${getSignalColor('S', signalPhase)}`}></div>
      </div>
      
      {/* Vehicle Indicators (simplified) */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 text-center">
        <span className="text-xs text-gray-300">North</span>
        <span className="block text-lg font-bold text-white">{trafficState?.lanes?.north?.vehicle_count || 0}</span>
      </div>
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-center">
        <span className="text-xs text-gray-300">South</span>
        <span className="block text-lg font-bold text-white">{trafficState?.lanes?.south?.vehicle_count || 0}</span>
      </div>
      <div className="absolute left-4 top-1/2 transform -translate-y-1/2 text-center">
        <span className="text-xs text-gray-300">West</span>
        <span className="block text-lg font-bold text-white">{trafficState?.lanes?.west?.vehicle_count || 0}</span>
      </div>
      <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-center">
        <span className="text-xs text-gray-300">East</span>
        <span className="block text-lg font-bold text-white">{trafficState?.lanes?.east?.vehicle_count || 0}</span>
      </div>
    </div>
  );
}

// Simulation Control Panel
function SimulationControls({ onStart, onStop, onStep, isRunning, speed, onSpeedChange }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <h4 className="text-sm font-medium text-gray-400 mb-4">Simulation Controls</h4>
      
      <div className="flex space-x-3 mb-4">
        <button
          onClick={onStart}
          disabled={isRunning}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
            isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-green-600 text-white hover:bg-green-700'
          }`}
        >
          ▶ Start
        </button>
        <button
          onClick={onStop}
          disabled={!isRunning}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
            !isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-red-600 text-white hover:bg-red-700'
          }`}
        >
          ⬛ Stop
        </button>
        <button
          onClick={onStep}
          disabled={isRunning}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
            isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          ⏭ Step
        </button>
      </div>
      
      <div>
        <label className="text-sm text-gray-400">Simulation Speed</label>
        <input
          type="range"
          min="0.5"
          max="5"
          step="0.5"
          value={speed}
          onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
          className="w-full mt-2"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>0.5x</span>
          <span>{speed}x</span>
          <span>5x</span>
        </div>
      </div>
    </div>
  );
}

// Main Simulation Component
function Simulation() {
  const [isRunning, setIsRunning] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [step, setStep] = useState(0);
  const [trafficState, setTrafficState] = useState({
    lanes: {
      north: { vehicle_count: 5, queue_length: 3 },
      south: { vehicle_count: 8, queue_length: 5 },
      east: { vehicle_count: 4, queue_length: 2 },
      west: { vehicle_count: 6, queue_length: 4 },
    },
  });
  const [signalPhase, setSignalPhase] = useState(0);
  const [rlEnabled, setRlEnabled] = useState(true);
  const [simulationLog, setSimulationLog] = useState([]);

  // Simulation loop
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setStep((prev) => prev + 1);
      
      // Update traffic state (simulated)
      setTrafficState((prev) => ({
        lanes: {
          north: {
            vehicle_count: Math.max(0, prev.lanes.north.vehicle_count + Math.floor(Math.random() * 3) - 1),
            queue_length: Math.max(0, prev.lanes.north.queue_length + Math.floor(Math.random() * 2) - 1),
          },
          south: {
            vehicle_count: Math.max(0, prev.lanes.south.vehicle_count + Math.floor(Math.random() * 3) - 1),
            queue_length: Math.max(0, prev.lanes.south.queue_length + Math.floor(Math.random() * 2) - 1),
          },
          east: {
            vehicle_count: Math.max(0, prev.lanes.east.vehicle_count + Math.floor(Math.random() * 3) - 1),
            queue_length: Math.max(0, prev.lanes.east.queue_length + Math.floor(Math.random() * 2) - 1),
          },
          west: {
            vehicle_count: Math.max(0, prev.lanes.west.vehicle_count + Math.floor(Math.random() * 3) - 1),
            queue_length: Math.max(0, prev.lanes.west.queue_length + Math.floor(Math.random() * 2) - 1),
          },
        },
      }));
      
      // Change signal phase every ~30 steps
      if (step % 30 === 0) {
        setSignalPhase((prev) => (prev + 1) % 4);
        addLog(`Phase changed to ${(signalPhase + 1) % 4}`);
      }
    }, 1000 / speed);

    return () => clearInterval(interval);
  }, [isRunning, speed, step, signalPhase]);

  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setSimulationLog((prev) => [...prev.slice(-49), { timestamp, message }]);
  };

  const handleStart = async () => {
    setIsRunning(true);
    addLog('Simulation started');
    try {
      await SignalService.startTraining();
    } catch (error) {
      // Continue with local simulation if API fails
    }
  };

  const handleStop = () => {
    setIsRunning(false);
    addLog('Simulation stopped');
  };

  const handleStep = () => {
    setStep((prev) => prev + 1);
    addLog(`Manual step: ${step + 1}`);
  };

  const handleEmergencyTest = async () => {
    addLog('Emergency vehicle detected! Activating override...');
    try {
      await TrafficService.triggerEmergency('north');
      setSignalPhase(0); // Set N-S to green
      setTimeout(() => {
        addLog('Emergency override completed');
      }, 3000);
    } catch (error) {
      addLog('Emergency override (simulated)');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">SUMO Simulation</h2>
        <div className="flex items-center space-x-4">
          <span className={`px-3 py-1 rounded-full text-sm ${isRunning ? 'bg-green-600' : 'bg-gray-600'}`}>
            {isRunning ? 'Running' : 'Stopped'}
          </span>
          <span className="text-gray-400">Step: {step}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Intersection Visualization */}
        <div className="lg:col-span-2 card">
          <h3 className="card-header">Intersection View</h3>
          <IntersectionVisualization trafficState={trafficState} signalPhase={signalPhase} />
        </div>

        {/* Control Panel */}
        <div className="space-y-6">
          <SimulationControls
            onStart={handleStart}
            onStop={handleStop}
            onStep={handleStep}
            isRunning={isRunning}
            speed={speed}
            onSpeedChange={setSpeed}
          />

          {/* RL Agent Controls */}
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <h4 className="text-sm font-medium text-gray-400 mb-4">Q-Learning Agent</h4>
            <div className="flex items-center justify-between mb-4">
              <span className="text-white">RL Control</span>
              <button
                onClick={() => setRlEnabled(!rlEnabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  rlEnabled ? 'bg-blue-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    rlEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Epsilon</span>
                <span className="text-white">0.1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Learning Rate</span>
                <span className="text-white">0.1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Actions</span>
                <span className="text-white">[10, 20, 30, 40]s</span>
              </div>
            </div>
          </div>

          {/* Emergency Test */}
          <button
            onClick={handleEmergencyTest}
            className="w-full py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
          >
            🚨 Test Emergency Override
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Total Vehicles</p>
          <p className="text-2xl font-bold text-white">
            {Object.values(trafficState.lanes).reduce((sum, lane) => sum + lane.vehicle_count, 0)}
          </p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Queue Length</p>
          <p className="text-2xl font-bold text-white">
            {Object.values(trafficState.lanes).reduce((sum, lane) => sum + lane.queue_length, 0)}
          </p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Current Phase</p>
          <p className="text-2xl font-bold text-white">{signalPhase}</p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Mode</p>
          <p className="text-2xl font-bold text-blue-400">{rlEnabled ? 'RL' : 'Fixed'}</p>
        </div>
      </div>

      {/* Simulation Log */}
      <div className="card">
        <h3 className="card-header">Simulation Log</h3>
        <div className="h-48 overflow-y-auto bg-gray-900 rounded-lg p-3 font-mono text-sm">
          {simulationLog.length === 0 ? (
            <p className="text-gray-500">No events logged yet...</p>
          ) : (
            simulationLog.map((log, idx) => (
              <p key={idx} className="text-gray-300">
                <span className="text-blue-400">[{log.timestamp}]</span> {log.message}
              </p>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default Simulation;
