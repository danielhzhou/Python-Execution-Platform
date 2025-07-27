import React, { useState } from 'react';
import { useAppStore } from '../../stores/appStore';
import { useEditorStore } from '../../stores/editorStore';
import { useTerminalStore } from '../../stores/terminalStore';
import { Button } from '../ui/button';
import { 
  Menu, 
  Play, 
  Square, 
  Save, 
  Upload, 
  Download,
  Settings,
  User,
  LogOut,
  Code,
  Terminal as TerminalIcon,
  Wifi,
  WifiOff
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const { 
    user, 
    currentContainer, 
    toggleSidebar, 
    sidebarOpen,
    isLoading,
    error 
  } = useAppStore();
  
  const { isDirty, content } = useEditorStore();
  const { isConnected } = useTerminalStore();
  
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleRunCode = () => {
    // This would trigger code execution
    console.log('Running code:', content);
  };

  const handleSubmitCode = () => {
    // This would open the submission dialog
    console.log('Submitting code for review');
  };

  const handleSaveFile = () => {
    // This would trigger manual save
    console.log('Saving file');
  };

  return (
    <header className={cn(
      'flex items-center justify-between px-4 py-2 border-b bg-background',
      className
    )}>
      {/* Left Section */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className="p-2"
        >
          <Menu className="h-4 w-4" />
        </Button>
        
        <div className="flex items-center gap-2">
          <Code className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold">
            Python Execution Platform
          </h1>
        </div>
        
        {/* Status Indicators */}
        <div className="flex items-center gap-3 text-sm">
          {/* Container Status */}
          {currentContainer && (
            <div className="flex items-center gap-1">
              <div className={cn(
                'w-2 h-2 rounded-full',
                currentContainer.status === 'running' ? 'bg-green-500' : 
                currentContainer.status === 'stopped' ? 'bg-red-500' : 
                'bg-yellow-500'
              )} />
              <span className="text-muted-foreground">
                Container: {currentContainer.id.substring(0, 8)}
              </span>
            </div>
          )}
          
          {/* Terminal Connection Status */}
          <div className="flex items-center gap-1">
            {isConnected ? (
              <Wifi className="h-3 w-3 text-green-500" />
            ) : (
              <WifiOff className="h-3 w-3 text-red-500" />
            )}
            <span className={cn(
              'text-xs',
              isConnected ? 'text-green-600' : 'text-red-600'
            )}>
              Terminal {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          {/* File Status */}
          {isDirty && (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-yellow-500" />
              <span className="text-yellow-600 text-xs">Unsaved changes</span>
            </div>
          )}
        </div>
      </div>

      {/* Center Section - Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="default"
          size="sm"
          onClick={handleRunCode}
          disabled={isLoading || !currentContainer}
          className="gap-2"
        >
          <Play className="h-4 w-4" />
          Run Code
        </Button>
        
        <Button
          variant="outline"
          size="sm"
          onClick={handleSaveFile}
          disabled={!isDirty}
          className="gap-2"
        >
          <Save className="h-4 w-4" />
          Save
        </Button>
        
        <Button
          variant="outline"
          size="sm"
          onClick={handleSubmitCode}
          disabled={isLoading || !currentContainer}
          className="gap-2"
        >
          <Upload className="h-4 w-4" />
          Submit
        </Button>
        
        <div className="w-px h-6 bg-border mx-2" />
        
        <Button
          variant="ghost"
          size="sm"
          className="gap-2"
        >
          <Download className="h-4 w-4" />
          Export
        </Button>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Error Display */}
        {error && (
          <div className="text-sm text-red-600 max-w-xs truncate">
            {error}
          </div>
        )}
        
        {/* Loading Indicator */}
        {isLoading && (
          <div className="text-sm text-muted-foreground">
            Loading...
          </div>
        )}
        
        <Button
          variant="ghost"
          size="sm"
          className="p-2"
        >
          <Settings className="h-4 w-4" />
        </Button>
        
        {/* User Menu */}
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="gap-2"
          >
            <User className="h-4 w-4" />
            <span className="text-sm">
              {user?.email?.split('@')[0] || 'User'}
            </span>
          </Button>
          
          {showUserMenu && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-background border rounded-md shadow-lg z-50">
              <div className="p-2">
                <div className="px-2 py-1 text-sm text-muted-foreground border-b mb-2">
                  {user?.email || 'Anonymous User'}
                </div>
                
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                >
                  <User className="h-4 w-4 mr-2" />
                  Profile
                </Button>
                
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Settings
                </Button>
                
                <div className="border-t my-2" />
                
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-red-600 hover:text-red-700"
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  Logout
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Backdrop for user menu */}
      {showUserMenu && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </header>
  );
} 