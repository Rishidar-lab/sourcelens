import { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { KnowledgeBasePanel } from "../components/KnowledgeBasePanel";
import { QueryPanel } from "../components/QueryPanel";
import { api } from "../services/api";
import { useDocuments } from "../hooks/useDocuments";
import { useQuery } from "../hooks/useQuery";
import type { HealthResponse, PublicConfig } from "../types";

export function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const docs = useDocuments();
  const query = useQuery();

  useEffect(() => {
    let active = true;
    Promise.all([api.getHealth(), api.getConfig()])
      .then(([h, c]) => {
        if (!active) return;
        setHealth(h);
        setConfig(c);
      })
      .catch(() => {
        /* health is optional; UI degrades gracefully */
      })
      .finally(() => active && setStatusLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="sl-app">
      <Header health={health} config={config} loading={statusLoading} />
      <main className="sl-layout">
        <KnowledgeBasePanel
          documents={docs.documents}
          totalChunks={docs.totalChunks}
          loading={docs.loading}
          uploading={docs.uploading}
          uploadErrors={docs.uploadErrors}
          config={config}
          onUpload={docs.upload}
          onDelete={docs.remove}
        />
        <QueryPanel
          onAsk={query.ask}
          response={query.response}
          loading={query.loading}
          error={query.error}
          config={config}
          hasDocuments={docs.documents.length > 0}
        />
      </main>
    </div>
  );
}
