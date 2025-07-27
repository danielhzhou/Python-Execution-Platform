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
  const [currentInput, setCurrentInput] = useState('');
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isTerminalInitialized, setIsTerminalInitialized] = useState(false);

  const {
    isConnected,
    theme,
    fontSize,
    fontFamily,
    commandHistory,
    historyIndex,
    currentCommand,
    setCurrentCommand,
    navigateHistory,
    clearOutput,
    sendCommand
  } = useTerminalStore();

  const { currentContainer } = useAppStore();
  const { connect, disconnect, sendCommand: wsSendCommand } = useWebSocket();

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
    let resizeObserver: ResizeObserver | null = null;
    let resizeTimeout: NodeJS.Timeout | null = null;

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

          // Set up ResizeObserver with proper error handling
          if (terminalRef.current && typeof ResizeObserver !== 'undefined') {
            resizeObserver = new ResizeObserver((entries) => {
              for (const entry of entries) {
                if (entry.target === terminalRef.current) {
                  if (resizeTimeout) {
                    clearTimeout(resizeTimeout);
                  }
                  resizeTimeout = setTimeout(() => {
                    safeFit();
                  }, 200); // Increased delay to reduce frequency
                }
              }
            });
            
            resizeObserver.observe(terminalRef.current);
          }

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
              handleTerminalInput(data);
            } catch (error) {
              console.error('Terminal input error:', error);
            }
          });

          // Handle terminal resize
          terminal.onResize(({ cols, rows }) => {
            console.log(`Terminal resized: ${cols}x${rows}`);
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
      if (resizeTimeout) {
        clearTimeout(resizeTimeout);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
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
  }, [theme, fontSize, fontFamily, currentContainer]);

  // Auto-connect WebSocket when terminal is ready
  useEffect(() => {
    if (isTerminalInitialized && xtermRef.current && currentContainer && !isConnected) {
      connect();
    }
  }, [currentContainer, isConnected, connect, isTerminalInitialized]);

  // Handle window resize with improved error handling
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current && xtermRef.current?.element && isTerminalInitialized) {
        try {
          // Add delay to ensure DOM has updated
          setTimeout(() => {
            if (fitAddonRef.current && xtermRef.current?.element) {
              fitAddonRef.current.fit();
            }
          }, 50);
        } catch (error) {
          console.warn('Terminal resize failed:', error);
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isTerminalInitialized]);

  // Handle terminal input
  const handleTerminalInput = useCallback((data: string) => {
    if (!xtermRef.current) return;

    const terminal = xtermRef.current;
    const code = data.charCodeAt(0);

    // Handle special keys
    switch (code) {
      case 13: // Enter
        terminal.writeln('');
        if (currentInput.trim()) {
          // Send command
          sendCommand(currentInput);
          setCurrentCommand(currentInput);
          
          // Add to history
          if (currentInput.trim() !== commandHistory[commandHistory.length - 1]) {
            // This would be handled by the store
          }
        }
        setCurrentInput('');
        setCursorPosition(0);
        terminal.write('\x1b[1;32m$ \x1b[0m');
        break;

      case 127: // Backspace
        if (cursorPosition > 0) {
          const newInput = currentInput.slice(0, cursorPosition - 1) + currentInput.slice(cursorPosition);
          setCurrentInput(newInput);
          setCursorPosition(cursorPosition - 1);
          
          // Update terminal display
          terminal.write('\b \b');
        }
        break;

      case 27: // Escape sequences (arrow keys, etc.)
        if (data.length === 3) {
          const direction = data.charCodeAt(2);
          if (direction === 65) { // Up arrow
            navigateHistory('up');
            // Update display with history command
            const historyCommand = currentCommand;
            if (historyCommand) {
              // Clear current line and write history command
              terminal.write('\r\x1b[K\x1b[1;32m$ \x1b[0m' + historyCommand);
              setCurrentInput(historyCommand);
              setCursorPosition(historyCommand.length);
            }
          } else if (direction === 66) { // Down arrow
            navigateHistory('down');
            const historyCommand = currentCommand;
            // Clear current line and write history command or empty
            terminal.write('\r\x1b[K\x1b[1;32m$ \x1b[0m' + (historyCommand || ''));
            setCurrentInput(historyCommand || '');
            setCursorPosition((historyCommand || '').length);
          } else if (direction === 67) { // Right arrow
            if (cursorPosition < currentInput.length) {
              setCursorPosition(cursorPosition + 1);
              terminal.write('\x1b[C');
            }
          } else if (direction === 68) { // Left arrow
            if (cursorPosition > 0) {
              setCursorPosition(cursorPosition - 1);
              terminal.write('\x1b[D');
            }
          }
        }
        break;

      case 3: // Ctrl+C
        terminal.writeln('^C');
        terminal.write('\x1b[1;32m$ \x1b[0m');
        setCurrentInput('');
        setCursorPosition(0);
        // Send interrupt signal to backend
        if (isConnected) {
          wsSendCommand('\x03'); // Send Ctrl+C
        }
        break;

      case 12: // Ctrl+L
        terminal.clear();
        terminal.write('\x1b[1;32m$ \x1b[0m' + currentInput);
        break;

      default:
        // Regular character input
        if (code >= 32 && code <= 126) {
          const newInput = currentInput.slice(0, cursorPosition) + data + currentInput.slice(cursorPosition);
          setCurrentInput(newInput);
          setCursorPosition(cursorPosition + 1);
          terminal.write(data);
        }
        break;
    }
  }, [currentInput, cursorPosition, commandHistory, currentCommand, isConnected, sendCommand, navigateHistory, setCurrentCommand, wsSendCommand]);

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
    setCurrentInput('');
    setCursorPosition(0);
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
          <span>History: {commandHistory.length} commands</span>
          <span>Font: {fontSize}px</span>
        </div>
      </div>
    </Card>
  );
} 