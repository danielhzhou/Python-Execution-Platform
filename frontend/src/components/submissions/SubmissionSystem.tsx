import { useAppStore } from '../../stores/appStore';
import { ReviewerDashboard } from './ReviewerDashboard';
import { SimpleSubmitterInterface } from './SimpleSubmitterInterface';
import type { UserRole } from '../../types';

interface SubmissionSystemProps {
  className?: string;
  currentFiles: Array<{ path: string; content: string; name: string }>;
}

export function SubmissionSystem({ className, currentFiles }: SubmissionSystemProps) {
  const { user } = useAppStore();

  if (!user) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="text-lg text-muted-foreground">Please log in to access submissions</div>
      </div>
    );
  }

  // Default to submitter if role is not set
  const userRole: UserRole = user.role || 'submitter';

  if (userRole === 'reviewer' || userRole === 'admin') {
    return <ReviewerDashboard className={className} />;
  }

    return (
    <SimpleSubmitterInterface 
      className={className}
      currentFiles={currentFiles}
    />
  );
}