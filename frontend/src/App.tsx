import { useEffect } from 'react';
import { Header } from './components/layout/Header';
import { AuthForm } from './components/common/AuthForm';
import { ToastProvider } from './components/common/ToastProvider';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { CodeExecutionInterface } from './components/CodeExecutionInterface';
import { ReviewerDashboard } from './components/submissions/ReviewerDashboard';
import { SaveStatusIndicator } from './components/editor/SaveStatusIndicator';
import { useAppStore } from './stores/appStore';
import { useContainer } from './hooks/useContainer';
import type { UserRole } from './types';

import './App.css';

function App() {
  const { 
    isAuthenticated, 
    loading, 
    error, 
    user,
    checkAuthStatus, 
    setError 
  } = useAppStore();

  const { currentContainer } = useContainer();

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Clear any previous errors when component mounts
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  // Show loading screen
  if (loading) {
    return (
      <ToastProvider>
        <ErrorBoundary>
          <div className="min-h-screen bg-background flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              <div className="text-lg">Loading...</div>
            </div>
          </div>
        </ErrorBoundary>
      </ToastProvider>
    );
  }

  // Show authentication form if not authenticated
  if (!isAuthenticated) {
    return (
      <ToastProvider>
        <ErrorBoundary>
          <div className="min-h-screen bg-background flex items-center justify-center">
            <AuthForm />
          </div>
        </ErrorBoundary>
      </ToastProvider>
    );
  }

  // Determine user role (default to submitter if not set)
  const userRole: UserRole = user?.role || 'submitter';

  return (
    <ToastProvider>
      <ErrorBoundary>
        <div className="h-screen bg-background overflow-hidden">
          {/* Global Error Display */}
          {error && (
            <div className="bg-destructive/10 border-l-4 border-destructive p-4 mb-4">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-destructive">
                    {typeof error === 'string' ? error : 'An error occurred'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Header */}
          <Header className="flex-shrink-0" />
          
          {/* Main Content - Role-based UI */}
          <div className="h-[calc(100vh-5rem)] overflow-hidden">
            {userRole === 'reviewer' || userRole === 'admin' ? (
              // Reviewer Interface - Only submission dashboard
              <div className="h-full p-6 bg-background overflow-auto">
                <ReviewerDashboard />
              </div>
            ) : (
              // Submitter Interface - Full code execution environment
              <div className="h-full relative">
                <CodeExecutionInterface />
              </div>
            )}
          </div>

          {/* VS Code Style Status Bar - Only for submitters */}
          {userRole !== 'reviewer' && userRole !== 'admin' && (
            <div className="h-6 bg-[#007acc] text-white text-xs flex items-center justify-between px-3 flex-shrink-0">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-white/80"></div>
                  <span>Python 3.11.13</span>
                </div>
                <span>UTF-8</span>
                <span>LF</span>
                <span>Spaces: 4</span>
                {/* Save Status in Status Bar */}
                <SaveStatusIndicator />
              </div>
              
              <div className="flex items-center gap-4">
                <span>Ln 1, Col 1</span>
                <span>100%</span>
                {currentContainer && (
                  <div className="flex items-center gap-1">
                    <div className={`w-2 h-2 rounded-full ${
                      currentContainer.status === 'running' ? 'bg-green-400' : 'bg-red-400'
                    }`}></div>
                    <span>{currentContainer.status === 'running' ? 'Ready' : 'Starting'}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </ErrorBoundary>
    </ToastProvider>
  );
}

export default App;