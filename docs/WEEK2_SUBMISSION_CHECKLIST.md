# Week 2 submission checklist — SourceLens

## Repository

- [x] README complete (what/why/features/stack/setup/API/testing/limitations)
- [x] SECURITY.md complete
- [x] docs/ARCHITECTURE.md, docs/RAG_PIPELINE.md, docs/EVALUATION.md
- [x] LICENSE (MIT)
- [x] .gitignore excludes `.venv`, `node_modules`, `backend/data`
      (Chroma DB + uploads), `.env`, build artifacts
- [x] `.env.example` present with no real values; `.env` confirmed untracked
- [x] No secrets in tracked files (audited — see SECURITY.md)
- [x] `backend/requirements.txt` present and pinned
- [ ] Pushed to a public (or reviewer-accessible) GitHub repository —
      **user action**: this recovery only prepared local commits

## Functionality

- [x] Backend starts (`uvicorn app.main:app`)
- [x] Frontend starts and builds (`npm run dev`, `npm run build`)
- [x] Upload works for PDF, DOCX, TXT, Markdown
- [x] Real embeddings (SentenceTransformer, loaded once)
- [x] Chroma runs without telemetry-error log spam or top-k crashes
- [x] Evidence-sufficiency gate verified against the FIFA World Cup /
      capital-of-Japan style unsupported questions, both in unit tests and
      live in the browser
- [x] Citations sourced from real retrieval metadata (never LLM-invented)
- [x] Delete removes both metadata and vectors (tested end-to-end)
- [x] Prompt-injection defenses tested against a real LLM with real
      injected documents (see docs/EVALUATION.md)
- [x] 35/35 backend tests passing
- [ ] Real LLM provider — **user action**: this build ran against a local
      Ollama instance already present on the dev machine; if submitting
      from different hardware, set `LLM_PROVIDER`/credentials in `.env`

## Evaluation

- [x] 40-question golden benchmark executed (`--retrieval-only` and a real
      partial LLM run — see docs/EVALUATION.md for exact numbers and what
      wasn't fully re-run due to shared-GPU latency)
- [x] 15-case prompt-injection red team executed against the real LLM
- [x] Real metrics recorded with git commit, model, and config metadata —
      no invented numbers

## Demo & submission

- [x] docs/WEEK2_DEMO_SCRIPT.md written (spoken script, ~3–5 min)
- [ ] Screen recording — **user action**: record following the script
- [x] docs/WEEK2_LINKEDIN_POST.md drafted
- [ ] LinkedIn post reviewed and published — **user action**
- [ ] GitHub link and demo video link added to the LinkedIn post —
      **user action**, links don't exist yet
