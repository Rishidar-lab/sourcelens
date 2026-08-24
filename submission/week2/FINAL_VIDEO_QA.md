# SourceLens — Week 2 Final Video QA

## Status: NO VIDEO EXISTS. Do not treat any file in this repository as a Week-2 recording.

## What was attempted

Three independent, real attempts were made to record the supported hero
query (grounded answer + citations) against the live local application and
the actual configured LLM (`qwen2.5-coder:7b` via Ollama). All three failed
identically at the same step: retrieval succeeded every time (top score
0.749), the evidence gate correctly passed the query through to generation
every time, and then Ollama's token generation exhausted a 180-second
timeout every time — under sustained, near-100% GPU compute contention from
another process already running on this shared machine.

This is an infrastructure ceiling on this machine at this time, not a
demonstrated defect in SourceLens: the evidence gate, retrieval, and routing
all behaved correctly on every attempt. Full detail is in
[`RECORDING_EXECUTION.md`](RECORDING_EXECUTION.md), which was produced as a
direct result of these three failed attempts and remains accurate.

## What is verified instead, right now, without a live LLM call

| Claim | Evidence | Live or prior? |
|---|---|---|
| Corpus indexing (7 docs / 32 chunks) | Real running app, `GET /api/health` | **LIVE**, re-checkable any time |
| Evidence-gate refusal (unsupported query, no LLM call) | Real running app, `POST /api/query` — deterministic, ~0.2s | **LIVE**, re-checkable any time |
| Grounded answer + citation provenance | `qa/runs/full_llm_run.json`, question `QA-005`, completed 2026-08-22 at commit `3593ae6` | **PRIOR VERIFIED**, committed |
| Retrieval-quality metrics (Recall@1 94.12%, Recall@3/5 97.06%, MRR 0.956) | `docs/EVALUATION.md`, saved benchmark run | **PRIOR VERIFIED**, committed |
| UI states (landing, indexed corpus, refusal) | `docs/assets/sourcelens-*.webp`, 3 real captured screenshots | **PRIOR VERIFIED**, committed |

Nothing above required inventing evidence for this QA pass — it is either
re-checkable live right now or already sitting in the repository's commit
history with a checksum/commit reference.

## Recording runbook

A concrete, deterministic runbook already exists and was validated as
current in this pass: [`RECORDING_EXECUTION.md`](RECORDING_EXECUTION.md). It
specifies:

- Exactly which segments are live-recordable today (landing, indexed
  corpus, live refusal) versus which must be shown as clearly-labeled
  **prior verified evidence** (the grounded-answer/citation example and the
  retrieval-quality table) rather than re-attempted live, since re-attempting
  generation today would hit the same GPU-contention ceiling.
- A concrete Playwright `record_video_dir` capture script (Option A —
  the only path confirmed available from this machine's current tty
  session, which has no X11/Wayland desktop for a traditional screen
  recorder) plus the exact `ffmpeg` mux command to produce the final MP4.
- A word-for-word ~222-word narration script that explicitly separates live
  from prior-verified content on camera, and explicitly does not claim
  today's live generation succeeded.
- An explicit list of what the recording must **not** do: stage findings as
  a live happy path, claim zero hallucinations or production-readiness, or
  mention GPU/process debugging detail on camera.

**This pass did not execute the runbook.** Per the publication task's own
Phase 2 instructions ("do NOT resume unnecessary engineering") and because
the GPU-contention condition that caused three prior failures has not been
independently re-verified as cleared, re-attempting the live-generation
recording was left as a deliberate manual next action rather than retried
here.

## Duration / narration / intro / demo / outro / captions

Not applicable — no video file exists to measure. See the runbook above for
the planned ~100-second timeline (0–12s landing, 12–27s indexed corpus,
27–47s prior-verified evidence slide, 47–72s live refusal, 72–92s citation
provenance, 92–105s closing) once it is executed.

## Audio status

Not applicable — no audio has been recorded or synthesized for Week 2.

## Visual QA

Not applicable to a video. The three committed screenshots
(`docs/assets/sourcelens-*.webp`) were visually re-inspected this pass:
real running application, no secrets, no credentials, no personal data, no
browser chrome artifacts.

## Secret / privacy QA

`grep`-based scan of `RECORDING_EXECUTION.md`, `SUBMISSION_READINESS.md`,
and this file for API-key/token/password/bearer/private-key patterns:
**clean, zero matches.** No `.env`, credential, or personal data is
referenced anywhere in the Week-2 submission surface.

## Final verdict

**NOT READY — recording still required.** Everything that does not depend
on a live LLM call is verified and committed. The one remaining step is
executing the already-prepared runbook once GPU contention on this shared
machine has cleared (or from a machine without that contention), then
replacing `[ADD DEMO VIDEO URL]` in `README.md` and
`docs/WEEK2_LINKEDIN_POST.md` with the real upload URL. No video, video
URL, or narration audio should be treated as existing until that runbook
actually produces one.
