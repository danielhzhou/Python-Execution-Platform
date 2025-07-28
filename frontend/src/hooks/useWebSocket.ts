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
      console.error('❌ No container ID available for WebSocket connection');
      setError('No container ID available for WebSocket connection');
      return;
    }

    console.log('🔌 Connecting WebSocket to container:', containerId);

    if (!wsRef.current) {
      wsRef.current = new WebSocketManager();
      
      // Set up event handlers
      wsRef.current.on('connection', () => {
        console.log('WebSocket connected successfully');
        // Don't set connected=true here, wait for terminal session confirmation
      });

      wsRef.current.on('disconnection', () => {
        console.log('WebSocket disconnected');
        setConnected(false);
      });

      // Handle terminal output from backend - write directly to xterm
      wsRef.current.on('terminal_output', (message: WebSocketMessage) => {
        console.log('📥 Received terminal_output:', message);
        if (message.type === 'terminal_output' && message.data) {
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

      wsRef.current.on('output', (message: WebSocketMessage) => {
        console.log('📥 Received output:', message);
        if (message.type === 'output' && message.data?.content) {
          if (terminalRef.current) {
            try {
              console.log('📝 Writing to terminal:', message.data.content);
              terminalRef.current.write(message.data.content);
            } catch (error) {
              console.error('Error writing to terminal:', error);
            }
          } else {
            console.warn('⚠️ Terminal ref not available for output');
          }
          addOutput(message.data.content);
        }
      });

      // Handle connection confirmation
      wsRef.current.on('connected', (message: WebSocketMessage) => {
        if (message.type === 'connected') {
          console.log('Terminal connection confirmed:', message.data?.message);
          console.log('Terminal ref available:', !!terminalRef.current);
          setConnected(true); // Set connected=true when terminal session is ready
          if (terminalRef.current) {
            try {
              // Clear any existing content and show welcome
              terminalRef.current.clear();
              
              // Test if terminal is working by writing directly
              terminalRef.current.write('Testing terminal...\r\n');
              
              terminalRef.current.writeln('\x1b[1;32m╭─ Python Execution Platform Terminal ─╮\x1b[0m');
              terminalRef.current.writeln('\x1b[1;32m│ Ready for Python development         │\x1b[0m');
              terminalRef.current.writeln('\x1b[1;32m╰───────────────────────────────────────╯\x1b[0m');
              terminalRef.current.writeln('');
              terminalRef.current.writeln(`\x1b[32m✅ Connected to container\x1b[0m`);
              terminalRef.current.write('\x1b[1;32m$ \x1b[0m');
              
              // Focus the terminal
              terminalRef.current.focus();
              
              console.log('✅ Welcome message written to terminal');
              
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
            console.error('❌ Terminal ref not available when trying to show welcome');
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