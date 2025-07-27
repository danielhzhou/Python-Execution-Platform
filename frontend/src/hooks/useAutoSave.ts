import { useEffect, useCallback, useRef } from 'react';
import { useEditorStore } from '../stores/editorStore';
import { useAppStore } from '../stores/appStore';
import { fileApi } from '../lib/api';
import { debounce } from '../lib/utils';

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
    setError 
  } = useAppStore();

  const lastSavedContent = useRef<string>('');

  const saveFile = useCallback(async (content: string) => {
    if (!currentContainer || !currentFile) {
      return;
    }

    try {
      const response = await fileApi.save(
        currentContainer.id,
        currentFile.path,
        content
      );

      if (response.success && response.data) {
        updateFile(currentFile.id, {
          content,
          lastModified: new Date(),
          size: content.length
        });
        markSaved();
        lastSavedContent.current = content;
        setError(null);
      } else {
        setError(response.error || 'Failed to save file');
      }
    } catch (error) {
      setError('Failed to save file');
      console.error('Auto-save error:', error);
    }
  }, [currentContainer, currentFile, updateFile, markSaved, setError]);

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
    if (currentContainer && currentFile && isDirty) {
      await saveFile(content);
    }
  }, [saveFile, content, currentContainer, currentFile, isDirty]);

  const hasUnsavedChanges = isDirty && content !== lastSavedContent.current;

  return {
    manualSave,
    hasUnsavedChanges,
    isAutoSaveEnabled: autoSaveEnabled
  };
} 