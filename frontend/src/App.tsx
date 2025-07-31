import { useEffect, useState } from 'react';
import { Header } from './components/layout/Header';
import { FileTree } from './components/layout/FileTree';
import { ResizablePanel } from './components/layout/ResizablePanel';

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
          <Header className="flex-shrink-0" />
          
          {/* Main Layout with Resizable Panels */}
          <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden bg-background">
            <ResizablePanel
              direction="horizontal"
              defaultSize={20}
              minSize={15}
              maxSize={35}
            >
              {/* File Explorer Panel */}
              <div className="h-full border-r border-border/50 bg-muted/20">
                <ErrorBoundary>
                  <FileTree />
                </ErrorBoundary>
              </div>
              
              {/* Editor & Terminal Panel */}
              <div className="h-full flex flex-col">
                <ResizablePanel
                  direction="vertical"
                  defaultSize={65}
                  minSize={30}
                  maxSize={80}
                >
                  {/* Code Editor */}
                  <div className="h-full border-b border-border/50">
                    <MonacoErrorBoundary>
                      <MonacoEditor />
                    </MonacoErrorBoundary>
                  </div>
                  
                  {/* Terminal/Output */}
                  <div className="h-full bg-background">
                    <TerminalErrorBoundary>
                      <Terminal />
                    </TerminalErrorBoundary>
                  </div>
                </ResizablePanel>
              </div>
            </ResizablePanel>
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
