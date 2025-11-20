import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api/v1', // Proxied to FastAPI via next.config.mjs
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token here later
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);

    // Handle specific error codes
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login (later)
      console.error('Unauthorized');
    }

    return Promise.reject(error);
  }
);
