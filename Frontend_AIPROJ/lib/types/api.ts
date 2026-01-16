// API Types matching backend responses

export interface Document {
  id: string;
  filename: string;
  source: string;
  format: string;
  size?: number;
  created_at: string;
  status: 'success' | 'failed' | 'processing';
  chunk_count: number;
  file_path?: string;
  checksum?: string;
}

export interface DocumentMeta {
  id: string;
  filename: string;
  format: string;
  chunk_count: number;
  ingestion_time_ms?: number;
  source: string;
  created_at: string;
  status: string;
}

export interface DocumentListResponse {
  status: string;
  documents: Document[];
  pagination: {
    total_count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  health_summary: {
    success?: { count: number; total_chunks: number };
    failed?: { count: number };
    processing?: { count: number };
  };
}

export interface SearchResult {
  content: string;
  score: number;
  metadata: {
    filename: string;
    chunk_index: number;
    format: string;
    document_id?: string;
  };
}

export interface Citation {
  chunk: string;
  page?: number;
  source?: string;
}

export interface AnswerMeta {
  mode?: string;
  confidence_top?: number;
  confidence_threshold?: number;
  confidence_decision?: string;
  retrieval_pass?: string;
  top_k_scores?: number[];
  provider?: string;
  latency_ms_retrieval: number;
  latency_ms_llm: number;
  cache_hit: boolean;
  graceful_message?: string;
  degradation_level?: string;
  user_action_hint?: string;
  fallback_reason?: string;
  error_class?: string;
}

export interface AnswerResponse {
  answer: string;
  citations: Citation[];
  used_chunks: number;
  metadata?: AnswerMeta;
}

export interface CSVInsights {
  summary: {
    rows: number;
    columns: number;
    numeric_columns: number;
    categorical_columns: number | null;
    analysis_performed: boolean;
  };
  column_profiles: Record<string, any>;
  data_quality: {
    total_rows: number;
    total_columns: number;
    total_cells: number;
    null_cells: number;
    null_ratio: number;
    duplicate_rows: number;
    duplicate_ratio: number;
    memory_usage_kb: number;
    flags: string[];
  };
  insight_notes: string;
  llm_insights: {
    enabled?: boolean;
    mode?: string;
    summary?: string;
    key_findings?: string[];
    recommendations?: string[];
    dataset_explanation?: string;
    key_patterns?: string[];
    relationships?: string[];
    outliers_and_risks?: string[];
    data_quality_commentary?: string;
  } | null;
  meta: {
    routing: string;
    mode: string;
    source: string | null;
    rows: number;
    columns: number;
    cache_hit: boolean;
    cache_checked: boolean;
    cache_saved: boolean;
    cache_skipped: boolean;
    cache_source: string | null;
    latency_ms_cache_read: number;
    latency_ms_compute: number;
    cache_access_count: number | null;
    cached_at: string | null;
    graceful_message: string | null;
    degradation_level: string;
    user_action_hint: string | null;
    fallback_reason: string | null;
  };
}

export interface ToolExecution {
  iteration: number;
  tool: string;
  arguments: Record<string, any>;
  result: string;
}

export interface AgentMeta {
  decision_route?: string;
  tool_selected?: string;
  iterations: number;
  latency_ms_agent_total: number;
  provider_used?: string;
  fallback_triggered?: boolean;
}

export interface AgentResponse {
  response: string;
  result?: string; // Alias for response
  success: boolean;
  tools_used?: string[]; // List of tools used
  trace?: Array<{
    iteration: number;
    tool_name?: string;
    tool_input?: any;
    tool_output?: string;
    reasoning?: string;
    timestamp?: string;
  }>;
  metadata?: {
    iterations: number;
    execution_time?: number;
    tools_used?: string[];
    model_name?: string;
  };
}

export interface PredictResponse {
  prediction: string;
  probabilities?: Record<string, number>;
  feature_importance?: Record<string, number>;
  metadata?: {
    model_name?: string;
    prediction_time?: number;
    cache_hit?: boolean;
  };
}

export interface SummarizeResponse {
  summary: string;
  key_points?: string[];
  metadata?: {
    mode?: string;
    chunks_used?: number;
    model_name?: string;
    generation_time?: number;
    document_count?: number;
  };
}

export interface ExportResponse {
  success: boolean;
  format: string;
  content: string;
  metadata: Record<string, any>;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  services?: Record<string, {
    status: string;
    response_time?: number;
    version?: string;
    details?: any;
  }>;
}

export interface IngestionHealthResponse {
  total_documents?: number;
  success_rate?: number;
  total_chunks?: number;
  avg_processing_time?: number;
}

// Auth Types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
}

export interface TokenVerifyRequest {
  token: string;
}

export interface TokenVerifyResponse {
  valid: boolean;
  role?: string;
  username?: string;
}

export interface AuthStatusResponse {
  status: string;
  admin_configured: boolean;
  jwt_configured: boolean;
}

// Admin Types
export interface AdminStatsResponse {
  total_documents: number;
  total_chunks: number;
  formats: Record<string, number>;
  statuses: Record<string, number>;
  database_status: string;
  database_error: string | null;
  vector_store_status: string;  llm_configured: boolean;  timestamp: string;
}

export interface DeleteResponse {
  status: string;
  document_id: string;
  filename?: string;
  message: string;
}
