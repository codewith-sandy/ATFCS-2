import React, { useState, useEffect, useCallback } from 'react';
import { DatasetService, ModelTrainingService } from '../services/api';

// File Upload Component
function FileUpload({ onUpload, acceptedTypes, label }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onUpload(files[0], setUploadProgress, setIsUploading);
    }
  }, [onUpload]);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      onUpload(files[0], setUploadProgress, setIsUploading);
    }
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        isDragging ? 'border-blue-500 bg-blue-900/20' : 'border-gray-600 hover:border-gray-500'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isUploading ? (
        <div className="space-y-2">
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <p className="text-gray-400">Uploading... {uploadProgress}%</p>
        </div>
      ) : (
        <>
          <div className="text-4xl mb-4">📁</div>
          <p className="text-gray-300 mb-2">{label || 'Drag and drop files here'}</p>
          <p className="text-gray-500 text-sm mb-4">or</p>
          <label className="px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors">
            Browse Files
            <input
              type="file"
              className="hidden"
              accept={acceptedTypes}
              onChange={handleFileSelect}
            />
          </label>
          <p className="text-gray-500 text-xs mt-4">
            Supported: {acceptedTypes || 'All files'}
          </p>
        </>
      )}
    </div>
  );
}

// Dataset Card
function DatasetCard({ dataset, onDelete, onSelect, selected }) {
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getTypeIcon = (type) => {
    const icons = {
      video: '🎬',
      traffic_counts: '📊',
      prediction_logs: '📈',
    };
    return icons[type] || '📄';
  };

  return (
    <div
      className={`bg-gray-800 rounded-lg p-4 cursor-pointer transition-all ${
        selected ? 'ring-2 ring-blue-500' : 'hover:bg-gray-750'
      }`}
      onClick={() => onSelect && onSelect(dataset)}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">{getTypeIcon(dataset.dataset_type)}</span>
          <div>
            <h4 className="text-white font-medium">{dataset.name}</h4>
            <p className="text-gray-400 text-sm">{dataset.dataset_type}</p>
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(dataset.dataset_id); }}
          className="text-gray-500 hover:text-red-500 transition-colors"
        >
          🗑️
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-4 text-sm">
        <div>
          <p className="text-gray-500">Size</p>
          <p className="text-gray-300">{formatSize(dataset.size_bytes)}</p>
        </div>
        <div>
          <p className="text-gray-500">Samples</p>
          <p className="text-gray-300">{dataset.num_samples}</p>
        </div>
        <div>
          <p className="text-gray-500">Status</p>
          <p className={dataset.processed ? 'text-green-400' : 'text-yellow-400'}>
            {dataset.processed ? 'Processed' : 'Pending'}
          </p>
        </div>
      </div>

      {dataset.features && dataset.features.length > 0 && (
        <div className="mt-3">
          <p className="text-gray-500 text-xs">Features:</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {dataset.features.slice(0, 5).map((feature, idx) => (
              <span key={idx} className="px-2 py-1 bg-gray-700 rounded text-xs text-gray-300">
                {feature}
              </span>
            ))}
            {dataset.features.length > 5 && (
              <span className="px-2 py-1 bg-gray-700 rounded text-xs text-gray-400">
                +{dataset.features.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}

      <p className="text-gray-500 text-xs mt-3">
        Uploaded: {formatDate(dataset.created_at)}
      </p>
    </div>
  );
}

// Dataset Management Component
function DatasetManagement() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState('all');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadType, setUploadType] = useState('traffic_counts');

  const fetchDatasets = async () => {
    try {
      const data = await DatasetService.listDatasets(
        selectedType === 'all' ? null : selectedType
      );
      setDatasets(data.datasets || []);
    } catch (err) {
      console.error('Failed to fetch datasets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, [selectedType]);

  const handleUpload = async (file, setProgress, setUploading) => {
    setUploading(true);
    try {
      await DatasetService.uploadDataset(
        file,
        file.name,
        uploadType,
        '',
        setProgress
      );
      setUploadOpen(false);
      fetchDatasets();
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (datasetId) => {
    if (window.confirm('Are you sure you want to delete this dataset?')) {
      try {
        await DatasetService.deleteDataset(datasetId);
        fetchDatasets();
      } catch (err) {
        console.error('Delete failed:', err);
      }
    }
  };

  const getAcceptedTypes = () => {
    const types = {
      video: '.mp4,.avi,.mov,.mkv,.webm',
      traffic_counts: '.csv,.json',
      prediction_logs: '.csv,.json',
    };
    return types[uploadType] || '*/*';
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-white">Dataset Management</h2>
        <button
          onClick={() => setUploadOpen(!uploadOpen)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Upload Dataset
        </button>
      </div>

      {/* Upload Panel */}
      {uploadOpen && (
        <div className="bg-gray-800 rounded-lg p-4 space-y-4">
          <h3 className="text-white font-medium">Upload New Dataset</h3>
          
          <div>
            <label className="text-gray-400 text-sm">Dataset Type</label>
            <select
              value={uploadType}
              onChange={(e) => setUploadType(e.target.value)}
              className="w-full mt-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
            >
              <option value="traffic_counts">Traffic Counts (CSV/JSON)</option>
              <option value="prediction_logs">Prediction Logs (CSV/JSON)</option>
              <option value="video">Traffic Video (MP4/AVI)</option>
            </select>
          </div>

          <FileUpload
            onUpload={handleUpload}
            acceptedTypes={getAcceptedTypes()}
            label={`Upload ${uploadType.replace('_', ' ')} file`}
          />
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex space-x-2">
        {['all', 'video', 'traffic_counts', 'prediction_logs'].map((type) => (
          <button
            key={type}
            onClick={() => setSelectedType(type)}
            className={`px-3 py-1 rounded-lg transition-colors ${
              selectedType === type
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {type === 'all' ? 'All' : type.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Dataset Grid */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : datasets.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <p className="text-4xl mb-2">📭</p>
          <p>No datasets found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((dataset) => (
            <DatasetCard
              key={dataset.dataset_id}
              dataset={dataset}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Training Job Card
function TrainingJobCard({ job }) {
  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-gray-500',
      preprocessing: 'bg-yellow-500',
      training: 'bg-blue-500',
      evaluating: 'bg-purple-500',
      completed: 'bg-green-500',
      failed: 'bg-red-500',
      cancelled: 'bg-gray-600',
    };
    return colors[status] || 'bg-gray-500';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="text-white font-medium">{job.model_type.toUpperCase()} Training</h4>
          <p className="text-gray-400 text-sm">ID: {job.job_id.slice(0, 8)}...</p>
        </div>
        <span className={`px-2 py-1 rounded text-xs text-white ${getStatusColor(job.status)}`}>
          {job.status}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-sm text-gray-400 mb-1">
          <span>Progress</span>
          <span>{(job.progress * 100).toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${job.progress * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-gray-500">Epoch</p>
          <p className="text-gray-300">{job.current_epoch} / {job.total_epochs}</p>
        </div>
        <div>
          <p className="text-gray-500">Loss</p>
          <p className="text-gray-300">{job.current_loss?.toFixed(4) || '-'}</p>
        </div>
        <div>
          <p className="text-gray-500">Best Loss</p>
          <p className="text-green-400">{job.best_loss?.toFixed(4) || '-'}</p>
        </div>
        <div>
          <p className="text-gray-500">Started</p>
          <p className="text-gray-300">{formatDate(job.started_at)}</p>
        </div>
      </div>

      {job.error_message && (
        <div className="mt-3 p-2 bg-red-900/30 rounded text-red-400 text-sm">
          Error: {job.error_message}
        </div>
      )}
    </div>
  );
}

// Model Training Component
function ModelTraining({ datasets }) {
  const [jobs, setJobs] = useState([]);
  const [versions, setVersions] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [selectedModel, setSelectedModel] = useState('lstm');
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [isTraining, setIsTraining] = useState(false);

  const fetchData = async () => {
    try {
      const [jobsData, versionsData] = await Promise.all([
        ModelTrainingService.getAllTrainingJobs(),
        ModelTrainingService.listVersions(),
      ]);
      setJobs(jobsData.jobs || []);
      setVersions(versionsData.versions || []);
    } catch (err) {
      console.error('Failed to fetch training data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll for updates during active training
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Load default config when model type changes
    const loadConfig = async () => {
      try {
        const data = await ModelTrainingService.getDefaultConfig(selectedModel);
        setConfig(data.config);
      } catch (err) {
        console.error('Failed to load default config:', err);
      }
    };
    loadConfig();
  }, [selectedModel]);

  const handleStartTraining = async () => {
    if (!selectedDataset) {
      alert('Please select a dataset first');
      return;
    }

    setIsTraining(true);
    try {
      let result;
      switch (selectedModel) {
        case 'lstm':
          result = await ModelTrainingService.trainLSTM(selectedDataset.dataset_id, config);
          break;
        case 'yolo':
          result = await ModelTrainingService.trainYOLO(selectedDataset.dataset_id, config);
          break;
        case 'rl':
          result = await ModelTrainingService.trainRL(selectedDataset.dataset_id, config);
          break;
        default:
          throw new Error('Invalid model type');
      }
      fetchData();
    } catch (err) {
      console.error('Failed to start training:', err);
      alert('Failed to start training: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsTraining(false);
    }
  };

  const handleActivateVersion = async (versionId) => {
    try {
      await ModelTrainingService.activateVersion(versionId);
      fetchData();
    } catch (err) {
      console.error('Failed to activate version:', err);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white">Model Training</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Training Configuration */}
        <div className="bg-gray-800 rounded-lg p-4 space-y-4">
          <h3 className="text-white font-medium">Start New Training</h3>

          {/* Model Type Selection */}
          <div>
            <label className="text-gray-400 text-sm">Model Type</label>
            <div className="flex space-x-2 mt-1">
              {['lstm', 'yolo', 'rl'].map((model) => (
                <button
                  key={model}
                  onClick={() => setSelectedModel(model)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    selectedModel === model
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {model.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Dataset Selection */}
          <div>
            <label className="text-gray-400 text-sm">Select Dataset</label>
            <select
              value={selectedDataset?.dataset_id || ''}
              onChange={(e) => {
                const ds = datasets?.find(d => d.dataset_id === e.target.value);
                setSelectedDataset(ds);
              }}
              className="w-full mt-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
            >
              <option value="">-- Select a dataset --</option>
              {datasets?.map((ds) => (
                <option key={ds.dataset_id} value={ds.dataset_id}>
                  {ds.name} ({ds.dataset_type})
                </option>
              ))}
            </select>
          </div>

          {/* Training Config */}
          <div>
            <label className="text-gray-400 text-sm">Training Configuration</label>
            <div className="grid grid-cols-2 gap-2 mt-1">
              <div>
                <label className="text-xs text-gray-500">Epochs</label>
                <input
                  type="number"
                  value={config.epochs || 100}
                  onChange={(e) => setConfig({ ...config, epochs: parseInt(e.target.value) })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Learning Rate</label>
                <input
                  type="number"
                  step="0.0001"
                  value={config.learning_rate || 0.001}
                  onChange={(e) => setConfig({ ...config, learning_rate: parseFloat(e.target.value) })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Batch Size</label>
                <input
                  type="number"
                  value={config.batch_size || 32}
                  onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
                />
              </div>
              {selectedModel === 'lstm' && (
                <div>
                  <label className="text-xs text-gray-500">Sequence Length</label>
                  <input
                    type="number"
                    value={config.sequence_length || 10}
                    onChange={(e) => setConfig({ ...config, sequence_length: parseInt(e.target.value) })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
                  />
                </div>
              )}
            </div>
          </div>

          <button
            onClick={handleStartTraining}
            disabled={isTraining || !selectedDataset}
            className={`w-full py-2 rounded-lg transition-colors ${
              isTraining || !selectedDataset
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-green-600 text-white hover:bg-green-700'
            }`}
          >
            {isTraining ? 'Starting...' : 'Start Training'}
          </button>
        </div>

        {/* Active Training Jobs */}
        <div className="space-y-4">
          <h3 className="text-white font-medium">Training Jobs</h3>
          {loading ? (
            <div className="flex justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-4 text-gray-400">
              No training jobs
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {jobs.map((job) => (
                <TrainingJobCard key={job.job_id} job={job} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Model Versions */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white font-medium mb-4">Model Versions</h3>
        
        {versions.length === 0 ? (
          <div className="text-center py-4 text-gray-400">No model versions available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-2">Model</th>
                  <th className="pb-2">Version</th>
                  <th className="pb-2">Created</th>
                  <th className="pb-2">Metrics</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.version_id} className="border-b border-gray-700">
                    <td className="py-2 text-white">{v.model_type.toUpperCase()}</td>
                    <td className="py-2 text-gray-300">v{v.version}</td>
                    <td className="py-2 text-gray-400">{new Date(v.created_at).toLocaleDateString()}</td>
                    <td className="py-2 text-gray-400">
                      {Object.entries(v.metrics || {}).slice(0, 2).map(([k, val]) => (
                        <span key={k} className="mr-2">{k}: {typeof val === 'number' ? val.toFixed(3) : val}</span>
                      ))}
                    </td>
                    <td className="py-2">
                      {v.is_active ? (
                        <span className="px-2 py-1 bg-green-600 text-white rounded text-xs">Active</span>
                      ) : (
                        <span className="px-2 py-1 bg-gray-600 text-gray-300 rounded text-xs">Inactive</span>
                      )}
                    </td>
                    <td className="py-2">
                      {!v.is_active && (
                        <button
                          onClick={() => handleActivateVersion(v.version_id)}
                          className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                        >
                          Activate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// Main Dataset & Training Page
function DatasetUpload() {
  const [activeTab, setActiveTab] = useState('datasets');
  const [datasets, setDatasets] = useState([]);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const data = await DatasetService.listDatasets();
        setDatasets(data.datasets || []);
      } catch (err) {
        console.error('Failed to fetch datasets:', err);
      }
    };
    fetchDatasets();
  }, []);

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex space-x-4 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('datasets')}
          className={`pb-2 px-4 transition-colors ${
            activeTab === 'datasets'
              ? 'text-blue-500 border-b-2 border-blue-500'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          Datasets
        </button>
        <button
          onClick={() => setActiveTab('training')}
          className={`pb-2 px-4 transition-colors ${
            activeTab === 'training'
              ? 'text-blue-500 border-b-2 border-blue-500'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          Model Training
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'datasets' && <DatasetManagement />}
      {activeTab === 'training' && <ModelTraining datasets={datasets} />}
    </div>
  );
}

export default DatasetUpload;
export { DatasetManagement, ModelTraining, FileUpload };
