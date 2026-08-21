import type { DocumentInfo, PublicConfig } from "../types";
import { DocumentCard } from "./DocumentCard";
import { UploadDropzone } from "./UploadDropzone";

interface KnowledgeBasePanelProps {
  documents: DocumentInfo[];
  totalChunks: number;
  loading: boolean;
  uploading: boolean;
  uploadErrors: Array<{ filename: string; code: string; message: string }> | null;
  config: PublicConfig | null;
  onUpload: (files: File[]) => void;
  onDelete: (id: string) => void;
}

export function KnowledgeBasePanel({
  documents,
  totalChunks,
  loading,
  uploading,
  uploadErrors,
  config,
  onUpload,
  onDelete,
}: KnowledgeBasePanelProps) {
  return (
    <section className="sl-panel sl-kb" aria-label="Knowledge base">
      <div className="sl-panel-head">
        <h2>Knowledge Base</h2>
        <span className="sl-count">
          {documents.length} docs · {totalChunks} chunks
        </span>
      </div>

      <UploadDropzone onFiles={onUpload} uploading={uploading} config={config} />

      {uploadErrors && uploadErrors.length > 0 && (
        <ul className="sl-upload-errors" role="alert">
          {uploadErrors.map((e, i) => (
            <li key={i}>
              <strong>{e.filename}</strong>: {e.message}
            </li>
          ))}
        </ul>
      )}

      {loading ? (
        <p className="sl-muted">Loading documents…</p>
      ) : documents.length === 0 ? (
        <div className="sl-empty">
          <p>No documents yet.</p>
          <p className="sl-muted">
            Upload documents to create your knowledge base.
          </p>
        </div>
      ) : (
        <ul className="sl-doc-list">
          {documents.map((doc) => (
            <DocumentCard key={doc.document_id} doc={doc} onDelete={onDelete} />
          ))}
        </ul>
      )}
    </section>
  );
}
