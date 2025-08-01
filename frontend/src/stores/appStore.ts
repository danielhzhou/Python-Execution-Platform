import { create } from 'zustand';
import type { Container, User } from '../types';
import { getAuthToken, authApi } from '../lib/api';

interface AppState {
  // User authentication
  user: User | null;
  isAuthenticated: boolean;
  
  // Container management
  currentContainer: Container | null;
  containers: Container[];
  
  // File management
  files: any[];
  currentFile: any | null;
  
  // UI state
  loading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: User | null) => void;
  setAuthenticated: (authenticated: boolean) => void;
  checkAuthStatus: () => Promise<void>;
  logout: () => Promise<void>;
  
  setCurrentContainer: (container: Container | null) => void;
  addContainer: (container: Container) => void;
  updateContainer: (id: string, updates: Partial<Container>) => void;
  removeContainer: (id: string) => void;
  setContainers: (containers: Container[]) => void;
  
  setFiles: (files: any[]) => void;
  setCurrentFile: (file: any | null) => void;
  updateFile: (id: string, updates: Partial<any>) => void;
  
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  isLoading: boolean;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  currentContainer: null,
  containers: [],
  files: [],
  currentFile: null,
  loading: false,
  error: null,
  
  get isLoading() { return get().loading; },

  // Auth actions
  setUser: (user) => set({ user }),
  
  setAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),
  
  checkAuthStatus: async () => {
    const token = getAuthToken();
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    // Set loading while checking auth
    set({ loading: true });

    try {
      const response = await authApi.getCurrentUser();
      if (response.success && response.data) {
        console.log('Authentication verified for user:', response.data.email);
        set({ 
          isAuthenticated: true, 
          user: response.data,
          loading: false,
          error: null
        });
      } else {
        console.log('Authentication failed:', response.error);
        set({ 
          isAuthenticated: false, 
          user: null,
          loading: false
        });
      }
    } catch (error) {
      console.error('Auth check error:', error);
      set({ 
        isAuthenticated: false, 
        user: null,
        loading: false
      });
    }
  },

  logout: async () => {
    set({ loading: true });
    
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('currentContainerId');
      
      set({ 
        isAuthenticated: false, 
        user: null,
        currentContainer: null,
        containers: [],
        files: [],
        currentFile: null,
        loading: false,
        error: null
      });
    }
  },

  // Container actions
  setCurrentContainer: (container) => {
    set({ currentContainer: container });
    if (container) {
      localStorage.setItem('currentContainerId', container.id);
    } else {
      localStorage.removeItem('currentContainerId');
    }
  },
  
  addContainer: (container) => set(state => {
    // Check if container already exists
    const existingIndex = state.containers.findIndex(c => c.id === container.id);
    
    if (existingIndex >= 0) {
      // Replace existing container
      const updatedContainers = [...state.containers];
      updatedContainers[existingIndex] = container;
      return { containers: updatedContainers };
    } else {
      // Add new container
      return { containers: [...state.containers, container] };
    }
  }),
  
  updateContainer: (id, updates) => set(state => ({
    containers: state.containers.map(container =>
      container.id === id ? { ...container, ...updates } : container
    ),
    currentContainer: state.currentContainer?.id === id 
      ? { ...state.currentContainer, ...updates }
      : state.currentContainer
  })),
  
  removeContainer: (id) => set(state => ({
    containers: state.containers.filter(container => container.id !== id),
    currentContainer: state.currentContainer?.id === id ? null : state.currentContainer
  })),
  
  setContainers: (containers) => set({ containers }),
  
  // File actions
  setFiles: (files) => set({ files }),
  setCurrentFile: (currentFile) => set({ currentFile }),
  
  updateFile: (id, updates) => set(state => ({
    files: state.files.map(file =>
      file.id === id ? { ...file, ...updates } : file
    ),
    currentFile: state.currentFile?.id === id 
      ? { ...state.currentFile, ...updates }
      : state.currentFile
  })),
  
  // UI actions
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));      