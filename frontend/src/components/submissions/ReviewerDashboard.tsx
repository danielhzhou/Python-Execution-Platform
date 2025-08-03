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
  const [reviewing, setReviewing] = useState(false);
  const [reviewComment, setReviewComment] = useState('');
  const [approvedSubmissions, setApprovedSubmissions] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'pending' | 'approved'>('pending');

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
    if (!selectedSubmission || !reviewComment.trim()) {
      alert('Please enter a review comment');
      return;
    }

    setReviewing(true);
    try {
      const response = await submissionApi.reviewSubmission({
        submission_id: selectedSubmission.submission.id,
        status,
        comment: reviewComment,
      });

      if (response.success) {
        alert(`Submission ${status} successfully`);
        setSelectedSubmission(null);
        setReviewComment('');
        loadSubmissions();
        if (status === 'approved') {
          loadApprovedSubmissions();
        }
      } else {
        alert(`Error: ${response.error}`);
      }
    } catch (error) {
      console.error('Error reviewing submission:', error);
      alert('Error reviewing submission');
    } finally {
      setReviewing(false);
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Submissions List */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Submissions for Review</h2>
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

          {/* Submission Details */}
          <div className="space-y-4">
            {selectedSubmission ? (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Review Submission</h2>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => downloadSubmission(selectedSubmission.submission.id)}
                  >
                    Download Files
                  </Button>
                </div>

                <Card className="p-6">
                  <div className="space-y-4">
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

                    {/* Files */}
                    <div>
                      <h4 className="font-medium mb-2">Files ({selectedSubmission.files.length})</h4>
                      <div className="space-y-2">
                        {selectedSubmission.files.map((file) => (
                          <details key={file.id} className="border rounded p-2">
                            <summary className="cursor-pointer font-mono text-sm">
                              {file.file_name} ({file.file_size} bytes)
                            </summary>
                            <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-x-auto">
                              {file.content}
                            </pre>
                          </details>
                        ))}
                      </div>
                    </div>

                    {/* Review Form */}
                    <div className="border-t pt-4">
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
                          disabled={reviewing || !reviewComment.trim()}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          {reviewing ? (
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
                          disabled={reviewing || !reviewComment.trim()}
                          variant="destructive"
                        >
                          {reviewing ? (
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
                  </div>
                </Card>
              </>
            ) : (
              <Card className="p-6">
                <p className="text-center text-muted-foreground">
                  Select a submission to review
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {activeTab === 'approved' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Approved Submissions</h2>
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
                      onClick={() => downloadSubmission(submission.submission_id)}
                      className="w-full"
                    >
                      Download
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}