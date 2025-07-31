import { useState } from 'react';
import { Save, Check, Loader2 } from 'lucide-react';
import { useAutoSave } from '../../hooks/useAutoSave';
import { useEditorStore } from '../../stores/editorStore';
import { useAppStore } from '../../stores/appStore';

export function SaveButton() {
  const [isSaving, setIsSaving] = useState(false);
  const { manualSave, hasUnsavedChanges } = useAutoSave();
  const { isDirty } = useEditorStore();
  const { currentFile } = useAppStore();

  const handleSave = async () => {
    if (!currentFile || isSaving) return;
    
    setIsSaving(true);
    try {
      await manualSave();
    } catch (error) {
      console.error('Save failed:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const getSaveButtonState = () => {
    if (isSaving) {
      return {
        className: 'text-blue-400 cursor-not-allowed',
        disabled: true,
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
        tooltip: 'Saving...'
      };
    }
    
    if (!currentFile) {
      return {
        className: 'text-white/40 cursor-not-allowed',
        disabled: true,
        icon: <Save className="w-4 h-4" />,
        tooltip: 'No file to save'
      };
    }
    
    if (hasUnsavedChanges || isDirty) {
      return {
        className: 'text-white/70 hover:text-white hover:bg-white/10 cursor-pointer',
        disabled: false,
        icon: <Save className="w-4 h-4" />,
        tooltip: `Save ${currentFile.name} (Ctrl+S)`
      };
    }
    
    return {
      className: 'text-green-400 cursor-default',
      disabled: true,
      icon: <Check className="w-4 h-4" />,
      tooltip: `${currentFile.name} is saved`
    };
  };

  const saveState = getSaveButtonState();

  return (
    <button
      onClick={handleSave}
      disabled={saveState.disabled}
      className={`p-1.5 rounded transition-all ${saveState.className}`}
      title={saveState.tooltip}
    >
      {saveState.icon}
    </button>
  );
}