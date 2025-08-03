import { useState, useEffect } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Dialog } from '../ui/dialog';
import { Input } from '../ui/input';
import { Spinner } from '../ui/spinner';
import { submissionApi } from '../../lib/api';
import { useAppStore } from '../../stores/appStore';
import type { Submission, CreateSubmissionRequest, SubmitFilesRequest } from '../../types';

interface SubmitterInterfaceProps {
  className?: string;
  currentFiles: Array<{ path: string; content: string; name: string }>;
}

interface CreateSubmissionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateSubmissionRequest) => void;
  loading: boolean;
}

interface FileSelectionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (selectedFiles: Array<{ path: string; content: string; name: string }>) => void;
  availableFiles: Array<{ path: string; content: string; name: string }>;
  loading: boolean;
}

function CreateSubmissionDialog({ isOpen, onClose, onSubmit, loading }: CreateSubmissionDialogProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const { currentContainer } = useAppStore();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !currentContainer) return;

    onSubmit({
      project_id: currentContainer.id, // Using container ID as project ID
      title: title.trim(),
      description: description.trim() || undefined,
    });
  };

  const handleClose = () => {
    setTitle('');
    setDescription('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">Create New Submission</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title *</label>
            <Input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter submission title"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              className="w-full p-2 border rounded-md resize-none"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
            />
          </div>
          
          <div className="flex space-x-2 pt-4">
            <Button
              type="submit"
              disabled={loading || !title.trim()}
              className="flex-1"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <Spinner size="sm" />
                  <span>Creating...</span>
                </div>
              ) : (
                'Create Submission'
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FileSelectionDialog({ isOpen, onClose, onSubmit, availableFiles, loading }: FileSelectionDialogProps) {
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());

  const handleFileToggle = (filePath: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(filePath)) {
      newSelected.delete(filePath);
    } else {
      newSelected.add(filePath);
    }
    setSelectedFiles(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedFiles.size === availableFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(availableFiles.map(f => f.path)));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const filesToSubmit = availableFiles.filter(file => selectedFiles.has(file.path));
    onSubmit(filesToSubmit);
  };

  const handleClose = () => {
    setSelectedFiles(new Set());
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[80vh] flex flex-col">
        <h2 className="text-xl font-semibold mb-4">Select Files to Upload</h2>
        
        <form onSubmit={handleSubmit} className="flex flex-col flex-1">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-gray-600">
              {selectedFiles.size} of {availableFiles.length} files selected
            </span>
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              {selectedFiles.size === availableFiles.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          <div className="flex-1 overflow-auto border rounded-md p-2 mb-4 max-h-96">
            {availableFiles.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                No files available. Create some files in your workspace first.
              </div>
            ) : (
              <div className="space-y-2">
                {availableFiles.map((file) => (
                  <label
                    key={file.path}
                    className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.path)}
                      onChange={() => handleFileToggle(file.path)}
                      className="mr-3"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-sm">{file.name}</div>
                      <div className="text-xs text-gray-500">{file.path}</div>
                      <div className="text-xs text-gray-400 mb-1">
                        {file.content.length} characters
                      </div>
                      {file.content.trim() && (
                        <div className="text-xs text-gray-600 bg-gray-50 p-1 rounded max-h-12 overflow-hidden">
                          {file.content.substring(0, 100)}
                          {file.content.length > 100 && '...'}
                        </div>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
          
          <div className="flex space-x-2">
            <Button
              type="submit"
              disabled={loading || selectedFiles.size === 0}
              className="flex-1"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <Spinner size="sm" />
                  <span>Uploading...</span>
                </div>
              ) : (
                `Upload ${selectedFiles.size} Files`
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function SubmitterInterface({ className, currentFiles }: SubmitterInterfaceProps) {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [submissionFiles, setSubmissionFiles] = useState<Record<string, SubmissionFile[]>>({});
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [showFileSelectionDialog, setShowFileSelectionDialog] = useState(false);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);
  const [expandedSubmissions, setExpandedSubmissions] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      const response = await submissionApi.getMySubmissions();
      if (response.success && response.data) {
        setSubmissions(response.data);
      }
    } catch (error) {
      console.error('Error loading submissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSubmissionFiles = async (submissionId: string) => {
    try {
      const response = await submissionApi.getSubmissionDetails(submissionId);
      if (response.success && response.data) {
        setSubmissionFiles(prev => ({
          ...prev,
          [submissionId]: response.data.files
        }));
      }
    } catch (error) {
      console.error('Error loading submission files:', error);
    }
  };

  const toggleSubmissionExpanded = (submissionId: string) => {
    const newExpanded = new Set(expandedSubmissions);
    if (newExpanded.has(submissionId)) {
      newExpanded.delete(submissionId);
    } else {
      newExpanded.add(submissionId);
      // Load files when expanding for the first time
      if (!submissionFiles[submissionId]) {
        loadSubmissionFiles(submissionId);
      }
    }
    setExpandedSubmissions(newExpanded);
  };

  const handleCreateSubmission = async (data: CreateSubmissionRequest) => {
    setCreating(true);
    try {
      const response = await submissionApi.createSubmission(data);
      if (response.success && response.data) {
        setSubmissions([response.data, ...submissions]);
        setShowCreateDialog(false);
        alert('Submission created successfully!');
      } else {
        alert(`Error: ${response.error}`);
      }
    } catch (error) {
      console.error('Error creating submission:', error);
      alert('Error creating submission');
    } finally {
      setCreating(false);
    }
  };

  const handleUploadFiles = (submissionId: string) => {
    if (currentFiles.length === 0) {
      alert('No files to upload. Please create some files first.');
      return;
    }

    setSelectedSubmissionId(submissionId);
    setShowFileSelectionDialog(true);
  };

  const handleFileSelectionSubmit = async (selectedFiles: Array<{ path: string; content: string; name: string }>) => {
    if (!selectedSubmissionId) return;

    setUploading(selectedSubmissionId);
    setShowFileSelectionDialog(false);
    
    try {
      const request: SubmitFilesRequest = {
        submission_id: selectedSubmissionId,
        files: selectedFiles,
      };

      const response = await submissionApi.uploadFiles(request);
      if (response.success) {
        alert(`${selectedFiles.length} files uploaded successfully!`);
        loadSubmissions(); // Refresh the list
        // Refresh the files for this submission if it's expanded
        if (expandedSubmissions.has(selectedSubmissionId)) {
          loadSubmissionFiles(selectedSubmissionId);
        }
      } else {
        alert(`Error: ${response.error}`);
      }
    } catch (error) {
      console.error('Error uploading files:', error);
      alert('Error uploading files');
    } finally {
      setUploading(null);
      setSelectedSubmissionId(null);
    }
  };

  const handleFileSelectionCancel = () => {
    setShowFileSelectionDialog(false);
    setSelectedSubmissionId(null);
  };

  const handleSubmitForReview = async (submissionId: string) => {
    if (!confirm('Are you sure you want to submit this for review? You won\'t be able to modify it after submission.')) {
      return;
    }

    setSubmitting(submissionId);
    try {
      const response = await submissionApi.submitForReview(submissionId);
      if (response.success) {
        alert('Submission sent for review!');
        loadSubmissions(); // Refresh the list
      } else {
        alert(`Error: ${response.error}`);
      }
    } catch (error) {
      console.error('Error submitting for review:', error);
      alert('Error submitting for review');
    } finally {
      setSubmitting(null);
    }
  };

  const downloadSubmission = async (submissionId: string) => {
    try {
      const response = await submissionApi.downloadSubmission(submissionId);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `submission_${submissionId}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Error downloading submission');
      }
    } catch (error) {
      console.error('Error downloading submission:', error);
      alert('Error downloading submission');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'submitted':
        return 'bg-blue-100 text-blue-800';
      case 'under_review':
        return 'bg-yellow-100 text-yellow-800';
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className={`flex flex-col items-center justify-center h-64 ${className}`}>
        <Spinner size="lg" className="mb-4" />
        <div className="text-lg">Loading submissions...</div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Submissions</h1>
        <Button onClick={() => setShowCreateDialog(true)}>
          Create New Submission
        </Button>
      </div>

      <div className="text-sm text-muted-foreground mb-4">
        Current workspace has {currentFiles.length} file(s) ready for submission
      </div>

      {submissions.length === 0 ? (
        <Card className="p-8">
          <div className="text-center">
            <h3 className="text-lg font-medium mb-2">No submissions yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first submission to get started
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              Create Submission
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {submissions.map((submission) => (
            <Card key={submission.id} className="p-4">
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <h3 className="font-medium line-clamp-2">{submission.title}</h3>
                  <span className={`text-xs px-2 py-1 rounded ${getStatusColor(submission.status)}`}>
                    {submission.status}
                  </span>
                </div>

                {submission.description && (
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {submission.description}
                  </p>
                )}

                <div className="text-xs text-muted-foreground space-y-1">
                  <p>Created: {formatDate(submission.created_at)}</p>
                  {submission.submitted_at && (
                    <p>Submitted: {formatDate(submission.submitted_at)}</p>
                  )}
                  {submission.reviewed_at && (
                    <p>Reviewed: {formatDate(submission.reviewed_at)}</p>
                  )}
                </div>

                {/* Files section */}
                <div className="border-t pt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      Files {submissionFiles[submission.id] ? `(${submissionFiles[submission.id].length})` : ''}
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => toggleSubmissionExpanded(submission.id)}
                      className="h-6 px-2 text-xs"
                    >
                      {expandedSubmissions.has(submission.id) ? '▼' : '▶'}
                    </Button>
                  </div>
                  
                  {expandedSubmissions.has(submission.id) && (
                    <div className="mt-2 space-y-1">
                      {submissionFiles[submission.id] ? (
                        submissionFiles[submission.id].length > 0 ? (
                          submissionFiles[submission.id].map((file) => (
                            <div key={file.id} className="flex items-center justify-between text-xs bg-gray-50 p-2 rounded">
                              <div className="flex-1 min-w-0">
                                <div className="font-medium truncate">{file.file_name}</div>
                                <div className="text-gray-500 truncate">{file.file_path}</div>
                              </div>
                              <div className="text-gray-500 ml-2">
                                {file.file_size ? `${Math.round(file.file_size / 1024)}KB` : ''}
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-xs text-gray-500 italic p-2">No files uploaded yet</div>
                        )
                      ) : (
                        <div className="flex items-center space-x-2 p-2">
                          <Spinner size="sm" />
                          <span className="text-xs text-gray-500">Loading files...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  {submission.status === 'draft' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleUploadFiles(submission.id)}
                        disabled={uploading === submission.id || currentFiles.length === 0}
                        className="w-full"
                      >
                        {uploading === submission.id ? (
                          <div className="flex items-center space-x-2">
                            <Spinner size="sm" />
                            <span>Uploading...</span>
                          </div>
                        ) : (
                          'Select & Upload Files'
                        )}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleSubmitForReview(submission.id)}
                        disabled={submitting === submission.id}
                        className="w-full"
                      >
                        {submitting === submission.id ? (
                          <div className="flex items-center space-x-2">
                            <Spinner size="sm" />
                            <span>Submitting...</span>
                          </div>
                        ) : (
                          'Submit for Review'
                        )}
                      </Button>
                    </>
                  )}

                  {submission.status !== 'draft' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => downloadSubmission(submission.id)}
                      className="w-full"
                    >
                      Download Files
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CreateSubmissionDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSubmit={handleCreateSubmission}
        loading={creating}
      />

      <FileSelectionDialog
        isOpen={showFileSelectionDialog}
        onClose={handleFileSelectionCancel}
        onSubmit={handleFileSelectionSubmit}
        availableFiles={currentFiles}
        loading={uploading !== null}
      />
    </div>
  );
}