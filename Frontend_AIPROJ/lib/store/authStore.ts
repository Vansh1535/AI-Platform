import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authAPI } from '../api/endpoints';
import type { LoginRequest } from '../types/api';

interface AuthState {
  token: string | null;
  role: string | null;
  username: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  verifyToken: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      role: null,
      username: null,
      isAuthenticated: false,
      isAdmin: false,

      login: async (credentials: LoginRequest) => {
        try {
          const response = await authAPI.login(credentials);
          set({
            token: response.access_token,
            role: response.role,
            username: response.username,
            isAuthenticated: true,
            isAdmin: response.role === 'admin',
          });
        } catch (error) {
          console.error('Login failed:', error);
          throw error;
        }
      },

      logout: () => {
        set({
          token: null,
          role: null,
          username: null,
          isAuthenticated: false,
          isAdmin: false,
        });
      },

      verifyToken: async () => {
        const { token } = get();
        if (!token) {
          set({ isAuthenticated: false, isAdmin: false });
          return false;
        }

        try {
          const response = await authAPI.verify(token);
          if (response.valid) {
            set({
              isAuthenticated: true,
              isAdmin: response.role === 'admin',
              role: response.role,
              username: response.username,
            });
            return true;
          } else {
            get().logout();
            return false;
          }
        } catch (error) {
          get().logout();
          return false;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        role: state.role,
        username: state.username,
        isAuthenticated: state.isAuthenticated,
        isAdmin: state.isAdmin,
      }),
    }
  )
);
