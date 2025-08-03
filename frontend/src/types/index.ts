/**
 * Core type definitions for Python Execution Platform
 */

// User types
export type UserRole = 'submitter' | 'reviewer' | 'admin';

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  role: UserRole;
  created_at?: string;
  updated_at?: string;
}

// Container types
export type ContainerStatus = 'creating' | 'running' | 'stopped' | 'error' | 'terminated';

export interface Container {
  id: string;
  userId: string;
  dockerId: string;
  status: ContainerStatus;
  createdAt: Date;
  lastActivity: Date;
}

// Backend container response structure
export interface ContainerResponse {
  session_id: string;
  container_id: string;
  status: ContainerStatus;
  websocket_url: string;
  user_id?: string;
}

// Container creation request
export interface ContainerCreateRequest {
  project_id?: string | null;
  project_name?: string;
  initial_files?: Record<string, string>;
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
  | { type: 'input'; data: { data: string } }
  | { type: 'output'; data: { content: string; stream?: string; timestamp?: string } }
  | { type: 'terminal_input'; data: string; containerId: string }
  | { type: 'terminal_output'; data: string; containerId: string }
  | { type: 'connected'; data: { session_id: string; message: string } }
  | { type: 'resized'; data: { rows: number; cols: number } }
  | { type: 'resize'; data: { rows: number; cols: number } }
  | { type: 'ping'; data?: any }
  | { type: 'pong'; data?: any }
  | { type: 'connection'; data: string }
  | { type: 'disconnection'; data: string }
  | { type: 'filesystem_change'; data: { command_type: string; command: string; timestamp: string } }
  | { type: 'directory_change'; data: { current_directory: string; timestamp: string } }
  | { type: 'error'; data?: { message: string }; message?: string };

// API response types
export type Result<T, E = Error> = 
  | { success: true; data: T }
  | { success: false; error: E };

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string | { error: string; message?: string; suggestion?: string };
  message?: string;
}

// Auth response types
export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    user_metadata?: {
      full_name?: string;
      avatar_url?: string;
    };
  };
  message?: string;
}

// Container status response
export interface ContainerStatusResponse {
  user_id: string;
  total_containers: number;
  active_containers: number;
  can_create_new: boolean;
  active_container_ids: string[];
  max_containers_per_user: number;
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

// Submission types
export type SubmissionStatus = 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'revision_requested';

export interface SubmissionFile {
  id: string;
  file_path: string;
  file_name: string;
  content: string;
  file_size?: number;
  mime_type?: string;
}

export interface SubmissionReview {
  id: string;
  reviewer_id: string;
  status: string;
  comment: string;
  file_path?: string;
  line_number?: number;
  created_at: string;
}

export interface Submission {
  id: string;
  title: string;
  description?: string;
  status: SubmissionStatus;
  submitter_id: string;
  project_id: string;
  submitted_at?: string;
  reviewed_at?: string;
  reviewer_id?: string;
  created_at: string;
  updated_at: string;
}

export interface SubmissionDetail {
  submission: Submission;
  files: SubmissionFile[];
  reviews: SubmissionReview[];
}

export interface CreateSubmissionRequest {
  project_id: string;
  title: string;
  description?: string;
}

export interface SubmitFilesRequest {
  submission_id: string;
  files: Array<{
    path: string;
    content: string;
    name: string;
  }>;
}

export interface ReviewSubmissionRequest {
  submission_id: string;
  status: 'approved' | 'rejected';
  comment: string;
}

// Application state types
export interface AppState {
  user: User | null;
  currentContainer: Container | null;
  files: FileInfo[];
  isLoading: boolean;
  error: string | null;
} 