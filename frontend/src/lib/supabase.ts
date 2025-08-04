import { createClient, SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'http://localhost:8000'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'your-anon-key'

// Create Supabase client with automatic silent token refresh
export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Enable automatic token refresh (happens silently in background)
    autoRefreshToken: true,
    // Persist session in localStorage
    persistSession: true,
    // Detect session from URL (for OAuth flows)
    detectSessionInUrl: true,
    // Storage key for session data
    storageKey: 'supabase.auth.token',
    // Refresh tokens when they're 30 seconds from expiry (default is 10 seconds)
    // This gives more buffer time and reduces refresh frequency
    refreshTokenRotationEnabled: true,
    // Flow type for better security
    flowType: 'pkce',
    // Custom storage implementation for better control
    storage: {
      getItem: (key: string) => {
        if (typeof window !== 'undefined') {
          return window.localStorage.getItem(key)
        }
        return null
      },
      setItem: (key: string, value: string) => {
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, value)
        }
      },
      removeItem: (key: string) => {
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem(key)
        }
      },
    },
  },
})

// Session change event types
export type SessionChangeEvent = 'SIGNED_IN' | 'SIGNED_OUT' | 'TOKEN_REFRESHED' | 'USER_UPDATED'

// Helper function to get current session
export const getCurrentSession = () => {
  return supabase.auth.getSession()
}

// Helper function to get current user
export const getCurrentUser = () => {
  return supabase.auth.getUser()
}

// Helper function to sign out
export const signOut = () => {
  return supabase.auth.signOut()
}

// Helper function to sign in with password
export const signInWithPassword = (email: string, password: string) => {
  return supabase.auth.signInWithPassword({ email, password })
}

// Helper function to sign up
export const signUp = (email: string, password: string, options?: { data?: { full_name?: string } }) => {
  return supabase.auth.signUp({ email, password, options })
}

// Helper function to refresh session manually (usually not needed due to auto-refresh)
export const refreshSession = () => {
  return supabase.auth.refreshSession()
}

// Helper function to check if we have a valid session
export const hasValidSession = async () => {
  try {
    const { data: { session }, error } = await supabase.auth.getSession()
    return !error && session && session.access_token
  } catch {
    return false
  }
}