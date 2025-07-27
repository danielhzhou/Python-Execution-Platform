import React, { useEffect } from 'react';
import { useAppStore } from './stores/appStore';
import { useEditorStore } from './stores/editorStore';
import { useTerminalStore } from './stores/terminalStore';
import { useContainer } from './hooks/useContainer';

// Layout components
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ResizablePanel } from './components/layout/ResizablePanel';

// Core components
import { MonacoEditor } from './components/editor/MonacoEditor';
import { Terminal } from './components/terminal/Terminal';

// Common components
import { SubmissionDialog } from './components/common/SubmissionDialog';
import { ToastProvider } from './components/common/ToastProvider';
import { AuthForm } from './components/common/AuthForm';

// Hooks
import { useAutoSave } from './hooks/useAutoSave';

function App() {
  const { 
    user,
    isAuthenticated,
    currentContainer, 
    loading, 
    error,
    checkAuthStatus,
    setUser,
    setAuthenticated,
    setError
  } = useAppStore();

  const { code } = useEditorStore();
  const { output } = useTerminalStore();
  const { createContainer } = useContainer();

  // Auto-save functionality
  useAutoSave();

  // Check authentication status on app load
  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Handle successful authentication
  const handleAuthSuccess = (userData: any) => {
    setUser(userData);
    setAuthenticated(true);
    setError(null);
  };

  // Show authentication form if not authenticated
  if (!isAuthenticated) {
    return (
      <ToastProvider>
        <AuthForm onAuthSuccess={handleAuthSuccess} />
      </ToastProvider>
    );
  }

  // Show loading state
  if (loading && !currentContainer) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Setting up your environment...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error && !currentContainer) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null);
              createContainer();
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <ToastProvider>
      <div className="h-screen flex flex-col bg-gray-50">
        {/* Header */}
        <Header />

        {/* Main content area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar */}
          <Sidebar />

          {/* Main editor and terminal area */}
          <div className="flex-1 flex flex-col">
            <ResizablePanel
              direction="vertical"
              initialSize={60}
              minSize={30}
              maxSize={80}
              className="flex-1"
            >
              {/* Editor panel */}
              <div className="h-full border-r border-gray-200">
                <div className="h-full flex flex-col">
                  <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                    <span className="text-sm text-gray-600">main.py</span>
                    <div className="w-16"></div> {/* Spacer for centering */}
                  </div>
                  <div className="flex-1">
                    <MonacoEditor />
                  </div>
                </div>
              </div>

              {/* Terminal panel */}
              <div className="h-full bg-gray-900">
                <div className="h-full flex flex-col">
                  <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                    <span className="text-sm text-gray-300">Terminal</span>
                    <div className="w-16"></div> {/* Spacer for centering */}
                  </div>
                  <div className="flex-1">
                    <Terminal />
                  </div>
                </div>
              </div>
            </ResizablePanel>
          </div>
        </div>

        {/* Submission Dialog */}
        <SubmissionDialog />
      </div>
    </ToastProvider>
  );
}

export default App;
