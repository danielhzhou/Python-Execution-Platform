import { useEffect, useRef, useCallback } from 'react';
import { useTerminalStore } from '../stores/terminalStore';
import { useAppStore } from '../stores/appStore';
import { WebSocketManager } from '../lib/websocket';
import type { WebSocketMessage } from '../types';

export function useWebSocket() {
  const wsRef = useRef<WebSocketManager | null>(null);
  const terminalRef = useRef<any>(null); // Reference to xterm terminal instance
  
  const {
    setConnected,
    addOutput,
    containerId
  } = useTerminalStore();
  const { setError } = useAppStore();

  // Method to set terminal reference from Terminal component
  const setTerminalRef = useCallback((terminal: any) => {
    terminalRef.current = terminal;
  }, []);

  const connect = useCallback(async () => {
    if (!containerId) {
      setError('No container ID available for WebSocket connection');
      return;
    }

    if (!wsRef.current) {
      wsRef.current = new WebSocketManager();
      
      // Set up event handlers
      wsRef.current.on('connection', () => {
        console.log('WebSocket connected successfully');
        setConnected(true);
      });

      wsRef.current.on('disconnection', () => {
        console.log('WebSocket disconnected');
        setConnected(false);
      });

      // Handle terminal output from backend - write directly to xterm
      wsRef.current.on('terminal_output', (message: WebSocketMessage) => {
        if (message.type === 'terminal_output' && message.data) {
          // Write directly to xterm terminal if available
          if (terminalRef.current) {
            try {
              terminalRef.current.write(message.data);
            } catch (error) {
              console.error('Error writing to terminal:', error);
            }
          }
          // Also add to store for debugging
          addOutput(message.data);
        }
      });

      // Handle other output types
      wsRef.current.on('output', (message: WebSocketMessage) => {
        if (message.type === 'output' && message.data?.content) {
          if (terminalRef.current) {
            try {
              terminalRef.current.write(message.data.content);
            } catch (error) {
              console.error('Error writing to terminal:', error);
            }
          }
          addOutput(message.data.content);
        }
      });

      // Handle connection confirmation
      wsRef.current.on('connected', (message: WebSocketMessage) => {
        if (message.type === 'connected') {
          console.log('Terminal connection confirmed:', message.data?.message);
          if (terminalRef.current) {
            terminalRef.current.writeln(`\r\n\x1b[32m✅ Connected to container\x1b[0m`);
            terminalRef.current.write('\x1b[1;32m$ \x1b[0m');
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
  }, [containerId, setConnected, addOutput, setError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    setConnected(false);
  }, [setConnected]);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current && containerId) {
      wsRef.current.send({
        type: 'terminal_input',
        data: command,
        containerId: containerId
      });
    }
  }, [containerId]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connect,
    disconnect,
    sendCommand,
    setTerminalRef,
    isConnected: wsRef.current?.isConnected || false
  };
} 