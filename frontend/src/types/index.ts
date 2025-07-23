/**
 * Core type definitions for Python Execution Platform
 */

// User types
export interface User {
  id: string;
  email: string;
  role: 'learner' | 'reviewer' | 'admin';
  createdAt: Date;
  lastActivity: Date;
}

// Container types
export type ContainerStatus = 'creating' | 'running' | 'stopped' | 'error';

export interface Container {
  id: string;
  userId: string;
  dockerId: string;
  status: ContainerStatus;
  createdAt: Date;
  lastActivity: Date;
}

// File types
export interface FileInfo {
  id: string;
  name: string;
  path: string;
  content: string;
  language: string;
  size: number;
  lastModified: Date;
}

// WebSocket message types
export type WebSocketMessage = 
  | { type: 'terminal_input'; data: string; containerId: string }
  | { type: 'terminal_output'; data: string; containerId: string }
  | { type: 'file_save'; path: string; content: string }
  | { type: 'container_status'; status: ContainerStatus; containerId: string }
  | { type: 'error'; message: string; code?: string };

// API response types
export type Result<T, E = Error> = 
  | { success: true; data: T }
  | { success: false; error: E };

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Editor types
export interface EditorState {
  content: string;
  language: string;
  isDirty: boolean;
  lastSaved: Date | null;
}

// Terminal types
export interface TerminalState {
  output: string[];
  isConnected: boolean;
  containerId: string | null;
}

// Application state types
export interface AppState {
  user: User | null;
  currentContainer: Container | null;
  files: FileInfo[];
  isLoading: boolean;
  error: string | null;
} 