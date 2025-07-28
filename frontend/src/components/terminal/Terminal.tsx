import React, { useEffect, useRef, useCallback, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { WebLinksAddon } from 'xterm-addon-web-links';
import { FitAddon } from 'xterm-addon-fit';
import { useTerminalStore } from '../../stores/terminalStore';
import { useAppStore } from '../../stores/appStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Terminal as TerminalIcon, Trash2, Settings, Wifi, WifiOff } from 'lucide-react';
import 'xterm/css/xterm.css';

interface TerminalProps {
  className?: string;
}

export function Terminal({ className }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [isTerminalInitialized, setIsTerminalInitialized] = useState(false);

  const {
    isConnected,
    theme,
    fontSize,
    fontFamily,
    clearOutput
  } = useTerminalStore();

  const { currentContainer, loading } = useAppStore();
  
  // Debug: Track renders
  console.log('📱 Terminal component render:', {
    hasXterm: !!xtermRef.current,
    isInitialized: isTerminalInitialized,
    containerExists: !!currentContainer,
    isConnected
  });
  const { connect, disconnect, sendCommand: wsSendCommand, setTerminalRef } = useWebSocket();

  // Show loading state when container is being created or terminal is connecting
  const isLoading = loading || (currentContainer && !isConnected && isTerminalInitialized);

  // Initialize terminal with improved error handling
  useEffect(() => {
    if (!terminalRef.current || isTerminalInitialized) {
      console.log('Terminal init skipped:', { hasRef: !!terminalRef.current, isInitialized: isTerminalInitialized });
      return;
    }
    
    console.log('🔄 Terminal useEffect triggered with dependencies:', {
      theme: theme.background,
      fontSize,
      fontFamily,
      hasTerminalRef: !!terminalRef.current,
      isInitialized: isTerminalInitialized
    });
    
    console.log('🖥️ Initializing terminal...');

    let terminal: XTerm | null = null;
    let webLinksAddon: WebLinksAddon | null = null;

    const initializeTerminal = async () => {
      try {
        // Create terminal instance
        terminal = new XTerm({
          theme: {
            background: theme.background,
            foreground: theme.foreground,
            cursor: theme.cursor,
          },
          fontSize,
          fontFamily,
          cursorBlink: true,
          cursorStyle: 'block',
          scrollback: 1000,
          tabStopWidth: 4,
          allowTransparency: false,
          macOptionIsMeta: true,
          rightClickSelectsWord: true,
          convertEol: true,
          // Remove fixed cols/rows to allow FitAddon to handle sizing
        });

        // Create addons
        webLinksAddon = new WebLinksAddon();
        const fitAddon = new FitAddon();
        fitAddonRef.current = fitAddon;

        // Load addons before opening terminal
        terminal.loadAddon(webLinksAddon);
        terminal.loadAddon(fitAddon);

        // Store refs
        xtermRef.current = terminal;
        
        // Provide terminal reference to WebSocket hook
        setTerminalRef(terminal);

        // Open terminal in container
        if (terminalRef.current && terminal) {
          console.log('📺 Opening terminal in container:', terminalRef.current);
          console.log('📏 Terminal container dimensions:', {
            width: terminalRef.current.clientWidth,
            height: terminalRef.current.clientHeight,
            offsetWidth: terminalRef.current.offsetWidth,
            offsetHeight: terminalRef.current.offsetHeight
          });
          
          terminal.open(terminalRef.current);
          
          // Fit terminal to container size
          setTimeout(() => {
            if (fitAddonRef.current && terminal) {
              try {
                fitAddonRef.current.fit();
                console.log('📏 Terminal fitted to container');
              } catch (error) {
                console.warn('FitAddon error:', error);
              }
            }
          }, 100);
          
          xtermRef.current = terminal;
          
          // Pass terminal reference to WebSocket hook
          setTerminalRef(terminal);

          // Mark terminal as initialized
          setIsTerminalInitialized(true);

          // Show initial prompt even without WebSocket connection
          terminal.writeln('\x1b[1;32m╭─ Python Execution Platform Terminal ─╮\x1b[0m');
          terminal.writeln('\x1b[1;32m│ Initializing terminal...               │\x1b[0m');
          terminal.writeln('\x1b[1;32m╰───────────────────────────────────────╯\x1b[0m');
          terminal.writeln('');

          // Focus the terminal when ready
          setTimeout(() => {
            if (terminal) {
              terminal.focus();
              console.log('🎯 Terminal focused');
            }
          }, 200);

          // Handle terminal input with error boundaries
          terminal.onData((data) => {
            try {
              console.log('🎹 Terminal input:', data, 'Store Connected:', isConnected);
              
              // Always try to send to WebSocket if we have a current container
              // The WebSocket service will handle connection state
              if (currentContainer && wsSendCommand) {
                console.log('📤 Sending to WebSocket (container exists)');
                wsSendCommand(data);
              } else {
                // If no container, show error
                console.log('❌ No container available, showing error');
                if (terminal) {
                  terminal.write('\r\n\x1b[31m❌ No container available\x1b[0m\r\n');
                }
              }
            } catch (error) {
              console.error('Terminal input error:', error);
            }
          });

          // Handle selection
          terminal.onSelectionChange(() => {
            try {
              const selection = terminal?.getSelection();
              if (selection) {
                // Could add copy functionality here
              }
            } catch (error) {
              console.warn('Terminal selection error:', error);
            }
          });
        }
      } catch (error) {
        console.error('Terminal initialization error:', error);
        setIsTerminalInitialized(true); // Mark as initialized to prevent retry loops
      }
    };

    initializeTerminal();

    // Cleanup function
    return () => {
      console.log('🧹 Cleaning up terminal...');
      if (terminal) {
        try {
          terminal.dispose();
        } catch (error) {
          console.warn('Terminal disposal error:', error);
        }
      }
      xtermRef.current = null;
      setIsTerminalInitialized(false);
    };
  }, [theme, fontSize, fontFamily, setTerminalRef]);

  // Auto-connect WebSocket when terminal is ready
  useEffect(() => {
    if (isTerminalInitialized && xtermRef.current && currentContainer && !isConnected) {
      connect();
    }
  }, [currentContainer, isConnected, connect, isTerminalInitialized]);

  // Handle window resize to fit terminal
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current && xtermRef.current) {
        try {
          fitAddonRef.current.fit();
          console.log('🔄 Terminal resized');
        } catch (error) {
          console.warn('Terminal resize error:', error);
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isTerminalInitialized]);

  // Handle WebSocket messages (terminal output)
  useEffect(() => {
    if (xtermRef.current && isConnected) {
      // This would be handled by the WebSocket hook
      // For now, we'll simulate receiving output
    }
  }, [isConnected]);

  const handleClearTerminal = useCallback(() => {
    if (xtermRef.current) {
      xtermRef.current.clear();
      xtermRef.current.writeln('\x1b[1;32m╭─ Python Execution Platform Terminal ─╮\x1b[0m');
      xtermRef.current.writeln('\x1b[1;32m│ Terminal cleared                       │\x1b[0m');
      xtermRef.current.writeln('\x1b[1;32m╰───────────────────────────────────────╯\x1b[0m');
      xtermRef.current.writeln('');
      xtermRef.current.write('\x1b[1;32m$ \x1b[0m');
    }
    clearOutput();
  }, [clearOutput]);

  const handleReconnect = useCallback(() => {
    if (!isConnected) {
      connect();
    } else {
      disconnect();
    }
  }, [isConnected, connect, disconnect]);

  return (
    <Card className={`flex flex-col h-full w-full ${className}`}>
      {/* Terminal Header */}
      <div className="flex items-center justify-between p-3 border-b flex-shrink-0">
        <div className="flex items-center gap-2">
          <TerminalIcon className="h-4 w-4" />
          <span className="font-medium">Terminal</span>
          <div className="flex items-center gap-1 ml-2">
            {isConnected ? (
              <>
                <Wifi className="h-3 w-3 text-green-500" />
                <span className="text-xs text-green-600">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-red-500" />
                <span className="text-xs text-red-600">Disconnected</span>
              </>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {/* disconnect logic */}}
            className="h-7 px-2"
          >
            <WifiOff className="h-3 w-3" />
            <span className="ml-1 text-xs">Disconnect</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearTerminal}
            className="h-7 px-2"
          >
            <Trash2 className="h-3 w-3" />
            <span className="ml-1 text-xs">Clear</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
          >
            <Settings className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Terminal Content */}
      <div className="flex-1 relative overflow-hidden min-h-0">
        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mx-auto mb-4"></div>
              <div className="text-white">
                <div className="font-medium">
                  {loading ? 'Creating container...' : 'Connecting to terminal...'}
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  Please wait while we set up your Python environment
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div 
          ref={terminalRef} 
          className="w-full h-full"
          style={{ 
            backgroundColor: theme.background,
            cursor: 'text',
            position: 'relative',
            zIndex: 1,
            overflow: 'auto',
            minHeight: '400px'
          }}
          onClick={() => {
            // Focus the terminal when clicked
            console.log('Terminal clicked, focusing...');
            if (xtermRef.current) {
              xtermRef.current.focus();
            }
          }}
        />
      </div>

      {/* Terminal Footer */}
      <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground flex-shrink-0">
        <div className="flex items-center gap-4">
          <span>Shell: bash</span>
          <span>Encoding: UTF-8</span>
          {currentContainer && (
            <span>Container: {currentContainer.id.substring(0, 8)}</span>
          )}
        </div>
        
        <div className="flex items-center gap-4">
          <span>Connected: {isConnected ? 'Yes' : 'No'}</span>
          <span>Font: {fontSize}px</span>
        </div>
      </div>
    </Card>
  );
} 