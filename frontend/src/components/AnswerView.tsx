import type { QueryResponse } from "../types";
import { SourceCard } from "./SourceCard";

interface AnswerViewProps {
  response: QueryResponse;
}

export function AnswerView({ response }: AnswerViewProps) {
  const { grounded, answer, refusal_reason, sources, retrieval } = response;

  if (!grounded) {
    return (
      <div className="sl-answer sl-answer-refusal" role="status">
        <div className="sl-answer-badge refusal">Insufficient evidence</div>
        <p className="sl-answer-text">{answer}</p>
        {refusal_reason && (
          <p className="sl-muted">
            SourceLens only answers from the documents you uploaded.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="sl-answer sl-answer-grounded">
      <div className="sl-answer-badge grounded">Grounded answer</div>
      <p className="sl-answer-text">{answer}</p>

      <div className="sl-sources">
        <h3 className="sl-sources-title">
          Sources
          <span className="sl-muted">
            {" "}
            · {sources.length} citation{sources.length === 1 ? "" : "s"}
          </span>
        </h3>
        {sources.length === 0 ? (
          <p className="sl-muted">No citations were returned.</p>
        ) : (
          <ol className="sl-source-list">
            {sources.map((s) => (
              <SourceCard key={s.chunk_id} source={s} />
            ))}
          </ol>
        )}
      </div>

      <p className="sl-retrieval-meta sl-muted">
        Considered {retrieval.chunks_considered} chunks · top relevance{" "}
        {Math.round(retrieval.best_score * 100)}% · {retrieval.latency_ms} ms
        {retrieval.model ? ` · ${retrieval.model}` : ""}
      </p>
    </div>
  );
}
