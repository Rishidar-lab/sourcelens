import { useCallback, useRef, useState } from "react";
import type { PublicConfig } from "../types";

interface UploadDropzoneProps {
  onFiles: (files: File[]) => void;
  uploading: boolean;
  config: PublicConfig | null;
}

function humanSize(mb: number): string {
  return `${mb} MB`;
}

export function UploadDropzone({ onFiles, uploading, config }: UploadDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const accepted = config?.accepted_extensions?.join(",") ?? ".pdf,.docx,.txt,.md";
  const maxFiles = config?.max_files_per_upload ?? 10;
  const maxBytes = (config?.max_upload_mb ?? 20) * 1024 * 1024;

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      setLocalError(null);
      const files = Array.from(fileList);
      if (files.length > maxFiles) {
        setLocalError(`You can upload at most ${maxFiles} files at once.`);
        return;
      }
      const tooLarge = files.filter((f) => f.size > maxBytes);
      if (tooLarge.length) {
        setLocalError(
          `Some files exceed the ${humanSize(config?.max_upload_mb ?? 20)} limit.`
        );
        return;
      }
      onFiles(files);
    },
    [maxFiles, maxBytes, onFiles, config]
  );

  return (
    <div
      className={`sl-dropzone ${dragging ? "dragging" : ""} ${
        uploading ? "busy" : ""
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      role="button"
      tabIndex={0}
      aria-label="Upload documents by dragging files here or activating to browse"
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accepted}
        className="sl-hidden-input"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={uploading}
      />
      <div className="sl-dropzone-icon" aria-hidden="true">
        ⬆
      </div>
      <p className="sl-dropzone-title">
        {uploading ? "Indexing documents…" : "Drop files or click to upload"}
      </p>
      <p className="sl-dropzone-hint">
        PDF, DOCX, TXT, Markdown · up to {maxFiles} files · {humanSize(
          config?.max_upload_mb ?? 20
        )}{" "}
        each
      </p>
      {localError && (
        <p className="sl-dropzone-error" role="alert">
          {localError}
        </p>
      )}
    </div>
  );
}
