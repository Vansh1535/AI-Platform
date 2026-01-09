import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: any[];
  metadata?: any;
}

interface ChatStore {
  messages: Message[];
  addMessage: (message: Omit<Message, 'id'>) => void;
  clearMessages: () => void;
  updateLastMessage: (updates: Partial<Message>) => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      messages: [],
      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: Date.now().toString(),
              timestamp: message.timestamp || new Date().toISOString(),
            },
          ],
        })),
      clearMessages: () => set({ messages: [] }),
      updateLastMessage: (updates) =>
        set((state) => ({
          messages: state.messages.map((msg, idx) =>
            idx === state.messages.length - 1 ? { ...msg, ...updates } : msg
          ),
        })),
    }),
    {
      name: 'chat-storage',
    }
  )
);
