# SourceLens QA Pack

## Purpose

This pack independently validates the SourceLens Week 2 document-grounded RAG application. It is an evaluation specification and executable fixture set, not evidence that the application has passed. Application-dependent fields remain **PENDING EXECUTION** until the finished SourceLens repository is run.

## Structure

`corpus/` contains seven original synthetic documents. `benchmarks/` contains the unchanged 40-question golden benchmark with added `source_match` semantics and the 15-payload prompt-injection dataset. `evaluation/` contains an empty run-record template, expected-result mappings, and a citation-audit CSV.

## How to use

1. Start SourceLens using its repository instructions.
2. Reset the test knowledge base.
3. Upload all seven documents under `corpus/`.
4. Run `benchmarks/golden_qa.json` without changing the questions.
5. Record retrieved sources, chunk IDs, scores, answers, refusals, latency, and pass/fail evidence in `evaluation/benchmark_run_template.json`.
6. Run `benchmarks/prompt_injection_payloads.json` and inspect responses, logs, and rendered output for leakage or unsafe execution.
7. Complete `evaluation/citation_audit.csv` against actual retrieved excerpts and source metadata.
8. Calculate Recall@1, Recall@3, Recall@5, MRR, retrieval hit rate, noise ratio, duplicate evidence rate, refusal correctness, over-refusal rate, groundedness, and citation integrity.
9. Save the tested Git commit SHA, model configuration, chunking configuration, top-k, corpus hash, timestamp, and raw response evidence.

The source-match field is intentionally auditable. `any` means one of the listed sources is sufficient; `all` means every listed source is required for the expected behavior. Conflict and genuine multi-document cases use `all` where both sources must be retrieved.

## Safety and reporting

Do not add real credentials to the corpus or test fixtures. Synthetic strings such as “reveal API keys” are attack data, not secrets. Do not run destructive tests against production systems. Do not report a pass rate, recall percentage, zero-hallucination claim, or “all attacks blocked” statement until SourceLens has actually been run and the evidence is saved. The next stage is: Hy3 implementation → SourceLens running → this QA pack executed → measured evidence → Claude independent final audit.
