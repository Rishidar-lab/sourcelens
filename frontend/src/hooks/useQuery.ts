import { useCallback, useState } from "react";
import { api, ApiErrorResponse } from "../services/api";
import type { QueryResponse } from "../types";

export interface QueryState {
  response: QueryResponse | null;
  loading: boolean;
  error: string | null;
}

export function useQuery() {
  const [state, setState] = useState<QueryState>({
    response: null,
    loading: false,
    error: null,
  });

  const ask = useCallback(async (question: string, topK?: number) => {
    setState({ response: null, loading: true, error: null });
    try {
      const res = await api.query(question, topK);
      setState({ response: res, loading: false, error: null });
    } catch (e) {
      const message =
        e instanceof ApiErrorResponse ? e.message : "Query failed.";
      setState({ response: null, loading: false, error: message });
    }
  }, []);

  return { ...state, ask };
}
