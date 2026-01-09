import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsStore {
  useMockData: boolean;
  role: 'user' | 'admin';
  setUseMockData: (value: boolean) => void;
  setRole: (role: 'user' | 'admin') => void;
  toggleRole: () => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      useMockData: process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true',
      role: 'user',
      setUseMockData: (value) => set({ useMockData: value }),
      setRole: (role) => set({ role }),
      toggleRole: () => set((state) => ({ role: state.role === 'user' ? 'admin' : 'user' })),
    }),
    {
      name: 'settings-storage',
    }
  )
);
