# Week 2 recording execution — submission-safe fallback

**Status of this document: a prepared runbook, not a record of a completed
recording.** No video has been recorded yet. This exists because three real,
independent attempts to record the supported hero query against the live
local LLM all failed identically — retrieval succeeded every time (top
score 0.749), the evidence gate correctly passed it to generation every
time, and Ollama's actual token generation exhausted the 180s timeout every
time, under sustained 100% GPU compute contention from another process on
this shared dev machine. That is an infrastructure ceiling on this specific
machine today, not a demonstrated defect in SourceLens. Full evidence is in
the session record; it is not repeated here.

This runbook builds a **truthful ~100s recording** around what is actually,
currently, live-verifiable — the corpus, the evidence gate, and the refusal
path — plus **clearly labeled prior verified evidence** (already-committed
screenshots and already-completed benchmark runs) for the grounded-answer
and citation behavior that could not be re-demonstrated live today. Nothing
here is fabricated. Nothing here presents today's failed generation as a
success.

## What is live vs. what is prior evidence

| Segment | Content | Status |
|---|---|---|
| Landing / indexed corpus | Real running app, `localhost:5173` | **LIVE**, recordable right now |
| Grounded-answer + citation example | `qa/runs/full_llm_run.json`, question `QA-005` | **PRIOR VERIFIED** — completed 2026-08-22, commit `3593ae6`, not re-run today |
| Retrieval-quality metrics | `docs/EVALUATION.md` (94.12% / 97.06% / 97.06% / MRR 0.956) | **PRIOR VERIFIED** — committed, pushed |
| Unsupported-query refusal | Real running app, live `POST /api/query` | **LIVE**, deterministic, ~0.2s, no LLM call |
| Architecture closing beat | Narration only, no new screen | — |

The recording must visually and verbally distinguish these two categories —
see narration below, which does this explicitly rather than letting a viewer
assume everything shown happened in one continuous live session.

## Pre-recording state (already verified, do not repeat)

- Backend: `uvicorn app.main:app --port 8000`, running, `/api/health` →
  `documents_indexed: 7, chunks_indexed: 32`.
- Frontend: `npm run dev`, Vite, `localhost:5173`.
- Corpus: the same 7-document synthetic set, already indexed, unchanged
  since the original rehearsal. **Do not re-upload, do not delete/reset.**
- Do not run the supported hero query again today. Do not restart Ollama.
  Do not touch GPU processes. Engineering remains frozen at the pushed
  commit.

## Environment constraint (read before recording)

This machine's current session is a **tty, no X11/Wayland desktop**
(`XDG_SESSION_TYPE=tty`). There is no live GUI screen to point a
traditional desktop recorder (OBS, `ffmpeg -f x11grab`, etc.) at from here.
Two ways to actually produce the MP4:

**Option A — automated capture from this environment (recommended, provable
end-to-end right now):** drive the real app through Playwright with
`record_video_dir` / `record_video_size` set to `1920x1080`. This is a real
headless Chromium session rendering the real app — not a mock, not a
synthetic UI — Playwright just captures the actual rendered frames instead
of a human watching a monitor. This is the same mechanism already used
successfully in this session's rehearsal screenshots.

**Option B — manual capture from an actual desktop session:** if this
machine (or another one pointed at the same running backend/frontend) has a
real X11/Wayland session, open Chrome/Chromium at 1920×1080, browser zoom
100%, no other tabs, no notifications, no visible terminal/secrets, and
record with a standard screen recorder, muxing/encoding to H.264 MP4 at
30fps. I cannot verify tool availability for this path from the current tty
session — check `wf-recorder` (Wayland) or `ffmpeg -f x11grab` (X11) if you
take this route.

This document specifies Option A as the concrete command, since it is the
only path verified available in this session.

## Recording script outline (Option A, Playwright)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir="submission/week2/_raw_video",
        record_video_size={"width": 1920, "height": 1080},
    )
    page = ctx.new_page()

    # Segment A/B (0-27s): landing + indexed corpus, already live-verified
    page.goto("http://localhost:5173", wait_until="networkidle")
    page.wait_for_timeout(15_000)  # hold on screen for narration pacing

    # Segment C (27-47s): prior-verified evidence, shown as a real,
    # unmodified render of the committed doc/JSON — NOT the live app.
    # Recommended: render docs/EVALUATION.md's benchmark table + the
    # QA-005 transcript to a local, dark-themed HTML file with content
    # copied verbatim (zero wording changes) for on-camera legibility,
    # then:
    page.goto("file:///tmp/.../evidence_slide.html")
    page.wait_for_timeout(20_000)

    # Segment D (47-72s): LIVE unsupported hero query — deterministic, fast
    page.goto("http://localhost:5173", wait_until="networkidle")
    page.fill("#sl-question", "Who won the 2018 FIFA World Cup?")
    page.click("button.sl-btn.primary")
    page.wait_for_selector(".sl-answer-refusal", timeout=15_000)
    page.wait_for_timeout(10_000)

    # Segment E/F (72-105s): citation-provenance still on screen + closing
    page.wait_for_timeout(15_000)

    ctx.close()
    browser.close()
