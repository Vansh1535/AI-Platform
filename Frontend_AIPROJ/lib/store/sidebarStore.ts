import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SidebarState {
  collapsed: boolean;
  mobileOpen: boolean;
  toggleCollapsed: () => void;
  setCollapsed: (collapsed: boolean) => void;
  toggleMobileOpen: () => void;
  setMobileOpen: (open: boolean) => void;
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      collapsed: false,
      mobileOpen: false,
      toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),
      setCollapsed: (collapsed) => set({ collapsed }),
      toggleMobileOpen: () => set((state) => ({ mobileOpen: !state.mobileOpen })),
      setMobileOpen: (open) => set({ mobileOpen: open }),
    }),
    {
      name: 'sidebar-storage',
      partialize: (state) => ({ collapsed: state.collapsed }),
    }
  )
);
