import { useAutoSave } from '../../hooks/useAutoSave';
import { useEditorStore } from '../../stores/editorStore';

export function FileTabIndicator() {
  const { hasUnsavedChanges } = useAutoSave();
  const { isDirty } = useEditorStore();

  if (hasUnsavedChanges || isDirty) {
    return (
      <div 
        className="w-2 h-2 rounded-full bg-white animate-pulse" 
        title="File has unsaved changes"
      />
    );
  }

  return (
    <div 
      className="w-1 h-1 rounded-full bg-white/60" 
      title="File is saved"
    />
  );
}