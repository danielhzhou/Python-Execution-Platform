import React, { useEffect, useRef, useCallback, useState } from 'react';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useEditorStore } from '../../stores/editorStore';
import { useAppStore } from '../../stores/appStore';
import { useTerminalStore } from '../../stores/terminalStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAutoSave } from '../../hooks/useAutoSave';
import { validatePythonSyntax } from '../../lib/utils';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Save, Settings, FileText, Play, Square } from 'lucide-react';

interface MonacoEditorProps {
  className?: string;
}

export function MonacoEditor({ className }: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [isEditorReady, setIsEditorReady] = useState(false);
  const [isMonacoLoaded, setIsMonacoLoaded] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  
  const {
    content,
    language,
    isDirty,
    theme,
    fontSize,
    wordWrap,
    minimap,
    setContent,
    setDirty,
    markSaved
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
      // Save the code to a temporary file and execute it
      const timestamp = Date.now();
      const filename = `script_${timestamp}.py`;
      
      // Clear terminal and show execution start
      sendCommand('\x0c'); // Clear screen
      sendCommand(`echo "🚀 Executing Python code..."\n`);
      
      // Create the Python file with the current code
      const escapedContent = content.replace(/'/g, "'\"'\"'");
      sendCommand(`cat > /workspace/${filename} << 'EOF'\n${content}\nEOF\n`);
      
      // Execute the Python file
      sendCommand(`python3 /workspace/${filename}\n`);
      
      // Show completion message
      sendCommand(`echo "\n✅ Execution completed."\n`);
      
    } catch (error) {
      console.error('Code execution error:', error);
      setError('Failed to execute code. Please try again.');
    } finally {
      setIsExecuting(false);
    }
  }, [content, currentContainer, isConnected, sendCommand, setError]);

  // Stop code execution (send interrupt signal)
  const stopExecution = useCallback(() => {
    if (isConnected) {
      sendCommand('\x03'); // Send Ctrl+C to interrupt
      setIsExecuting(false);
    }
  }, [isConnected, sendCommand]);

  const handleEditorDidMount = useCallback((editor: editor.IStandaloneCodeEditor, monaco: any) => {
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
        if (monaco?.KeyMod && monaco?.KeyCode) {
          // Save shortcut
          editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            try {
              manualSave();
            } catch (error) {
              console.error('Manual save error:', error);
            }
          });

          // Execute code shortcut (Ctrl+Enter)
          if (language === 'python') {
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
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
    if (!currentFile) return 'text-muted-foreground';
    if (hasUnsavedChanges) return 'text-yellow-500';
    if (isDirty) return 'text-blue-500';
    return 'text-green-500';
  };

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      {/* Editor Header */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          <span className="text-sm font-medium">
            {currentFile?.name || 'script.py'}
          </span>
          <span className={`text-xs ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSaveClick}
            disabled={!hasUnsavedChanges || !isEditorReady}
            className="h-8 px-2"
          >
            <Save className="h-4 w-4" />
            <span className="ml-1 text-xs">Save</span>
          </Button>
          
          {/* Execute/Run Button */}
          <Button
            variant={isExecuting ? "destructive" : "default"}
            size="sm"
            onClick={isExecuting ? stopExecution : executeCode}
            disabled={!isEditorReady || !currentContainer || !isConnected}
            className="h-8 px-2"
          >
            {isExecuting ? (
              <>
                <Square className="h-4 w-4" />
                <span className="ml-1 text-xs">Stop</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span className="ml-1 text-xs">Run</span>
              </>
            )}
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1 min-h-0">
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
          beforeMount={(monaco) => {
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
    </Card>
  );
} 