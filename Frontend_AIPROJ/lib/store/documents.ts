import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Document } from '../types/api';

interface DocumentsStore {
  documents: Document[];
  selectedDocument: Document | null;
  setDocuments: (documents: Document[]) => void;
  addDocument: (document: Document) => void;
  setSelectedDocument: (document: Document | null) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
}

export const useDocumentsStore = create<DocumentsStore>()(
  persist(
    (set) => ({
      documents: [],
      selectedDocument: null,
      setDocuments: (documents) => set({ documents }),
      addDocument: (document) =>
        set((state) => ({ documents: [document, ...state.documents] })),
      setSelectedDocument: (document) => set({ selectedDocument: document }),
      updateDocument: (id, updates) =>
        set((state) => ({
          documents: state.documents.map((doc) =>
            doc.id === id ? { ...doc, ...updates } : doc
          ),
        })),
    }),
    {
      name: 'documents-storage',
    }
  )
);
