import React, { useEffect, useRef, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useEditorStore } from '../../stores/editorStore';
import { useAppStore } from '../../stores/appStore';
import { useAutoSave } from '../../hooks/useAutoSave';
import { validatePythonSyntax } from '../../lib/utils';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Save, Settings, FileText } from 'lucide-react';

interface MonacoEditorProps {
  className?: string;
}

export function MonacoEditor({ className }: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
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

  const { currentFile, setError } = useAppStore();
  const { manualSave, hasUnsavedChanges } = useAutoSave();

  const handleEditorDidMount = useCallback((editor: editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;

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

    // Add keyboard shortcuts
    editor.addCommand(editor.KeyMod.CtrlCmd | editor.KeyCode.KeyS, () => {
      manualSave();
    });

    // Add Python-specific configurations
    if (language === 'python') {
      editor.addCommand(editor.KeyMod.CtrlCmd | editor.KeyCode.Enter, () => {
        // Could trigger code execution here
        console.log('Execute code shortcut pressed');
      });
    }

    // Focus the editor
    editor.focus();
  }, [fontSize, wordWrap, minimap, language, manualSave]);

  const handleEditorChange = useCallback((value: string | undefined) => {
    if (value !== undefined && value !== content) {
      setContent(value);
      
      // Basic syntax validation for Python
      if (language === 'python') {
        const validation = validatePythonSyntax(value);
        if (!validation.isValid && validation.error) {
          // You could show syntax errors in the UI here
          console.warn('Python syntax issues:', validation.error);
        }
      }
    }
  }, [content, language, setContent]);

  const handleSaveClick = useCallback(async () => {
    await manualSave();
  }, [manualSave]);

  // Update editor theme when store changes
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.updateOptions({
        fontSize,
        wordWrap,
        minimap: { enabled: minimap }
      });
    }
  }, [fontSize, wordWrap, minimap]);

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
            disabled={!hasUnsavedChanges}
            className="h-8 px-2"
          >
            <Save className="h-4 w-4" />
            <span className="ml-1 text-xs">Save</span>
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
        />
      </div>

      {/* Editor Footer */}
      <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Python</span>
          <span>UTF-8</span>
          <span>LF</span>
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