import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter,
  DialogDescription 
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { File, Folder, FileText, Code, Settings, Database } from 'lucide-react';

interface CreateFileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateFile: (fileName: string, template?: string) => Promise<void>;
  onCreateFolder?: (folderName: string) => Promise<void>;
  currentDirectory?: string;
  loading?: boolean;
}

interface FileTemplate {
  name: string;
  extension: string;
  icon: React.ReactNode;
  description: string;
  template: string;
}

const FILE_TEMPLATES: FileTemplate[] = [
  {
    name: 'New Folder',
    extension: '',
    icon: <Folder className="h-4 w-4 text-[#dcb67a]" />,
    description: 'Create a new directory',
    template: '__FOLDER__'
  },
  {
    name: 'Python File',
    extension: '.py',
    icon: <Code className="h-4 w-4 text-[#3776ab]" />,
    description: 'Python script with basic structure',
    template: `#!/usr/bin/env python3
"""
Module description here
"""

def main():
    """Main function"""
    print("Hello, World!")

if __name__ == "__main__":
    main()
`
  },
  {
    name: 'Text File',
    extension: '.txt',
    icon: <FileText className="h-4 w-4 text-white/60" />,
    description: 'Plain text file',
    template: ''
  },
  {
    name: 'JSON File',
    extension: '.json',
    icon: <Database className="h-4 w-4 text-[#cbcb41]" />,
    description: 'JSON configuration file',
    template: `{
  "name": "example",
  "version": "1.0.0",
  "description": ""
}
`
  },
  {
    name: 'Markdown File',
    extension: '.md',
    icon: <FileText className="h-4 w-4 text-white/70" />,
    description: 'Markdown documentation',
    template: `# Title

## Description

Your content here...
`
  },
  {
    name: 'Requirements File',
    extension: '.txt',
    icon: <Settings className="h-4 w-4 text-white/70" />,
    description: 'Python requirements file',
    template: `# Python package requirements
# Example:
# requests>=2.25.1
# numpy>=1.20.0
`
  },
  {
    name: 'Custom File',
    extension: '',
    icon: <File className="h-4 w-4 text-white/70" />,
    description: 'Create a file with custom name and extension',
    template: ''
  }
];

