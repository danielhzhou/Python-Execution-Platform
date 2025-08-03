import { useEffect, useCallback, useRef } from 'react';
import { useEditorStore } from '../stores/editorStore';
import { useAppStore } from '../stores/appStore';
import { fileApi } from '../lib/api';
import { debounce } from '../lib/utils';
import { monacoModelManager } from '../lib/monacoModelManager';
import { fileCache } from '../lib/fileCache';

export function useAutoSave() {
  const {
    content,
    isDirty,
    autoSaveEnabled,
    autoSaveDelay,
    markSaved,
    setDirty
  } = useEditorStore();
  
  const { 
    currentContainer,
    currentFile,
    updateFile,
    setCurrentFile,
    setError 
  } = useAppStore();

  const lastSavedContent = useRef<string>('');

  const saveFile = useCallback(async (content: string) => {
    if (!currentContainer || !currentFile) {
      console.warn('⚠️ Auto-save skipped: missing container or file', {
        hasContainer: !!currentContainer,
        hasFile: !!currentFile
      });
      return;
    }

    console.log('💾 Auto-saving file:', {
      path: currentFile.path,
      containerId: currentContainer.id,
      contentLength: content.length,
      contentPreview: content.substring(0, 100) + '...'
    });

    try {
      console.log('📤 Sending save request to API...');
      const response = await fileApi.save(
        currentContainer.id,
        currentFile.path,
        content
      );
      console.log('📥 Save response received:', response);

      if (response.success && response.data) {
        // Update the file in the store if updateFile is available
        if (updateFile && currentFile.id) {
          updateFile(currentFile.id, {
            content,
            lastModified: new Date(),
            size: content.length
          });
        }
        
        // Always update the current file with the latest content
        setCurrentFile({
          ...currentFile,
          content,
          lastModified: new Date(),
          size: content.length
        });
        
        markSaved();
        lastSavedContent.current = content;
        setError(null);
        
        // Update cache with saved content
        if (currentContainer?.id && currentFile?.path) {
          fileCache.set(
            currentContainer.id, 
            currentFile.path, 
            content, 
            currentFile.language || 'plaintext'
          );
          
          // Mark model as saved in model manager
          monacoModelManager.markModelSaved(currentContainer.id, currentFile.path);
        }
        
        console.log('✅ File saved successfully:', currentFile.path);
      } else {
        const errorMsg = response.error || 'Failed to save file';
        console.error('❌ File save failed:', {
          error: errorMsg,
          file: currentFile?.path,
          container: currentContainer?.id,
          responseStatus: response.status || 'unknown'
        });
        
        // Provide more user-friendly error messages
        let userFriendlyError = errorMsg;
        if (typeof errorMsg === 'string') {
          if (errorMsg.includes('verification failed')) {
            userFriendlyError = 'File saved but verification failed. The file should still work correctly.';
          } else if (errorMsg.includes('Container not found')) {
            userFriendlyError = 'Container not available. Please refresh and try again.';
          } else if (errorMsg.includes('Access denied')) {
            userFriendlyError = 'Access denied. Please check your permissions.';
          }
        }
        
        setError(userFriendlyError);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('❌ Auto-save error:', {
        error: errorMessage,
        file: currentFile?.path,
        container: currentContainer?.id,
        fullError: error
      });
      setError(`Failed to save file: ${errorMessage}`);
    }
  }, [currentContainer, currentFile, updateFile, setCurrentFile, markSaved, setError]);

  const debouncedSave = useRef(
    debounce((content: string) => {
      saveFile(content);
    }, autoSaveDelay)
  );

  // Update debounced function when delay changes
  useEffect(() => {
    debouncedSave.current = debounce((content: string) => {
      saveFile(content);
    }, autoSaveDelay);
  }, [autoSaveDelay, saveFile]);

  // Auto-save when content changes
  useEffect(() => {
    if (
      autoSaveEnabled &&
      isDirty &&
      content !== lastSavedContent.current &&
      currentContainer &&
      currentFile
    ) {
      debouncedSave.current(content);
    }
  }, [content, isDirty, autoSaveEnabled, currentContainer, currentFile]);

  const manualSave = useCallback(async () => {
    if (!currentContainer || !currentFile) {
      console.warn('⚠️ Manual save skipped: missing container or file');
      return;
    }

    // Always save if there's content, regardless of isDirty flag
    // This ensures execution always uses the latest content
    console.log('🔄 Manual save triggered:', {
      path: currentFile.path,
      isDirty,
      contentLength: content.length,
      hasChanges: content !== lastSavedContent.current
    });

    await saveFile(content);
  }, [saveFile, content, currentContainer, currentFile, isDirty]);

  const hasUnsavedChanges = isDirty && content !== lastSavedContent.current;

  return {
    manualSave,
    hasUnsavedChanges,
    isAutoSaveEnabled: autoSaveEnabled
  };
} 