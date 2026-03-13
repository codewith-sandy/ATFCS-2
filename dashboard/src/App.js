import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import Analytics from './components/Analytics';
import Simulation from './components/Simulation';
import Settings from './components/Settings';
import LiveTrafficFeed from './components/LiveTrafficFeed';
import PredictionVisualization from './components/PredictionVisualization';
import DatasetUpload from './components/DatasetUpload';
import AdminPanel from './components/AdminPanel';
import { TrafficService } from './services/api';

// Navigation component
function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', name: 'Dashboard', icon: '📊' },
    { path: '/live', name: 'Live Feed', icon: '📹' },
    { path: '/predictions', name: 'AI Predictions', icon: '🤖' },
    { path: '/analytics', name: 'Analytics', icon: '📈' },
    { path: '/training', name: 'Training', icon: '🎓' },
    { path: '/simulation', name: 'Simulation', icon: '🚗' },
    { path: '/admin', name: 'Admin', icon: '⚙️' },
  ];

  return (
    <nav className="bg-gray-900 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <span className="text-2xl mr-2">🚦</span>
              <span className="text-xl font-bold text-white">
                Adaptive Traffic Control
              </span>
            </div>
          </div>
          <div className="flex items-center">
            <div className="hidden md:block mr-6">
              <div className="flex items-baseline space-x-4">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`${
                      location.pathname === item.path
                        ? 'bg-gray-800 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    } px-3 py-2 rounded-md text-sm font-medium transition-colors`}
                  >
                    <span className="mr-2">{item.icon}</span>
                    {item.name}
                  </Link>
                ))}
              </div>
            </div>
            <StatusIndicator />
          </div>
        </div>
      </div>
    </nav>
  );
}

// System status indicator
function StatusIndicator() {
  const [status, setStatus] = useState({ healthy: false, services: {} });

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const health = await TrafficService.getHealth();
        setStatus({ healthy: true, services: health.services });
      } catch (error) {
        setStatus({ healthy: false, services: {} });
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center space-x-2">
      <span className={`status-dot ${status.healthy ? 'status-online' : 'status-offline'}`}></span>
      <span className="text-sm text-gray-300">
        {status.healthy ? 'System Online' : 'System Offline'}
      </span>
    </div>
  );
}

// Main App component
function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900">
        <Navigation />
        <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/live" element={<LiveTrafficFeed />} />
            <Route path="/predictions" element={<PredictionVisualization />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/training" element={<DatasetUpload />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
