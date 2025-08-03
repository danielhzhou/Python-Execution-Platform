import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface EditorState {
  // Content state
  content: string;
  language: string;
  isDirty: boolean;
  lastSaved: Date | null;
  
  // Editor settings
  theme: 'vs-dark' | 'vs-light' | 'hc-black';
  fontSize: number;
  wordWrap: 'on' | 'off' | 'wordWrapColumn' | 'bounded';
  minimap: boolean;
  
  // Auto-save
  autoSaveEnabled: boolean;
  autoSaveDelay: number; // milliseconds
  
  // Actions
  setContent: (content: string) => void;
  setLanguage: (language: string) => void;
  setDirty: (dirty: boolean) => void;
  markSaved: () => void;
  setTheme: (theme: 'vs-dark' | 'vs-light' | 'hc-black') => void;
  setFontSize: (size: number) => void;
  setWordWrap: (wrap: 'on' | 'off' | 'wordWrapColumn' | 'bounded') => void;
  toggleMinimap: () => void;
  setAutoSave: (enabled: boolean) => void;
  setAutoSaveDelay: (delay: number) => void;
  reset: () => void;
}

const initialState = {
  content: '',
  language: 'python',
  isDirty: false,
  lastSaved: null,
  theme: 'vs-dark' as const,
  fontSize: 14,
  wordWrap: 'on' as const,
  minimap: true,
  autoSaveEnabled: true,
  autoSaveDelay: 5000,
};

export const useEditorStore = create<EditorState>()(
  devtools(
    (set) => ({
      ...initialState,
      
      setContent: (content) => set({ 
        content, 
        isDirty: true 
      }),
      
      setLanguage: (language) => set({ language }),
      
      setDirty: (isDirty) => set({ isDirty }),
      
      markSaved: () => set({ 
        isDirty: false, 
        lastSaved: new Date() 
      }),
      
      setTheme: (theme) => set({ theme }),
      
      setFontSize: (fontSize) => set({ fontSize }),
      
      setWordWrap: (wordWrap) => set({ wordWrap }),
      
      toggleMinimap: () => set((state) => ({ 
        minimap: !state.minimap 
      })),
      
      setAutoSave: (autoSaveEnabled) => set({ autoSaveEnabled }),
      
      setAutoSaveDelay: (autoSaveDelay) => set({ autoSaveDelay }),
      
      reset: () => set(initialState),
    }),
    {
      name: 'editor-store',
    }
  )
); 