import type { 
  ApiResponse, 
  AuthResponse, 
  User, 
  ContainerResponse, 
  ContainerCreateRequest,
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
  localStorage.removeItem('refresh_token')
  // Clear any scheduled refresh when removing tokens
  clearRefreshTimer()
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token')
}

export function setRefreshToken(token: string): void {
  localStorage.setItem('refresh_token', token)
}

// JWT token utilities
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const currentTime = Math.floor(Date.now() / 1000)
    return payload.exp < currentTime
  } catch {
    return true // Invalid token format
  }
}

function getTokenExpirationTime(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 // Convert to milliseconds
  } catch {
    return null
  }
}

// Global auth state handler - will be set by the app store
let onTokenExpired: (() => void) | null = null

// Token refresh scheduling
let refreshTimer: NodeJS.Timeout | null = null
let refreshPromise: Promise<boolean> | null = null

export function setTokenExpirationHandler(handler: () => void) {
  onTokenExpired = handler
}

// Token refresh scheduling functions
function scheduleTokenRefresh(token: string): void {
  // Clear any existing timer
  clearRefreshTimer()
  
  const expirationTime = getTokenExpirationTime(token)
  if (!expirationTime) {
    console.warn('⚠️ Cannot schedule refresh: invalid token')
    return
  }
  
  const currentTime = Date.now()
  const timeUntilExpiry = expirationTime - currentTime
  
  // Schedule refresh 5 minutes before expiry (or immediately if less than 5 minutes left)
  const REFRESH_BUFFER = 5 * 60 * 1000 // 5 minutes in milliseconds
  const refreshTime = Math.max(timeUntilExpiry - REFRESH_BUFFER, 1000) // At least 1 second delay
  
  console.log(`⏰ Scheduling token refresh in ${Math.round(refreshTime / 1000)} seconds`)
  
  refreshTimer = setTimeout(async () => {
    console.log('🔄 Periodic token refresh triggered')
    const success = await refreshAccessToken()
    if (!success && onTokenExpired) {
      console.log('❌ Periodic refresh failed, triggering logout')
      onTokenExpired()
    }
  }, refreshTime)
}

function clearRefreshTimer(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer)
    refreshTimer = null
    console.log('🧹 Refresh timer cleared')
  }
}

// Export timer management functions for external use
export function startTokenRefreshScheduling(): void {
  const token = getAuthToken()
  if (token && !isTokenExpired(token)) {
    scheduleTokenRefresh(token)
  }
}

export function stopTokenRefreshScheduling(): void {
  clearRefreshTimer()
}

async function apiRequest<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  let token = getAuthToken()
  
  // Check token expiration before making request
  if (token && isTokenExpired(token)) {
    // Try to refresh the token first
    const refreshSuccess = await refreshAccessToken()
    if (!refreshSuccess) {
      if (onTokenExpired) {
        onTokenExpired()
      }
      return {
        success: false,
        error: 'Session expired. Please log in again.',
      }
    }
    // Update token for this request
    token = getAuthToken()
  }
  
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
      // Handle 401 Unauthorized responses
      if (response.status === 401) {
        // Try to refresh token on 401 error
        const refreshSuccess = await refreshAccessToken()
        if (refreshSuccess) {
          // Retry the original request with new token
          const retryConfig = {
            ...config,
            headers: {
              ...config.headers,
              Authorization: `Bearer ${getAuthToken()}`,
            },
          }
          const retryResponse = await fetch(`${API_BASE_URL}${endpoint}`, retryConfig)
          const retryData = await retryResponse.json()
          
          if (retryResponse.ok) {
            return { success: true, data: retryData }
          }
        }
        
        // If refresh fails or retry fails, logout user
        if (onTokenExpired) {
          onTokenExpired()
        }
        return {
          success: false,
          error: 'Session expired. Please log in again.',
        }
      }
      
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

// Token refresh functionality with race condition protection
async function refreshAccessToken(): Promise<boolean> {
  // If there's already a refresh in progress, wait for it
  if (refreshPromise) {
    console.log('🔄 Refresh already in progress, waiting...')
    return refreshPromise
  }

  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    console.log('❌ No refresh token available')
    return false
  }

  console.log('🔄 Starting token refresh...')
  refreshPromise = performTokenRefresh(refreshToken)
  
  try {
    const result = await refreshPromise
    return result
  } finally {
    refreshPromise = null
  }
}

async function performTokenRefresh(refreshToken: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (response.ok) {
      const data = await response.json()
      if (data.access_token) {
        setAuthToken(data.access_token)
        if (data.refresh_token) {
          setRefreshToken(data.refresh_token)
        }
        
        // Schedule the next refresh
        scheduleTokenRefresh(data.access_token)
        console.log('✅ Token refreshed successfully')
        return true
      }
    } else {
      console.error('❌ Token refresh failed:', response.status, response.statusText)
    }
  } catch (error) {
    console.error('❌ Token refresh error:', error)
  }

  // If refresh fails, clear tokens and stop scheduling
  console.log('🧹 Clearing tokens due to refresh failure')
  removeAuthToken()
  clearRefreshTimer()
  return false
}

export const authApi = {
  async login(email: string, password: string): Promise<ApiResponse<AuthResponse>> {
    const response = await apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    
    if (response.success && response.data?.access_token) {
      setAuthToken(response.data.access_token)
      if (response.data.refresh_token) {
        setRefreshToken(response.data.refresh_token)
      }
      
      // Start periodic refresh scheduling
      scheduleTokenRefresh(response.data.access_token)
    }
    
    return response
  },

  async refreshToken(): Promise<ApiResponse<AuthResponse>> {
    const success = await refreshAccessToken()
    if (success) {
      return { 
        success: true, 
        data: { 
          access_token: getAuthToken()!, 
          user: { id: '', email: '' } // This will be populated by the actual refresh endpoint
        } 
      }
    } else {
      return { success: false, error: 'Failed to refresh token' }
    }
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
    // Stop refresh scheduling before logout
    stopTokenRefreshScheduling()
    
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


}

export const projectApi = {
  // Project API methods can be added here as needed
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
