import { useEffect, useRef, useCallback } from 'react';
import { useTerminalStore } from '../stores/terminalStore';
import { useAppStore } from '../stores/appStore';
import { WebSocketManager } from '../lib/websocket';
import type { WebSocketMessage } from '../types';

export function useWebSocket() {
  const wsRef = useRef<WebSocketManager | null>(null);
  const {
    setConnected,
    setWebSocket,
    addOutput,
    containerId
  } = useTerminalStore();
  const { setError } = useAppStore();

  const connect = useCallback(async () => {
    if (!wsRef.current) {
      wsRef.current = new WebSocketManager();
      
      // Set up event handlers
      wsRef.current.on('connection', () => {
        setConnected(true);
        setWebSocket(wsRef.current?.ws || null);
      });

      wsRef.current.on('disconnection', () => {
        setConnected(false);
        setWebSocket(null);
      });

      wsRef.current.on('terminal_output', (message: WebSocketMessage) => {
        if (message.type === 'terminal_output') {
          addOutput(message.data);
        }
      });

      wsRef.current.on('error', (message: WebSocketMessage) => {
        if (message.type === 'error') {
          setError(message.message);
        }
      });
    }

    try {
      await wsRef.current.connect();
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setError('Failed to connect to terminal');
    }
  }, [setConnected, setWebSocket, addOutput, setError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    setConnected(false);
    setWebSocket(null);
  }, [setConnected, setWebSocket]);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current && containerId) {
      wsRef.current.send({
        type: 'terminal_input',
        data: command,
        containerId
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