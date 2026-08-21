export interface HealthResponse {
  status: string;
  app: string;
  embedding_model: string;
  embedding_loaded: boolean;
  vector_store: string;
  llm_configured: boolean;
  llm_provider: string | null;
  documents_indexed: number;
  chunks_indexed: number;
  version: string;
}

export interface PublicConfig {
  llm_provider: string | null;
  llm_configured: boolean;
  embedding_model: string;
  embedding_dim: number;
  rag_top_k: number;
  rag_min_relevance_score: number;
  accepted_extensions: string[];
  max_upload_mb: number;
  max_files_per_upload: number;
  max_query_length: number;
  app_env: string;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  chunk_count: number;
  status: string;
  created_at: string;
  error: string | null;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
  total_documents: number;
  total_chunks: number;
}

export interface UploadResult extends DocumentInfo {}

export interface UploadResponse {
  uploaded: number;
  results: UploadResult[];
  errors: Array<{ filename: string; code: string; message: string }>;
}

export interface Source {
  source_number: number;
  filename: string;
  page: number | null;
  chunk_id: string;
  excerpt: string;
  score: number;
}

export interface QueryResponse {
  answer: string;
  grounded: boolean;
  refusal_reason: string | null;
  sources: Source[];
  retrieval: {
    chunks_considered: number;
    best_score: number;
    filtered_out: number;
    expanded: number;
    top_k: number;
    latency_ms: number;
    provider?: string;
    model?: string;
  };
  request_id: string;
}

export interface ApiError {
  error: { code: string; message: string };
}
