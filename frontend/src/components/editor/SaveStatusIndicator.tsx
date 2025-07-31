import { useAutoSave } from '../../hooks/useAutoSave';
import { useEditorStore } from '../../stores/editorStore';
import { useAppStore } from '../../stores/appStore';

export function SaveStatusIndicator() {
  const { hasUnsavedChanges, isAutoSaveEnabled } = useAutoSave();
  const { isDirty, lastSaved } = useEditorStore();
  const { currentFile } = useAppStore();

  if (!currentFile) {
    return null;
  }

  const formatLastSaved = (date: Date | null) => {
    if (!date) return 'Never';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return `${minutes}m ago`;
    }
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (hasUnsavedChanges || isDirty) {
    return (
      <div className="flex items-center gap-1 text-amber-400" title="You have unsaved changes. Press Ctrl+S to save.">
        <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></div>
        <span className="text-xs">Unsaved</span>
      </div>
    );
  }

  if (lastSaved) {
    return (
      <div className="flex items-center gap-1 text-green-400" title={`File saved at ${lastSaved.toLocaleString()}`}>
        <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
        <span className="text-xs">{formatLastSaved(lastSaved)}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 text-white/50" title="Ready to save">
      <div className="w-1.5 h-1.5 rounded-full bg-white/50"></div>
      <span className="text-xs">Ready</span>
    </div>
  );
}