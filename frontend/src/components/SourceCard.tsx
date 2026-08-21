import { useState } from "react";
import type { Source } from "../types";

interface SourceCardProps {
  source: Source;
}

export function SourceCard({ source }: SourceCardProps) {
  const [open, setOpen] = useState(false);
  const pageLabel =
    source.page && source.page > 0 ? `Page ${source.page}` : "Page unknown";

  return (
    <li className="sl-source-card">
      <button
        type="button"
        className="sl-source-head"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="sl-source-num">{source.source_number}</span>
        <span className="sl-source-file">{source.filename}</span>
        <span className="sl-source-page">{pageLabel}</span>
        <span className="sl-source-score" title="Retrieval relevance score">
          {Math.round(source.score * 100)}%
        </span>
        <span className="sl-source-chevron" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <blockquote className="sl-source-excerpt">{source.excerpt}</blockquote>
      )}
    </li>
  );
}
