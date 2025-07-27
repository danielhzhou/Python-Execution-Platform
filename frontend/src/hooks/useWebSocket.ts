import { useEffect, useRef, useCallback } from 'react';
import { useTerminalStore } from '../stores/terminalStore';
import { useAppStore } from '../stores/appStore';
import { WebSocketManager } from '../lib/websocket';
import type { WebSocketMessage } from '../types';

export function useWebSocket() {
  const wsRef = useRef<WebSocketManager | null>(null);
  const {
    setConnected,
    addOutput,
    containerId
  } = useTerminalStore();
  const { setError } = useAppStore();

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

      // Handle terminal output from backend
      wsRef.current.on('output', (message: WebSocketMessage) => {
        if (message.type === 'output' && message.data?.content) {
          addOutput(message.data.content);
        }
      });

      wsRef.current.on('terminal_output', (message: WebSocketMessage) => {
        if (message.type === 'terminal_output') {
          addOutput(message.data);
        }
      });

      // Handle connection confirmation
      wsRef.current.on('connected', (message: WebSocketMessage) => {
        if (message.type === 'connected') {
          console.log('Terminal connection confirmed:', message.data?.message);
        }
      });

      // Handle terminal resize confirmation
      wsRef.current.on('resized', (message: WebSocketMessage) => {
        if (message.type === 'resized') {
          console.log('Terminal resized:', message.data);
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
        type: 'input',
        data: { data: command }
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
    isConnected: wsRef.current?.isConnected || false
  };
}  