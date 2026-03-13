import React, { useState, useEffect } from 'react';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { TrafficService, PredictionService, SignalService } from '../services/api';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

// Metric Card Component
function MetricCard({ title, value, unit, trend, icon, color }) {
  const trendColors = {
    up: 'text-green-400',
    down: 'text-red-400',
    stable: 'text-gray-400',
  };

  const bgColors = {
    blue: 'from-blue-900 to-blue-800',
    green: 'from-green-900 to-green-800',
    yellow: 'from-yellow-900 to-yellow-800',
    red: 'from-red-900 to-red-800',
    purple: 'from-purple-900 to-purple-800',
  };

  return (
    <div className={`metric-card bg-gradient-to-br ${bgColors[color] || bgColors.blue}`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm text-gray-400">{title}</p>
          <p className="metric-value mt-1">
            {value}
            {unit && <span className="text-lg ml-1">{unit}</span>}
          </p>
          {trend && (
            <p className={`text-sm mt-1 ${trendColors[trend.direction]}`}>
              {trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'}{' '}
              {trend.value}
            </p>
          )}
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}

// Traffic Light Component
function TrafficLight({ phases, currentPhase }) {
  const getLightClass = (phaseIndex, lightType) => {
    const isActive = currentPhase === phaseIndex;
    
    if (!isActive) return 'light-off';
    
    switch (lightType) {
      case 'green':
        return phaseIndex % 2 === 0 ? 'light-green' : 'light-off';
      case 'yellow':
        return phaseIndex % 2 === 1 ? 'light-yellow' : 'light-off';
      case 'red':
        return !isActive ? 'light-red' : 'light-off';
      default:
        return 'light-off';
    }
  };

  return (
    <div className="flex justify-center space-x-8">
      {['N-S', 'E-W'].map((direction, idx) => (
        <div key={direction} className="text-center">
          <p className="text-sm text-gray-400 mb-2">{direction}</p>
          <div className="bg-gray-700 rounded-lg p-2 inline-block">
            <div className={`w-8 h-8 rounded-full mb-2 mx-auto ${currentPhase === idx * 2 ? 'light-off' : 'light-red'}`}></div>
            <div className={`w-8 h-8 rounded-full mb-2 mx-auto ${currentPhase === idx * 2 + 1 ? 'light-yellow' : 'light-off'}`}></div>
            <div className={`w-8 h-8 rounded-full mx-auto ${currentPhase === idx * 2 ? 'light-green' : 'light-off'}`}></div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Lane Status Component
function LaneStatus({ lanes }) {
  const laneNames = ['North', 'East', 'South', 'West'];
  
  return (
    <div className="grid grid-cols-2 gap-4">
      {laneNames.map((name, idx) => {
        const lane = lanes[idx] || { vehicle_count: 0, queue_length: 0, density: 0 };
        return (
          <div key={name} className="bg-gray-700 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-300">{name} Lane</p>
            <div className="mt-2 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">Vehicles</span>
                <span className="text-white">{lane.vehicle_count}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">Queue</span>
                <span className="text-white">{lane.queue_length}</span>
              </div>
              <div className="w-full bg-gray-600 rounded-full h-2 mt-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${(lane.density || 0) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Main Dashboard Component
function Dashboard() {
  const [trafficData, setTrafficData] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [signals, setSignals] = useState(null);
  const [vehicleHistory, setVehicleHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [traffic, pred, sigs] = await Promise.all([
          TrafficService.getLiveTraffic(),
          PredictionService.getCurrentPrediction(),
          SignalService.getCurrentSignals(),
        ]);

        setTrafficData(traffic);
        setPrediction(pred);
        setSignals(sigs);

        // Update vehicle history
        setVehicleHistory((prev) => {
          const newHistory = [...prev, { time: new Date().toLocaleTimeString(), count: traffic.vehicle_count || 0 }];
          return newHistory.slice(-20); // Keep last 20 points
        });

        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to fetch traffic data');
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000); // Update every 2 seconds

    return () => clearInterval(interval);
  }, []);

  // Chart data
  const vehicleChartData = {
    labels: vehicleHistory.map((h) => h.time),
    datasets: [
      {
        label: 'Vehicle Count',
        data: vehicleHistory.map((h) => h.count),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9ca3af',
        },
      },
      y: {
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9ca3af',
        },
      },
    },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Emergency Alert */}
      {trafficData?.emergency_active && (
        <div className="emergency-alert flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-3xl mr-4">🚨</span>
            <div>
              <p className="font-bold text-red-300">Emergency Vehicle Detected</p>
              <p className="text-sm text-red-200">Signal override in progress</p>
            </div>
          </div>
          <span className="text-red-300 animate-pulse">PRIORITY MODE</span>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Vehicle Count"
          value={trafficData?.vehicle_count || 0}
          icon="🚗"
          color="blue"
          trend={{ direction: 'stable', value: 'Real-time' }}
        />
        <MetricCard
          title="Queue Length"
          value={trafficData?.queue_length || 0}
          icon="📊"
          color="yellow"
        />
        <MetricCard
          title="Predicted Count"
          value={Math.round(prediction?.predicted_vehicle_count || 0)}
          icon="🔮"
          color="purple"
          trend={{ direction: prediction?.trend || 'stable', value: prediction?.trend }}
        />
        <MetricCard
          title="Green Time"
          value={signals?.green_time || 30}
          unit="s"
          icon="🟢"
          color="green"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Vehicle Count Chart */}
        <div className="lg:col-span-2 card">
          <h3 className="card-header">Real-time Vehicle Count</h3>
          <div className="h-64">
            <Line data={vehicleChartData} options={chartOptions} />
          </div>
        </div>

        {/* Traffic Light Status */}
        <div className="card">
          <h3 className="card-header">Signal Status</h3>
          <TrafficLight
            phases={signals?.phases || []}
            currentPhase={signals?.current_phase || 0}
          />
          <div className="mt-4 text-center">
            <p className="text-sm text-gray-400">Current Phase</p>
            <p className="text-2xl font-bold text-white">
              {signals?.phases?.[signals?.current_phase]?.description || 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Lane Status */}
      <div className="card">
        <h3 className="card-header">Lane Status</h3>
        <LaneStatus lanes={trafficData?.analytics?.lanes || {}} />
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Avg Waiting Time</p>
          <p className="text-2xl font-bold text-white">
            {trafficData?.analytics?.avg_vehicle_count?.toFixed(1) || 0}s
          </p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Throughput</p>
          <p className="text-2xl font-bold text-white">
            {trafficData?.analytics?.states_collected || 0} vehicles/hr
          </p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">Signal Changes</p>
          <p className="text-2xl font-bold text-white">
            {trafficData?.analytics?.current_phase || 0}
          </p>
        </div>
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <p className="text-sm text-gray-400">System Status</p>
          <p className="text-2xl font-bold text-green-400">
            {trafficData?.is_running ? 'Active' : 'Standby'}
          </p>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
