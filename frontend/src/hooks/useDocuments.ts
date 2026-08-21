import { useCallback, useEffect, useState } from "react";
import { api, ApiErrorResponse } from "../services/api";
import type { DocumentInfo, DocumentListResponse, UploadResponse } from "../types";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<
    UploadResponse["errors"] | null
  >(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: DocumentListResponse = await api.listDocuments();
      setDocuments(data.documents);
      setTotalChunks(data.total_chunks);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const upload = useCallback(
    async (files: File[]) => {
      setUploading(true);
      setUploadErrors(null);
      try {
        const res = await api.uploadDocuments(files);
        if (res.errors.length) setUploadErrors(res.errors);
        await refresh();
      } catch (e) {
        // Surface upload failures (e.g. unsupported type) cleanly.
        if (e instanceof ApiErrorResponse) {
          setUploadErrors([{ filename: "upload", code: e.code, message: e.message }]);
        } else {
          setError(e instanceof Error ? e.message : "Upload failed.");
        }
      } finally {
        setUploading(false);
      }
    },
    [refresh]
  );

  const remove = useCallback(
    async (id: string) => {
      try {
        await api.deleteDocument(id);
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Delete failed.");
      }
    },
    [refresh]
  );

  return {
    documents,
    totalChunks,
    loading,
    error,
    uploading,
    uploadErrors,
    refresh,
    upload,
    remove,
  };
}