```

Output is a `.webm`. Convert/mux to the required MP4:

```bash
ffmpeg -i submission/week2/_raw_video/<generated>.webm \
  -vf "fps=30,scale=1920:1080:flags=lanczos" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
  -movflags +faststart \
  /home/parzival/sourcelens/submission/week2/sourcelens-week2-demo-raw.mp4
```

Target output: `1920x1080`, `30fps`, `H.264`, `MP4`, at
`/home/parzival/sourcelens/submission/week2/sourcelens-week2-demo-raw.mp4`.

**This script is prepared, not executed.** No video file exists yet. It
runs only on explicit instruction to record.

## Timeline (approx. 100s)

| Time | Screen | Action | Expected visual | Narration beat |
|---|---|---|---|---|
| 0–12s | App landing | none (static hold) | Header, "System online", 7 docs · 32 chunks | Problem statement |
| 12–27s | Knowledge Base panel | none | 7 indexed documents, chunk counts | Pipeline / corpus explanation |
| 27–47s | Evidence slide (prior verified) | none | `QA-005` question/answer/citations + retrieval metrics table, labeled "Prior verified result — docs/EVALUATION.md" | Evidence-gate thesis + prior grounded example |
| 47–72s | Query panel | type + click Ask, live | "Who won the 2018 FIFA World Cup?" → **INSUFFICIENT EVIDENCE** refusal badge, ~0.2s | Live refusal, no LLM call |
| 72–92s | Evidence slide (prior verified) or citation panel | none | Citation provenance fields (filename/excerpt/score) | Provenance explanation |
| 92–105s | App or repo | none | — | Closing thesis |

## Asset list (for later assembly)

1. `docs/assets/sourcelens-landing.webp` — real, verified, no secrets.
2. `docs/assets/sourcelens-indexed-corpus.webp` — real, verified, 7 docs/32 chunks match live state.
3. `docs/assets/sourcelens-unsupported-refusal.webp` — real, verified, FIFA World Cup refusal example (static backup if live capture segment needs a fallback still frame).
4. `qa/runs/full_llm_run.json`, record `QA-005` — real, completed 2026-08-22, commit `3593ae6`: Q "Who owns the current Remote Work Policy?" → A "The current Remote Work Policy is owned by People Operations [1]." — 1 citation, `remote-work-policy.md`, score 0.6873.
5. `docs/EVALUATION.md` — retrieval-quality table (Recall@1 94.12%, Recall@3/5 97.06%, MRR 0.956) and the honest 16/21 (76%) breakdown.

All five are pre-existing, committed, verified content — nothing new was generated for this list.

## Narration script (222 words)

> Most RAG systems confuse retrieval with evidence. A vector store will
> almost always return its closest match, even when nothing in the corpus
> actually answers the question — and a model asked to answer from that
> match will often try anyway.
>
> This is SourceLens, running here against seven synthetic HR and security
> policy documents, thirty-two chunks, indexed locally through a real
> sentence-transformer embedding model and a persistent vector store.
>
> Finding the nearest chunk is not enough. The evidence gate decides
> whether the model is allowed to answer. In prior verified runs,
> SourceLens answered direct questions like who owns the current Remote
> Work Policy correctly and grounded, with citations traced back to the
> exact source excerpt, filename, and relevance score.
>
> Now watch it refuse. Who won the 2018 FIFA World Cup? Retrieval still
> runs — it always does — but the evidence gate rejects the result as
> insufficient, and the language model is never called. No guess, no
> fallback to outside knowledge.
>
> Citations are assembled from retrieval provenance, not generated by the
> language model — filename, excerpt, and score, every time, for every
> grounded answer.
>
> The full generation path is benchmarked separately across forty real
> questions, documented with its failures alongside its successes; this
> recording focuses on the deterministic evidence boundary.
>
> SourceLens treats retrieval as a candidate for evidence, not permission
> to generate.

**Explicitly not claimed anywhere above or elsewhere in this recording**:
zero hallucinations, prompt-injection immunity, production readiness,
perfect accuracy, or that today's supported-query generation completed.

## What this recording does not do

- Does not stage the QA-031 current-vs-legacy conflict scenario as a happy path.
- Does not stage the PI-003 prompt-injection finding live.
- Does not claim today's live supported-query generation succeeded — it explicitly did not, three times, under GPU contention, and that is not mentioned in the narration at all (per instruction, no GPU/process debugging detail on camera).
- Does not modify, re-index, or re-configure the running application.
