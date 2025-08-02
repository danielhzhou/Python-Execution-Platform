import { useEffect, useRef, useCallback } from 'react';
import { useTerminalStore } from '../stores/terminalStore';
import { useAppStore } from '../stores/appStore';
import { WebSocketManager } from '../lib/websocket';
import type { WebSocketMessage } from '../types';

export function useWebSocket() {
  const wsRef = useRef<WebSocketManager | null>(null);
  const terminalRef = useRef<any>(null); // Reference to xterm terminal instance
  const lastKnownContainerIdRef = useRef<string | null>(null); // Store last known container ID
  
  const {
    setConnected,
    addOutput
  } = useTerminalStore();
  const { setError, currentContainer } = useAppStore();
  
  const containerId = currentContainer?.id || null;
  
  // Update last known container ID when we have one
  useEffect(() => {
    if (containerId) {
      lastKnownContainerIdRef.current = containerId;
      console.log('📝 Updated last known container ID:', containerId);
    }
  }, [containerId]);

  // Wait for container to be fully ready before connecting
  const waitForContainerReady = useCallback(async (maxWaitTime = 10000): Promise<boolean> => {
    if (!currentContainer) return false;
    
    const startTime = Date.now();
    while (Date.now() - startTime < maxWaitTime) {
      if (currentContainer.status === 'running') {
        // Additional check: give container a moment to fully initialize
        await new Promise(resolve => setTimeout(resolve, 1000));
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    return false;
  }, [currentContainer]);

  // Method to set terminal reference from Terminal component
  const setTerminalRef = useCallback((terminal: any) => {
    terminalRef.current = terminal;
  }, []);

  const connect = useCallback(async () => {
    if (!containerId) {
      console.error('❌ No container ID available for WebSocket connection');
      setError('No container ID available for WebSocket connection');
      return;
    }

    console.log('🔌 Preparing to connect WebSocket to container:', containerId);

    // Wait for container to be fully ready
    const isReady = await waitForContainerReady();
    if (!isReady) {
      console.error('❌ Container not ready for WebSocket connection after waiting');
      setError('Container not ready for terminal connection');
      return;
    }

    console.log('✅ Container is ready, establishing WebSocket connection...');

    // Disconnect existing connection first to prevent duplicates
    if (wsRef.current) {
      console.log('🔌 Disconnecting existing WebSocket before reconnecting');
      wsRef.current.disconnect();
      wsRef.current = null;
    }

    if (!wsRef.current) {
      wsRef.current = new WebSocketManager();
      
      // Set up event handlers
      wsRef.current.on('connection', () => {
        console.log('✅ WebSocket raw connection established');
        // Set connected=true immediately when WebSocket connects
        // This allows immediate input while waiting for terminal session confirmation
        setConnected(true);
        console.log('✅ Connection state set to true via raw connection');
      });

      wsRef.current.on('disconnection', () => {
        console.log('WebSocket disconnected');
        setConnected(false);
      });

      // Handle terminal output from backend - write directly to xterm
      wsRef.current.on('terminal_output', (message: WebSocketMessage) => {
        console.log('📥 Received terminal_output:', message);
        if (message.type === 'terminal_output' && message.data) {
          // If we receive terminal output but aren't marked as connected yet,
          // this means the terminal session is working - set connected=true
          const currentState = useTerminalStore.getState();
          if (!currentState.isConnected) {
            console.log('🔄 Setting connected=true due to terminal_output (fallback)');
            setConnected(true);
          }
          
          // Write directly to xterm terminal if available
          if (terminalRef.current) {
            try {
              console.log('📝 Writing to terminal:', message.data);
              terminalRef.current.write(message.data);
            } catch (error) {
              console.error('Error writing to terminal:', error);
            }
          } else {
            console.warn('⚠️ Terminal ref not available for output');
          }
          addOutput(message.data); // Also add to store for debugging
        }
      });


      // Handle connection confirmation
      wsRef.current.on('connected', (message: WebSocketMessage) => {
        if (message.type === 'connected') {
          console.log('🎉 Terminal session confirmed:', message.data?.message);
          console.log('🔍 Terminal ref available:', !!terminalRef.current);
          
          // Set connected=true when terminal session is confirmed
          setConnected(true);
          console.log('✅ Connection state set to true via connected message');
          
          if (terminalRef.current) {
            try {
              // Don't clear - just append connection message
              terminalRef.current.writeln(`\x1b[32m✅ Connected to container\x1b[0m`);
              terminalRef.current.write('\x1b[1;32m$ \x1b[0m');
              
              // Focus the terminal
              terminalRef.current.focus();
              
              console.log('✅ Connection message written to terminal');
              
              // Send a test command to see if terminal responds
              setTimeout(() => {
                if (wsRef.current && containerId) {
                  console.log('🧪 Sending test command to terminal');
                  wsRef.current.send({
                    type: 'terminal_input',
                    data: 'echo "Terminal is working!"\n',
                    containerId: containerId
                  });
                }
              }, 1000);
              
            } catch (error) {
              console.error('❌ Error writing welcome message:', error);
            }
          } else {
            console.warn('⚠️ Terminal ref not available when trying to show welcome');
          }
        }
      });

      wsRef.current.on('error', (message: WebSocketMessage) => {
        if (message.type === 'error') {
          const errorMsg = message.message || 'WebSocket error';
          console.error('WebSocket error:', errorMsg);
          setError(errorMsg);
        }
      });
    }

    try {
      await wsRef.current.connect(containerId);
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setError('Failed to connect to terminal');
    }
  }, [containerId, currentContainer, waitForContainerReady, setConnected, addOutput, setError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    setConnected(false);
  }, [setConnected]);

  const sendCommand = useCallback((command: string) => {
    console.log('🎯 sendCommand called with:', command);
    
    // Use the container ID that was used to establish the connection
    // Priority: current container ID > WebSocket manager stored ID > last known ID
    const activeContainerId = containerId || wsRef.current?.currentContainerId || lastKnownContainerIdRef.current;
    
    console.log('🔍 sendCommand state:', {
      hasWsRef: !!wsRef.current,
      wsRefConnected: wsRef.current?.isConnected,
      containerId,
      wsManagerContainerId: wsRef.current?.currentContainerId,
      lastKnownContainerId: lastKnownContainerIdRef.current,
      activeContainerId,
      wsRefExists: !!wsRef.current
    });
    
    if (wsRef.current && activeContainerId) {
      console.log('✅ Sending command via WebSocket');
      wsRef.current.send({
        type: 'terminal_input',
        data: command,
        containerId: activeContainerId
      });
    } else {
      console.error('❌ Cannot send command - missing wsRef or containerId', {
        hasWsRef: !!wsRef.current,
        containerId,
        activeContainerId
      });
    }
  }, [containerId]);

  // Health check and recovery mechanism
  useEffect(() => {
    if (!containerId || !currentContainer) return;

    const healthCheckInterval = setInterval(() => {
      // If we should be connected but aren't, try to reconnect
      if (currentContainer.status === 'running' && !wsRef.current?.isConnected) {
        console.log('🔍 Health check: Connection lost, attempting recovery...');
        connect();
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(healthCheckInterval);
  }, [containerId, currentContainer, connect]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Get connection state from terminal store (which is set by 'connected' message)
  const { isConnected: terminalStoreConnected } = useTerminalStore();
  
  return {
    connect,
    disconnect,
    sendCommand,
    setTerminalRef,
    isConnected: terminalStoreConnected // Use terminal store state for consistency
  };
} 