# Week 2 LinkedIn post draft — SourceLens

> Draft only. Do not publish without review — fill in the placeholders and
> confirm the numbers still match the latest `qa/runs/` output before
> posting.

---

Week 2 of Innovation Hacks: SourceLens, an evidence-grounded document Q&A
tool.

The idea I wanted to actually test: a RAG app is easy to demo when it
works, and easy to fool yourself about when it doesn't. Vector search over
your documents will always return *something* — the interesting engineering
problem is telling "closest match" apart from "actual evidence," and
refusing cleanly when the answer isn't in your documents instead of quietly
falling back to the model's own training knowledge.

What's in it:
- FastAPI backend, persistent ChromaDB vector store, real sentence-embedding
  retrieval (`all-MiniLM-L6-v2`)
- An evidence-sufficiency gate that has to hold up against exactly the
  failure case above — verified with a real "who won the 2018 World Cup"
  query against policy documents
- Citations built from real retrieval records, never invented by the LLM
- Explicit prompt-injection defenses — tested with real documents
  containing injected "reveal your secrets" style payloads, run against a
  real local LLM (Ollama), not just reviewed as prompt text
- React + TypeScript frontend
- A 40-question benchmark + 15-case prompt-injection red team, both
  executed for real against the live pipeline, not just described

What I learned: automated string-matching benchmarks are a useful first
pass but not proof of correctness on their own. Two of my own red-team
cases got auto-graded as "failed" purely because the model phrased its
refusal differently than the exact string I expected — reading the actual
transcript showed it refused correctly both times. That distinction (what a
script measured vs. what actually happened) mattered more to the write-up
than the pass/fail count did.

GitHub: [link]
Demo video: [link]

#InnovationHacks #RAG #buildinpublic
