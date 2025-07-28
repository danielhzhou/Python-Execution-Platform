import React, { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../../stores/appStore';
import { useEditorStore } from '../../stores/editorStore';
import { fileApi } from '../../lib/api';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { 
  File, 
  Folder, 
  FolderOpen, 
  Plus, 
  Trash2, 
  Edit3,
  RotateCcw,
  ChevronRight,
  ChevronDown
} from 'lucide-react';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: FileNode[];
  isExpanded?: boolean;
}

export function FileTree({ className }: { className?: string }) {
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const { currentContainer, setCurrentFile, setError } = useAppStore();
  const { setContent, setLanguage, setDirty } = useEditorStore();

  // Fetch files from Docker container
  const fetchContainerFiles = useCallback(async () => {
    if (!currentContainer?.id) {
      console.log('❌ No current container available');
      setFileTree([]);
      return;
    }
    
    if (currentContainer.status !== 'running') {
      console.log('⏳ Container not ready yet, status:', currentContainer.status);
      setFileTree([]);
      return;
    }

    setLoading(true);
    try {
      console.log('🗂️ Fetching container files for session:', currentContainer.id);
      console.log('🐳 Docker container ID:', currentContainer.dockerId);
      console.log('📊 Container status:', currentContainer.status);
      
      // Use the existing API client with proper auth handling
      console.log('📡 Calling fileApi.list...');
      const result = await fileApi.list(currentContainer.id);
      
      if (!result.success) {
        console.error('📛 API Error Details:', {
          error: result.error,
          errorType: typeof result.error,
          fullResult: result
        });
        
        // Extract more detailed error message
        let errorMessage = 'Failed to fetch files';
        if (typeof result.error === 'string') {
          errorMessage = result.error;
        } else if (result.error && typeof result.error === 'object') {
          errorMessage = result.error.message || result.error.error || JSON.stringify(result.error);
        }
        
        throw new Error(errorMessage);
      }
      
      const files = result.data || [];
      console.log('📁 Container files:', files);
      
      // Transform flat file list into tree structure
      const tree = buildFileTree(files);
      setFileTree(tree);
      
      // Auto-load main.py if it exists and no file is currently selected
      if (!selectedFile && files.length > 0) {
        const mainFile = files.find(f => f.name === 'main.py' || f.path.endsWith('/main.py'));
        if (mainFile) {
          console.log('🎯 Auto-loading main.py file');
          setTimeout(() => loadFile(mainFile.path), 500);
        }
      }
      
    } catch (error) {
      console.error('Failed to fetch container files:', error);
      setError('Failed to load container files');
      setFileTree([]);
    } finally {
      setLoading(false);
    }
  }, [currentContainer?.id, setError]);

  // Build hierarchical file tree from flat file list
  const buildFileTree = (files: any[]): FileNode[] => {
    const tree: FileNode[] = [];
    const pathMap = new Map<string, FileNode>();

    // Sort files to ensure directories come before their contents
    files.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'directory' ? -1 : 1;
      }
      return a.path.localeCompare(b.path);
    });

    files.forEach(file => {
      const parts = file.path.split('/').filter(Boolean);
      let currentPath = '';
      let currentLevel = tree;

      parts.forEach((part, index) => {
        currentPath += '/' + part;
        const isLast = index === parts.length - 1;
        
        let existingNode = pathMap.get(currentPath);
        
        if (!existingNode) {
          const node: FileNode = {
            name: part,
            path: currentPath,
            type: isLast ? file.type : 'directory',
            size: isLast ? file.size : undefined,
            children: file.type === 'directory' || !isLast ? [] : undefined,
            isExpanded: false
          };
          
          pathMap.set(currentPath, node);
          currentLevel.push(node);
          existingNode = node;
        }
        
        if (existingNode.children) {
          currentLevel = existingNode.children;
        }
      });
    });

    return tree;
  };

  // Load file content into editor
  const loadFile = useCallback(async (filePath: string) => {
    if (!currentContainer?.id) return;

    try {
      console.log('📖 Loading file:', filePath);
      
      const result = await fileApi.get(currentContainer.id, filePath);
      
      if (!result.success) {
        console.error('📛 Failed to load file:', result.error);
        throw new Error(typeof result.error === 'string' ? result.error : 'Failed to load file');
      }
      
      const fileData = result.data;
      
      // Update editor with file content
      setContent(fileData.content);
      setLanguage(getLanguageFromPath(filePath));
      setDirty(false);
      
      // Update app state
      setCurrentFile({
        id: `${currentContainer.id}:${filePath}`,
        name: filePath.split('/').pop() || 'untitled',
        path: filePath,
        content: fileData.content,
        language: getLanguageFromPath(filePath)
      });
      
      setSelectedFile(filePath);
      
    } catch (error) {
      console.error('Failed to load file:', error);
      setError(`Failed to load file: ${filePath}`);
    }
  }, [currentContainer?.id, setContent, setLanguage, setDirty, setCurrentFile, setError]);

  // Get language from file extension
  const getLanguageFromPath = (path: string): string => {
    const extension = path.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'py': return 'python';
      case 'js': return 'javascript';
      case 'ts': return 'typescript';
      case 'json': return 'json';
      case 'md': return 'markdown';
      case 'txt': return 'plaintext';
      case 'yaml':
      case 'yml': return 'yaml';
      default: return 'plaintext';
    }
  };

  // Toggle directory expansion
  const toggleDirectory = useCallback((path: string) => {
    const updateTree = (nodes: FileNode[]): FileNode[] => {
      return nodes.map(node => {
        if (node.path === path && node.type === 'directory') {
          return { ...node, isExpanded: !node.isExpanded };
        }
        if (node.children) {
          return { ...node, children: updateTree(node.children) };
        }
        return node;
      });
    };
    
    setFileTree(updateTree(fileTree));
  }, [fileTree]);

  // Create new file
  const createFile = useCallback(async () => {
    if (!currentContainer?.id) return;

    const fileName = prompt('Enter file name:');
    if (!fileName) return;

    const filePath = `/workspace/${fileName}`;
    
    try {
      const result = await fileApi.save(currentContainer.id, filePath, '');
      
      if (!result.success) {
        console.error('📛 Failed to create file:', result.error);
        throw new Error(typeof result.error === 'string' ? result.error : 'Failed to create file');
      }

      // Refresh file tree and load the new file
      await fetchContainerFiles();
      await loadFile(filePath);
      
    } catch (error) {
      console.error('Failed to create file:', error);
      setError(`Failed to create file: ${fileName}`);
    }
  }, [currentContainer?.id, fetchContainerFiles, loadFile, setError]);

  // Fetch files when container changes
  useEffect(() => {
    if (currentContainer?.status === 'running') {
      // Add small delay to let container fully initialize
      const timer = setTimeout(() => {
        fetchContainerFiles();
      }, 1000);
      
      return () => clearTimeout(timer);
    } else if (currentContainer) {
      console.log('🔄 Container not running yet, will retry when ready');
    }
  }, [currentContainer?.id, currentContainer?.status, fetchContainerFiles]);

  // Render file tree node
  const renderFileNode = (node: FileNode, level: number = 0): React.ReactNode => {
    const isSelected = selectedFile === node.path;
    
    return (
      <div key={node.path}>
        <div
          className={`flex items-center gap-1 p-1 cursor-pointer hover:bg-muted/50 ${
            isSelected ? 'bg-primary/10 text-primary' : ''
          }`}
          style={{ paddingLeft: `${level * 16 + 8}px` }}
          onClick={() => {
            if (node.type === 'directory') {
              toggleDirectory(node.path);
            } else {
              loadFile(node.path);
            }
          }}
        >
          {node.type === 'directory' ? (
            <>
              {node.isExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              {node.isExpanded ? (
                <FolderOpen className="h-4 w-4" />
              ) : (
                <Folder className="h-4 w-4" />
              )}
            </>
          ) : (
            <>
              <div className="w-3" /> {/* Spacer for alignment */}
              <File className="h-4 w-4" />
            </>
          )}
          <span className="text-sm truncate">{node.name}</span>
          {node.size !== undefined && (
            <span className="text-xs text-muted-foreground ml-auto">
              {formatFileSize(node.size)}
            </span>
          )}
        </div>
        
        {node.type === 'directory' && node.isExpanded && node.children && (
          <div>
            {node.children.map(child => renderFileNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      {/* File Tree Header */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <Folder className="h-4 w-4" />
          <span className="font-medium">Files</span>
          {currentContainer && (
            <span className="text-xs text-muted-foreground">
              ({currentContainer.id.substring(0, 8)})
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={createFile}
            disabled={!currentContainer}
            className="h-7 px-2"
          >
            <Plus className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchContainerFiles}
            disabled={loading || !currentContainer}
            className="h-7 px-2"
          >
            <RotateCcw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* File Tree Content */}
      <div className="flex-1 overflow-auto min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="text-sm text-muted-foreground">Loading files...</div>
          </div>
        ) : !currentContainer ? (
          <div className="flex items-center justify-center h-32">
            <div className="text-sm text-muted-foreground">No container selected</div>
          </div>
        ) : fileTree.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2">
            <div className="text-sm text-muted-foreground">No files found</div>
            <Button
              variant="outline"
              size="sm"
              onClick={createFile}
            >
              <Plus className="h-3 w-3 mr-1" />
              Create file
            </Button>
          </div>
        ) : (
          <div className="py-2">
            {fileTree.map(node => renderFileNode(node))}
          </div>
        )}
      </div>

      {/* File Tree Footer */}
      <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>{fileTree.length} items</span>
          {selectedFile && (
            <span>Selected: {selectedFile.split('/').pop()}</span>
          )}
        </div>
      </div>
    </Card>
  );
}