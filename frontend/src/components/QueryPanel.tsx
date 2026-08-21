import { useState } from "react";
import type { PublicConfig, QueryResponse } from "../types";
import { AnswerView } from "./AnswerView";

interface QueryPanelProps {
  onAsk: (question: string, topK?: number) => void;
  response: QueryResponse | null;
  loading: boolean;
  error: string | null;
  errorCode: string | null;
  config: PublicConfig | null;
  hasDocuments: boolean;
}

const EXAMPLES = [
  "How many remote work days are employees permitted?",
  "How quickly must a security incident be reported?",
  "How many paid vacation days do employees receive?",
  "Who won the FIFA World Cup in 2018?",
];

export function QueryPanel({
  onAsk,
  response,
  loading,
  error,
  errorCode,
  config,
  hasDocuments,
}: QueryPanelProps) {
  const [question, setQuestion] = useState("");
  const maxLen = config?.max_query_length ?? 2000;

  const submit = () => {
    const q = question.trim();
    if (!q || loading) return;
    onAsk(q);
  };

  return (
    <section className="sl-panel sl-query" aria-label="Ask SourceLens">
      <div className="sl-panel-head">
        <h2>Ask SourceLens</h2>
      </div>

      <label className="sl-visually-hidden" htmlFor="sl-question">
        Your question
      </label>
      <textarea
        id="sl-question"
        className="sl-question-input"
        placeholder="Ask a question about your indexed documents…"
        value={question}
        maxLength={maxLen}
        rows={3}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            submit();
          }
        }}
      />

      <div className="sl-query-actions">
        <button
          type="button"
          className="sl-btn primary"
          onClick={submit}
          disabled={loading || !question.trim() || !hasDocuments}
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
        <span className="sl-muted">
          {question.length}/{maxLen}
        </span>
      </div>

      {!hasDocuments && (
        <p className="sl-warn" role="alert">
          Upload at least one document before asking questions.
        </p>
      )}

      {error && errorCode === "llm_not_configured" && (
        <div className="sl-answer sl-answer-llm-missing" role="alert">
          <div className="sl-answer-badge llm-missing">LLM not configured</div>
          <p className="sl-answer-text">{error}</p>
          <p className="sl-muted">
            Retrieval and the evidence gate work without an LLM - set
            LLM_PROVIDER (and its credentials) in the backend's .env to get
            generated answers.
          </p>
        </div>
      )}

      {error && errorCode !== "llm_not_configured" && (
        <div className="sl-answer sl-answer-error" role="alert">
          <div className="sl-answer-badge error">System error</div>
          <p className="sl-answer-text">{error}</p>
        </div>
      )}

      {!response && !loading && !error && (
        <div className="sl-empty">
          <p>Ask SourceLens a question about your indexed documents.</p>
          {hasDocuments && (
            <div className="sl-examples">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  className="sl-chip"
                  onClick={() => setQuestion(ex)}
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="sl-answer sl-answer-loading" aria-live="polite">
          <div className="sl-thinking">SourceLens is reviewing the evidence…</div>
        </div>
      )}

      {response && !loading && <AnswerView response={response} />}
    </section>
  );
}
