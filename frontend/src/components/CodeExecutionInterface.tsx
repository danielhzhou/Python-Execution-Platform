import { useEffect, useState, useCallback } from 'react';
import { FileTree } from './layout/FileTree';
import { ResizablePanel } from './layout/ResizablePanel';
import { MonacoEditor } from './editor/MonacoEditor';
import { SaveButton } from './editor/SaveButton';
import { FileTabIndicator } from './editor/FileTabIndicator';
import { Terminal } from './terminal/Terminal';
import { SubmissionDialog } from './common/SubmissionDialog';
import { ErrorBoundary, MonacoErrorBoundary, TerminalErrorBoundary } from './common/ErrorBoundary';
import { SubmissionModal } from './submissions/SubmissionModal';
import { useAppStore } from '../stores/appStore';
import { useContainer } from '../hooks/useContainer';
import { useAutoSave } from '../hooks/useAutoSave';
import { fileApi } from '../lib/api';

interface CodeExecutionInterfaceProps {
  className?: string;
}

export function CodeExecutionInterface({ className }: CodeExecutionInterfaceProps) {
  const { 
    isAuthenticated, 
    currentFile,
    setError 
  } = useAppStore();
  
  const {
    currentContainer,
    createContainer,
    isInitialized
  } = useContainer();

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
  const [showSubmissionModal, setShowSubmissionModal] = useState(false);
  const [currentFiles, setCurrentFiles] = useState<Array<{ path: string; content: string; name: string }>>([]);

  // Function to fetch all files from container for submissions
  const fetchAllFiles = useCallback(async () => {
    if (!currentContainer?.id || currentContainer.status !== 'running') {
      setCurrentFiles([]);
      return;
    }

    try {
      // Get file list
      const listResponse = await fileApi.list(currentContainer.id);
      if (!listResponse.success || !listResponse.data) {
        setCurrentFiles([]);
        return;
      }

      const files = listResponse.data;
      const fileContents: Array<{ path: string; content: string; name: string }> = [];

      // Fetch content for each file (only text files)
      for (const file of files) {
        try {
          if (file.type === 'file' && file.name.match(/\.(py|txt|md|json|yaml|yml|js|ts|html|css|sh)$/i)) {
            const contentResponse = await fileApi.get(currentContainer.id, file.path);
            if (contentResponse.success && contentResponse.data?.content) {
              fileContents.push({
                path: file.path,
                content: contentResponse.data.content,
                name: file.name
              });
            }
          }
        } catch (error) {
          console.warn(`Failed to fetch content for ${file.path}:`, error);
        }
      }

      setCurrentFiles(fileContents);
    } catch (error) {
      console.error('Error fetching files:', error);
      setCurrentFiles([]);
    }
  }, [currentContainer]);

  // Auto-create container when user is authenticated and containers are loaded
  // Only attempt once per session
  useEffect(() => {
    if (
      isAuthenticated && 
      isInitialized && 
      !currentContainer && 
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
  }, [isAuthenticated, isInitialized, currentContainer, hasAttemptedContainerCreation, createContainer]);

  // Handle Run button click - execute code in the integrated terminal
  const handleRunCode = useCallback(async () => {
    if (!currentContainer || !terminalSendCommand || !currentFile) {
      console.error('Cannot run code: missing container, terminal, or file');
      return;
    }

    setIsExecuting(true);
    
    try {
      // First save the current file
      await manualSave();
      
      // Small delay to ensure file is saved
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Run the Python file with full path
      const command = `python3 ${currentFile.path}\n`;
      console.log('🏃‍♂️ Executing command:', command);
      terminalSendCommand(command);
      
    } catch (error) {
      console.error('Error running code:', error);
      setError('Failed to run code. Please try again.');
    } finally {
      // Reset executing state after a delay
      setTimeout(() => setIsExecuting(false), 2000);
    }
  }, [currentContainer, terminalSendCommand, currentFile, manualSave, setError]);

  // Keyboard shortcut for running code
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        handleRunCode();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleRunCode]);

  // Update current files when needed
  useEffect(() => {
    fetchAllFiles();
  }, [fetchAllFiles]);

  return (
    <div className={`flex h-full overflow-hidden bg-background ${className}`}>
      {/* Sidebar - File Explorer */}
      <div className="w-64 border-r border-border bg-[#252526] flex-shrink-0">
        <ErrorBoundary>
          <FileTree />
        </ErrorBoundary>
      </div>
      
      {/* Main Editor Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* File Tab and Action Buttons */}
        <div className="h-9 bg-[#2d2d30] border-b border-border/50 flex items-center justify-between px-2">
          <div className="flex items-center">
            <div className="px-3 py-1 text-sm border-r border-border/30 flex items-center gap-2 text-white bg-[#1e1e1e]">
              <span>{currentFile?.name || 'main.py'}</span>
              <FileTabIndicator />
            </div>
          </div>
          
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
            <button 
              onClick={() => setShowSubmissionModal(true)}
              disabled={!currentContainer || !isAuthenticated}
              className="flex items-center gap-1.5 px-3 py-1 bg-[#28a745] hover:bg-[#218838] disabled:bg-gray-500 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
              title="Submit your work"
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Submit
            </button>
          </div>
        </div>
        
        {/* Content Container - Editor and Terminal */}
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



      {/* Submission Dialog */}
      <SubmissionDialog
        open={showSubmissionDialog}
        onOpenChange={setShowSubmissionDialog}
      />

      {/* Submission Modal */}
      <SubmissionModal
        isOpen={showSubmissionModal}
        onClose={() => setShowSubmissionModal(false)}
        currentFiles={currentFiles}
      />
    </div>
  );
}