export function CreateFileModal({ 
  isOpen, 
  onClose, 
  onCreateFile, 
  onCreateFolder,
  currentDirectory = '/workspace',
  loading = false 
}: CreateFileModalProps) {
  const [fileName, setFileName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<FileTemplate | null>(null);
  const [error, setError] = useState('');
  const [step, setStep] = useState<'template' | 'name'>('template');

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setFileName('');
      setSelectedTemplate(null);
      setError('');
      setStep('template');
    }
  }, [isOpen]);

  // Auto-generate filename when template is selected
  useEffect(() => {
    if (selectedTemplate) {
      if (selectedTemplate.name === 'New Folder') {
        setFileName('new_folder');
      } else if (selectedTemplate.name === 'Requirements File') {
        setFileName('requirements.txt');
      } else if (selectedTemplate.extension) {
        const baseName = selectedTemplate.name.toLowerCase().replace(/\s+/g, '_');
        setFileName(`${baseName}${selectedTemplate.extension}`);
      }
    }
  }, [selectedTemplate]);

  const validateFileName = (name: string): string | null => {
    if (!name.trim()) {
      return 'File name is required';
    }

    // Check for invalid characters
    const invalidChars = /[<>:"/\\|?*\x00-\x1f]/;
    if (invalidChars.test(name)) {
      return 'File name contains invalid characters';
    }

    // Check for reserved names (Windows)
    const reservedNames = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'];
    const nameWithoutExt = name.split('.')[0].toUpperCase();
    if (reservedNames.includes(nameWithoutExt)) {
      return 'File name is reserved and cannot be used';
    }

    // Check length
    if (name.length > 255) {
      return 'File name is too long (max 255 characters)';
    }

    return null;
  };

  const handleTemplateSelect = (template: FileTemplate) => {
    setSelectedTemplate(template);
    setError('');
    
    if (template.name === 'Custom File') {
      setStep('name');
    } else {
      setStep('name');
    }
  };

  const handleCreateFile = async () => {
    const trimmedName = fileName.trim();
    const validationError = validateFileName(trimmedName);
    
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      if (selectedTemplate?.name === 'New Folder') {
        if (onCreateFolder) {
          await onCreateFolder(trimmedName);
        } else {
          throw new Error('Folder creation not supported');
        }
      } else {
        const template = selectedTemplate?.template || '';
        await onCreateFile(trimmedName, template);
      }
      onClose();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to create file');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading && fileName.trim() && !error) {
      handleCreateFile();
    }
  };

  const renderTemplateStep = () => (
    <div className="space-y-4">
      <DialogDescription>
        Choose a file type to get started with a template, or select "Custom File" for a blank file.
      </DialogDescription>
      
      <div className="grid grid-cols-1 gap-2 max-h-96 overflow-y-auto">
        {FILE_TEMPLATES.map((template) => (
          <button
            key={template.name}
            onClick={() => handleTemplateSelect(template)}
            className="flex items-center gap-3 p-3 text-left rounded-lg border border-border hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            {template.icon}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm">{template.name}</div>
              <div className="text-xs text-muted-foreground truncate">
                {template.description}
              </div>
            </div>
            {template.extension && (
              <div className="text-xs text-muted-foreground font-mono">
                {template.extension}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );

  const renderNameStep = () => (
    <div className="space-y-4">
      <DialogDescription>
        {selectedTemplate ? (
          <>Creating a <strong>{selectedTemplate.name}</strong> in <code className="text-xs bg-muted px-1 py-0.5 rounded">{currentDirectory}</code></>
        ) : (
          <>Creating a file in <code className="text-xs bg-muted px-1 py-0.5 rounded">{currentDirectory}</code></>
        )}
      </DialogDescription>

      <div className="space-y-2">
        <label htmlFor="fileName" className="text-sm font-medium">
          {selectedTemplate?.name === 'New Folder' ? 'Folder Name' : 'File Name'}
        </label>
        <Input
          id="fileName"
          value={fileName}
          onChange={(e) => {
            setFileName(e.target.value);
            setError('');
          }}
          onKeyPress={handleKeyPress}
          placeholder={
            selectedTemplate?.name === 'New Folder' 
              ? 'my_folder' 
              : selectedTemplate?.name === 'Custom File' 
                ? 'example.py' 
                : 'Enter file name...'
          }
          className={error ? 'border-red-500' : ''}
          autoFocus
        />
        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}
      </div>

      {selectedTemplate && selectedTemplate.template && selectedTemplate.name !== 'New Folder' && (
        <div className="space-y-2">
          <label className="text-sm font-medium">Template Preview</label>
          <div className="bg-muted p-3 rounded-md text-xs font-mono max-h-32 overflow-y-auto">
            <pre className="whitespace-pre-wrap">{selectedTemplate.template.slice(0, 200)}{selectedTemplate.template.length > 200 ? '...' : ''}</pre>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <File className="h-5 w-5" />
            {step === 'template' ? 'Create New File' : 'File Details'}
          </DialogTitle>
        </DialogHeader>

        {step === 'template' ? renderTemplateStep() : renderNameStep()}

        <DialogFooter className="flex justify-between sm:justify-between">
          {step === 'name' && (
            <Button
              variant="outline"
              onClick={() => setStep('template')}
              disabled={loading}
            >
              Back
            </Button>
          )}
          
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            
            {step === 'name' && (
              <Button
                onClick={handleCreateFile}
                disabled={loading || !fileName.trim() || !!error}
              >
                {loading ? 'Creating...' : selectedTemplate?.name === 'New Folder' ? 'Create Folder' : 'Create File'}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}