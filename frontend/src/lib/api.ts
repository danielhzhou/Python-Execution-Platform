import type { 
  ApiResponse, 
  AuthResponse, 
  User, 
  ContainerResponse, 
  ContainerCreateRequest,
  ContainerStatusResponse,
  Submission,
  SubmissionDetail,
  CreateSubmissionRequest,
  SubmitFilesRequest,
  ReviewSubmissionRequest
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export function getAuthToken(): string | null {
  return localStorage.getItem('auth_token')
}

export function setAuthToken(token: string): void {
  localStorage.setItem('auth_token', token)
}

export function removeAuthToken(): void {
  localStorage.removeItem('auth_token')
}

async function apiRequest<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = getAuthToken()
  
  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
    ...options,
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config)
    const data = await response.json()

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || data.message || `HTTP ${response.status}`,
      }
    }

    return {
      success: true,
      data,
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
    }
  }
}

export const authApi = {
  async login(email: string, password: string): Promise<ApiResponse<AuthResponse>> {
    const response = await apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    
    if (response.success && response.data?.access_token) {
      setAuthToken(response.data.access_token)
    }
    
    return response
  },

  async register(email: string, password: string, fullName?: string): Promise<ApiResponse<any>> {
    return apiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ 
        email, 
        password, 
        full_name: fullName 
      }),
    })
  },

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return apiRequest<User>('/auth/me')
  },

  async logout(): Promise<ApiResponse<any>> {
    const response = await apiRequest('/auth/logout', {
      method: 'POST',
    })
    removeAuthToken()
    return response
  },
}

export const containerApi = {
  async create(request: ContainerCreateRequest = {}): Promise<ApiResponse<ContainerResponse>> {
    return apiRequest<ContainerResponse>('/containers/create', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },

  async list(): Promise<ApiResponse<ContainerResponse[]>> {
    return apiRequest<ContainerResponse[]>('/containers/')
  },

  async getInfo(sessionId: string): Promise<ApiResponse<ContainerResponse>> {
    return apiRequest<ContainerResponse>(`/containers/${sessionId}/info`)
  },

  async stop(sessionId: string): Promise<ApiResponse<any>> {
    return apiRequest(`/containers/${sessionId}/terminate`, {
      method: 'POST',
    })
  },

  async delete(sessionId: string): Promise<ApiResponse<any>> {
    return apiRequest(`/containers/${sessionId}/terminate`, {
      method: 'POST',
    })
  },

  async cleanup(): Promise<ApiResponse<any>> {
    return apiRequest('/containers/cleanup', {
      method: 'POST',
    })
  },

  async getStatus(): Promise<ApiResponse<ContainerStatusResponse>> {
    return apiRequest<ContainerStatusResponse>('/containers/status')
  },
}

export const fileApi = {
  async list(containerId: string): Promise<ApiResponse<any[]>> {
    return apiRequest<any[]>(`/containers/${containerId}/files`)
  },

  async get(containerId: string, path: string): Promise<ApiResponse<any>> {
    return apiRequest<any>(`/containers/${containerId}/files/content?path=${encodeURIComponent(path)}`)
  },

  async save(containerId: string, path: string, content: string): Promise<ApiResponse<any>> {
    return apiRequest<any>(`/containers/${containerId}/files`, {
      method: 'POST',
      body: JSON.stringify({
        path,
        content
      }),
    })
  },

  async delete(containerId: string, path: string): Promise<ApiResponse<any>> {
    return apiRequest(`/containers/${containerId}/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    })
  },

  async createDirectory(containerId: string, path: string): Promise<ApiResponse<any>> {
    return apiRequest(`/containers/${containerId}/directories?path=${encodeURIComponent(path)}`, {
      method: 'POST',
    })
  },

  async rename(containerId: string, oldPath: string, newPath: string): Promise<ApiResponse<any>> {
    return apiRequest(`/containers/${containerId}/files/rename?old_path=${encodeURIComponent(oldPath)}&new_path=${encodeURIComponent(newPath)}`, {
      method: 'POST',
    })
  },
}

export const projectApi = {
  async submit(containerId: string, title: string, description?: string): Promise<ApiResponse<any>> {
    return apiRequest('/projects/submit', {
      method: 'POST',
      body: JSON.stringify({
        container_id: containerId,
        title,
        description,
      }),
    })
  },
}

// Submission API
export const submissionApi = {
  // Submitter endpoints
  createSubmission: (request: CreateSubmissionRequest): Promise<ApiResponse<Submission>> => {
    return apiRequest('/submissions/create', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },

  uploadFiles: (request: SubmitFilesRequest): Promise<ApiResponse<{ message: string }>> => {
    return apiRequest('/submissions/upload-files', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },

  submitForReview: (submissionId: string): Promise<ApiResponse<{ message: string }>> => {
    return apiRequest(`/submissions/submit/${submissionId}`, {
      method: 'POST',
    })
  },

  getMySubmissions: (): Promise<ApiResponse<Submission[]>> => {
    return apiRequest('/submissions/my-submissions')
  },

  getSubmissionDetails: (submissionId: string): Promise<ApiResponse<SubmissionDetail>> => {
    return apiRequest(`/submissions/${submissionId}/details`)
  },

  // Reviewer endpoints
  getSubmissionsForReview: (): Promise<ApiResponse<Submission[]>> => {
    return apiRequest('/submissions/for-review')
  },

  reviewSubmission: (request: ReviewSubmissionRequest): Promise<ApiResponse<{ message: string }>> => {
    return apiRequest('/submissions/review', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },

  getApprovedSubmissions: (): Promise<ApiResponse<any[]>> => {
    return apiRequest('/submissions/approved')
  },

  downloadSubmission: (submissionId: string): Promise<Response> => {
    const token = getAuthToken()
    return fetch(`${API_BASE_URL}/submissions/${submissionId}/download`, {
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    })
  },

  // Admin endpoints
  updateUserRole: (userId: string, role: string): Promise<ApiResponse<{ message: string }>> => {
    return apiRequest(`/submissions/users/${userId}/role`, {
      method: 'POST',
      body: JSON.stringify({ role }),
    })
  },
}
