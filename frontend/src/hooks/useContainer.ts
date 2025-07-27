import { useCallback, useEffect, useRef } from 'react';
import { useAppStore } from '../stores/appStore';
import { useTerminalStore } from '../stores/terminalStore';
import { containerApi } from '../lib/api';
import type { Container } from '../types';

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
    if (isCreatingRef.current) {
      return null; // Prevent multiple simultaneous creations
    }
    
    isCreatingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const response = await containerApi.create();
      
      if (response.success && response.data) {
        // The backend returns a different structure, let's adapt it
        const containerData = response.data;
        const container: Container = {
          id: containerData.container_id || containerData.session_id,
          userId: containerData.user_id || 'unknown', // Will be set by backend
          dockerId: containerData.container_id,
          status: containerData.status || 'running',
          createdAt: new Date(),
          lastActivity: new Date()
        };
        
        addContainer(container);
        setCurrentContainer(container);
        setContainerId(container.id);
        return container;
      } else {
        setError(response.error || 'Failed to create container');
        return null;
      }
    } catch (error) {
      setError('Failed to create container');
      console.error('Container creation error:', error);
      return null;
    } finally {
      isCreatingRef.current = false;
      setLoading(false);
    }
  }, [addContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const stopContainer = useCallback(async (containerId: string) => {
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
        setError(response.error || 'Failed to stop container');
      }
    } catch (error) {
      setError('Failed to stop container');
      console.error('Container stop error:', error);
    } finally {
      setLoading(false);
    }
  }, [currentContainer, updateContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const deleteContainer = useCallback(async (containerId: string) => {
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
        setError(response.error || 'Failed to delete container');
      }
    } catch (error) {
      setError('Failed to delete container');
      console.error('Container delete error:', error);
    } finally {
      setLoading(false);
    }
  }, [currentContainer, updateContainer, setCurrentContainer, setContainerId, setLoading, setError]);

  const loadContainers = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await containerApi.list();
      
      if (response.success && response.data) {
        // You'd need to add a setContainers action to the store
        // For now, we'll add them individually
        response.data.forEach((container: any) => {
          addContainer(container);
        });
      } else {
        setError(response.error || 'Failed to load containers');
      }
    } catch (error) {
      setError('Failed to load containers');
      console.error('Container load error:', error);
    } finally {
      setLoading(false);
    }
  }, [addContainer, setLoading, setError]);

  const selectContainer = useCallback((container: Container) => {
    setCurrentContainer(container);
    setContainerId(container.id);
  }, [setCurrentContainer, setContainerId]);

  // Auto-create container if none exists - only after authentication
  useEffect(() => {
    if (isAuthenticated && containers.length === 0 && !currentContainer && !isCreatingRef.current) {
      createContainer();
    }
  }, [isAuthenticated, containers.length, currentContainer]); // Added isAuthenticated dependency

  return {
    currentContainer,
    containers,
    createContainer,
    stopContainer,
    deleteContainer,
    loadContainers,
    selectContainer
  };
} 