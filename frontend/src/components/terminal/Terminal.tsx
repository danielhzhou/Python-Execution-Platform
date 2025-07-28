import React, { useEffect, useRef, useCallback, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
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

  const { currentContainer } = useAppStore();
  const { connect, disconnect, sendCommand: wsSendCommand, setTerminalRef } = useWebSocket();

  // Initialize terminal with improved error handling
  useEffect(() => {
    if (!terminalRef.current || isTerminalInitialized) {
      console.log('Terminal init skipped:', { hasRef: !!terminalRef.current, isInitialized: isTerminalInitialized });
      return;
    }
    
    console.log('🖥️ Initializing terminal...');

    let terminal: XTerm | null = null;
    let fitAddon: FitAddon | null = null;
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
          allowTransparency: true,
          macOptionIsMeta: true,
          rightClickSelectsWord: true,
          convertEol: true,
        });

        // Create addons
        fitAddon = new FitAddon();
        webLinksAddon = new WebLinksAddon();

        // Load addons before opening terminal
        terminal.loadAddon(fitAddon);
        terminal.loadAddon(webLinksAddon);

        // Store refs
        xtermRef.current = terminal;
        fitAddonRef.current = fitAddon;
        
        // Provide terminal reference to WebSocket hook
        setTerminalRef(terminal);

        // Open terminal in container
        if (terminalRef.current) {
          terminal.open(terminalRef.current);
          
          // Wait for terminal to be properly rendered
          await new Promise(resolve => {
            requestAnimationFrame(() => {
              requestAnimationFrame(resolve);
            });
          });

          // Safe fit function with proper checks
          const safeFit = () => {
            try {
              if (
                terminal && 
                fitAddon && 
                terminalRef.current &&
                terminal.element &&
                terminalRef.current.offsetWidth > 0 && 
                terminalRef.current.offsetHeight > 0 &&
                terminal.element.offsetWidth > 0 &&
                terminal.element.offsetHeight > 0
              ) {
                fitAddon.fit();
                return true;
              }
            } catch (error) {
              console.warn('Terminal fit error:', error);
            }
            return false;
          };

          // Initial fit with retries
          let fitAttempts = 0;
          const maxFitAttempts = 10;
          
          const attemptFit = () => {
            if (safeFit()) {
              console.log('Terminal successfully initialized and fitted');
              setIsTerminalInitialized(true);
              return;
            }
            
            fitAttempts++;
            if (fitAttempts < maxFitAttempts) {
              setTimeout(attemptFit, 50);
            } else {
              console.warn('Terminal fit failed after maximum attempts');
              setIsTerminalInitialized(true); // Continue anyway
            }
          };

          attemptFit();

          // Welcome message
          terminal.writeln('\x1b[1;32m╭─ Python Execution Platform Terminal ─╮\x1b[0m');
          terminal.writeln('\x1b[1;32m│ Ready for Python development         │\x1b[0m');
          terminal.writeln('\x1b[1;32m╰───────────────────────────────────────╯\x1b[0m');
          terminal.writeln('');
          
          if (currentContainer) {
            terminal.writeln(`\x1b[1;36mContainer: ${currentContainer.id.substring(0, 12)}\x1b[0m`);
            terminal.write('\x1b[1;32m$ \x1b[0m');
          } else {
            terminal.writeln('\x1b[1;33mNo container available. Creating...\x1b[0m');
          }

          // Handle terminal input with error boundaries
          terminal.onData((data) => {
            try {
              // Send raw input directly to WebSocket instead of handling locally
              if (isConnected && terminal) {
                wsSendCommand(data);
              } else if (!isConnected && terminal) {
                // If not connected, show a message
                terminal.write('\r\n\x1b[31m❌ Not connected to container\x1b[0m\r\n');
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
      fitAddonRef.current = null;
      setIsTerminalInitialized(false);
    };
  }, [theme, fontSize, fontFamily, currentContainer, setTerminalRef]);

  // Auto-connect WebSocket when terminal is ready
  useEffect(() => {
    if (isTerminalInitialized && xtermRef.current && currentContainer && !isConnected) {
      connect();
    }
  }, [currentContainer, isConnected, connect, isTerminalInitialized]);

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
      xtermRef.current.write('\x1b[1;32m$ \x1b[0m');
    }
    clearOutput();
    setIsTerminalInitialized(false); // Reset initialization state
  }, [clearOutput]);

  const handleReconnect = useCallback(() => {
    if (!isConnected) {
      connect();
    } else {
      disconnect();
    }
  }, [isConnected, connect, disconnect]);

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      {/* Terminal Header */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <TerminalIcon className="h-4 w-4" />
          <span className="text-sm font-medium">Terminal</span>
          <div className="flex items-center gap-1">
            {isConnected ? (
              <Wifi className="h-3 w-3 text-green-500" />
            ) : (
              <WifiOff className="h-3 w-3 text-red-500" />
            )}
            <span className={`text-xs ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReconnect}
            className="h-8 px-2"
          >
            {isConnected ? <WifiOff className="h-4 w-4" /> : <Wifi className="h-4 w-4" />}
            <span className="ml-1 text-xs">
              {isConnected ? 'Disconnect' : 'Connect'}
            </span>
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearTerminal}
            className="h-8 px-2"
          >
            <Trash2 className="h-4 w-4" />
            <span className="ml-1 text-xs">Clear</span>
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Terminal Container */}
      <div className="flex-1 min-h-0 p-2">
        <div
          ref={terminalRef}
          className="w-full h-full rounded-md bg-black/90"
          style={{
            fontFamily: fontFamily,
            fontSize: `${fontSize}px`,
          }}
        />
      </div>

      {/* Terminal Footer */}
      <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground">
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