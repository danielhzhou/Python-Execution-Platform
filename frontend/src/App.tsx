import React, { useEffect, useState } from 'react';
import { useAppStore } from './stores/appStore';
import { useContainer } from './hooks/useContainer';
import { authApi } from './lib/api';

// Layout Components
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ResizablePanel } from './components/layout/ResizablePanel';

// Main Components
import { MonacoEditor } from './components/editor/MonacoEditor';
import { Terminal } from './components/terminal/Terminal';

// Common Components
import { SubmissionDialog } from './components/common/SubmissionDialog';
import { ToastProvider } from './components/common/ToastProvider';

// UI Components
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';

import { cn } from './lib/utils';
import './App.css';

function App() {
  const {
    user,
    currentContainer,
    sidebarOpen,
    isLoading,
    error,
    setUser,
    setError,
    setLoading
  } = useAppStore();

  const { createContainer } = useContainer();
  const [submissionDialogOpen, setSubmissionDialogOpen] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize the application
  useEffect(() => {
    const initializeApp = async () => {
      setLoading(true);
      
      try {
        // Try to get current user (mock implementation)
        const userResponse = await authApi.getCurrentUser();
        if (userResponse.success && userResponse.data) {
          setUser(userResponse.data);
        } else {
          // For demo purposes, create a mock user
          setUser({
            id: 'demo-user',
            email: 'demo@example.com',
            role: 'learner',
            createdAt: new Date(),
            lastActivity: new Date()
          });
        }

        // Auto-create a container if none exists
        if (!currentContainer) {
          await createContainer();
        }

        setIsInitialized(true);
      } catch (error) {
        console.error('Failed to initialize app:', error);
        setError('Failed to initialize application');
        
        // Still set a demo user for development
        setUser({
          id: 'demo-user',
          email: 'demo@example.com',
          role: 'learner',
          createdAt: new Date(),
          lastActivity: new Date()
        });
        setIsInitialized(true);
      } finally {
        setLoading(false);
      }
    };

    initializeApp();
  }, [setUser, setError, setLoading, currentContainer, createContainer]);

  // Loading screen
  if (!isInitialized || isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="w-96">
          <CardHeader>
            <CardTitle className="text-center">Python Execution Platform</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center space-y-4">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-muted-foreground text-center">
                {isLoading ? 'Initializing application...' : 'Setting up your environment...'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error screen
  if (error && !isInitialized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="w-96">
          <CardHeader>
            <CardTitle className="text-center text-red-600">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                {error}
              </p>
              <Button 
                onClick={() => window.location.reload()}
                variant="outline"
              >
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <ToastProvider>
      <div className="h-screen flex flex-col bg-background">
        {/* Header */}
        <Header />

        {/* Main Content */}
        <div className="flex-1 flex min-h-0">
          {/* Sidebar */}
          {sidebarOpen && <Sidebar />}

          {/* Main Editor Area */}
          <div className="flex-1 flex flex-col min-w-0">
            {currentContainer ? (
              <ResizablePanel
                direction="vertical"
                defaultSize={60}
                minSize={30}
                maxSize={80}
                className="flex-1"
              >
                {/* Editor Panel */}
                <div className="p-2 h-full">
                  <MonacoEditor className="h-full" />
                </div>

                {/* Terminal Panel */}
                <div className="p-2 h-full">
                  <Terminal className="h-full" />
                </div>
              </ResizablePanel>
            ) : (
              /* No Container State */
              <div className="flex-1 flex items-center justify-center p-8">
                <Card className="w-full max-w-md">
                  <CardHeader>
                    <CardTitle className="text-center">No Container Available</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-col items-center space-y-4">
                      <p className="text-sm text-muted-foreground text-center">
                        You need a container to start coding. Create one to get started.
                      </p>
                      <Button 
                        onClick={createContainer}
                        disabled={isLoading}
                        className="w-full"
                      >
                        {isLoading ? (
                          <>
                            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                            Creating Container...
                          </>
                        ) : (
                          'Create Container'
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        {/* Submission Dialog */}
        <SubmissionDialog
          open={submissionDialogOpen}
          onOpenChange={setSubmissionDialogOpen}
        />

        {/* Global Error Display */}
        {error && (
          <div className="fixed bottom-4 right-4 z-50">
            <Card className="bg-red-50 border-red-200 max-w-sm">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-red-800">Error</p>
                    <p className="text-xs text-red-600 mt-1">{error}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setError(null)}
                    className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                  >
                    ×
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Keyboard Shortcuts Helper */}
        <div className="fixed bottom-4 left-4 z-40">
          <Card className="bg-muted/50 backdrop-blur-sm">
            <CardContent className="p-2">
              <div className="text-xs text-muted-foreground space-y-1">
                <div><kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl+S</kbd> Save</div>
                <div><kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl+Enter</kbd> Run</div>
                <div><kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl+`</kbd> Terminal</div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </ToastProvider>
  );
}

export default App;
