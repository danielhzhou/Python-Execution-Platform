import { useEffect, useState } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { FileTree } from './components/layout/FileTree';

import { MonacoEditor } from './components/editor/MonacoEditor';
import { Terminal } from './components/terminal/Terminal';
import { AuthForm } from './components/common/AuthForm';
import { SubmissionDialog } from './components/common/SubmissionDialog';
import { ToastProvider } from './components/common/ToastProvider';
import { ErrorBoundary, MonacoErrorBoundary, TerminalErrorBoundary } from './components/common/ErrorBoundary';
import { useAppStore } from './stores/appStore';
import { useContainer } from './hooks/useContainer';
import './App.css';

function App() {
  const { 
    isAuthenticated, 
    loading, 
    error, 
    checkAuthStatus, 
    setError 
  } = useAppStore();
  
  const {
    currentContainer,
    createContainer,
    isInitialized
  } = useContainer();

  const [showSubmissionDialog, setShowSubmissionDialog] = useState(false);
  const [hasAttemptedContainerCreation, setHasAttemptedContainerCreation] = useState(false);

  // Check auth status only once on mount
  useEffect(() => {
    console.log('🔑 Checking authentication status...');
    checkAuthStatus();
  }, []); // Remove checkAuthStatus from dependencies to prevent loops

  // Auto-create container when user is authenticated and containers are loaded
  // Only attempt once per session
  useEffect(() => {
    if (
      isAuthenticated && 
      isInitialized && 
      !currentContainer && 
      !loading && 
      !hasAttemptedContainerCreation
    ) {
      console.log('🚀 Auto-creating container for authenticated user...');
      setHasAttemptedContainerCreation(true);
      createContainer().catch(err => {
        console.error('❌ Auto-container creation failed:', err);
        // Reset flag on failure so user can try again manually
        setHasAttemptedContainerCreation(false);
      });
    }
  }, [isAuthenticated, isInitialized, currentContainer, loading, hasAttemptedContainerCreation, createContainer]);

  // Clear any previous errors when component mounts
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

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
          <Header className="border-b flex-shrink-0" />
          
          {/* Main Layout */}
          <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
            {/* Sidebar */}
            <Sidebar />
            
            {/* Main Content - Three Panel Layout */}
            <div className="flex-1 flex overflow-hidden">
              {/* File Tree - Left Panel */}
              <div className="w-64 border-r overflow-hidden">
                <ErrorBoundary>
                  <FileTree />
                </ErrorBoundary>
              </div>
              
              {/* Editor and Terminal - Right Panels */}
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* Code Editor - Top Half */}
                <div className="flex-1 border-b overflow-hidden">
                  <MonacoErrorBoundary>
                    <MonacoEditor />
                  </MonacoErrorBoundary>
                </div>
                
                {/* Terminal - Bottom Half */}
                <div className="flex-1 overflow-hidden">
                  <TerminalErrorBoundary>
                    <Terminal />
                  </TerminalErrorBoundary>
                </div>
              </div>
            </div>
          </div>

          {/* Submission Dialog */}
          <SubmissionDialog
            open={showSubmissionDialog}
            onOpenChange={setShowSubmissionDialog}
          />
        </div>
      </ErrorBoundary>
    </ToastProvider>
  );
}

export default App;
