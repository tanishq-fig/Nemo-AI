import { create } from 'zustand';
import api from '../lib/api';

export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => {
  // Initialize from localStorage
  const token = localStorage.getItem('token');
  
  return {
    user: null,
    token: token,
    isAuthenticated: !!token,
    isLoading: false,
    
    login: async (email: string, password: string) => {
      set({ isLoading: true });
      try {
        const response = await api.post('/auth/login', { email, password });
        const { access_token } = response.data;
        
        localStorage.setItem('token', access_token);
        set({ token: access_token, isAuthenticated: true });
        
        const userResponse = await api.get('/auth/me');
        set({ user: userResponse.data, isLoading: false });
      } catch (error) {
        set({ isLoading: false });
        throw error;
      }
    },
    
    register: async (name: string, email: string, password: string) => {
      set({ isLoading: true });
      try {
        await api.post('/auth/register', { name, email, password });
        
        // Auto-login after registration
        const response = await api.post('/auth/login', { email, password });
        const { access_token } = response.data;
        
        localStorage.setItem('token', access_token);
        set({ token: access_token, isAuthenticated: true });
        
        const userResponse = await api.get('/auth/me');
        set({ user: userResponse.data, isLoading: false });
      } catch (error) {
        set({ isLoading: false });
        throw error;
      }
    },
    
    logout: () => {
      localStorage.removeItem('token');
      set({ user: null, token: null, isAuthenticated: false });
    },
    
    fetchUser: async () => {
      try {
        const response = await api.get('/auth/me');
        set({ user: response.data });
      } catch (error) {
        set({ user: null, token: null, isAuthenticated: false });
        localStorage.removeItem('token');
      }
    },
  };
});
