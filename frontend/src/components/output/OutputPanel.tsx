import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Spinner } from '../ui/spinner';
import { useAppStore } from '../../stores/appStore';

interface OutputData {
  images: Array<{
    type: 'image';
    name: string;
    path: string;
    size: number;
    mime_type: string;
    base64_data?: string;
    storage_url?: string;
    created_at: string;
  }>;
  files: Array<{
    type: 'file';
    name: string;
    path: string;
    size: number;
    mime_type: string;
    download_url?: string;
    created_at: string;
  }>;
  data: Array<{
    type: 'data';
    name: string;
    path: string;
    size: number;
    mime_type: string;
    preview_content: string;
    download_url?: string;
    created_at: string;
  }>;
}

interface OutputPanelProps {
  className?: string;
}

export function OutputPanel({ className }: OutputPanelProps) {
  const [outputs, setOutputs] = useState<OutputData>({ images: [], files: [], data: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { currentContainer } = useAppStore();

  const fetchOutputs = useCallback(async () => {
    if (!currentContainer?.id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/outputs/containers/${currentContainer.id}/outputs`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch outputs: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success && result.data) {
        setOutputs(result.data);
      } else {
        throw new Error(result.message || 'Failed to fetch outputs');
      }
    } catch (err) {
      console.error('Error fetching outputs:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch outputs');
    } finally {
      setLoading(false);
    }
  }, [currentContainer?.id]);

  const captureOutputs = useCallback(async () => {
    if (!currentContainer?.id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/outputs/containers/${currentContainer.id}/capture-outputs`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to capture outputs: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.success && result.data) {
        setOutputs(result.data);
      } else {
        throw new Error(result.message || 'Failed to capture outputs');
      }
    } catch (err) {
      console.error('Error capturing outputs:', err);
      setError(err instanceof Error ? err.message : 'Failed to capture outputs');
    } finally {
      setLoading(false);
    }
  }, [currentContainer?.id]);

  const clearOutputs = useCallback(async () => {
    if (!currentContainer?.id) return;

    try {
      const response = await fetch(`/api/outputs/containers/${currentContainer.id}/outputs`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        setOutputs({ images: [], files: [], data: [] });
      }
    } catch (err) {
      console.error('Error clearing outputs:', err);
    }
  }, [currentContainer?.id]);

  // Auto-refresh outputs when container changes or when enabled
  useEffect(() => {
    if (autoRefresh && currentContainer?.id) {
      fetchOutputs();
      
      // Set up periodic refresh
      const interval = setInterval(fetchOutputs, 5000); // Every 5 seconds
      return () => clearInterval(interval);
    }
  }, [fetchOutputs, autoRefresh, currentContainer?.id]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const downloadFile = (url: string, filename: string) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalOutputs = outputs.images.length + outputs.files.length + outputs.data.length;

  return (
    <div className={`flex flex-col h-full bg-[#1e1e1e] ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border/30 bg-[#2d2d30]">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-white">Output</h3>
          {totalOutputs > 0 && (
            <span className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded-full">
              {totalOutputs}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            size="sm"
            variant={autoRefresh ? "default" : "outline"}
            className="h-7 px-2 text-xs"
          >
            Auto
          </Button>
          <Button
            onClick={captureOutputs}
            disabled={loading || !currentContainer}
            size="sm"
            className="h-7 px-2 text-xs"
          >
            {loading ? <Spinner className="w-3 h-3" /> : 'Capture'}
          </Button>
          <Button
            onClick={clearOutputs}
            disabled={!currentContainer || totalOutputs === 0}
            size="sm"
            variant="outline"
            className="h-7 px-2 text-xs"
          >
            Clear
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {error && (
          <div className="p-3 bg-red-900/20 border border-red-500/30 rounded text-red-300 text-sm">
            {error}
          </div>
        )}

        {loading && totalOutputs === 0 && (
          <div className="flex items-center justify-center py-8">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Spinner className="w-4 h-4" />
              <span className="text-sm">Loading outputs...</span>
            </div>
          </div>
        )}

        {!loading && totalOutputs === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <svg className="w-12 h-12 mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-sm">No outputs found</p>
            <p className="text-xs opacity-70 mt-1">Run code that generates images or files</p>
          </div>
        )}

        {/* Images */}
        {outputs.images.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-white flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
              Images ({outputs.images.length})
            </h4>
            {outputs.images.map((image, index) => (
              <Card key={index} className="p-3 bg-[#252526] border-border/30">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">{image.name}</span>
                    <span className="text-xs text-muted-foreground">{formatFileSize(image.size)}</span>
                  </div>
                  
                  {image.base64_data && (
                    <div className="rounded overflow-hidden bg-white/5 p-2">
                      <img 
                        src={image.base64_data} 
                        alt={image.name}
                        className="max-w-full h-auto rounded"
                        style={{ maxHeight: '300px' }}
                      />
                    </div>
                  )}
                  
                  <div className="flex items-center gap-2">
                    {image.storage_url && (
                      <Button
                        onClick={() => downloadFile(image.storage_url!, image.name)}
                        size="sm"
                        className="h-6 px-2 text-xs"
                      >
                        Download
                      </Button>
                    )}
                    <span className="text-xs text-muted-foreground">{image.path}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Data Files */}
        {outputs.data.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-white flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
              </svg>
              Data Files ({outputs.data.length})
            </h4>
            {outputs.data.map((dataFile, index) => (
              <Card key={index} className="p-3 bg-[#252526] border-border/30">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">{dataFile.name}</span>
                    <span className="text-xs text-muted-foreground">{formatFileSize(dataFile.size)}</span>
                  </div>
                  
                  <div className="bg-[#1e1e1e] rounded p-2 text-xs font-mono text-gray-300 max-h-32 overflow-auto">
                    <pre>{dataFile.preview_content}</pre>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {dataFile.download_url && (
                      <Button
                        onClick={() => downloadFile(dataFile.download_url!, dataFile.name)}
                        size="sm"
                        className="h-6 px-2 text-xs"
                      >
                        Download
                      </Button>
                    )}
                    <span className="text-xs text-muted-foreground">{dataFile.path}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Other Files */}
        {outputs.files.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-white flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
              </svg>
              Files ({outputs.files.length})
            </h4>
            {outputs.files.map((file, index) => (
              <Card key={index} className="p-3 bg-[#252526] border-border/30">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-white">{file.name}</span>
                    <div className="text-xs text-muted-foreground">{file.path}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                    {file.download_url && (
                      <Button
                        onClick={() => downloadFile(file.download_url!, file.name)}
                        size="sm"
                        className="h-6 px-2 text-xs"
                      >
                        Download
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}