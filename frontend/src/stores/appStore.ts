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
  
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  currentContainer: null,
  containers: [],
  loading: false,
  error: null,

  // Auth actions
  setUser: (user) => set({ user }),
  
  setAuthenticated: (authenticated) => set({ isAuthenticated: authenticated }),
  
  checkAuthStatus: async () => {
    const token = getAuthToken();
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const response = await authApi.getCurrentUser();
      if (response.success) {
        set({ 
          isAuthenticated: true, 
          user: response.data 
        });
      } else {
        set({ 
          isAuthenticated: false, 
          user: null 
        });
      }
    } catch (error) {
      set({ 
        isAuthenticated: false, 
        user: null 
      });
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      set({ 
        isAuthenticated: false, 
        user: null,
        currentContainer: null,
        containers: []
      });
    }
  },

  // Container actions
  setCurrentContainer: (container) => set({ currentContainer: container }),
  
  addContainer: (container) => set(state => ({
    containers: [...state.containers, container]
  })),
  
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
  
  // UI actions
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
})); 