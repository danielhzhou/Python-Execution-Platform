import { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { WebLinksAddon } from 'xterm-addon-web-links';
import { FitAddon } from 'xterm-addon-fit';
import { useTerminalStore } from '../../stores/terminalStore';
import { useAppStore } from '../../stores/appStore';
import { useWebSocket } from '../../hooks/useWebSocket';

import 'xterm/css/xterm.css';

interface TerminalProps {
  className?: string;
  onSendCommandReady?: (sendCommand: (command: string) => void) => void;
}

export function Terminal({ className, onSendCommandReady }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [isTerminalInitialized, setIsTerminalInitialized] = useState(false);

  const {
    isConnected,
    theme,
    fontSize,
    fontFamily
  } = useTerminalStore();

  const { currentContainer, loading } = useAppStore();
  
  // Debug: Track renders
  console.log('📱 Terminal component render:', {
    hasXterm: !!xtermRef.current,
    isInitialized: isTerminalInitialized,
    containerExists: !!currentContainer,
    isConnected
  });
  const { connect, sendCommand: wsSendCommand, setTerminalRef } = useWebSocket();

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
          
          // Fit terminal to container size with multiple attempts
          const fitTerminal = () => {
            if (fitAddonRef.current && terminal && terminalRef.current) {
              try {
                // Ensure the container has proper dimensions
                const container = terminalRef.current;
                if (container.clientWidth > 0 && container.clientHeight > 0) {
                  fitAddonRef.current.fit();
                  console.log('📏 Terminal fitted to container:', {
                    width: container.clientWidth,
                    height: container.clientHeight,
                    cols: terminal.cols,
                    rows: terminal.rows
                  });
                  
                  // Scroll to bottom to ensure prompt is visible
                  terminal.scrollToBottom();
                } else {
                  console.warn('Container not ready for fitting, retrying...');
                  setTimeout(fitTerminal, 50);
                }
              } catch (error) {
                console.warn('FitAddon error:', error);
              }
            }
          };
          
          // Try fitting multiple times to ensure it works
          setTimeout(fitTerminal, 50);
          setTimeout(fitTerminal, 200);
          setTimeout(fitTerminal, 500);
          
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
              console.log('🎹 Terminal input:', data, 'WebSocket Connected:', isConnected, 'Current Container:', currentContainer?.id);
              console.log('🔍 DEBUG: Terminal state - wsSendCommand:', !!wsSendCommand, 'isConnected:', isConnected, 'currentContainer:', !!currentContainer);
              console.log('🔍 DEBUG: Connection sources - terminalStore.isConnected:', isConnected);
              
              // Check if we have the WebSocket sendCommand function
              if (!wsSendCommand) {
                console.error('🚨 CRITICAL: wsSendCommand is null/undefined!');
                console.log('🔍 DEBUG: WebSocket hook state investigation needed');
              }
              
              // Handle Ctrl+L to clear terminal (traditional shell behavior)
              if (data === '\f' || data === '\x0c') { // Ctrl+L
                if (terminal) {
                  terminal.clear();
                  terminal.writeln('\x1b[1;32m╭─ Python Execution Platform Terminal ─╮\x1b[0m');
                  terminal.writeln('\x1b[1;32m│ Terminal cleared (Ctrl+L)              │\x1b[0m');
                  terminal.writeln('\x1b[1;32m╰───────────────────────────────────────╯\x1b[0m');
                  terminal.writeln('');
                }
                return;
              }
              
              // Send to WebSocket if connection is available
              // Be more permissive about sending - if we have the function, try to use it
              if (wsSendCommand) {
                if (isConnected) {
                  console.log('📤 Sending to WebSocket (connection confirmed)');
                } else if (currentContainer) {
                  console.log('📤 Sending to WebSocket (container exists, connection state uncertain)');
                } else {
                  console.log('📤 Sending to WebSocket (attempting anyway - have sendCommand function)');
                }
                wsSendCommand(data);
              } else {
                // Only show error if we truly have no way to send
                console.log('❌ No WebSocket sendCommand function available');
                console.log('🔍 DEBUG: Error state - wsSendCommand:', !!wsSendCommand, 'isConnected:', isConnected, 'currentContainer:', !!currentContainer);
                if (terminal) {
                  terminal.write('\r\n\x1b[31m❌ No connection available\x1b[0m\r\n');
                }
              }
              
              // Ensure terminal stays at bottom after input
              setTimeout(() => {
                if (terminal) {
                  terminal.scrollToBottom();
                }
              }, 10);
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
      console.log('🔗 Terminal initialized, attempting WebSocket connection...');
      // Add a small delay to ensure terminal is fully ready
      const timer = setTimeout(() => {
        connect();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [currentContainer, isConnected, connect, isTerminalInitialized]);

  // Expose sendCommand function to parent component when terminal is connected
  useEffect(() => {
    if (onSendCommandReady && wsSendCommand && isConnected) {
      console.log('🔗 Exposing sendCommand function to parent - terminal is connected');
      onSendCommandReady(wsSendCommand);
    }
  }, [onSendCommandReady, wsSendCommand, isConnected]);

  // Handle window resize to fit terminal
  useEffect(() => {
    const handleResize = () => {
      if (fitAddonRef.current && xtermRef.current && terminalRef.current) {
        try {
          // Add a small delay to ensure layout has stabilized
          setTimeout(() => {
            if (fitAddonRef.current && xtermRef.current) {
              fitAddonRef.current.fit();
              xtermRef.current.scrollToBottom();
              console.log('🔄 Terminal resized and scrolled to bottom');
            }
          }, 100);
        } catch (error) {
          console.warn('Terminal resize error:', error);
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isTerminalInitialized]);

  // Handle WebSocket messages (terminal output) and ensure visibility
  useEffect(() => {
    if (xtermRef.current && isConnected) {
      // This would be handled by the WebSocket hook
      // Ensure terminal stays scrolled to bottom for new content
      const terminal = xtermRef.current;
      
      // Add a mutation observer to detect when content is added
      const observer = new MutationObserver(() => {
        if (terminal) {
          terminal.scrollToBottom();
        }
      });
      
      // Observe the terminal element for changes
      if (terminalRef.current) {
        observer.observe(terminalRef.current, {
          childList: true,
          subtree: true,
          characterData: true
        });
      }
      
      return () => observer.disconnect();
    }
  }, [isConnected, isTerminalInitialized]);



  return (
    <div className={`flex flex-col h-full w-full bg-[#1e1e1e] ${className}`}>
      {/* Terminal Content - Full Height */}
      <div className="flex-1 relative overflow-hidden min-h-0">
        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-[#1e1e1e]/95 backdrop-blur-sm flex items-center justify-center z-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#007acc] mx-auto mb-4"></div>
              <div className="text-white">
                <div className="font-medium text-sm">
                  {loading ? 'Creating container...' : 'Connecting to terminal...'}
                </div>
                <div className="text-xs text-white/60 mt-2">
                  Setting up your Python environment
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
            overflow: 'hidden'
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
    </div>
  );
} 