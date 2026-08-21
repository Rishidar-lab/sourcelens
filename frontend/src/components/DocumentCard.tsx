import type { DocumentInfo } from "../types";
import { StatusBadge } from "./StatusBadge";

interface DocumentCardProps {
  doc: DocumentInfo;
  onDelete: (id: string) => void;
}

function extLabel(filename: string): string {
  const ext = filename.split(".").pop()?.toUpperCase() ?? "";
  return ext || "FILE";
}

function humanBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentCard({ doc, onDelete }: DocumentCardProps) {
  return (
    <li className="sl-doc-card">
      <div className="sl-doc-icon" aria-hidden="true">
        {extLabel(doc.filename)}
      </div>
      <div className="sl-doc-body">
        <div className="sl-doc-row">
          <span className="sl-doc-name" title={doc.filename}>
            {doc.filename}
          </span>
          <StatusBadge status={doc.status} />
        </div>
        <div className="sl-doc-meta">
          <span>{humanBytes(doc.size_bytes)}</span>
          <span>·</span>
          <span>
            {doc.chunk_count} {doc.chunk_count === 1 ? "chunk" : "chunks"}
          </span>
        </div>
        {doc.error && <p className="sl-doc-error">{doc.error}</p>}
      </div>
      <button
        type="button"
        className="sl-icon-btn"
        aria-label={`Delete ${doc.filename}`}
        title="Delete document"
        onClick={() => onDelete(doc.document_id)}
      >
        ✕
      </button>
    </li>
  );
}
