import type {
  ApiError,
  DocumentListResponse,
  HealthResponse,
  PublicConfig,
  QueryResponse,
  UploadResponse,
} from "../types";

const BASE = import.meta.env.VITE_API_TARGET || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail: ApiError;
    try {
      detail = (await res.json()) as ApiError;
    } catch {
      detail = { error: { code: "unknown", message: res.statusText } };
    }
    throw new ApiErrorResponse(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiErrorResponse extends Error {
  status: number;
  code: string;
  constructor(status: number, detail: ApiError) {
    super(detail.error.message);
    this.status = status;
    this.code = detail.error.code;
    this.name = "ApiErrorResponse";
  }
}

export const api = {
  getHealth: () => request<HealthResponse>("/api/health"),
  getConfig: () => request<PublicConfig>("/api/config/public"),
  listDocuments: () => request<DocumentListResponse>("/api/documents"),
  deleteDocument: (id: string) =>
    request<unknown>(`/api/documents/${id}`, { method: "DELETE" }),
  uploadDocuments: async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));
    return request<UploadResponse>("/api/documents/upload", {
      method: "POST",
      body: form,
    });
  },
  query: (question: string, topK?: number, documentIds?: string[]) =>
    request<QueryResponse>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK, document_ids: documentIds || [] }),
    }),
};
