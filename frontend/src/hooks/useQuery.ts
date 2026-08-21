import { useCallback, useState } from "react";
import { api, ApiErrorResponse } from "../services/api";
import type { QueryResponse } from "../types";

export interface QueryState {
  response: QueryResponse | null;
  loading: boolean;
  error: string | null;
  errorCode: string | null;
}

export function useQuery() {
  const [state, setState] = useState<QueryState>({
    response: null,
    loading: false,
    error: null,
    errorCode: null,
  });

  const ask = useCallback(async (question: string, topK?: number) => {
    setState({ response: null, loading: true, error: null, errorCode: null });
    try {
      const res = await api.query(question, topK);
      setState({ response: res, loading: false, error: null, errorCode: null });
    } catch (e) {
      const message =
        e instanceof ApiErrorResponse ? e.message : "Query failed.";
      const code = e instanceof ApiErrorResponse ? e.code : null;
      setState({ response: null, loading: false, error: message, errorCode: code });
    }
  }, []);

  return { ...state, ask };
}
