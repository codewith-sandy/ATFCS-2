import React, { useState, useEffect } from 'react';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { AnalyticsService, PredictionService } from '../services/api';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

// Performance Card Component
function PerformanceCard({ title, current, baseline, unit, improved }) {
  const improvement = baseline > 0 ? ((baseline - current) / baseline * 100).toFixed(1) : 0;
  
  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <h4 className="text-sm font-medium text-gray-400">{title}</h4>
      <div className="mt-2 flex items-baseline justify-between">
        <p className="text-3xl font-bold text-white">
          {current}{unit}
        </p>
        <span className={`text-sm ${improved ? 'text-green-400' : 'text-red-400'}`}>
          {improved ? '↓' : '↑'} {Math.abs(improvement)}% vs baseline
        </span>
      </div>
      <div className="mt-3 w-full bg-gray-700 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${improved ? 'bg-green-500' : 'bg-red-500'}`}
          style={{ width: `${Math.min(100, Math.abs(improvement))}%` }}
        ></div>
      </div>
    </div>
  );
}

// Main Analytics Component
function Analytics() {
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [dateRange, setDateRange] = useState('24h');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [metricsData, historyData] = await Promise.all([
          AnalyticsService.getPerformanceMetrics(),
          PredictionService.getHistory(),
        ]);
        
        setMetrics(metricsData);
        setHistory(historyData);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching analytics:', error);
        setLoading(false);
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000); // Update every 30 seconds
    
    return () => clearInterval(interval);
  }, [dateRange]);

  // Generate sample data for demonstration
  const generateTimeLabels = () => {
    const labels = [];
    const now = new Date();
    for (let i = 23; i >= 0; i--) {
      const hour = new (Date)(now - i * 60 * 60 * 1000);
      labels.push(hour.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
    }
    return labels;
  };

  // Traffic Flow Chart Data
  const flowChartData = {
    labels: generateTimeLabels(),
    datasets: [
      {
        label: 'Actual Traffic',
        data: Array(24).fill(0).map(() => Math.floor(Math.random() * 50) + 20),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Predicted Traffic',
        data: Array(24).fill(0).map(() => Math.floor(Math.random() * 50) + 18),
        borderColor: 'rgb(168, 85, 247)',
        backgroundColor: 'rgba(168, 85, 247, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  // Waiting Time Chart Data
  const waitingTimeData = {
    labels: ['North', 'East', 'South', 'West'],
    datasets: [
      {
        label: 'Avg Waiting Time (s)',
        data: [25, 32, 28, 35],
        backgroundColor: [
          'rgba(59, 130, 246, 0.7)',
          'rgba(16, 185, 129, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(239, 68, 68, 0.7)',
        ],
        borderColor: [
          'rgb(59, 130, 246)',
          'rgb(16, 185, 129)',
          'rgb(245, 158, 11)',
          'rgb(239, 68, 68)',
        ],
        borderWidth: 1,
      },
    ],
  };

  // Vehicle Distribution Chart Data
  const vehicleDistribution = {
    labels: ['Cars', 'Trucks', 'Buses', 'Motorcycles', 'Emergency'],
    datasets: [
      {
        data: [65, 15, 10, 8, 2],
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(168, 85, 247, 0.8)',
          'rgba(239, 68, 68, 0.8)',
        ],
        borderColor: [
          'rgb(59, 130, 246)',
          'rgb(245, 158, 11)',
          'rgb(16, 185, 129)',
          'rgb(168, 85, 247)',
          'rgb(239, 68, 68)',
        ],
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#9ca3af',
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(75, 85, 99, 0.3)',
        },
        ticks: {
          color: '#9ca3af',
          maxTicksLimit: 12,
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

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
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
      {/* Header with Date Range Selector */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Traffic Analytics</h2>
        <div className="flex space-x-2">
          {['1h', '24h', '7d', '30d'].map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                dateRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <PerformanceCard
          title="Average Waiting Time"
          current={28.5}
          baseline={45}
          unit="s"
          improved={true}
        />
        <PerformanceCard
          title="Queue Length"
          current={12}
          baseline={18}
          unit=" vehicles"
          improved={true}
        />
        <PerformanceCard
          title="Throughput"
          current={245}
          baseline={205}
          unit="/hr"
          improved={true}
        />
        <PerformanceCard
          title="Emergency Response"
          current={15}
          baseline={25}
          unit="s"
          improved={true}
        />
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Traffic Flow Over Time */}
        <div className="card lg:col-span-2">
          <h3 className="card-header">Traffic Flow Analysis</h3>
          <div className="h-80">
            <Line data={flowChartData} options={chartOptions} />
          </div>
        </div>

        {/* Waiting Time by Lane */}
        <div className="card">
          <h3 className="card-header">Waiting Time by Lane</h3>
          <div className="h-64">
            <Bar data={waitingTimeData} options={chartOptions} />
          </div>
        </div>

        {/* Vehicle Distribution */}
        <div className="card">
          <h3 className="card-header">Vehicle Distribution</h3>
          <div className="h-64">
            <Doughnut data={vehicleDistribution} options={doughnutOptions} />
          </div>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="card">
        <h3 className="card-header">System Performance Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-4">
          <div className="text-center">
            <p className="text-4xl font-bold text-green-400">32-45%</p>
            <p className="text-sm text-gray-400 mt-1">Waiting Time Reduction</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold text-blue-400">28-40%</p>
            <p className="text-sm text-gray-400 mt-1">Queue Length Reduction</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold text-purple-400">19%</p>
            <p className="text-sm text-gray-400 mt-1">Throughput Improvement</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold text-yellow-400">40%</p>
            <p className="text-sm text-gray-400 mt-1">Faster Emergency Response</p>
          </div>
        </div>
      </div>

      {/* Model Performance */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="card-header">YOLOv8 Detection</h3>
          <div className="space-y-3 mt-4">
            <div className="flex justify-between">
              <span className="text-gray-400">Accuracy</span>
              <span className="text-white">94.5%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">FPS</span>
              <span className="text-white">30</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Confidence Threshold</span>
              <span className="text-white">0.25</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="card-header">LSTM Prediction</h3>
          <div className="space-y-3 mt-4">
            <div className="flex justify-between">
              <span className="text-gray-400">MAE</span>
              <span className="text-white">2.3 vehicles</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">RMSE</span>
              <span className="text-white">3.1</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Sequence Length</span>
              <span className="text-white">15</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="card-header">Q-Learning Agent</h3>
          <div className="space-y-3 mt-4">
            <div className="flex justify-between">
              <span className="text-gray-400">Episodes</span>
              <span className="text-white">5,000</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Epsilon</span>
              <span className="text-white">0.1</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Avg Reward</span>
              <span className="text-green-400">+85.2</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Analytics;
