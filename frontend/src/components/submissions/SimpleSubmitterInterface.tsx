import { useState, useEffect } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Spinner } from '../ui/spinner';
import { SuccessModal, ErrorModal } from '../ui/modal';
import { submissionApi } from '../../lib/api';
import { useAppStore } from '../../stores/appStore';
import type { Submission, SubmissionFile } from '../../types';

interface SimpleSubmitterInterfaceProps {
  className?: string;
  currentFiles: Array<{ path: string; content: string; name: string }>;
}

interface CreateAndSubmitDialogProps {
  isOpen: boolean;
  onClose: () => void;
  availableFiles: Array<{ path: string; content: string; name: string }>;
  onSuccess: () => void;
}

function CreateAndSubmitDialog({ isOpen, onClose, availableFiles, onSuccess }: CreateAndSubmitDialogProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [modalMessage, setModalMessage] = useState('');
  const { currentContainer } = useAppStore();

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !currentContainer || selectedFiles.size === 0) return;

    setSubmitting(true);
    try {
      // 1. Create submission
      const createResponse = await submissionApi.createSubmission({
        project_id: currentContainer.id,
        title: title.trim(),
        description: description.trim() || undefined,
      });

      if (!createResponse.success || !createResponse.data) {
        throw new Error(createResponse.error || 'Failed to create submission');
      }

      const submissionId = createResponse.data.id;

      // 2. Upload selected files
      const selectedFileData = availableFiles.filter(f => selectedFiles.has(f.path));
      const uploadResponse = await submissionApi.uploadFiles({
        submission_id: submissionId,
        files: selectedFileData,
      });

      if (!uploadResponse.success) {
        throw new Error(uploadResponse.error || 'Failed to upload files');
      }

      // 3. Submit for review
      const submitResponse = await submissionApi.submitForReview(submissionId);
      if (!submitResponse.success) {
        throw new Error(submitResponse.error || 'Failed to submit for review');
      }

      setModalMessage('Your submission has been created and submitted for review successfully!');
      setShowSuccessModal(true);
    } catch (error) {
      console.error('Error creating submission:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setModalMessage(errorMessage);
      setShowErrorModal(true);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setTitle('');
    setDescription('');
    setSelectedFiles(new Set());
    onClose();
  };

  const handleSuccessModalClose = () => {
    setShowSuccessModal(false);
    handleClose();
    onSuccess();
  };

  const handleErrorModalClose = () => {
    setShowErrorModal(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">Create and Submit</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title *</label>
            <Input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter submission title"
              required
              disabled={submitting}
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
              disabled={submitting}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium">Select Files to Submit *</label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleSelectAll}
                disabled={submitting}
              >
                {selectedFiles.size === availableFiles.length ? 'Deselect All' : 'Select All'}
              </Button>
            </div>
            
            {availableFiles.length === 0 ? (
              <div className="text-sm text-gray-500 p-4 border rounded-md">
                No files available in workspace
              </div>
            ) : (
              <div className="border rounded-md max-h-60 overflow-y-auto">
                {availableFiles.map((file) => (
                  <label key={file.path} className="flex items-start p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0">
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.path)}
                      onChange={() => handleFileToggle(file.path)}
                      className="mt-1 mr-3"
                      disabled={submitting}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{file.name}</div>
                      <div className="text-xs text-gray-500 truncate">{file.path}</div>
                      <div className="text-xs text-gray-400">
                        {file.content.length} characters
                      </div>
                      {file.content.trim() && (
                        <div className="text-xs text-gray-600 bg-gray-50 p-1 rounded max-h-12 overflow-hidden mt-1">
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
          
          <div className="flex space-x-2 pt-4">
            <Button
              type="submit"
              disabled={submitting || !title.trim() || selectedFiles.size === 0}
              className="flex-1"
            >
              {submitting ? (
                <div className="flex items-center space-x-2">
                  <Spinner size="sm" />
                  <span>Creating & Submitting...</span>
                </div>
              ) : (
                `Create & Submit (${selectedFiles.size} files)`
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={submitting}
            >
              Cancel
            </Button>
          </div>
        </form>
      </div>

      {/* Success Modal */}
      <SuccessModal
        isOpen={showSuccessModal}
        onClose={handleSuccessModalClose}
        title="Submission Successful"
        message={modalMessage}
      />

      {/* Error Modal */}
      <ErrorModal
        isOpen={showErrorModal}
        onClose={handleErrorModalClose}
        title="Submission Failed"
        message={modalMessage}
      />
    </div>
  );
}

export function SimpleSubmitterInterface({ className, currentFiles }: SimpleSubmitterInterfaceProps) {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [submissionFiles, setSubmissionFiles] = useState<Record<string, SubmissionFile[]>>({});
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [expandedSubmissions, setExpandedSubmissions] = useState<Set<string>>(new Set());
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

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

  const downloadSubmission = async (submissionId: string) => {
    try {
      const response = await submissionApi.downloadSubmission(submissionId);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `submission-${submissionId}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading submission:', error);
      const errorMsg = error instanceof Error ? error.message : 'Failed to download submission';
      setErrorMessage(errorMsg);
      setShowErrorModal(true);
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
          Create & Submit
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
              Create & Submit
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
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
                          <div className="text-xs text-gray-500 italic p-2">No files uploaded</div>
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

                <div className="flex space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => downloadSubmission(submission.id)}
                    className="flex-1"
                  >
                    Download Files
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CreateAndSubmitDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        availableFiles={currentFiles}
        onSuccess={loadSubmissions}
      />

      {/* Error Modal for download errors */}
      <ErrorModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title="Error"
        message={errorMessage}
      />
    </div>
  );
}