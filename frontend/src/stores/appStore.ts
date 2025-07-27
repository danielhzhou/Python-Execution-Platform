import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { User, Container, FileInfo } from '../types';

interface AppState {
  // User state
  user: User | null;
  isAuthenticated: boolean;
  
  // Container state
  currentContainer: Container | null;
  containers: Container[];
  
  // File state
  files: FileInfo[];
  currentFile: FileInfo | null;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  sidebarOpen: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setCurrentContainer: (container: Container | null) => void;
  addContainer: (container: Container) => void;
  updateContainer: (id: string, updates: Partial<Container>) => void;
  setFiles: (files: FileInfo[]) => void;
  setCurrentFile: (file: FileInfo | null) => void;
  updateFile: (id: string, updates: Partial<FileInfo>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  toggleSidebar: () => void;
  reset: () => void;
}

const initialState = {
  user: null,
  isAuthenticated: false,
  currentContainer: null,
  containers: [],
  files: [],
  currentFile: null,
  isLoading: false,
  error: null,
  sidebarOpen: true,
};

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      setUser: (user) => set({ 
        user, 
        isAuthenticated: !!user 
      }),
      
      setCurrentContainer: (container) => set({ 
        currentContainer: container 
      }),
      
      addContainer: (container) => set((state) => ({
        containers: [...state.containers, container]
      })),
      
      updateContainer: (id, updates) => set((state) => ({
        containers: state.containers.map(c => 
          c.id === id ? { ...c, ...updates } : c
        ),
        currentContainer: state.currentContainer?.id === id 
          ? { ...state.currentContainer, ...updates }
          : state.currentContainer
      })),
      
      setFiles: (files) => set({ files }),
      
      setCurrentFile: (file) => set({ currentFile: file }),
      
      updateFile: (id, updates) => set((state) => ({
        files: state.files.map(f => 
          f.id === id ? { ...f, ...updates } : f
        ),
        currentFile: state.currentFile?.id === id 
          ? { ...state.currentFile, ...updates }
          : state.currentFile
      })),
      
      setLoading: (isLoading) => set({ isLoading }),
      
      setError: (error) => set({ error }),
      
      toggleSidebar: () => set((state) => ({ 
        sidebarOpen: !state.sidebarOpen 
      })),
      
      reset: () => set(initialState),
    }),
    {
      name: 'app-store',
    }
  )
); 