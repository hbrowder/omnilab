import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Wrench, Shield } from 'lucide-react';
import axios from 'axios';

const PermissionMonitoringDashboard = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fixing, setFixing] = useState(false);
  const [lastCheck, setLastCheck] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const checkPermissions = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/system/permissions');
      setStatus(response.data);
      setLastCheck(new Date());
    } catch (error) {
      console.error('Permission check failed:', error);
      setStatus({ status: 'error', error: error.message });
    } finally {
      setLoading(false);
    }
  };

  const fixPermissions = async () => {
    setFixing(true);
    try {
      const response = await axios.post('/api/system/permissions/fix');
      setStatus(response.data);
      setLastCheck(new Date());
    } catch (error) {
      console.error('Fix failed:', error);
    } finally {
      setFixing(false);
    }
  };

  useEffect(() => {
    checkPermissions();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(checkPermissions, 30000); // Every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getStatusColor = () => {
    if (!status) return 'gray';
    switch (status.status) {
      case 'ok': return 'green';
      case 'fixed': return 'yellow';
      case 'warning': return 'orange';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const statusColor = getStatusColor();

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                <Shield className="w-8 h-8 mr-3 text-purple-600" />
                Permission Monitoring
              </h1>
              <p className="text-gray-600 mt-2">
                Real-time monitoring of image file permissions
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              <label className="flex items-center text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="mr-2"
                />
                Auto-refresh (30s)
              </label>
              
              <button
                onClick={checkPermissions}
                disabled={loading}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Status Card */}
        {status && (
          <div className={`bg-${statusColor}-50 border-2 border-${statusColor}-200 rounded-xl p-6 mb-6 shadow-lg`}>
            <div className="flex items-start justify-between">
              <div className="flex items-start">
                {status.status === 'ok' ? (
                  <CheckCircle className={`w-12 h-12 text-${statusColor}-600 mr-4`} />
                ) : status.status === 'error' ? (
                  <XCircle className={`w-12 h-12 text-${statusColor}-600 mr-4`} />
                ) : (
                  <AlertTriangle className={`w-12 h-12 text-${statusColor}-600 mr-4`} />
                )}
                
                <div>
                  <h2 className={`text-2xl font-bold text-${statusColor}-900 mb-2`}>
                    {status.status === 'ok' && 'All Systems Normal'}
                    {status.status === 'fixed' && 'Issues Auto-Fixed'}
                    {status.status === 'warning' && 'Warnings Detected'}
                    {status.status === 'error' && 'Errors Detected'}
                  </h2>
                  
                  <p className={`text-${statusColor}-800 mb-4`}>
                    {status.status === 'ok' && `All ${status.total_images} images have correct permissions.`}
                    {status.status === 'fixed' && `Fixed ${status.auto_fixed?.length || 0} permission issues automatically.`}
                    {status.status === 'warning' && 'Some permission issues were detected and auto-fixed.'}
                    {status.status === 'error' && status.error}
                  </p>
                  
                  {lastCheck && (
                    <p className="text-sm text-gray-600">
                      Last checked: {lastCheck.toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>
              
              {(status.status === 'warning' || status.status === 'fixed') && (
                <button
                  onClick={fixPermissions}
                  disabled={fixing}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center"
                >
                  <Wrench className={`w-4 h-4 mr-2 ${fixing ? 'animate-spin' : ''}`} />
                  {fixing ? 'Fixing...' : 'Force Fix All'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Stats Grid */}
        {status && (
          <div className="grid grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-600 text-sm">Total Images</span>
                <CheckCircle className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{status.total_images || 0}</p>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-600 text-sm">Correct Permissions</span>
                <CheckCircle className="w-5 h-5 text-green-500" />
              </div>
              <p className="text-3xl font-bold text-green-600">
                {status.correct || status.total_images || 0}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-600 text-sm">Auto-Fixed</span>
                <Wrench className="w-5 h-5 text-yellow-500" />
              </div>
              <p className="text-3xl font-bold text-yellow-600">
                {status.auto_fixed?.length || 0}
              </p>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-600 text-sm">Issues</span>
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
              <p className="text-3xl font-bold text-red-600">
                {status.issues?.length || 0}
              </p>
            </div>
          </div>
        )}

        {/* Auto-Fixed List */}
        {status?.auto_fixed && status.auto_fixed.length > 0 && (
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Wrench className="w-5 h-5 mr-2 text-yellow-600" />
                Auto-Fixed Issues
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                These permission issues were automatically corrected
              </p>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {status.auto_fixed.map((fix, index) => (
                  <div key={index} className="flex items-start p-3 bg-yellow-50 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-yellow-600 mr-3 mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">{fix}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Permissions corrected automatically
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Issues List */}
        {status?.issues && status.issues.length > 0 && (
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-red-600" />
                Current Issues
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                These issues require attention
              </p>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {status.issues.map((issue, index) => (
                  <div key={index} className="flex items-start p-3 bg-red-50 rounded-lg">
                    <XCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5" />
                    <div>
                      <p className="font-medium text-gray-900">{issue}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Manual intervention may be required
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Info Card: Why This Matters */}
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg shadow p-6 border-2 border-purple-200">
          <h3 className="text-lg font-semibold text-purple-900 mb-4">
            🎉 Why OmniLab is Different
          </h3>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-red-800 mb-2">EVE-NG</h4>
              <ul className="text-sm text-gray-700 space-y-2">
                <li>✗ Manual <code className="bg-red-100 px-2 py-1 rounded">fixpermissions</code> after every upload</li>
                <li>✗ 3-5 minutes per image</li>
                <li>✗ Easy to forget → breaks web UI</li>
                <li>✗ No auto-detection of issues</li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-green-800 mb-2">OmniLab</h4>
              <ul className="text-sm text-gray-700 space-y-2">
                <li>✓ Automatic permission management</li>
                <li>✓ 30 seconds per image</li>
                <li>✓ Auto-fixes issues on upload</li>
                <li>✓ Real-time monitoring + alerts</li>
              </ul>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-white rounded border border-purple-200">
            <p className="text-sm text-gray-700">
              <strong>Time saved per 20-image lab:</strong> 50 minutes 🚀
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default PermissionMonitoringDashboard;
