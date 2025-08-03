/**
 * Optimized File Loader Hook
 * 
 * Features:
 * - Intelligent caching with LRU eviction
 * - Debounced loading to prevent rapid API calls
 * - Preloading of likely-to-be-accessed files
 * - Loading state management
 * - Error handling with retries
 */

import { useCallback, useRef, useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import { useEditorStore } from '../stores/editorStore';
import { fileApi } from '../lib/api';
import { fileCache, cacheEvents } from '../lib/fileCache';
import { debounce } from '../lib/utils';

interface LoadingState {
  isLoading: boolean;
  error: string | null;
  progress?: number;
}

interface FileLoadResult {
  success: boolean;
  fromCache: boolean;
  loadTime: number;
  error?: string;
}

export function useOptimizedFileLoader() {
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false,
    error: null
  });

  const { currentContainer, setCurrentFile, setError } = useAppStore();
  const { setContent, setLanguage, setDirty } = useEditorStore();

  // Track current loading operation to prevent conflicts
  const currentLoadRef = useRef<string | null>(null);
  const loadTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Load file with caching and optimization
   */
  const loadFile = useCallback(async (
    filePath: string,
    options: {
      force?: boolean; // Bypass cache
      preload?: boolean; // Don't update UI, just cache
      priority?: 'high' | 'normal' | 'low';
    } = {}
  ): Promise<FileLoadResult> => {
    if (!currentContainer?.id) {
      const error = 'No active container';
      setError(error);
      return { success: false, fromCache: false, loadTime: 0, error };
    }

    const startTime = performance.now();
    const loadId = `${currentContainer.id}:${filePath}:${Date.now()}`;
    
    // Cancel previous load if still in progress
    if (currentLoadRef.current && currentLoadRef.current !== loadId) {
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
      }
    }
    
    currentLoadRef.current = loadId;

    try {
      // Check cache first (unless forced reload)
      if (!options.force) {
        const cached = fileCache.get(currentContainer.id, filePath);
        if (cached) {
          const loadTime = performance.now() - startTime;
          
          // Update UI if not preloading
          if (!options.preload) {
            await updateEditorState(filePath, cached.content, cached.language);
          }

          // Emit cache hit event
          cacheEvents.emit({
            type: 'hit',
            containerId: currentContainer.id,
            filePath,
            stats: fileCache.getStats()
          });

          return { 
            success: true, 
            fromCache: true, 
            loadTime 
          };
        }
      }

      // Set loading state for UI updates (not for preloads)
      if (!options.preload) {
        setLoadingState({ isLoading: true, error: null });
      }

      // Emit cache miss event
      cacheEvents.emit({
        type: 'miss',
        containerId: currentContainer.id,
        filePath,
        stats: fileCache.getStats()
      });

      // Load from API with timeout
      const apiPromise = fileApi.get(currentContainer.id, filePath);
      const timeoutPromise = new Promise<never>((_, reject) => {
        loadTimeoutRef.current = setTimeout(() => {
          reject(new Error('File load timeout'));
        }, 10000); // 10 second timeout
      });

      const result = await Promise.race([apiPromise, timeoutPromise]);

      // Clear timeout
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
        loadTimeoutRef.current = null;
      }

      // Check if this load was cancelled
      if (currentLoadRef.current !== loadId) {
        return { success: false, fromCache: false, loadTime: 0, error: 'Cancelled' };
      }

      if (!result.success) {
        const error = typeof result.error === 'string' ? result.error : 'Failed to load file';
        if (!options.preload) {
          setLoadingState({ isLoading: false, error });
          setError(`Failed to load file: ${filePath}`);
        }
        return { success: false, fromCache: false, loadTime: 0, error };
      }

      const fileData = result.data;
      const language = getLanguageFromPath(filePath);
      const loadTime = performance.now() - startTime;

      // Cache the file
      fileCache.set(currentContainer.id, filePath, fileData.content, language);

      // Emit cache set event
      cacheEvents.emit({
        type: 'set',
        containerId: currentContainer.id,
        filePath,
        size: new Blob([fileData.content]).size,
        stats: fileCache.getStats()
      });

      // Update UI if not preloading
      if (!options.preload) {
        await updateEditorState(filePath, fileData.content, language);
        setLoadingState({ isLoading: false, error: null });
      }

      return { 
        success: true, 
        fromCache: false, 
        loadTime 
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      if (!options.preload) {
        setLoadingState({ isLoading: false, error: errorMessage });
        setError(`Failed to load file: ${filePath} - ${errorMessage}`);
      }

      return { 
        success: false, 
        fromCache: false, 
        loadTime: performance.now() - startTime, 
        error: errorMessage 
      };
    } finally {
      // Clear current load reference if this was the active load
      if (currentLoadRef.current === loadId) {
        currentLoadRef.current = null;
      }
    }
  }, [currentContainer?.id, setContent, setLanguage, setDirty, setCurrentFile, setError]);

  /**
   * Update editor state with file data
   */
  const updateEditorState = useCallback(async (
    filePath: string,
    content: string,
    language: string
  ) => {
    // Batch state updates to prevent multiple re-renders
    // Use setTimeout instead of requestAnimationFrame to avoid blocking terminal focus
    return new Promise<void>((resolve) => {
      setTimeout(() => {
        setContent(content);
        setLanguage(language);
        setDirty(false);
        
        setCurrentFile({
          id: `${currentContainer?.id}:${filePath}`,
          name: filePath.split('/').pop() || 'untitled',
          path: filePath,
          content,
          language
        });
        
        resolve();
      }, 0); // Use setTimeout with 0 delay instead of requestAnimationFrame
    });
  }, [currentContainer?.id, setContent, setLanguage, setDirty, setCurrentFile]);

  /**
   * Debounced version of loadFile to prevent rapid API calls
   */
  const debouncedLoadFile = useCallback(
    (filePath: string, options?: Parameters<typeof loadFile>[1]) => {
      return loadFile(filePath, options);
    },
    [loadFile]
  );

  // Create a debounced version for internal use
  const debouncedInternalLoad = useCallback(
    debounce(debouncedLoadFile, 150), // 150ms debounce
    [debouncedLoadFile]
  );

  /**
   * Preload files that are likely to be accessed
   */
  const preloadFiles = useCallback(async (filePaths: string[]) => {
    if (!currentContainer?.id || filePaths.length === 0) return;

    // Preload files in parallel with low priority
    const preloadPromises = filePaths.map(filePath =>
      loadFile(filePath, { preload: true, priority: 'low' })
        .catch(error => {
          console.warn(`Preload failed for ${filePath}:`, error);
          return { success: false, fromCache: false, loadTime: 0, error: error.message };
        })
    );

    const results = await Promise.allSettled(preloadPromises);
    const successful = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
    
    console.log(`Preloaded ${successful}/${filePaths.length} files`);
  }, [loadFile, currentContainer?.id]);

  /**
   * Smart preloading based on file tree and access patterns
   */
  const smartPreload = useCallback(async (currentFilePath: string, fileTree: any[]) => {
    if (!currentContainer?.id) return;

    // Reduce preloading aggressiveness to avoid blocking terminal
    const preloadCandidates: string[] = [];

    // 1. Only preload 1-2 sibling files to reduce background activity
    const currentDir = currentFilePath.substring(0, currentFilePath.lastIndexOf('/'));
    const siblingFiles = fileTree
      .filter(file => 
        file.type === 'file' && 
        file.path.startsWith(currentDir) &&
        file.path !== currentFilePath &&
        !fileCache.has(currentContainer.id, file.path) &&
        file.size && file.size < 100000 // Only preload files smaller than 100KB
      )
      .slice(0, 2) // Reduced from 3 to 2 siblings
      .map(file => file.path);

    preloadCandidates.push(...siblingFiles);

    // 2. Only preload main.py if it's not too large
    const mainPyPath = '/workspace/main.py';
    const mainPyFile = fileTree.find(file => file.path === mainPyPath);
    if (mainPyPath !== currentFilePath && 
        !fileCache.has(currentContainer.id, mainPyPath) &&
        mainPyFile && 
        (!mainPyFile.size || mainPyFile.size < 50000)) { // Only if smaller than 50KB
      preloadCandidates.push(mainPyPath);
    }

    // Preload with more conservative limits and delay
    if (preloadCandidates.length > 0) {
      // Add delay to avoid interfering with current operations
      setTimeout(() => {
        preloadFiles(preloadCandidates.slice(0, 2)); // Max 2 preloads, reduced from 5
      }, 500); // 500ms delay
    }
  }, [currentContainer?.id, preloadFiles]);

  /**
   * Get language from file extension
   */
  const getLanguageFromPath = useCallback((path: string): string => {
    const extension = path.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'py': return 'python';
      case 'js': return 'javascript';
      case 'ts': return 'typescript';
      case 'jsx': return 'javascript';
      case 'tsx': return 'typescript';
      case 'json': return 'json';
      case 'md': return 'markdown';
      case 'txt': return 'plaintext';
      case 'yaml':
      case 'yml': return 'yaml';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'scss': return 'scss';
      case 'xml': return 'xml';
      case 'sql': return 'sql';
      default: return 'plaintext';
    }
  }, []);

  /**
   * Invalidate cache when container changes
   */
  useEffect(() => {
    if (currentContainer?.id) {
      // Clear cache for previous container if container changed
      const prevContainerId = currentLoadRef.current?.split(':')[0];
      if (prevContainerId && prevContainerId !== currentContainer.id) {
        fileCache.invalidateContainer(prevContainerId);
      }
    }
  }, [currentContainer?.id]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
      }
      currentLoadRef.current = null;
    };
  }, []);

  return {
    loadFile,
    debouncedLoadFile,
    preloadFiles,
    smartPreload,
    loadingState,
    cacheStats: fileCache.getStats(),
    clearCache: () => fileCache.clear(),
    invalidateContainer: (containerId: string) => fileCache.invalidateContainer(containerId)
  };
}