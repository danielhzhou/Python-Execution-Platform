import React, { useState } from 'react';
import { useAppStore } from '../../stores/appStore';
import { useContainer } from '../../hooks/useContainer';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { 
  FileText, 
  Folder, 
  Plus, 
  Play, 
  Square, 
  Trash2, 
  Container,
  User,
  Settings,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { 
    user, 
    currentContainer, 
    containers, 
    files, 
    currentFile, 
    setCurrentFile,
    sidebarOpen 
  } = useAppStore();
  
  const { 
    createContainer, 
    stopContainer, 
    selectContainer 
  } = useContainer();

  const [expandedSections, setExpandedSections] = useState({
    containers: true,
    files: true,
    settings: false
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleFileSelect = (file: any) => {
    setCurrentFile(file);
  };

  const handleCreateContainer = async () => {
    await createContainer();
  };

  const handleStopContainer = async (containerId: string) => {
    await stopContainer(containerId);
  };

  if (!sidebarOpen) {
    return null;
  }

  return (
    <div className={cn('w-64 h-full border-r bg-background', className)}>
      <div className="flex flex-col h-full">
        {/* User Section */}
        <Card className="m-2 mb-0">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <CardTitle className="text-sm">
                {user?.email || 'Anonymous User'}
              </CardTitle>
            </div>
          </CardHeader>
        </Card>

        {/* Containers Section */}
        <Card className="m-2 mb-0">
          <CardHeader 
            className="pb-2 cursor-pointer"
            onClick={() => toggleSection('containers')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Container className="h-4 w-4" />
                <CardTitle className="text-sm">Containers</CardTitle>
              </div>
              {expandedSections.containers ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </div>
          </CardHeader>
          
          {expandedSections.containers && (
            <CardContent className="pt-0">
              <div className="space-y-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCreateContainer}
                  className="w-full justify-start"
                >
                  <Plus className="h-3 w-3 mr-2" />
                  New Container
                </Button>
                
                {containers.map((container) => (
                  <div
                    key={container.id}
                    className={cn(
                      'flex items-center justify-between p-2 rounded-md border text-sm',
                      currentContainer?.id === container.id 
                        ? 'bg-primary/10 border-primary' 
                        : 'hover:bg-muted cursor-pointer'
                    )}
                    onClick={() => selectContainer(container)}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={cn(
                        'w-2 h-2 rounded-full flex-shrink-0',
                        container.status === 'running' ? 'bg-green-500' : 
                        container.status === 'stopped' ? 'bg-red-500' : 
                        'bg-yellow-500'
                      )} />
                      <span className="truncate">
                        {container.id.substring(0, 8)}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-1">
                      {container.status === 'running' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStopContainer(container.id);
                          }}
                          className="h-6 w-6 p-0"
                        >
                          <Square className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
                
                {containers.length === 0 && (
                  <div className="text-xs text-muted-foreground text-center py-2">
                    No containers available
                  </div>
                )}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Files Section */}
        <Card className="m-2 mb-0 flex-1 min-h-0">
          <CardHeader 
            className="pb-2 cursor-pointer"
            onClick={() => toggleSection('files')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Folder className="h-4 w-4" />
                <CardTitle className="text-sm">Files</CardTitle>
              </div>
              {expandedSections.files ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </div>
          </CardHeader>
          
          {expandedSections.files && (
            <CardContent className="pt-0 flex-1 min-h-0">
              <div className="space-y-1 max-h-full overflow-y-auto">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start mb-2"
                >
                  <Plus className="h-3 w-3 mr-2" />
                  New File
                </Button>
                
                {files.map((file) => (
                  <div
                    key={file.id}
                    className={cn(
                      'flex items-center gap-2 p-2 rounded-md text-sm cursor-pointer',
                      currentFile?.id === file.id 
                        ? 'bg-primary/10 border border-primary' 
                        : 'hover:bg-muted'
                    )}
                    onClick={() => handleFileSelect(file)}
                  >
                    <FileText className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{file.name}</span>
                  </div>
                ))}
                
                {files.length === 0 && (
                  <div className="text-xs text-muted-foreground text-center py-4">
                    No files available
                  </div>
                )}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Settings Section */}
        <Card className="m-2 mt-auto">
          <CardHeader 
            className="pb-2 cursor-pointer"
            onClick={() => toggleSection('settings')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                <CardTitle className="text-sm">Settings</CardTitle>
              </div>
              {expandedSections.settings ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </div>
          </CardHeader>
          
          {expandedSections.settings && (
            <CardContent className="pt-0">
              <div className="space-y-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                >
                  Editor Settings
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                >
                  Terminal Settings
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start"
                >
                  Preferences
                </Button>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
} 