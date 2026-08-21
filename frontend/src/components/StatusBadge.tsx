interface StatusBadgeProps {
  status: string;
}

const LABELS: Record<string, string> = {
  indexed: "Indexed",
  failed: "Failed",
  uploading: "Uploading",
  extracting: "Extracting",
  chunking: "Chunking",
  embedding: "Embedding",
  pending: "Pending",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const cls = status === "indexed" ? "ok" : status === "failed" ? "bad" : "warn";
  return (
    <span className={`sl-statusdot ${cls}`} data-status={status}>
      {LABELS[status] ?? status}
    </span>
  );
}
