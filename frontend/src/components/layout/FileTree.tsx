import React, { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../../stores/appStore';
import { useEditorStore } from '../../stores/editorStore';
import { useTerminalStore } from '../../stores/terminalStore';
import { fileApi } from '../../lib/api';
import { CreateFileModal } from '../common/CreateFileModal';

import { 
  File, 
  Folder, 
  FolderOpen, 
  Plus, 
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
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingFile, setCreatingFile] = useState(false);
  
  const { currentContainer, setCurrentFile, setError } = useAppStore();
  const { setContent, setLanguage, setDirty } = useEditorStore();
  const { currentDirectory } = useTerminalStore();

  // Fetch files from Docker container with retry logic
  const fetchContainerFiles = useCallback(async (retryCount = 0) => {
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
      
      // Retry logic for container not ready errors
      if (retryCount < 3 && (
        (error as Error).message?.includes('container not ready') ||
        (error as Error).message?.includes('connection refused') ||
        (error as Error).message?.includes('not found')
      )) {
        console.log(`🔄 Retrying file fetch in ${(retryCount + 1) * 1000}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => {
          fetchContainerFiles(retryCount + 1);
        }, (retryCount + 1) * 1000);
        return;
      }
      
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

              parts.forEach((part: string, index: number) => {
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

  // Open create file modal
  const openCreateFileModal = useCallback(() => {
    if (!currentContainer?.id) return;
    setShowCreateModal(true);
  }, [currentContainer?.id]);

  // Create new file with template
  const handleCreateFile = useCallback(async (fileName: string, template: string = '') => {
    if (!currentContainer?.id) return;

    setCreatingFile(true);
    
    // Determine the file path based on current directory
    const basePath = currentDirectory && currentDirectory !== '/workspace' 
      ? currentDirectory 
      : '/workspace';
    const filePath = `${basePath}/${fileName}`.replace(/\/+/g, '/');
    
    try {
      console.log('🔨 Creating file:', filePath, 'with template length:', template.length);
      
      const result = await fileApi.save(currentContainer.id, filePath, template);
      
      if (!result.success) {
        console.error('📛 Failed to create file:', result.error);
        throw new Error(typeof result.error === 'string' ? result.error : 'Failed to create file');
      }

      // Refresh file tree and load the new file
      await fetchContainerFiles();
      await loadFile(filePath);
      
      console.log('✅ File created successfully:', filePath);
      
    } catch (error) {
      console.error('Failed to create file:', error);
      setError(`Failed to create file: ${fileName}`);
      throw error; // Re-throw to let modal handle it
    } finally {
      setCreatingFile(false);
    }
  }, [currentContainer?.id, currentDirectory, fetchContainerFiles, loadFile, setError]);

  // Create new folder
  const handleCreateFolder = useCallback(async (folderName: string) => {
    if (!currentContainer?.id) return;

    setCreatingFile(true);
    
    // Determine the folder path based on current directory
    const basePath = currentDirectory && currentDirectory !== '/workspace' 
      ? currentDirectory 
      : '/workspace';
    const folderPath = `${basePath}/${folderName}`.replace(/\/+/g, '/');
    
    try {
      console.log('📁 Creating folder:', folderPath);
      
      // Create a temporary file in the folder to ensure it exists, then remove it
      const tempFilePath = `${folderPath}/.gitkeep`;
      const result = await fileApi.save(currentContainer.id, tempFilePath, '# This file ensures the directory exists\n');
      
      if (!result.success) {
        console.error('📛 Failed to create folder:', result.error);
        throw new Error(typeof result.error === 'string' ? result.error : 'Failed to create folder');
      }

      // Refresh file tree
      await fetchContainerFiles();
      
      console.log('✅ Folder created successfully:', folderPath);
      
    } catch (error) {
      console.error('Failed to create folder:', error);
      setError(`Failed to create folder: ${folderName}`);
      throw error; // Re-throw to let modal handle it
    } finally {
      setCreatingFile(false);
    }
  }, [currentContainer?.id, currentDirectory, fetchContainerFiles, setError]);

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

  // Listen for workspace file changes only (not directory navigation)
  useEffect(() => {
    const handleFilesystemChange = (event: CustomEvent) => {
      const { commandType } = event.detail;
      console.log('📁 FileTree received filesystem change event:', event.detail);
      
      // Only refresh for commands that actually affect workspace files
      if (['create_file', 'create_dir', 'delete', 'move_copy', 'extract', 'git_operations'].includes(commandType)) {
        // Refresh file tree with a small delay to allow command to complete
        setTimeout(() => {
          fetchContainerFiles();
        }, 1000);
      }
    };

    // Add event listener
    window.addEventListener('filesystem-change', handleFilesystemChange as EventListener);

    // Cleanup
    return () => {
      window.removeEventListener('filesystem-change', handleFilesystemChange as EventListener);
    };
  }, [fetchContainerFiles]);

  // Render file tree node - VS Code Style
  const renderFileNode = (node: FileNode, level: number = 0): React.ReactNode => {
    const isSelected = selectedFile === node.path;
    
    return (
      <div key={node.path}>
        <div
          className={`flex items-center gap-1 py-0.5 cursor-pointer transition-colors group ${
            isSelected 
              ? 'bg-[#094771] text-white' 
              : 'hover:bg-white/5 text-white/90'
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
                <ChevronDown className="h-3 w-3 text-white/60" />
              ) : (
                <ChevronRight className="h-3 w-3 text-white/60" />
              )}
              {node.isExpanded ? (
                <FolderOpen className="h-4 w-4 text-[#dcb67a]" />
              ) : (
                <Folder className="h-4 w-4 text-[#dcb67a]" />
              )}
            </>
          ) : (
            <>
              <div className="w-3" /> {/* Spacer for alignment */}
              <File className={`h-4 w-4 ${getFileIcon(node.name)}`} />
            </>
          )}
          <span className="text-sm truncate select-none">{node.name}</span>
        </div>
        
        {node.type === 'directory' && node.isExpanded && node.children && (
          <div>
            {node.children.map(child => renderFileNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  // Get file icon color based on extension - VS Code Style
  const getFileIcon = (fileName: string): string => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'py': return 'text-[#3776ab]';
      case 'js': return 'text-[#f7df1e]';
      case 'ts': return 'text-[#3178c6]';
      case 'json': return 'text-[#cbcb41]';
      case 'md': return 'text-white/70';
      case 'txt': return 'text-white/60';
      case 'yaml':
      case 'yml': return 'text-[#cb171e]';
      case 'css': return 'text-[#1572b6]';
      case 'html': return 'text-[#e34f26]';
      default: return 'text-white/70';
    }
  };

  return (
    <div className={`flex flex-col h-full bg-[#252526] ${className}`}>
      {/* File Tree Header - VS Code Style */}
      <div className="flex items-center justify-between px-3 py-2 text-white/90">
        <div className="flex flex-col gap-1">
          <span className="font-medium text-xs uppercase tracking-wider">Explorer</span>
          {currentDirectory && currentDirectory !== '/workspace' && (
            <span className="text-xs text-white/60 font-mono">
              {currentDirectory.replace('/workspace/', './')}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          <button
            onClick={openCreateFileModal}
            disabled={!currentContainer}
            className="p-1 hover:bg-white/10 rounded text-white/70 hover:text-white disabled:opacity-50"
            title="New File"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            onClick={() => fetchContainerFiles()}
            disabled={loading || !currentContainer}
            className="p-1 hover:bg-white/10 rounded text-white/70 hover:text-white disabled:opacity-50"
            title="Refresh"
          >
            <RotateCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* File Tree Content */}
      <div className="flex-1 overflow-auto min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="text-sm text-white/60">Loading files...</div>
          </div>
        ) : !currentContainer ? (
          <div className="flex items-center justify-center h-32">
            <div className="text-sm text-white/60">No container available</div>
          </div>
        ) : fileTree.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 gap-3">
            <div className="text-sm text-white/60">No files found</div>
            <button
              onClick={openCreateFileModal}
              className="px-3 py-1 bg-[#0e639c] hover:bg-[#1177bb] text-white text-sm rounded"
            >
              New File
            </button>
          </div>
        ) : (
          <div className="py-1">
            {fileTree.map(node => renderFileNode(node))}
          </div>
        )}
      </div>

      {/* Create File Modal */}
      <CreateFileModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreateFile={handleCreateFile}
        onCreateFolder={handleCreateFolder}
        currentDirectory={currentDirectory || '/workspace'}
        loading={creatingFile}
      />
    </div>
  );
}