import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { useTerminalStore } from '../stores/terminalStore';
import { containerApi } from '../lib/api';
import type { Container, ContainerResponse } from '../types';

// Cache for container data to avoid unnecessary requests
const containerCache = new Map<string, { data: Container[], timestamp: number }>();
const CACHE_DURATION = 30000; // 30 seconds

export function useContainer() {
  const {
    currentContainer,
    containers,
    isAuthenticated,
    user,
    setCurrentContainer,
    addContainer,
    updateContainer,
    setContainers,
    setLoading,
    setError
  } = useAppStore();

  const { setContainerId, containerId: terminalContainerId, reset: resetTerminal } = useTerminalStore();
  const isCreatingRef = useRef(false);
  const lastLoadTime = useRef(0);
  const [isInitialized, setIsInitialized] = useState(false);

  // Debounced container creation to prevent multiple simultaneous attempts
  const createContainer = useCallback(async (): Promise<Container | null> => {
    // Only create containers if authenticated
    if (!isAuthenticated) {
      setError('You must be logged in to create a container');
      return null;
    }

    if (isCreatingRef.current) {
      console.log('⏳ Container creation already in progress, skipping...');
      return null; // Prevent multiple simultaneous creations
    }
    
    isCreatingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      console.log('🚀 Starting container creation...');
      console.log('🔍 Current terminal container ID:', terminalContainerId);
      
      // Reset terminal state before creating new container
      resetTerminal();
      console.log('🧹 Terminal state reset');
      
      // Use the simplified create method - backend handles cleanup automatically
      const response = await containerApi.create();
      
      if (response.success && response.data) {
        // The backend returns ContainerResponse structure
        const containerData: ContainerResponse = response.data;
        const container: Container = {
          id: containerData.session_id,
          userId: containerData.user_id || 'unknown',
          dockerId: containerData.container_id,
          status: containerData.status,
          createdAt: new Date(),
          lastActivity: new Date()
        };
        
        console.log('✅ Container created successfully:', container.id);
        console.log('🔧 Setting terminal container ID to:', container.id);
        
        addContainer(container);
        setCurrentContainer(container);
        setContainerId(container.id);
        
        console.log('✅ Terminal container ID updated');
        
        // Invalidate cache
        containerCache.clear();
        
        return container;
      } else {
        // Better error handling for specific container issues
        let errorMessage = 'Failed to create container';
        
        if (response.error) {
          if (typeof response.error === 'string') {
            errorMessage = response.error;
          } else if (typeof response.error === 'object') {
            errorMessage = response.error.error || response.error.message || errorMessage;
          }
        }
        
        console.error('❌ Container creation failed:', errorMessage);
        setError(errorMessage);
        return null;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create container';
      setError(errorMessage);
      console.error('❌ Container creation error:', error);
      return null;
    } finally {
      isCreatingRef.current = false;
      setLoading(false);
    }
  }, [isAuthenticated, addContainer, setCurrentContainer, setContainerId, setLoading, setError, terminalContainerId, resetTerminal]);

  const cleanupContainers = useCallback(async () => {
    if (!isAuthenticated) {
      setError('You must be logged in to cleanup containers');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await containerApi.cleanup();
      
      if (response.success) {
        // Clear current container if it was terminated
        if (currentContainer) {
          setCurrentContainer(null);
          setContainerId(null);
        }
        
        return response.data;
      } else {
        const errorMessage = typeof response.error === 'string' 
          ? response.error 
          : 'Failed to cleanup containers';
        setError(errorMessage);
        return null;
      }
    } catch (error) {
      setError('Failed to cleanup containers');
      console.error('Container cleanup error:', error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, currentContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const getContainerStatus = useCallback(async () => {
    if (!isAuthenticated) {
      return null;
    }

    try {
      const response = await containerApi.getStatus();
      
      if (response.success) {
        return response.data;
      } else {
        console.error('Failed to get container status:', response.error);
        return null;
      }
    } catch (error) {
      console.error('Container status error:', error);
      return null;
    }
  }, [isAuthenticated]);

  const stopContainer = useCallback(async (containerId: string) => {
    if (!isAuthenticated) {
      setError('You must be logged in to stop containers');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await containerApi.stop(containerId);
      
      if (response.success) {
        updateContainer(containerId, { status: 'stopped' });
        
        // If this is the current container, clear it
        // But only if we explicitly stopped it, not if it was stopped by backend
        if (currentContainer?.id === containerId) {
          console.log('🛑 Clearing current container due to explicit stop');
          setCurrentContainer(null);
          setContainerId(null);
        }
      } else {
        const errorMessage = typeof response.error === 'string'
          ? response.error
          : 'Failed to stop container';
        setError(errorMessage);
      }
    } catch (error) {
      setError('Failed to stop container');
      console.error('Container stop error:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, currentContainer, updateContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const deleteContainer = useCallback(async (containerId: string) => {
    if (!isAuthenticated) {
      setError('You must be logged in to delete containers');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await containerApi.delete(containerId);
      
      if (response.success) {
        // Remove from containers list (you'd need to add this action to the store)
        // For now, just update status
        updateContainer(containerId, { status: 'stopped' });
        
        // If this is the current container, clear it
        if (currentContainer?.id === containerId) {
          setCurrentContainer(null);
          setContainerId(null);
        }
      } else {
        const errorMessage = typeof response.error === 'string'
          ? response.error
          : 'Failed to delete container';
        setError(errorMessage);
      }
    } catch (error) {
      setError('Failed to delete container');
      console.error('Container delete error:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, currentContainer, updateContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  // Optimized container loading with caching and debouncing
  const loadContainers = useCallback(async (forceRefresh: boolean = false) => {
    if (!isAuthenticated) {
      return;
    }

    const now = Date.now();
    const cacheKey = 'user_containers';
    
    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cached = containerCache.get(cacheKey);
      if (cached && (now - cached.timestamp) < CACHE_DURATION) {
        console.log('📦 Using cached container data');
        setContainers(cached.data);
        
        // Set current container if none selected
        if (cached.data.length > 0 && !currentContainer) {
          const runningContainer = cached.data.find(c => c.status === 'running');
          if (runningContainer) {
            setCurrentContainer(runningContainer);
            setContainerId(runningContainer.id);
          }
        }
        return;
      }
    }

    // Debounce API calls - don't call more than once per 5 seconds
    if (!forceRefresh && (now - lastLoadTime.current) < 5000) {
      console.log('⏳ Debouncing container load request');
      return;
    }

    lastLoadTime.current = now;
    setLoading(true);
    setError(null);

    try {
      console.log('🔄 Loading containers from API...');
      const response = await containerApi.list();
      
      if (response.success && response.data) {
        // Convert backend ContainerResponse[] to Container[]
        const containers: Container[] = response.data.map((containerResponse: ContainerResponse) => ({
          id: containerResponse.session_id,
          userId: containerResponse.user_id || 'unknown',
          dockerId: containerResponse.container_id,
          status: containerResponse.status,
          createdAt: new Date(),
          lastActivity: new Date()
        }));
        
        console.log(`✅ Loaded ${containers.length} containers`);
        console.log('🔍 DEBUG: Container details:', containers.map(c => ({ id: c.id, status: c.status })));
        
        // Update cache
        containerCache.set(cacheKey, { data: containers, timestamp: now });
        
        setContainers(containers);

        // If we have containers but no current container, set the first running one
        if (containers.length > 0 && !currentContainer) {
          const runningContainer = containers.find(c => c.status === 'running');
          if (runningContainer) {
            console.log('🎯 Setting current container:', runningContainer.id);
            console.log('🔍 DEBUG: Current container before setting:', currentContainer);
            setCurrentContainer(runningContainer);
            setContainerId(runningContainer.id);
            console.log('🔍 DEBUG: Current container after setting should be:', runningContainer.id);
          } else {
            console.log('🔍 DEBUG: No running containers found in:', containers.map(c => ({ id: c.id, status: c.status })));
          }
        } else {
          console.log('🔍 DEBUG: Container state - containers.length:', containers.length, 'currentContainer:', currentContainer?.id);
        }
        
        // If current container exists but backend shows different status, 
        // don't clear it immediately - let WebSocket connection determine actual state
        if (currentContainer && containers.length > 0) {
          const backendContainer = containers.find(c => c.id === currentContainer.id);
          if (backendContainer && backendContainer.status !== currentContainer.status) {
            console.log(`📊 Container status mismatch: frontend=${currentContainer.status}, backend=${backendContainer.status}`);
            // Update status but keep container active if WebSocket is connected
            updateContainer(currentContainer.id, { status: backendContainer.status });
          }
        }
        
        setIsInitialized(true);
      } else {
        const errorMessage = typeof response.error === 'string'
          ? response.error
          : 'Failed to load containers';
        console.error('❌ Failed to load containers:', errorMessage);
        setError(errorMessage);
      }
    } catch (error) {
      const errorMessage = 'Failed to load containers';
      console.error('❌ Container load error:', error);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, addContainer, currentContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const selectContainer = useCallback((container: Container) => {
    setCurrentContainer(container);
    setContainerId(container.id);
  }, [setCurrentContainer, setContainerId]);

  // Load existing containers when user authenticates and auto-create if none exist
  // Only run once when authenticated and not yet initialized
  // Only create containers for submitters (not reviewers/admins)
  useEffect(() => {
    if (isAuthenticated && !isInitialized) {
      const userRole = user?.role || 'submitter';
      const needsContainer = userRole === 'submitter';
      
      console.log('🔑 User authenticated, checking container needs...', {
        userRole,
        needsContainer
      });
      
      if (needsContainer) {
        console.log('🔑 Submitter user - loading existing containers...');
        
        const initializeUserContainer = async () => {
          try {
            // First, load existing containers
            await loadContainers();
            
            // Check if user has any running containers after loading
            const response = await containerApi.list();
            if (response.success && response.data) {
              const runningContainers = response.data.filter(c => c.status === 'running');
              
              if (runningContainers.length === 0) {
                console.log('📦 No running containers found, creating one...');
                await createContainer();
              } else {
                console.log(`✅ Found ${runningContainers.length} running container(s)`);
              }
            }
          } catch (error) {
            console.error('❌ Error initializing user container:', error);
            // Don't set error here as it might be temporary
          }
        };
        
        initializeUserContainer();
      } else {
        console.log('👨‍💼 Reviewer/Admin user - no container needed');
      }
      
      setIsInitialized(true);
    } else if (!isAuthenticated && isInitialized) {
      // Reset initialization state when user logs out
      setIsInitialized(false);
    }
  }, [isAuthenticated, isInitialized, user?.role, loadContainers, createContainer]);

  // Poll container status to detect changes and maintain connection health
  // Temporarily disabled to debug container state issues
  /*
  useEffect(() => {
    if (!isAuthenticated || !currentContainer) return;

    const statusPollingInterval = setInterval(async () => {
      try {
        await loadContainers(true); // Force refresh
        // Status update is handled in loadContainers
      } catch (error) {
        console.error('Status polling error:', error);
      }
    }, 15000); // Poll every 15 seconds

    return () => clearInterval(statusPollingInterval);
  }, [isAuthenticated, currentContainer, loadContainers]);
  */

  return {
    currentContainer,
    containers,
    createContainer,
    cleanupContainers,
    getContainerStatus,
    stopContainer,
    deleteContainer,
    loadContainers,
    selectContainer,
    isInitialized
  };
} 