import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface TerminalState {
  // Connection state
  isConnected: boolean;
  containerId: string | null;
  websocket: WebSocket | null;
  
  // Terminal state
  output: string[];
  commandHistory: string[];
  historyIndex: number;
  currentCommand: string;
  
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
  setWebSocket: (ws: WebSocket | null) => void;
  addOutput: (output: string) => void;
  clearOutput: () => void;
  addToHistory: (command: string) => void;
  setCurrentCommand: (command: string) => void;
  navigateHistory: (direction: 'up' | 'down') => void;
  setTheme: (theme: Partial<TerminalState['theme']>) => void;
  setFontSize: (size: number) => void;
  setFontFamily: (family: string) => void;
  sendCommand: (command: string) => void;
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
  websocket: null,
  output: [],
  commandHistory: [],
  historyIndex: -1,
  currentCommand: '',
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
      
      setWebSocket: (websocket) => set({ websocket }),
      
      addOutput: (output) => set((state) => ({
        output: [...state.output, output]
      })),
      
      clearOutput: () => set({ output: [] }),
      
      addToHistory: (command) => set((state) => ({
        commandHistory: [...state.commandHistory, command],
        historyIndex: -1
      })),
      
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
      
      setTheme: (theme) => set((state) => ({
        theme: { ...state.theme, ...theme }
      })),
      
      setFontSize: (fontSize) => set({ fontSize }),
      
      setFontFamily: (fontFamily) => set({ fontFamily }),
      
      sendCommand: (command) => {
        const { websocket, containerId } = get();
        if (websocket && containerId && websocket.readyState === WebSocket.OPEN) {
          websocket.send(JSON.stringify({
            type: 'terminal_input',
            data: command + '\n',
            containerId
          }));
          
          // Add to history if it's not empty and different from last command
          const { commandHistory } = get();
          const trimmedCommand = command.trim();
          if (trimmedCommand && 
              (commandHistory.length === 0 || 
               commandHistory[commandHistory.length - 1] !== trimmedCommand)) {
            set((state) => ({
              commandHistory: [...state.commandHistory, trimmedCommand],
              historyIndex: -1
            }));
          }
        }
      },
      
      reset: () => set(initialState),
    }),
    {
      name: 'terminal-store',
    }
  )
); 