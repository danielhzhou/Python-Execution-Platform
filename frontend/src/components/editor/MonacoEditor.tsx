import { useEffect, useRef, useCallback, useState } from 'react';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useEditorStore } from '../../stores/editorStore';
import { useAppStore } from '../../stores/appStore';
import { useTerminalStore } from '../../stores/terminalStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAutoSave } from '../../hooks/useAutoSave';
import { validatePythonSyntax } from '../../lib/utils';
import { monacoModelManager } from '../../lib/monacoModelManager';


interface MonacoEditorProps {
  className?: string;
  executeCodeRef?: React.MutableRefObject<(() => Promise<void>) | null>;
}

export function MonacoEditor({ className, executeCodeRef }: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [isEditorReady, setIsEditorReady] = useState(false);
  const [, setIsMonacoLoaded] = useState(false);
  const [, setIsExecuting] = useState(false);
  
  const {
    content,
    language,

    theme,
    fontSize,
    wordWrap,
    minimap,
    setContent
  } = useEditorStore();

  const { currentContainer, currentFile, setError } = useAppStore();
  const { isConnected } = useTerminalStore();
  const { sendCommand } = useWebSocket();
  const { manualSave } = useAutoSave();

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

  // Expose executeCode function through ref
  useEffect(() => {
    if (executeCodeRef) {
      executeCodeRef.current = executeCode;
    }
  }, [executeCode, executeCodeRef]);



  const handleEditorDidMount = useCallback((editor: editor.IStandaloneCodeEditor, _monaco: any) => {
    try {
      editorRef.current = editor;
      setIsMonacoLoaded(true);

      // Register editor with model manager for optimized model switching
      monacoModelManager.setEditor(editor);

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

                // Focus the editor only if no other element is actively focused (avoid stealing terminal focus)
          try {
            const activeElement = document.activeElement;
            const isTerminalFocused = activeElement && (
              activeElement.classList.contains('xterm-helper-textarea') ||
              activeElement.closest('.xterm-screen')
            );
            
            if (!isTerminalFocused) {
              editor.focus();
            } else {
              console.log('Terminal is focused, not stealing focus from editor');
            }
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

  // Cleanup effect to save editor state and manage model lifecycle
  useEffect(() => {
    return () => {
      // Save current editor state before cleanup
      monacoModelManager.saveEditorState();
    };
  }, []);

  // Save editor state when current file changes
  useEffect(() => {
    if (currentFile) {
      monacoModelManager.saveEditorState();
    }
  }, [currentFile?.path]);

  return (
    <div className={`flex flex-col h-full bg-[#1e1e1e] ${className}`}>
      {/* Monaco Editor - Full Height */}
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
    </div>
  );
} 