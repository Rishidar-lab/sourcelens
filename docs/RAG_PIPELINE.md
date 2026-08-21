# RAG pipeline

End-to-end flow, in the order it actually executes in code.

## 1. Upload → validate → extract → chunk → embed → persist

`POST /api/documents/upload` → `DocumentService.ingest_files()`
(`backend/app/services/documents.py`):

1. **Validate** (`services/ingestion/validation.py`): extension allowlist,
   size limit, file-count limit. MIME type is checked only as a secondary,
   non-authoritative signal.
2. **Parse** (`services/ingestion/parsers.py`): PyMuPDF for PDF (page-by-page,
   real page numbers preserved for citations), python-docx for DOCX
   (paragraph text joined; DOCX has no native page concept, so citations use
   an "unknown page" sentinel), UTF-8/Latin-1/CP1252-tolerant decoding for
   TXT/MD. A file that fails to parse (corrupt, or the wrong format renamed
   with a valid extension) raises a typed error and is rejected — it never
   silently becomes zero content.
3. **Sanitize + hash**: `sanitize_filename()` strips path components and
   unsafe characters; `content_hash()` (SHA-256) is used for duplicate
   detection, both within one upload batch and against everything already
   indexed.
4. **Chunk** (`services/chunking/chunker.py`): a recursive splitter that
   tries paragraph, then sentence, then word, then hard-character
   boundaries (in that order) to keep chunks under `chunk_size` (default
   900 chars) with `chunk_overlap` (default 150 chars) between adjacent
   chunks. Each `Chunk` carries `document_id`, `filename`, `page`, and
   `chunk_index` — this metadata is what citations are built from later, so
   it's preserved end-to-end rather than re-derived at answer time.
5. **Embed once, in batch**: `EmbeddingProvider.embed()` — the real provider
   is a `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")`,
   loaded exactly once per process (in `Container` at startup, not
   per-request) and reused for every embed call, in batches of
   `embedding_batch_size`.
6. **Persist**: `ChromaStore.add_chunks()` writes vectors + metadata +
   chunk text into a persistent Chroma collection
   (`backend/data/chroma` by default).

## 2. Query → embed → retrieve → gate → generate → cite

`POST /api/query` → `RAGService.answer()`
(`backend/app/services/rag/service.py`):

1. **Embed the question** with the same provider used at index time.
2. **Retrieve** (`services/retrieval/service.py`): vector search against
   Chroma, `top_k` nearest chunks by cosine similarity.
3. **Evidence-sufficiency gate** (see below) — decides whether what was
   retrieved counts as *evidence*, not just *the closest thing available*.
4. If insufficient: return a refusal (`grounded: false`,
   `refusal_reason: "insufficient_evidence"`) **without ever calling the
   LLM**. The LLM is architecturally incapable of overriding this — it
   simply isn't invoked.
5. If sufficient but no LLM is configured: raise `LLMNotConfiguredError`
   (503) with a message naming the missing requirement, rather than
   fabricating a "success."
6. If sufficient and an LLM is configured: build a prompt with three
   explicit sections — system policy, user question, then the retrieved
   chunks under an explicit "untrusted evidence" label — and call the LLM.
7. **Citations are built from the retrieval records**, not parsed out of
   the LLM's prose: `_build_sources()` maps each retained `RetrievedEvidence`
   item (already carrying real filename/page/chunk_id/score from step 1's
   index-time metadata) to a `Source`. The LLM is asked to reference sources
   by bracketed number (`[1]`, `[2]`, ...) matching this list; it cannot
   invent a citation's filename, page, or excerpt because those fields never
   come from its output.

## The evidence-sufficiency gate, in detail

This is the part of the system that has to hold up against "vector search
always returns something." A cosine-similarity search over policy documents
for "who won the 2018 FIFA World Cup" will still return its 5 closest
matches — they're just not relevant. Two independent checks run before
anything is treated as evidence:

**1. A score threshold** (`RAG_MIN_RELEVANCE_SCORE`, default 0.20). Chunks
below this are dropped immediately.

**2. A lexical-overlap check for anything below a high-confidence floor**
(`RAG_ZERO_OVERLAP_FLOOR`, default 0.35). A chunk scoring below the floor is
only kept if it shares **at least two** meaningful (stopword-filtered,
lightly stemmed) words with the question. This exists because a single
coincidental shared word is easy to hit by chance — during this project's
own recovery testing, an adversarial query containing the word "SourceLens"
scored just high enough on lexical overlap to slip through solely because
one *unrelated* corpus document happened to contain a QA-authoring
annotation that also said "SourceLens." Requiring two overlapping words
(kept at 26/26 backend tests passing, and closed that specific false
positive in the QA benchmark) is a deliberately cheap, explainable
safety net — not a claim that lexical overlap is a semantic-relevance
proxy in general. See [EVALUATION.md](EVALUATION.md) for the numbers this
was tuned against.

If nothing survives both checks, `retrieval.has_evidence` is `False` and
`RAGService.answer()` returns the refusal path — this is enforced in code,
not just prompted for; `test_unsupported_question_refused` and
`test_unrelated_query_not_grounded` (`backend/tests/`) assert it directly,
and it was re-verified in a live browser against the real pipeline (see
`docs/EVALUATION.md`).

## Handling small/empty collections safely

`ChromaStore.query()` (`backend/app/repositories/chroma_store.py`) computes
`effective_k = min(top_k, collection.count())` before ever calling Chroma,
and returns an empty result immediately when the collection has zero
chunks. This was a real bug found during this project's recovery: with no
clamping, Chroma would internally clamp `n_results` down to the available
count anyway (so it never actually crashed), but it logged a warning on
every call and represented a fragile assumption. It's now handled
explicitly and covered by `test_retrieval.py`.

## Handling conflicting/current-vs-legacy evidence

SourceLens doesn't have special-cased "conflict detection" logic — instead,
the system prompt's rule 5 instructs the model: if retrieved excerpts
contradict each other, say so explicitly and summarize each side with its
citation, rather than silently picking one. This relies on both documents
actually being retrieved (which is a retrieval-recall question, measured in
`EVALUATION.md`) and the LLM following the instruction (which is a
generation-quality question, spot-checked against the real configured LLM,
not assumed).

## Prompt-injection trust boundary

See [SECURITY.md](../SECURITY.md#prompt-injection-defense) for the full
writeup; in short, `services/rag/prompts.py` builds the prompt so retrieved
text is always framed as data to quote/summarize, never as instructions,
and this was verified against the real LLM with real injected documents,
not just reviewed as prompt text.
