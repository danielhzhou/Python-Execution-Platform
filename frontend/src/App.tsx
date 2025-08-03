import { useEffect, useState, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { FileTree } from './components/layout/FileTree';
import { ResizablePanel } from './components/layout/ResizablePanel';

import { MonacoEditor } from './components/editor/MonacoEditor';
import { SaveButton } from './components/editor/SaveButton';
import { SaveStatusIndicator } from './components/editor/SaveStatusIndicator';
import { FileTabIndicator } from './components/editor/FileTabIndicator';
import { Terminal } from './components/terminal/Terminal';
import { AuthForm } from './components/common/AuthForm';
import { SubmissionDialog } from './components/common/SubmissionDialog';
import { ToastProvider } from './components/common/ToastProvider';
import { ErrorBoundary, MonacoErrorBoundary, TerminalErrorBoundary } from './components/common/ErrorBoundary';
import { useAppStore } from './stores/appStore';
import { useContainer } from './hooks/useContainer';

import { useEditorStore } from './stores/editorStore';
import { useTerminalStore } from './stores/terminalStore';
import { useAutoSave } from './hooks/useAutoSave';

import './App.css';

function App() {
  const { 
    isAuthenticated, 
    loading, 
    error, 
    currentFile,
    checkAuthStatus, 
    setError 
  } = useAppStore();
  
  const {
    currentContainer,
    createContainer,
    isInitialized
  } = useContainer();

  const { content } = useEditorStore();
  const { isConnected } = useTerminalStore();
  const { manualSave } = useAutoSave();
  
  // Store the sendCommand function from Terminal component
  const [terminalSendCommand, setTerminalSendCommand] = useState<((command: string) => void) | null>(null);
  
  // Callback to receive sendCommand from Terminal
  const handleSendCommandReady = useCallback((sendCommand: (command: string) => void) => {
    console.log('🎯 App received sendCommand function from Terminal');
    setTerminalSendCommand(() => sendCommand);
  }, []);

  const [showSubmissionDialog, setShowSubmissionDialog] = useState(false);
  const [hasAttemptedContainerCreation, setHasAttemptedContainerCreation] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

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
      
      // Add a small delay to ensure all auth-related state is settled
      const timer = setTimeout(async () => {
        try {
          await createContainer();
          console.log('✅ Container created successfully');
        } catch (err) {
          console.error('❌ Auto-container creation failed:', err);
          // Reset flag on failure so user can try again manually
          setHasAttemptedContainerCreation(false);
        }
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, isInitialized, currentContainer, loading, hasAttemptedContainerCreation, createContainer]);

  // Clear any previous errors when component mounts
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  // Debug: Track app state during initialization
  useEffect(() => {
    console.log('🔍 App State Debug:', {
      isAuthenticated,
      loading,
      hasContainer: !!currentContainer,
      containerStatus: currentContainer?.status,
      isTerminalConnected: isConnected,
      hasAttemptedContainerCreation,
      isContainerInitialized: isInitialized
    });
  }, [isAuthenticated, loading, currentContainer, isConnected, hasAttemptedContainerCreation, isInitialized]);

  // Handle Run button click - execute code in the integrated terminal
  const handleRunCode = async () => {
    if (!currentContainer) {
      setError('No active container. Please wait for container to be ready.');
      return;
    }

    if (!isConnected) {
      setError('Terminal not connected. Please wait for connection.');
      return;
    }

    if (!terminalSendCommand) {
      console.log('🔍 DEBUG: terminalSendCommand not available:', {
        terminalSendCommand: !!terminalSendCommand,
        isConnected,
        currentContainer: !!currentContainer
      });
      setError('Terminal not ready. Please wait for terminal to initialize.');
      return;
    }

    if (!content.trim()) {
      setError('No code to execute.');
      return;
    }

    if (isExecuting) {
      return; // Prevent multiple simultaneous executions
    }

    setIsExecuting(true);
    setError(null);

    try {
      // Use current file if available, otherwise create a temporary file
      let filename = currentFile?.path || `/workspace/script_${Date.now()}.py`;
      
      // If using current file, save it first
      if (currentFile) {
        console.log('🔄 Saving file before execution:', {
          path: currentFile.path,
          contentLength: content.length
        });
        
        try {
          await manualSave();
          console.log('✅ File saved successfully before execution');
          
          // Add a small delay to ensure the save operation completes
          await new Promise(resolve => setTimeout(resolve, 500));
          
          filename = currentFile.path;
        } catch (saveError) {
          console.error('❌ Failed to save file before execution:', saveError);
          setError('Failed to save file before execution');
          return;
        }
      } else {
        // Create temporary file for execution
        filename = `/workspace/script_${Date.now()}.py`;
        console.log('📝 Creating temporary file for execution:', filename);
        terminalSendCommand(`cat > ${filename} << 'EOF'\n${content}\nEOF\n`);
      }
      
      // Execute the Python file
      terminalSendCommand(`python3 ${filename}\n`);
      
    } catch (error) {
      console.error('Code execution error:', error);
      setError('Failed to execute code. Please try again.');
    } finally {
      setIsExecuting(false);
    }
  };

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
          
          {/* Main Layout - VS Code Style */}
          <div className="flex h-[calc(100vh-5rem)] overflow-hidden bg-background">
            {/* Sidebar - File Explorer */}
            <div className="w-64 border-r border-border bg-[#252526] flex-shrink-0">
              <ErrorBoundary>
                <FileTree />
              </ErrorBoundary>
            </div>
            
            {/* Main Editor Area */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Editor Tabs Area */}
              <div className="h-9 bg-[#2d2d30] border-b border-border/50 flex items-center justify-between px-2">
                <div className="flex items-center">
                  <div className="px-3 py-1 text-sm text-white bg-[#1e1e1e] border-r border-border/30 flex items-center gap-2">
                    <span>{currentFile?.name || 'main.py'}</span>
                    <FileTabIndicator />
                  </div>
                </div>
                
                {/* Save and Run Buttons */}
                <div className="flex items-center gap-2">
                  <SaveButton />
                  <button 
                    onClick={handleRunCode}
                    disabled={!currentContainer || !isAuthenticated || isExecuting}
                    className="flex items-center gap-1.5 px-3 py-1 bg-[#0e639c] hover:bg-[#1177bb] disabled:bg-gray-500 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
                    title="Run Python file (Ctrl+Enter)"
                  >
                    {isExecuting ? (
                      <>
                        <div className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin"></div>
                        Running
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                        </svg>
                        Run
                      </>
                    )}
                  </button>
                </div>
              </div>
              
              {/* Editor and Terminal Container */}
              <div className="flex-1 flex flex-col min-h-0">
                <ResizablePanel
                  direction="vertical"
                  defaultSize={60}
                  minSize={20}
                  maxSize={90}
                  onResize={() => {
                    // Trigger immediate window resize event for terminal
                    window.dispatchEvent(new Event('resize'));
                  }}
                >
                  {/* Code Editor */}
                  <div className="h-full bg-[#1e1e1e]">
                    <MonacoErrorBoundary>
                      <MonacoEditor />
                    </MonacoErrorBoundary>
                  </div>
                  
                  {/* Integrated Terminal Panel */}
                  <div className="h-full bg-[#1e1e1e] flex flex-col">
                    {/* Terminal Header */}
                    <div className="h-9 bg-[#2d2d30] border-t border-border/30 flex items-center px-2 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        <span className="px-3 py-1 text-sm text-white bg-[#1e1e1e] rounded-t-sm">Terminal</span>
                      </div>
                    </div>
                    
                    {/* Terminal Content */}
                    <div className="flex-1 min-h-0">
                      <TerminalErrorBoundary>
                        <Terminal onSendCommandReady={handleSendCommandReady} />
                      </TerminalErrorBoundary>
                    </div>
                  </div>
                </ResizablePanel>
              </div>
            </div>
          </div>

          {/* VS Code Style Status Bar */}
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
