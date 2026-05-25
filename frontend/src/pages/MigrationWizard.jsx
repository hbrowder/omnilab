import React, { useState, useCallback } from 'react';
import { Upload, CheckCircle, XCircle, AlertCircle, Loader, Download } from 'lucide-react';
import axios from 'axios';

const MigrationWizard = () => {
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState(null); // 'eve-ng' or 'gns3'
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState([]);
  const [overallStatus, setOverallStatus] = useState(null);

  const handleFileSelect = useCallback((e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const startMigration = async () => {
    setUploading(true);
    setResults([]);
    const newResults = [];

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('platform', platform);

        const result = {
          filename: file.name,
          status: 'uploading',
          progress: 0
        };
        newResults.push(result);
        setResults([...newResults]);

        const response = await axios.post('/api/migration/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            result.progress = progress;
            setResults([...newResults]);
          }
        });

        result.status = 'success';
        result.labId = response.data.lab_id;
        result.labName = response.data.lab_name;
        setResults([...newResults]);

      } catch (error) {
        const result = newResults[newResults.length - 1];
        result.status = 'error';
        result.error = error.response?.data?.detail || error.message;
        setResults([...newResults]);
      }
    }

    // Check permissions after all uploads
    try {
      const permCheck = await axios.get('/api/system/permissions');
      setOverallStatus(permCheck.data);
    } catch (error) {
      console.error('Permission check failed:', error);
    }

    setUploading(false);
    setStep(4);
  };

  const exportCurrentLabs = async () => {
    try {
      const response = await axios.get('/api/labs');
      const labs = response.data;
      
      const exportData = {
        version: '1.0',
        exported_at: new Date().toISOString(),
        platform: 'omnilab',
        labs: labs
      };
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `omnilab-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Lab Migration Wizard</h1>
          <p className="text-purple-200">Migrate your EVE-NG or GNS3 labs to OmniLab</p>
        </div>

        {/* Progress Bar */}
        <div className="bg-white/10 backdrop-blur-lg rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center flex-1">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    step >= s ? 'bg-green-500 text-white' : 'bg-gray-600 text-gray-300'
                  }`}
                >
                  {s}
                </div>
                {s < 4 && (
                  <div
                    className={`flex-1 h-1 mx-2 ${step > s ? 'bg-green-500' : 'bg-gray-600'}`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between text-sm text-purple-200 mt-2">
            <span>Platform</span>
            <span>Upload</span>
            <span>Migrate</span>
            <span>Complete</span>
          </div>
        </div>

        {/* Main Content Card */}
        <div className="bg-white rounded-xl shadow-2xl p-8">
          
          {/* Step 1: Platform Selection */}
          {step === 1 && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Select Source Platform</h2>
              <p className="text-gray-600 mb-6">Where are your labs coming from?</p>
              
              <div className="grid grid-cols-2 gap-6">
                <button
                  onClick={() => { setPlatform('eve-ng'); setStep(2); }}
                  className="p-8 border-2 border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-all group"
                >
                  <div className="text-6xl mb-4">🦅</div>
                  <h3 className="text-xl font-bold mb-2">EVE-NG</h3>
                  <p className="text-gray-600">Migrate .unl lab files</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Say goodbye to fixpermissions!
                  </p>
                </button>
                
                <button
                  onClick={() => { setPlatform('gns3'); setStep(2); }}
                  className="p-8 border-2 border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-all group"
                >
                  <div className="text-6xl mb-4">🌐</div>
                  <h3 className="text-xl font-bold mb-2">GNS3</h3>
                  <p className="text-gray-600">Migrate .gns3 project files</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Web-based, multi-user ready
                  </p>
                </button>
              </div>

              <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-blue-600 mr-3 mt-0.5" />
                  <div>
                    <p className="text-sm text-blue-900 font-semibold">Already using OmniLab?</p>
                    <p className="text-sm text-blue-800 mt-1">
                      You can export your labs for backup or transfer to another OmniLab instance.
                    </p>
                    <button
                      onClick={exportCurrentLabs}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Export Current Labs
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: File Upload */}
          {step === 2 && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Upload Lab Files</h2>
              <p className="text-gray-600 mb-6">
                Drop your {platform === 'eve-ng' ? '.unl' : '.gns3'} files here, or click to browse
              </p>

              {/* Drop Zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-purple-500 transition-colors cursor-pointer"
                onClick={() => document.getElementById('fileInput').click()}
              >
                <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <p className="text-lg text-gray-700 mb-2">Drop files here or click to upload</p>
                <p className="text-sm text-gray-500">
                  Supports {platform === 'eve-ng' ? '.unl' : '.gns3'} and .zip files
                </p>
                <input
                  id="fileInput"
                  type="file"
                  multiple
                  accept={platform === 'eve-ng' ? '.unl,.zip' : '.gns3,.zip'}
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* File List */}
              {files.length > 0 && (
                <div className="mt-6">
                  <h3 className="font-semibold mb-3">Selected Files ({files.length})</h3>
                  <div className="space-y-2">
                    {files.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center">
                          <CheckCircle className="w-5 h-5 text-green-500 mr-3" />
                          <div>
                            <p className="font-medium">{file.name}</p>
                            <p className="text-sm text-gray-500">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Navigation */}
              <div className="flex justify-between mt-8">
                <button
                  onClick={() => setStep(1)}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={files.length === 0}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next: Review
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Review & Confirm */}
          {step === 3 && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Review & Confirm</h2>
              
              <div className="bg-gray-50 p-6 rounded-lg mb-6">
                <h3 className="font-semibold mb-3">Migration Summary</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Source Platform:</span>
                    <span className="font-medium">{platform === 'eve-ng' ? 'EVE-NG' : 'GNS3'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Files to migrate:</span>
                    <span className="font-medium">{files.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total size:</span>
                    <span className="font-medium">
                      {(files.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                <div className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-600 mr-3 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-green-900">
                      No manual fixpermissions needed!
                    </p>
                    <p className="text-sm text-green-800 mt-1">
                      OmniLab will automatically set correct permissions on all images.
                      Your labs will be ready to start immediately after migration.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(2)}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={startMigration}
                  disabled={uploading}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center"
                >
                  {uploading ? (
                    <>
                      <Loader className="w-5 h-5 mr-2 animate-spin" />
                      Migrating...
                    </>
                  ) : (
                    'Start Migration'
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Results */}
          {step === 4 && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Migration Complete!</h2>
              
              {/* Results List */}
              <div className="space-y-3 mb-6">
                {results.map((result, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-lg border-2 ${
                      result.status === 'success'
                        ? 'bg-green-50 border-green-200'
                        : result.status === 'error'
                        ? 'bg-red-50 border-red-200'
                        : 'bg-blue-50 border-blue-200'
                    }`}
                  >
                    <div className="flex items-start">
                      {result.status === 'success' ? (
                        <CheckCircle className="w-6 h-6 text-green-600 mr-3 mt-0.5" />
                      ) : result.status === 'error' ? (
                        <XCircle className="w-6 h-6 text-red-600 mr-3 mt-0.5" />
                      ) : (
                        <Loader className="w-6 h-6 text-blue-600 mr-3 mt-0.5 animate-spin" />
                      )}
                      
                      <div className="flex-1">
                        <p className="font-medium">{result.filename}</p>
                        {result.status === 'success' && (
                          <p className="text-sm text-green-700 mt-1">
                            ✓ Migrated as "{result.labName}" (ID: {result.labId})
                          </p>
                        )}
                        {result.status === 'error' && (
                          <p className="text-sm text-red-700 mt-1">✗ {result.error}</p>
                        )}
                        {result.status === 'uploading' && (
                          <div className="mt-2">
                            <div className="w-full bg-blue-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full transition-all"
                                style={{ width: `${result.progress}%` }}
                              />
                            </div>
                            <p className="text-sm text-blue-700 mt-1">{result.progress}%</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Permission Status */}
              {overallStatus && (
                <div className={`p-4 rounded-lg mb-6 ${
                  overallStatus.status === 'ok' ? 'bg-green-50 border-2 border-green-200' : 'bg-yellow-50 border-2 border-yellow-200'
                }`}>
                  <div className="flex items-start">
                    <CheckCircle className="w-6 h-6 text-green-600 mr-3 mt-0.5" />
                    <div>
                      <p className="font-semibold text-green-900">
                        All {overallStatus.total_images} images have correct permissions
                      </p>
                      <p className="text-sm text-green-800 mt-1">
                        No manual fixpermissions needed! Your labs are ready to start.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-green-50 p-4 rounded-lg text-center">
                  <p className="text-3xl font-bold text-green-600">
                    {results.filter(r => r.status === 'success').length}
                  </p>
                  <p className="text-sm text-green-800">Successful</p>
                </div>
                <div className="bg-red-50 p-4 rounded-lg text-center">
                  <p className="text-3xl font-bold text-red-600">
                    {results.filter(r => r.status === 'error').length}
                  </p>
                  <p className="text-sm text-red-800">Failed</p>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg text-center">
                  <p className="text-3xl font-bold text-blue-600">
                    {results.length}
                  </p>
                  <p className="text-sm text-blue-800">Total</p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-between">
                <button
                  onClick={() => {
                    setStep(1);
                    setFiles([]);
                    setResults([]);
                    setOverallStatus(null);
                  }}
                  className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Migrate More Labs
                </button>
                <button
                  onClick={() => window.location.href = '/labs'}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  Go to Labs
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-purple-200 text-sm">
          <p>Need help? Check out the <a href="/docs/migration" className="underline">migration guide</a></p>
        </div>
      </div>
    </div>
  );
};

export default MigrationWizard;
