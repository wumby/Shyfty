import { create } from 'zustand';

import { api } from '../services/api';
import type { User } from '../types';

type AuthMode = 'signin' | 'signup';

interface AuthStore {
  currentUser: User | null;
  authLoading: boolean;
  authPanelOpen: boolean;
  authMode: AuthMode;
  authError: string | null;
  refreshSession: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  openAuth: (mode?: AuthMode) => void;
  setAuthMode: (mode: AuthMode) => void;
  closeAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  currentUser: null,
  authLoading: false,
  authPanelOpen: false,
  authMode: 'signin',
  authError: null,
  refreshSession: async () => {
    set({ authLoading: true });
    try {
      const session = await api.getSession();
      set({ currentUser: session.user, authLoading: false, authError: null });
    } catch {
      set({ currentUser: null, authLoading: false });
    }
  },
  signIn: async (email, password) => {
    set({ authLoading: true, authError: null });
    try {
      const session = await api.signIn(email, password);
      set({ currentUser: session.user, authLoading: false, authPanelOpen: false });
    } catch (error) {
      set({ authLoading: false, authError: error instanceof Error ? error.message : 'Sign in failed.' });
      throw error;
    }
  },
  signUp: async (email, password) => {
    set({ authLoading: true, authError: null });
    try {
      const session = await api.signUp(email, password);
      set({ currentUser: session.user, authLoading: false, authPanelOpen: false });
    } catch (error) {
      set({ authLoading: false, authError: error instanceof Error ? error.message : 'Sign up failed.' });
      throw error;
    }
  },
  signOut: async () => {
    await api.signOut();
    set({ currentUser: null, authError: null, authPanelOpen: false });
  },
  openAuth: (mode = 'signin') => set({ authPanelOpen: true, authMode: mode, authError: null }),
  setAuthMode: (mode) => set({ authMode: mode, authError: null }),
  closeAuth: () => set({ authPanelOpen: false, authError: null }),
}));
