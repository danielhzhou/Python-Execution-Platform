import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface TerminalState {
  // Connection state
  isConnected: boolean;
  containerId: string | null;
  
  // Terminal state
  output: string[];
  commandHistory: string[];
  historyIndex: number;
  currentCommand: string;
  currentDirectory: string;
  
  // Terminal settings
  theme: {
    background: string;
    foreground: string;
    cursor: string;
    selection: string;
  };
  fontSize: number;
  fontFamily: string;
  
  // Actions
  setConnected: (connected: boolean) => void;
  setContainerId: (id: string | null) => void;
  addOutput: (output: string) => void;
  clearOutput: () => void;
  addToHistory: (command: string) => void;
  setCurrentCommand: (command: string) => void;
  navigateHistory: (direction: 'up' | 'down') => void;
  sendCommand: (command: string) => void;
  setTheme: (theme: Partial<TerminalState['theme']>) => void;
  setFontSize: (size: number) => void;
  setFontFamily: (family: string) => void;
  setCurrentDirectory: (directory: string) => void;
  reset: () => void;
}

const defaultTheme = {
  background: '#1e1e1e',
  foreground: '#d4d4d4',
  cursor: '#d4d4d4',
  selection: '#264f78',
};

const initialState = {
  isConnected: false,
  containerId: null,
  output: [],
  commandHistory: [],
  historyIndex: -1,
  currentCommand: '',
  currentDirectory: '/workspace',
  theme: defaultTheme,
  fontSize: 14,
  fontFamily: 'Consolas, "Courier New", monospace',
};

export const useTerminalStore = create<TerminalState>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      setConnected: (isConnected) => set({ isConnected }),
      
      setContainerId: (containerId) => set({ containerId }),
      
      addOutput: (output) => set((state) => ({
        output: [...state.output, output]
      })),
      
      clearOutput: () => set({ output: [] }),
      
      addToHistory: (command) => set((state) => {
        const trimmedCommand = command.trim();
        if (trimmedCommand && 
            (state.commandHistory.length === 0 || 
             state.commandHistory[state.commandHistory.length - 1] !== trimmedCommand)) {
          return {
            commandHistory: [...state.commandHistory, trimmedCommand],
            historyIndex: -1
          };
        }
        return state;
      }),
      
      setCurrentCommand: (currentCommand) => set({ currentCommand }),
      
      navigateHistory: (direction) => set((state) => {
        const { commandHistory, historyIndex } = state;
        if (commandHistory.length === 0) return state;
        
        let newIndex = historyIndex;
        if (direction === 'up') {
          newIndex = historyIndex < commandHistory.length - 1 
            ? historyIndex + 1 
            : historyIndex;
        } else {
          newIndex = historyIndex > -1 
            ? historyIndex - 1 
            : -1;
        }
        
        const currentCommand = newIndex === -1 
          ? '' 
          : commandHistory[commandHistory.length - 1 - newIndex];
        
        return {
          historyIndex: newIndex,
          currentCommand
        };
      }),
      
      sendCommand: (command) => {
        // Add command to history
        get().addToHistory(command);
        
        // This is handled by the WebSocket hook in practice
        // The terminal store just manages state, actual sending is done by useWebSocket
        console.log('Command queued for sending:', command);
      },
      
      setTheme: (theme) => set((state) => ({
        theme: { ...state.theme, ...theme }
      })),
      
      setFontSize: (fontSize) => set({ fontSize }),
      
      setFontFamily: (fontFamily) => set({ fontFamily }),
      
      setCurrentDirectory: (currentDirectory) => set({ currentDirectory }),
      
      reset: () => set(initialState),
    }),
    {
      name: 'terminal-store',
    }
  )
); 