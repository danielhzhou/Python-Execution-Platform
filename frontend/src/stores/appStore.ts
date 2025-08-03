import { create } from 'zustand';
import type { Container, User } from '../types';
import { getAuthToken, authApi, setTokenExpirationHandler, startTokenRefreshScheduling, stopTokenRefreshScheduling } from '../lib/api';

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

export const useAppStore = create<AppState>((set, get) => {
  // Set up token expiration handler
  const handleTokenExpiration = () => {
    console.log('Token expired, logging out user');
    // Stop any scheduled refresh
    stopTokenRefreshScheduling();
    set({ 
      isAuthenticated: false, 
      user: null,
      currentContainer: null,
      containers: [],
      files: [],
      currentFile: null,
      loading: false,
      error: 'Your session has expired. Please log in again.'
    });
  };
  
  setTokenExpirationHandler(handleTokenExpiration);
  
  return {
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
      set({ isAuthenticated: false, user: null, error: null });
      return;
    }

    // Set loading while checking auth
    set({ loading: true, error: null });

    try {
      const response = await authApi.getCurrentUser();
      if (response.success && response.data) {
        console.log('Authentication verified for user:', response.data.email);
        // Start periodic token refresh scheduling
        startTokenRefreshScheduling();
        set({ 
          isAuthenticated: true, 
          user: response.data,
          loading: false,
          error: null
        });
      } else {
        console.log('Authentication failed:', response.error);
        // Clear any expired token
        if (response.error?.includes('expired') || response.error?.includes('Session')) {
          set({ 
            isAuthenticated: false, 
            user: null,
            loading: false,
            error: response.error
          });
        } else {
          set({ 
            isAuthenticated: false, 
            user: null,
            loading: false,
            error: null
          });
        }
      }
    } catch (error) {
      console.error('Auth check error:', error);
      set({ 
        isAuthenticated: false, 
        user: null,
        loading: false,
        error: null
      });
    }
  },

  logout: async () => {
    set({ loading: true });
    
    // Stop token refresh scheduling
    stopTokenRefreshScheduling();
    
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
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
    console.log('🔄 setCurrentContainer called:', container?.id || 'null');
    set({ currentContainer: container });
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
  };
});   