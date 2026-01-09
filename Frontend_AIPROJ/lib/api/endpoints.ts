import apiClient from './client';
import type {
  Document,
  DocumentListResponse,
  DocumentMeta,
  SearchResult,
  AnswerResponse,
  CSVInsights,
  AgentResponse,
  PredictResponse,
  SummarizeResponse,
  ExportResponse,
  HealthResponse,
  IngestionHealthResponse,
  LoginRequest,
  LoginResponse,
  TokenVerifyRequest,
  TokenVerifyResponse,
  AuthStatusResponse,
  AdminStatsResponse,
  DeleteResponse,
} from '../types/api';

// Documents API
export const documentsAPI = {
  upload: async (formData: FormData) => {
    const response = await apiClient.post('/rag/ingest-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  list: async (params: { limit?: number; offset?: number; status?: string }) => {
    const response = await apiClient.get<DocumentListResponse>('/rag/docs/list', { params });
    return response.data;
  },

  getMeta: async (id: string) => {
    const response = await apiClient.get<{ status: string; document: DocumentMeta }>(
      `/rag/docs/${id}/meta`
    );
    return response.data.document;
  },

  preview: async (id: string, maxChunks: number = 5) => {
    const response = await apiClient.get(`/rag/docs/${id}/preview`, {
      params: { max_chunks: maxChunks },
    });
    return response.data;
  },

  checkDuplicate: async (checksum: string) => {
    const response = await apiClient.get(`/rag/docs/checksum/${checksum}`);
    return response.data;
  },

  getFormats: async () => {
    const response = await apiClient.get('/rag/supported-formats');
    return response.data;
  },

  delete: async (id: string) => {
    const response = await apiClient.delete<DeleteResponse>(`/rag/docs/${id}`);
    return response.data;
  },
};

// RAG API
export const ragAPI = {
  query: async (params: { query: string; top_k?: number }) => {
    const response = await apiClient.post<{ results: SearchResult[] }>('/rag/query', params);
    return response.data;
  },

  search: async (query: string, topK: number = 5) => {
    const response = await apiClient.post<{ results: SearchResult[] }>('/rag/query', {
      query,
      top_k: topK,
    });
    return response.data;
  },

  answer: async (params: { query: string; top_k?: number } | string, topK?: number) => {
    const requestBody = typeof params === 'string' 
      ? { question: params, top_k: topK || 5 }
      : { question: params.query, top_k: params.top_k || 5 };
    const response = await apiClient.post<AnswerResponse>('/rag/answer', requestBody);
    return response.data;
  },

  summarize: async (documentId: string, mode: 'auto' | 'extractive' | 'hybrid' = 'auto') => {
    const response = await apiClient.post<SummarizeResponse>('/rag/summarize', {
      document_id: documentId,
      mode,
    });
    return response.data;
  },
};

// Analytics API
export const analyticsAPI = {
  csvInsights: async (documentId: string, llmMode: boolean = false) => {
    const response = await apiClient.get<CSVInsights>(
      `/rag/analytics/csv/${documentId}`,
      {
        params: { llm_insight_mode: llmMode },
      }
    );
    return response.data;
  },

  crossFile: async (documentIds: string[], mode: string = 'extractive') => {
    const response = await apiClient.post('/rag/insights/cross-file', {
      document_ids: documentIds,
      mode,
    });
    return response.data;
  },

  aggregate: async (documentIds: string[], mode: string = 'auto', maxChunks: number = 5) => {
    const response = await apiClient.post('/rag/insights/aggregate', {
      document_ids: documentIds,
      mode,
      max_chunks: maxChunks,
    });
    return response.data;
  },
};

// Summarization API
export const summarizeAPI = {
  document: async (params: {
    document_id: string;
    mode: 'auto' | 'extractive' | 'hybrid';
    max_chunks?: number;
    summary_length?: 'short' | 'medium' | 'detailed';
  }) => {
    const response = await apiClient.post<SummarizeResponse>('/rag/summarize', params);
    return response.data;
  },
};

// Agent API
export const agentAPI = {
  run: async (prompt: string, maxIterations: number = 5, verbose: boolean = true) => {
    const response = await apiClient.post<AgentResponse>(
      `/agent/run?verbose=${verbose}`,
      {
        prompt,
        max_iterations: maxIterations,
      }
    );
    return response.data;
  },

  tools: async () => {
    const response = await apiClient.get('/agent/tools');
    return response.data;
  },

  getTools: async () => {
    const response = await apiClient.get('/agent/tools');
    return response.data;
  },
};

// ML API
export const mlAPI = {
  predict: async (features: number[]) => {
    const response = await apiClient.post<PredictResponse>('/ml/predict', { features });
    return response.data;
  },
};

// Export API
export const exportAPI = {
  report: async (params: {
    payload_source: string;
    payload: any;
    format: 'md' | 'pdf';
    filename: string;
  }) => {
    const response = await apiClient.post<ExportResponse>('/export/report', params);
    return response.data;
  },

  capabilities: async () => {
    const response = await apiClient.get('/export/capabilities');
    return response.data;
  },
};

// Health API
export const healthAPI = {
  system: async () => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  ingestion: async () => {
    const response = await apiClient.get<IngestionHealthResponse>('/rag/docs/health');
    return response.data;
  },
};

// Auth API
export const authAPI = {
  login: async (credentials: LoginRequest) => {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  verify: async (token: string) => {
    const response = await apiClient.post<TokenVerifyResponse>('/auth/verify', { token });
    return response.data;
  },

  status: async () => {
    const response = await apiClient.get<AuthStatusResponse>('/auth/status');
    return response.data;
  },
};

// Admin API
export const adminAPI = {
  stats: async () => {
    const response = await apiClient.get<AdminStatsResponse>('/rag/admin/stats');
    return response.data;
  },
};
