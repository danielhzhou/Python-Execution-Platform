import { useState, useEffect } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Spinner } from '../ui/spinner';
import { submissionApi } from '../../lib/api';
import type { Submission, SubmissionDetail } from '../../types';

interface ReviewerDashboardProps {
  className?: string;
}

export function ReviewerDashboard({ className }: ReviewerDashboardProps) {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [selectedSubmission, setSelectedSubmission] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewingAction, setReviewingAction] = useState<'approved' | 'rejected' | null>(null);
  const [reviewComment, setReviewComment] = useState('');
  const [approvedSubmissions, setApprovedSubmissions] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'pending' | 'approved'>('pending');
  const [downloadingIds, setDownloadingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadSubmissions();
    loadApprovedSubmissions();
  }, []);

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      const response = await submissionApi.getSubmissionsForReview();
      if (response.success && response.data) {
        setSubmissions(response.data);
      }
    } catch (error) {
      console.error('Error loading submissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadApprovedSubmissions = async () => {
    try {
      const response = await submissionApi.getApprovedSubmissions();
      if (response.success && response.data) {
        setApprovedSubmissions(response.data);
      }
    } catch (error) {
      console.error('Error loading approved submissions:', error);
    }
  };

  const loadSubmissionDetails = async (submissionId: string) => {
    try {
      const response = await submissionApi.getSubmissionDetails(submissionId);
      if (response.success && response.data) {
        setSelectedSubmission(response.data);
      }
    } catch (error) {
      console.error('Error loading submission details:', error);
    }
  };

  const handleReview = async (status: 'approved' | 'rejected') => {
    if (!selectedSubmission || !reviewComment.trim()) return;

    setReviewingAction(status);
    try {
      const response = await submissionApi.reviewSubmission({
        submission_id: selectedSubmission.submission.id,
        status,
        comment: reviewComment
      });

      if (response.success) {
        // Refresh submissions list
        await loadSubmissions();
        await loadApprovedSubmissions();
        
        // Clear selection and comment
        setSelectedSubmission(null);
        setReviewComment('');
      }
    } catch (error) {
      console.error('Error reviewing submission:', error);
    } finally {
      setReviewingAction(null);
    }
  };

  const downloadSubmission = async (submissionId: string) => {
    try {
      // Set loading state
      setDownloadingIds(prev => new Set(prev).add(submissionId));

      const response = await submissionApi.downloadSubmission(submissionId);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `submission-${submissionId}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } else {
        const errorText = await response.text();
        console.error('Download failed:', errorText);
        alert('Failed to download submission. Please try again.');
      }
    } catch (error) {
      console.error('Error downloading submission:', error);
      alert('Error downloading submission. Please check your connection and try again.');
    } finally {
      // Clear loading state
      setDownloadingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(submissionId);
        return newSet;
      });
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
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
    <div className={`h-full flex flex-col ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Reviewer Dashboard</h1>
        <div className="flex space-x-2">
          <Button
            variant={activeTab === 'pending' ? 'default' : 'outline'}
            onClick={() => setActiveTab('pending')}
          >
            Pending Reviews ({submissions.length})
          </Button>
          <Button
            variant={activeTab === 'approved' ? 'default' : 'outline'}
            onClick={() => setActiveTab('approved')}
          >
            Approved ({approvedSubmissions.length})
          </Button>
        </div>
      </div>

      {activeTab === 'pending' && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
          {/* Submissions List */}
          <div className="flex flex-col">
            <h2 className="text-xl font-semibold mb-4">Submissions for Review</h2>
            <div className="flex-1 space-y-4 overflow-y-auto pr-2">
              {submissions.length === 0 ? (
                <Card className="p-6">
                  <p className="text-center text-muted-foreground">
                    No submissions pending review
                  </p>
                </Card>
              ) : (
                submissions.map((submission) => (
                  <Card
                    key={submission.id}
                    className={`p-4 cursor-pointer transition-colors hover:bg-muted/50 ${
                      selectedSubmission?.submission.id === submission.id
                        ? 'border-primary bg-muted/30'
                        : ''
                    }`}
                    onClick={() => loadSubmissionDetails(submission.id)}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium">{submission.title}</h3>
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          {submission.status}
                        </span>
                      </div>
                      {submission.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {submission.description}
                        </p>
                      )}
                      <div className="text-xs text-muted-foreground">
                        Submitted: {submission.submitted_at && formatDate(submission.submitted_at)}
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Submission Details */}
          <div className="flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Review Submission</h2>
              {selectedSubmission && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={downloadingIds.has(selectedSubmission.submission.id)}
                  onClick={() => downloadSubmission(selectedSubmission.submission.id)}
                >
                  {downloadingIds.has(selectedSubmission.submission.id) ? (
                    <div className="flex items-center space-x-2">
                      <Spinner size="sm" />
                      <span>Downloading...</span>
                    </div>
                  ) : (
                    'Download Files'
                  )}
                </Button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto pr-2">
              {selectedSubmission ? (
                <Card className="p-6 h-full flex flex-col">
                  {/* Submission Info */}
                  <div className="space-y-4 flex-shrink-0">
                    <div>
                      <h3 className="font-medium text-lg">
                        {selectedSubmission.submission.title}
                      </h3>
                      {selectedSubmission.submission.description && (
                        <p className="text-muted-foreground mt-2">
                          {selectedSubmission.submission.description}
                        </p>
                      )}
                    </div>

                    <div className="text-sm text-muted-foreground">
                      <p>Status: {selectedSubmission.submission.status}</p>
                      <p>
                        Submitted: {selectedSubmission.submission.submitted_at && 
                          formatDate(selectedSubmission.submission.submitted_at)}
                      </p>
                    </div>
                  </div>

                  {/* Files - Scrollable */}
                  <div className="flex-1 min-h-0 my-4">
                    <h4 className="font-medium mb-2">Files ({selectedSubmission.files.length})</h4>
                    <div className="space-y-2 overflow-y-auto max-h-64">
                      {selectedSubmission.files.map((file) => (
                        <details key={file.id} className="border rounded p-2 group">
                          <summary className="cursor-pointer font-mono text-sm list-none">
                            <span className="inline-flex items-center">
                              <svg className="w-3 h-3 mr-2 transition-transform duration-200 group-open:rotate-90" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                              </svg>
                              {file.file_name} ({file.file_size} bytes)
                            </span>
                          </summary>
                          <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {file.content}
                          </pre>
                        </details>
                      ))}
                    </div>
                  </div>

                  {/* Review Form - Fixed at bottom */}
                  <div className="border-t pt-4 flex-shrink-0">
                    <h4 className="font-medium mb-2">Review</h4>
                    <textarea
                      className="w-full p-3 border rounded-md resize-none"
                      rows={4}
                      placeholder="Enter your review comments..."
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                    />
                    <div className="flex space-x-2 mt-3">
                      <Button
                        onClick={() => handleReview('approved')}
                        disabled={reviewingAction !== null || !reviewComment.trim()}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        {reviewingAction === 'approved' ? (
                          <div className="flex items-center space-x-2">
                            <Spinner size="sm" />
                            <span>Processing...</span>
                          </div>
                        ) : (
                          'Approve'
                        )}
                      </Button>
                      <Button
                        onClick={() => handleReview('rejected')}
                        disabled={reviewingAction !== null || !reviewComment.trim()}
                        variant="destructive"
                      >
                        {reviewingAction === 'rejected' ? (
                          <div className="flex items-center space-x-2">
                            <Spinner size="sm" />
                            <span>Processing...</span>
                          </div>
                        ) : (
                          'Reject'
                        )}
                      </Button>
                    </div>
                  </div>
                </Card>
              ) : (
                <Card className="p-6 h-full flex items-center justify-center">
                  <p className="text-center text-muted-foreground">
                    Select a submission to review
                  </p>
                </Card>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'approved' && (
        <div className="flex-1 flex flex-col">
          <h2 className="text-xl font-semibold mb-4">Approved Submissions</h2>
          <div className="flex-1 overflow-y-auto">
            {approvedSubmissions.length === 0 ? (
              <Card className="p-6">
                <p className="text-center text-muted-foreground">
                  No approved submissions yet
                </p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {approvedSubmissions.map((submission) => (
                  <Card key={submission.submission_id} className="p-4">
                    <div className="space-y-2">
                      <h3 className="font-medium">{submission.title}</h3>
                      <p className="text-sm text-muted-foreground">
                        Submitter: {submission.submitter_email}
                      </p>
                      <div className="text-xs text-muted-foreground">
                        <p>Submitted: {formatDate(submission.submitted_at)}</p>
                        <p>Approved: {formatDate(submission.reviewed_at)}</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={downloadingIds.has(submission.submission_id)}
                        onClick={() => downloadSubmission(submission.submission_id)}
                        className="w-full"
                      >
                        {downloadingIds.has(submission.submission_id) ? (
                          <div className="flex items-center space-x-2">
                            <Spinner size="sm" />
                            <span>Downloading...</span>
                          </div>
                        ) : (
                          'Download'
                        )}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}