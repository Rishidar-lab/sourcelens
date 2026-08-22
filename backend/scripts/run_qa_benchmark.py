#!/usr/bin/env python
"""Executable runner for the Manus QA pack's 40-question golden benchmark.

Builds an isolated SourceLens container (real SentenceTransformer embeddings,
whatever LLM provider is configured via .env), indexes the 7 QA corpus
documents from ../qa/corpus into a throwaway Chroma collection, then runs
every question in ../qa/benchmarks/golden_qa.json through the real retrieval
pipeline and - unless --retrieval-only is passed - the real LLM.

This performs deterministic checks only: whether the expected document(s)
were retrieved, whether the evidence gate refused/answered as expected, and
whether required/forbidden substrings appear in the generated answer. It does
NOT claim to measure semantic groundedness - that requires a human or an
LLM-as-judge pass, which is out of scope for this script (see
docs/EVALUATION.md). The `groundedness_score` field is always left null here
to keep that distinction explicit and honest.

Usage (from backend/):
    python scripts/run_qa_benchmark.py --retrieval-only
    python scripts/run_qa_benchmark.py                      # includes real LLM calls
    python scripts/run_qa_benchmark.py --limit 5 --category direct
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
QA_DIR = REPO_ROOT / "qa"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.container import build_container  # noqa: E402
from app.services.documents import DocumentService  # noqa: E402


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def corpus_hash(corpus_dir: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(corpus_dir.glob("*.md")):
        h.update(path.name.encode("utf-8"))
        h.update(path.read_bytes())
    return h.hexdigest()


def load_questions(path: Path) -> tuple[str, list[dict]]:
    data = json.loads(path.read_text())
    return data["dataset"], data["questions"]


def rank_of_first_expected(retrieved_filenames: list[str], expected: list[str]) -> int | None:
    for i, fn in enumerate(retrieved_filenames, start=1):
        if fn in expected:
            return i
    return None


def unique_in_order(items: list[str]) -> list[str]:
    seen: list[str] = []
    for it in items:
        if it not in seen:
            seen.append(it)
    return seen


def recall_at_k(retrieved_filenames: list[str], expected: list[str], k: int) -> bool:
    if not expected:
        return False
    top = set(retrieved_filenames[:k])
    return any(e in top for e in expected)


async def run_one(container, q: dict, *, retrieval_only: bool) -> dict:
    settings = container.settings
    start = time.time()
    question = q["question"]
    expected_docs = q.get("expected_documents") or []
    source_match = q.get("source_match")
    should_refuse = bool(q.get("should_refuse"))

    retrieval = container.retrieval.retrieve(
        question,
        top_k=settings.rag_top_k,
        min_relevance_score=settings.rag_min_relevance_score,
    )
    retrieved_filenames_all = [e.filename for e in retrieval.evidence]
    retrieved_sources = unique_in_order(retrieved_filenames_all)
    retrieved_chunk_ids = [e.chunk_id for e in retrieval.evidence]
    retrieval_scores = [round(e.score, 4) for e in retrieval.evidence]
    first_rank = rank_of_first_expected(retrieved_sources, expected_docs)

    if expected_docs:
        if source_match == "all":
            all_present = all(d in retrieved_sources for d in expected_docs)
        else:
            all_present = any(d in retrieved_sources for d in expected_docs)
        retrieval_hit = any(d in retrieved_sources for d in expected_docs)
    else:
        all_present = None
        retrieval_hit = None

    refused_by_gate = not retrieval.has_evidence or retrieval.best_score < settings.rag_min_relevance_score

    answer = None
    citations: list[dict] = []
    refused = refused_by_gate
    llm_error = None

    if not retrieval_only and not refused_by_gate:
        try:
            resp = await container.rag.answer(question, top_k=settings.rag_top_k)
            refused = not resp.grounded
            answer = resp.answer
            citations = [s.model_dump() for s in resp.sources]
        except Exception as exc:  # noqa: BLE001
            llm_error = f"{type(exc).__name__}: {exc}"
            refused = None  # unknown - the LLM call itself failed

    latency_ms = int((time.time() - start) * 1000)
    refusal_correct = (refused == should_refuse) if refused is not None else None

    must_include = q.get("must_include") or []
    must_not_include = q.get("must_not_include") or []
    failure_reasons: list[str] = []

    if llm_error:
        failure_reasons.append(f"llm_error:{llm_error}")
    if retrieval_hit is False:
        failure_reasons.append("expected_source_not_retrieved")
    if source_match == "all" and all_present is False:
        failure_reasons.append("not_all_required_sources_present")
    if refusal_correct is False:
        failure_reasons.append("over_refusal" if refused else "under_refusal")
    if answer is not None:
        lower = answer.lower()
        for phrase in must_include:
            if phrase.lower() not in lower:
                failure_reasons.append(f"missing_must_include:{phrase}")
        for phrase in must_not_include:
            if phrase.lower() in lower:
                failure_reasons.append(f"forbidden_phrase_present:{phrase}")

    passed = not failure_reasons and (llm_error is None)

    return {
        "question_id": q["id"],
        "question": question,
        "category": q["category"],
        "expected_sources": expected_docs,
        "source_match": source_match,
        "should_refuse": should_refuse,
        "retrieved_sources": retrieved_sources,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "retrieval_scores": retrieval_scores,
        "first_relevant_rank": first_rank,
        "retrieval_hit": retrieval_hit,
        "all_required_sources_present": all_present,
        "answer": answer,
        "refused": refused,
        "refusal_correct": refusal_correct,
        "citations": citations,
        "groundedness_score": None,  # requires human / LLM-judge review - not computed here
        "unsupported_claim_count": None,  # requires human / LLM-judge review - not computed here
        "latency_ms": latency_ms,
        "pass": passed,
        "failure_reason": "; ".join(failure_reasons) if failure_reasons else None,
    }


def summarize(results: list[dict]) -> dict:
    with_expected = [r for r in results if r["expected_sources"]]

    def recall_rate(k: int) -> float | None:
        rows = [r for r in with_expected]
        if not rows:
            return None
        hits = 0
        for r in rows:
            top = set(r["retrieved_sources"][:k])
            if any(e in top for e in r["expected_sources"]):
                hits += 1
        return round(hits / len(rows), 4)

    mrr_rows = with_expected
    mrr = None
    if mrr_rows:
        mrr = round(
            sum((1.0 / r["first_relevant_rank"]) if r["first_relevant_rank"] else 0.0 for r in mrr_rows)
            / len(mrr_rows),
            4,
        )

    hit_rows = [r for r in results if r["retrieval_hit"] is not None]
    hit_rate = round(sum(1 for r in hit_rows if r["retrieval_hit"]) / len(hit_rows), 4) if hit_rows else None

    multi_doc = [r for r in results if r["category"] == "multi_document"]
    multi_doc_coverage = None
    if multi_doc:
        fracs = []
        for r in multi_doc:
            exp = r["expected_sources"]
            if not exp:
                continue
            present = sum(1 for d in exp if d in r["retrieved_sources"])
            fracs.append(present / len(exp))
        multi_doc_coverage = round(sum(fracs) / len(fracs), 4) if fracs else None

    should_refuse_rows = [r for r in results if r["refusal_correct"] is not None]
    refusal_correctness = None
    if should_refuse_rows:
        refusal_correctness = round(
            sum(1 for r in should_refuse_rows if r["refusal_correct"]) / len(should_refuse_rows), 4
        )

    # Over-refusal: among questions that SHOULD have been answered
    # (should_refuse resolved to False) and whose refusal status is known,
    # what fraction did the system incorrectly refuse anyway?
    should_answer_rows = [
        r for r in results if r["refused"] is not None and not r["should_refuse"]
    ]
    over_refusal_rate = (
        round(sum(1 for r in should_answer_rows if r["refused"]) / len(should_answer_rows), 4)
        if should_answer_rows
        else None
    )

    answered = [r for r in results if r["answer"] is not None]
    citation_presence = (
        round(sum(1 for r in answered if r["citations"]) / len(answered), 4) if answered else None
    )

    return {
        "total_questions": len(results),
        "executed": len(results),
        "passed": sum(1 for r in results if r["pass"]),
        "failed": sum(1 for r in results if not r["pass"]),
        "recall_at_1": recall_rate(1),
        "recall_at_3": recall_rate(3),
        "recall_at_5": recall_rate(5),
        "mrr": mrr,
        "retrieval_hit_rate": hit_rate,
        "multi_document_source_coverage": multi_doc_coverage,
        "refusal_correctness_rate": refusal_correctness,
        "over_refusal_rate": over_refusal_rate,
        "citation_presence_rate": citation_presence,
        "llm_errors": sum(1 for r in results if r["failure_reason"] and "llm_error" in r["failure_reason"]),
        "note": (
            "recall/MRR/hit-rate are computed only over questions with "
            "expected_documents set (i.e. not the 'unsupported' category, "
            "which has none by design). groundedness_score and "
            "unsupported_claim_count are intentionally left null: this "
            "script checks deterministic string/retrieval facts, not "
            "semantic groundedness, which needs human or LLM-judge review."
        ),
    }


async def main_async(args: argparse.Namespace) -> None:
    corpus_dir = QA_DIR / "corpus"
    golden_path = QA_DIR / "benchmarks" / "golden_qa.json"
    dataset_name, questions = load_questions(golden_path)

    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
    if args.limit:
        questions = questions[: args.limit]

    run_dir = REPO_ROOT / "qa" / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    chroma_dir = run_dir / f"_chroma_{ts}"

    settings = Settings(
        chroma_persist_dir=str(chroma_dir),
        data_dir=str(run_dir / f"_data_{ts}"),
    )
    container = build_container(settings)
    doc_service = DocumentService(
        container.embedding_provider,
        container.store,
        container.chunker,
        max_bytes=settings.max_upload_bytes,
        max_files=settings.max_files_per_upload,
    )

    corpus_files = sorted(corpus_dir.glob("*.md"))
    files = [(p.name, p.read_bytes()) for p in corpus_files]
    print(f"Indexing {len(files)} QA corpus documents from {corpus_dir} ...")
    _, errors = doc_service.ingest_files(files)
    if errors:
        print("INGESTION ERRORS:", json.dumps(errors, indent=2))
        raise SystemExit(1)
    print(f"Indexed. chunks_indexed={container.store.count_chunks()}")

    print(
        f"Running {len(questions)} question(s) "
        f"(retrieval_only={args.retrieval_only}, llm_provider={settings.llm_provider}) ..."
    )
    results = []
    for i, q in enumerate(questions, start=1):
        r = await run_one(container, q, retrieval_only=args.retrieval_only)
        results.append(r)
        status = "PASS" if r["pass"] else f"FAIL ({r['failure_reason']})"
        print(f"[{i}/{len(questions)}] {q['id']} [{q['category']}] {status} ({r['latency_ms']}ms)")

    summary = summarize(results)
    out = {
        "benchmark_version": "1.0",
        "dataset": dataset_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "llm_model": getattr(container.llm_provider, "model", None) if container.llm_provider else None,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "top_k": settings.rag_top_k,
        "rag_min_relevance_score": settings.rag_min_relevance_score,
        "rag_zero_overlap_floor": settings.rag_zero_overlap_floor,
        "corpus_hash": corpus_hash(corpus_dir),
        "retrieval_only": args.retrieval_only,
        "summary": summary,
        "results": results,
    }

    out_path = Path(args.out) if args.out else run_dir / f"benchmark_run_{ts}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip LLM calls; evaluate retrieval only.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions.")
    parser.add_argument("--category", type=str, default=None, help="Only run questions in this category.")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path.")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
