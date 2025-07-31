import { useEffect, useRef, useCallback, useState } from 'react';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useEditorStore } from '../../stores/editorStore';
import { useAppStore } from '../../stores/appStore';
import { useTerminalStore } from '../../stores/terminalStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAutoSave } from '../../hooks/useAutoSave';
import { validatePythonSyntax } from '../../lib/utils';
import { Button } from '../ui/button';
import { Save, FileText, Play, Square } from 'lucide-react';

interface MonacoEditorProps {
  className?: string;
}

export function MonacoEditor({ className }: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [isEditorReady, setIsEditorReady] = useState(false);
  const [, setIsMonacoLoaded] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  
  const {
    content,
    language,
    isDirty,
    theme,
    fontSize,
    wordWrap,
    minimap,
    setContent
  } = useEditorStore();

  const { currentContainer, currentFile, setError } = useAppStore();
  const { isConnected } = useTerminalStore();
  const { sendCommand } = useWebSocket();
  const { manualSave, hasUnsavedChanges } = useAutoSave();

  // Execute the current code in the terminal
  const executeCode = useCallback(async () => {
    if (!currentContainer) {
      setError('No active container. Please wait for container to be ready.');
      return;
    }

    if (!isConnected) {
      setError('Terminal not connected. Please wait for connection.');
      return;
    }

    if (!content.trim()) {
      setError('No code to execute.');
      return;
    }

    setIsExecuting(true);
    setError(null);

    try {
      // Use current file if available, otherwise create a temporary file
      let filename = currentFile?.path || `/workspace/script_${Date.now()}.py`;
      
      // Clear terminal first
      sendCommand('\x0c'); // Clear screen
      
      // If using current file, save it first and verify
      if (currentFile) {
        sendCommand(`echo "💾 Saving ${currentFile.path}..."\n`);
        console.log('🔄 Saving file before execution:', {
          path: currentFile.path,
          contentLength: content.length,
          contentPreview: content.substring(0, 100) + '...'
        });
        
        try {
          await manualSave();
          console.log('✅ File saved successfully before execution');
          
          // Add a small delay to ensure the save operation completes
          await new Promise(resolve => setTimeout(resolve, 500));
          
          // Verify the file was saved by checking its content in the container
          sendCommand(`echo "🔍 Verifying file content..."\n`);
          sendCommand(`echo "📁 Current directory: $(pwd)"\n`);
          sendCommand(`echo "📋 Files in workspace: $(ls -la /workspace/)"\n`);
          sendCommand(`echo "📊 File size: $(wc -c < '${currentFile.path}') bytes"\n`);
          sendCommand(`echo "🔍 First 5 lines of ${currentFile.path}:"\n`);
          sendCommand(`head -5 '${currentFile.path}'\n`);
          sendCommand(`echo "🔍 Looking for [3, 3, 3, 3, 3] in file:"\n`);
          sendCommand(`grep -n "3, 3, 3" '${currentFile.path}' || echo "Pattern not found"\n`);
          
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
        sendCommand(`echo "📝 Creating temporary file: ${filename.split('/').pop()}..."\n`);
        sendCommand(`cat > ${filename} << 'EOF'\n${content}\nEOF\n`);
      }
      
      // Show execution start
      sendCommand(`echo "🚀 Executing ${filename.split('/').pop()}..."\n`);
      
      // Clear Python bytecode cache to ensure fresh execution
      sendCommand(`find /workspace -name "*.pyc" -delete 2>/dev/null || true\n`);
      sendCommand(`find /workspace -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true\n`);
      
      // Execute the Python file
      sendCommand(`python3 ${filename}\n`);
      
      // Show completion message
      sendCommand(`echo "\n✅ Execution completed."\n`);
      
    } catch (error) {
      console.error('Code execution error:', error);
      setError('Failed to execute code. Please try again.');
    } finally {
      setIsExecuting(false);
    }
  }, [content, currentContainer, currentFile, isConnected, sendCommand, setError, manualSave]);

  // Stop code execution (send interrupt signal)
  const stopExecution = useCallback(() => {
    if (isConnected) {
      sendCommand('\x03'); // Send Ctrl+C to interrupt
      setIsExecuting(false);
    }
  }, [isConnected, sendCommand]);

  const handleEditorDidMount = useCallback((editor: editor.IStandaloneCodeEditor, _monaco: any) => {
    try {
      editorRef.current = editor;
      setIsMonacoLoaded(true);

      // Configure editor options
      editor.updateOptions({
        fontSize,
        wordWrap,
        minimap: { enabled: minimap },
        automaticLayout: true,
        scrollBeyondLastLine: false,
        renderWhitespace: 'selection',
        bracketPairColorization: { enabled: true },
        guides: {
          bracketPairs: true,
          indentation: true
        },
        suggest: {
          showKeywords: true,
          showSnippets: true
        }
      });

      // Add keyboard shortcuts with proper error handling
      try {
        // Ensure KeyMod and KeyCode are available
        if (_monaco?.KeyMod && _monaco?.KeyCode) {
          // Save shortcut
          editor.addCommand(_monaco.KeyMod.CtrlCmd | _monaco.KeyCode.KeyS, () => {
            try {
              manualSave();
            } catch (error) {
              console.error('Manual save error:', error);
            }
          });

          // Execute code shortcut (Ctrl+Enter)
          if (language === 'python') {
            editor.addCommand(_monaco.KeyMod.CtrlCmd | _monaco.KeyCode.Enter, () => {
              executeCode();
            });
          }
        } else {
          console.warn('Monaco KeyMod or KeyCode not available, shortcuts disabled');
        }
      } catch (error) {
        console.error('Error setting up Monaco keyboard shortcuts:', error);
      }

      // Focus the editor
      try {
        editor.focus();
      } catch (error) {
        console.warn('Error focusing editor:', error);
      }

      setIsEditorReady(true);
    } catch (error) {
      console.error('Monaco editor mount error:', error);
      setError('Failed to initialize code editor');
    }
  }, [fontSize, wordWrap, minimap, language, manualSave, setError, executeCode]);

  const handleEditorChange = useCallback((value: string | undefined) => {
    if (!isEditorReady) return;
    
    try {
      if (value !== undefined && value !== content) {
        console.log('🔄 Editor content changed:', {
          oldLength: content.length,
          newLength: value.length,
          preview: value.substring(0, 50) + '...'
        });
        setContent(value);
        
        // Basic syntax validation for Python
        if (language === 'python') {
          const validation = validatePythonSyntax(value);
          if (!validation.isValid && validation.error) {
            console.warn('Python syntax issues:', validation.error);
          }
        }
      }
    } catch (error) {
      console.error('Editor change error:', error);
    }
  }, [content, language, setContent, isEditorReady]);

  const handleSaveClick = useCallback(async () => {
    try {
      await manualSave();
    } catch (error) {
      console.error('Save click error:', error);
      setError('Failed to save file');
    }
  }, [manualSave, setError]);

  // Update editor options when store changes
  useEffect(() => {
    if (editorRef.current && isEditorReady) {
      try {
        editorRef.current.updateOptions({
          fontSize,
          wordWrap,
          minimap: { enabled: minimap }
        });
      } catch (error) {
        console.warn('Error updating editor options:', error);
      }
    }
  }, [fontSize, wordWrap, minimap, isEditorReady]);

  const getStatusText = () => {
    if (!currentFile) return 'No file selected';
    if (hasUnsavedChanges) return 'Unsaved changes';
    if (isDirty) return 'Modified';
    return 'Saved';
  };

  const getStatusColor = () => {
    if (!currentFile) return 'bg-gray-100 text-gray-600';
    if (hasUnsavedChanges) return 'bg-amber-100 text-amber-800';
    if (isDirty) return 'bg-blue-100 text-blue-800';
    return 'bg-emerald-100 text-emerald-800';
  };

  return (
    <div className={`flex flex-col h-full bg-background ${className}`}>
      {/* Editor Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 bg-muted/10">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-semibold">
              {currentFile?.name || 'main.py'}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </span>
            {hasUnsavedChanges && (
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500" title="Unsaved changes" />
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSaveClick}
            disabled={!hasUnsavedChanges || !isEditorReady}
            className="h-8 px-3 text-xs"
          >
            <Save className="h-3.5 w-3.5 mr-1.5" />
            Save
          </Button>
          
          {/* Execute/Run Button */}
          <Button
            variant={isExecuting ? "destructive" : "default"}
            size="sm"
            onClick={isExecuting ? stopExecution : executeCode}
            disabled={!isEditorReady || !currentContainer || !isConnected}
            className="h-8 px-3 text-xs font-medium"
          >
            {isExecuting ? (
              <>
                <Square className="h-3.5 w-3.5 mr-1.5" />
                Stop
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 mr-1.5" />
                Run
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1 min-h-0 bg-background">
        <Editor
          height="100%"
          language={language}
          theme={theme}
          value={content}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          options={{
            selectOnLineNumbers: true,
            roundedSelection: false,
            readOnly: false,
            cursorStyle: 'line',
            automaticLayout: true,
            scrollBeyondLastLine: false,
            renderWhitespace: 'selection',
            bracketPairColorization: { enabled: true },
            guides: {
              bracketPairs: true,
              indentation: true
            },
            suggest: {
              showKeywords: true,
              showSnippets: true
            },
            quickSuggestions: {
              other: true,
              comments: true,
              strings: true
            },
            parameterHints: {
              enabled: true
            },
            hover: {
              enabled: true
            },
            contextmenu: true,
            mouseWheelZoom: true,
            smoothScrolling: true,
            cursorBlinking: 'blink',
            cursorSmoothCaretAnimation: 'on',
            renderLineHighlight: 'all',
            lineNumbers: 'on',
            glyphMargin: true,
            folding: true,
            foldingStrategy: 'indentation',
            showFoldingControls: 'mouseover',
            unfoldOnClickAfterEndOfLine: true,
            tabSize: 4,
            insertSpaces: true,
            detectIndentation: true,
            trimAutoWhitespace: true,
            largeFileOptimizations: true
          }}
          loading={
            <div className="flex items-center justify-center h-full">
              <div className="text-sm text-muted-foreground">Loading editor...</div>
            </div>
          }
          beforeMount={(_monaco) => {
            // Configure Monaco before it mounts
            try {
              // Set up any global Monaco configurations here
              console.log('Monaco editor preparing to mount');
            } catch (error) {
              console.error('Monaco beforeMount error:', error);
            }
          }}
        />
      </div>

      {/* Editor Footer */}
      <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Python</span>
          <span>UTF-8</span>
          <span>LF</span>
          {!isEditorReady && <span className="text-yellow-500">Loading...</span>}
        </div>
        
        <div className="flex items-center gap-4">
          <span>Lines: {content.split('\n').length}</span>
          <span>Characters: {content.length}</span>
          {currentFile && (
            <span>Size: {Math.round(content.length / 1024 * 100) / 100} KB</span>
          )}
        </div>
      </div>
    </div>
  );
} 