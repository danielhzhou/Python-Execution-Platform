import { useCallback, useEffect, useRef } from 'react';
import { useAppStore } from '../stores/appStore';
import { useTerminalStore } from '../stores/terminalStore';
import { containerApi } from '../lib/api';
import type { Container, ContainerResponse } from '../types';

export function useContainer() {
  const {
    currentContainer,
    containers,
    isAuthenticated,
    setCurrentContainer,
    addContainer,
    updateContainer,
    setLoading,
    setError
  } = useAppStore();

  const { setContainerId } = useTerminalStore();
  const isCreatingRef = useRef(false);

  const createContainer = useCallback(async (): Promise<Container | null> => {
    // Only create containers if authenticated
    if (!isAuthenticated) {
      setError('You must be logged in to create a container');
      return null;
    }

    if (isCreatingRef.current) {
      return null; // Prevent multiple simultaneous creations
    }
    
    isCreatingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      // Use the new createWithCleanup method for better handling of existing containers
      const response = await containerApi.createWithCleanup();
      
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
        
        addContainer(container);
        setCurrentContainer(container);
        setContainerId(container.id);
        return container;
      } else {
        // Better error handling for specific container issues
        let errorMessage = 'Failed to create container';
        
        if (response.error) {
          if (typeof response.error === 'string') {
            errorMessage = response.error;
          } else if (typeof response.error === 'object') {
            errorMessage = response.error.error || response.error.message || errorMessage;
            
            // Handle specific error cases
            if (errorMessage.includes('already has an active container')) {
              errorMessage = 'You have an active container. Please wait while we clean it up and retry...';
            }
          }
        }
        
        setError(errorMessage);
        return null;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create container';
      setError(errorMessage);
      console.error('Container creation error:', error);
      return null;
    } finally {
      isCreatingRef.current = false;
      setLoading(false);
    }
  }, [isAuthenticated, addContainer, setCurrentContainer, setContainerId, setLoading, setError]);

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
        if (currentContainer?.id === containerId) {
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

  const loadContainers = useCallback(async () => {
    if (!isAuthenticated) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
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
        
        containers.forEach(container => {
          addContainer(container);
        });

        // If we have containers but no current container, set the first running one
        if (containers.length > 0 && !currentContainer) {
          const runningContainer = containers.find(c => c.status === 'running');
          if (runningContainer) {
            setCurrentContainer(runningContainer);
            setContainerId(runningContainer.id);
          }
        }
      } else {
        const errorMessage = typeof response.error === 'string'
          ? response.error
          : 'Failed to load containers';
        setError(errorMessage);
      }
    } catch (error) {
      setError('Failed to load containers');
      console.error('Container load error:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, addContainer, currentContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const selectContainer = useCallback((container: Container) => {
    setCurrentContainer(container);
    setContainerId(container.id);
  }, [setCurrentContainer, setContainerId]);

  // Load existing containers when user authenticates (but don't auto-create)
  useEffect(() => {
    if (isAuthenticated && containers.length === 0) {
      loadContainers();
    }
  }, [isAuthenticated, containers.length, loadContainers]);

  return {
    currentContainer,
    containers,
    createContainer,
    cleanupContainers,
    getContainerStatus,
    stopContainer,
    deleteContainer,
    loadContainers,
    selectContainer
  };
} 