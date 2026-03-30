/**
 * API Configuration for AWS Amplify Deployment
 * Centralized API URL management with fallback handling
 */

export const API_CONFIG = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || '',
  timeout: 30000, // 30 seconds
} as const;

/**
 * Get API URL with validation
 * @throws Error if API URL is not configured
 */
export function getApiUrl(): string {
  const url = API_CONFIG.baseURL;
  
  if (!url) {
    console.error('NEXT_PUBLIC_API_URL is not configured');
    throw new Error('API URL not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
  }
  
  return url;
}

/**
 * Create fetch options with default headers
 */
export function createFetchOptions(
  token?: string,
  options?: RequestInit
): RequestInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...(options?.headers || {}),
  };

  return {
    ...options,
    headers,
  };
}

/**
 * Fetch with automatic error handling
 */
export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${getApiUrl()}${endpoint}`;
  
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Fetch Error (${endpoint}):`, error);
    throw error;
  }
}
