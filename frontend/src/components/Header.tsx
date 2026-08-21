import type { HealthResponse, PublicConfig } from "../types";

interface HeaderProps {
  health: HealthResponse | null;
  config: PublicConfig | null;
  loading: boolean;
}

export function Header({ health, config, loading }: HeaderProps) {
  const llm = health?.llm_configured
    ? `LLM: ${health.llm_provider ?? "configured"}`
    : "LLM: not configured";
  const docs = health ? `${health.documents_indexed} docs` : "—";
  const chunks = health ? `${health.chunks_indexed} chunks` : "—";

  return (
    <header className="sl-header">
      <div className="sl-brand">
        <div className="sl-logo" aria-hidden="true">
          SL
        </div>
        <div>
          <h1>SourceLens</h1>
          <p className="sl-tagline">Evidence-grounded answers from your documents</p>
        </div>
      </div>
      <div className="sl-status" aria-live="polite">
        <span className={`sl-pill ${health ? "ok" : "warn"}`}>
          {loading ? "Connecting…" : health ? "System online" : "Offline"}
        </span>
        <span className="sl-pill subtle">{docs}</span>
        <span className="sl-pill subtle">{chunks}</span>
        <span
          className={`sl-pill ${health?.llm_configured ? "ok" : "warn"}`}
        >
          {llm}
        </span>
        {config && (
          <span className="sl-pill subtle" title={config.embedding_model}>
            {config.embedding_model}
          </span>
        )}
      </div>
    </header>
  );
}
