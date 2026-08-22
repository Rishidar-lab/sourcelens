# Failure analysis

Deep-dive on the 5 real, reproducible model-quality gaps found while running
the full 40-question benchmark against the real configured LLM (Ollama,
`qwen2.5-coder:7b`) — see `docs/EVALUATION.md` for the run this data comes
from (`qa/runs/full_llm_run.json`) and `docs/EVIDENCE_LEDGER.md` for how
these fit into the overall requirement coverage. This document exists to
show the reasoning behind each finding, not just the fact of it.

**One fact established up front, common to all 5**: in every case, `refused
== False` (the response was `grounded: true`) and the log shows real
citations with strong retrieval scores (0.36–0.79 cosine similarity, 9–13
citations after adjacent-chunk expansion). **The retrieval layer worked in
all 5 cases.** Every failure below is a generation-layer failure — the
right evidence was in the model's context; what it did with that evidence
is what's being analyzed.

---

## Class 1 — Partial-evidence over-refusal

**Questions**: QA-022 ("What is the exact tax treatment for a remote
employee who changes countries?"), QA-024 ("What exact customer-notification
wording must be used after a critical incident?")

**Observed behavior**: Both retrieved genuinely relevant evidence
(`remote-work-policy.md` for QA-022, `incident-response-policy.md` for
QA-024 — both in the expected-document set) with citations and real scores,
yet the model's answer was the literal configured `REFUSAL_MESSAGE`
("I couldn't find sufficient evidence...") rather than any use of that
evidence.

**Expected behavior**: A partial, hedged answer — e.g. "the tax treatment
isn't specified in these documents; consult People Operations" — that uses
what *is* available while explicitly flagging what isn't, per the QA pack's
`expected_behavior` field for these `partially_answerable`-category
questions.

**Likely layer responsible**: Generation, not retrieval or the evidence
gate — `refused: False` proves the gate passed the evidence through; the
LLM was called with real relevant context and still chose to output the
refusal sentence.

**Retrieval vs generation vs policy-gate classification**: Generation.

**Root cause — verified fact, not a hypothesis**: the system prompt
(`backend/app/services/rag/prompts.py`) has exactly one instruction about
what to do when full certainty isn't available — rule 4, which is binary:
*"If the retrieved excerpts do not contain enough information to answer the
question, respond exactly with: [REFUSAL_MESSAGE]."* There is no rule
instructing a hedged, partial answer. The model was never told that mode
exists.

**Hypothesis, not verified**: adding an explicit rule ("if only partial
information is available, answer what you can and explicitly say what's
missing, rather than refusing outright") would likely reduce this failure
mode. Not tested in this session — the fix wasn't attempted, so this is a
prediction, not a confirmed remediation.

**Why not fixed before submission**: this is a genuine prompt-policy gap,
not a bug — fixing it means designing and testing a new behavioral mode
(when does "partial" become "insufficient"? how is the boundary worded so
it doesn't cause new over-answering on genuinely unsupported questions like
the FIFA World Cup case, which is the project's core acceptance test?)
rather than a small patch. Given the FIFA-World-Cup-style refusal is the
single most important behavior in this project, a same-day prompt change
risks trading a real but narrower gap for a regression in the primary
acceptance criterion. Reported honestly and left for deliberate follow-up
work instead.

---

## Class 2 — Conflicting-source not surfaced

**Question**: QA-031 ("How many remote days are employees allowed per
week?")

**Observed behavior**: Both `remote-work-policy.md` (current, "three days")
and `legacy-remote-policy.md` (superseded, "two days") were retrieved and
cited (9 citations, top score 0.79). The answer correctly stated the
*current* three-day policy — but never mentioned the legacy policy, the
conflict, or the supersession at all.

**Expected behavior**: Per the QA pack and the system prompt's own rule 5,
state that the sources conflict and summarize each side with its citation
before (or while) resolving to the current one.

**Likely layer responsible**: Generation.

**Retrieval vs generation vs policy-gate classification**: Generation —
and specifically the sharpest finding of the 5, because unlike Class 1
there **is** an explicit, on-point instruction already in the system
prompt (*"5. If the retrieved excerpts contradict each other, state that
the sources conflict..."*), and it wasn't followed even though both
conflicting documents were demonstrably in the model's context. This is a
real instruction-following miss, not a missing-instruction gap.

**Hypothesis, not verified**: this may reflect a genuine limitation of a
7B quantized local model's ability to notice a contradiction between two
retrieved passages when the direct question ("how many days") has an
easy, confident single answer available — i.e., the model may be
optimizing for "answer the question" over "check rule 5" when both are
satisfiable independently. Whether a larger/frontier model follows rule 5
more reliably here was not tested (see `docs/EVALUATION.md` for why the
27B local model comparison couldn't be completed on this hardware).

**Why not fixed before submission**: the instruction already exists and
is correctly worded; there's no cheap prompt change to try that isn't
already present. The honest fix is either a better/larger model or an
explicit code-level conflict-detection pass (e.g., flag when two retrieved
chunks from different documents both match strongly on a similar topic and
force the prompt to address them separately) — real engineering work, not
a same-session patch, and reported as such rather than papered over with a
cosmetic prompt tweak that duplicates an instruction already being ignored.

---

## Class 3 — Ambiguity not recognized

**Question**: QA-039 ("What is the deadline for reporting?")

**Observed behavior**: Answered confidently with one interpretation ("30
minutes", the security-incident reporting deadline) without noting the
question could also mean the travel-expense reporting deadline ("ten
business days", per the QA pack's expectation) or asking which was meant.

**Expected behavior**: Recognize the question is ambiguous between at
least two real, retrievable deadlines and either present both or ask for
clarification.

**Likely layer responsible**: Generation.

**Retrieval vs generation vs policy-gate classification**: Generation —
11 citations were retrieved, so the "ten business days" fact was very
likely present in context alongside "30 minutes" (not independently
re-verified by inspecting every one of the 11 raw excerpts for this
report, so stated as likely rather than confirmed).

**Root cause — verified fact**: same gap as Class 1 — there is no system
prompt rule instructing the model to recognize or handle an ambiguous
question. It has rules for "not enough evidence" (refuse) and "conflicting
evidence" (state the conflict), but no rule for "the question itself has
more than one reasonable reading."

**Hypothesis, not verified**: an explicit ambiguity-handling rule would
likely help, for the same reason as Class 1 — this is currently an
unhandled case, not a case the model was asked to handle and failed at.

**Why not fixed before submission**: same reasoning as Class 1 — this
needs a deliberately designed and tested behavioral rule, not a rushed
one-line addition, particularly since "ambiguous" and "insufficient
evidence" need to stay clearly distinguishable to the model or the fix
risks blurring the refusal behavior that's the project's core guarantee.

---

## Class 4 — Thin multi-document synthesis

**Question**: QA-018 ("What should an employee do if a remote-work device
may have exposed a password?")

**Observed behavior**: All 3 expected documents (`security-guidelines.md`,
`incident-response-policy.md`, `remote-work-policy.md`) were retrieved (13
citations total) — but the answer used only one fact from one document
("report within 30 minutes", cited to `incident-response-policy.md`) and
never mentioned `security-guidelines.md`'s content about the device being
company-managed or not sharing the password further.

**Expected behavior**: A synthesized answer combining the reporting
deadline with the device-handling guidance from the second document.

**Likely layer responsible**: Generation.

**Retrieval vs generation vs policy-gate classification**: Generation —
retrieval clearly succeeded (all 3 required documents present with strong
scores), so this is specifically a synthesis failure: the model picked the
single most directly-responsive fact ("what's the deadline") and didn't
continue integrating the other retrieved, relevant chunks into a fuller
answer.

**Hypothesis, not verified**: this may be related to prompt rule 6 ("be
concise and factual") being interpreted as "answer with the single most
direct fact" rather than "be concise while still using all relevant
evidence" — plausible given the wording, but not confirmed by testing an
alternative phrasing in this session.

**Why not fixed before submission**: same category of reasoning as
Classes 1 and 3 — untested prompt surgery risks trading a synthesis gap
for verbosity or scope creep on simpler questions that currently get
correctly concise answers (8 of the 15 real-LLM-answered questions in the
full run passed cleanly; a prompt change tuned for this one failure mode
could regress those). Reported as a real, measured limitation rather than
patched blind.

---

## Summary table

| Class | Questions | Root cause (verified) | Fix attempted this session |
|---|---|---|---|
| Partial-evidence over-refusal | QA-022, QA-024 | No system-prompt rule for hedged partial answers exists | No |
| Conflicting-source not surfaced | QA-031 | Rule 5 exists and directly applies, but wasn't followed | No |
| Ambiguity not recognized | QA-039 | No system-prompt rule for ambiguous questions exists | No |
| Thin multi-document synthesis | QA-018 | All evidence retrieved; model used only the most direct fact | No |

Common thread across all 4 classes: **retrieval is not the bottleneck.**
Every one of these questions had the right evidence in the model's
context. The gap is entirely in how a small, locally-hosted model
reasons over multiple pieces of evidence when the desired behavior isn't
(or, for Class 2, is but wasn't followed by) explicitly instructed. This
is consistent with the same underlying limitation documented for the
PI-003 prompt-injection finding in `SECURITY.md` — a real, disclosed
ceiling of the current small-model configuration, not a retrieval,
citation, or evidence-gate defect.
