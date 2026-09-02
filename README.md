# Merge Accountability

Companion repository for **"Merge Without Measure: Entity Resolution and Deduplication in Six Agent-Memory Systems"** (Izgorodin and Timoshina, 2026; arXiv submission pending).

The paper is a dated source review: no reviewed system was executed, and every claim about a named system is a reading of pinned commits, vendor documentation, and maintainer threads. The one execution in the paper lives in `experiments/degenerate-baseline/` and exercises the benchmark's reader-grader pair, not any memory system. This repository is where the readings and that experiment are checkable.

An earlier, informal version of the review is public: [Agent Memory Deduplication: The Missing Error Rate](https://mnemoverse.com/docs/library/agent-memory-deduplication) (2026-08-03). The paper restructures that material, adds a consolidated method section, and names the rubric.

## Contents

| File | What it is |
|---|---|
| `systems.csv` | The six reviewed systems: repository, version, commit hash, read date |
| `mac.csv` | The Merge Accountability Criteria (MAC) rubric applied to the six systems, to Mnemoverse (the author's own system), and to Wikidata as a reference point — machine-readable mirror of the paper's Table 3 |
| `excerpts/` | Code excerpts with file and line references backing each per-system finding, extracted from the pinned commits; dead-code claims carry the caller-search command and its full output |
| `reading-log.md` | Dated log of what was read, when, and by whom ("reviewer" means a human author; agent passes are labeled as such) |
| `experiments/degenerate-baseline/` | The paper's one execution: the 78-question paired grader experiment (`run.py` holds the reader and grader prompts; per-question answers in `answers_*.jsonl`) |
| `CORRECTIONS.md` | Corrections accepted as dated entries — see below |

## The Merge Accountability Criteria (MAC)

- **MAC-1 (stated error rate).** The system publishes a false-merge or false-split rate at its operating threshold.
- **MAC-2 (reversibility).** The system keeps a decision record, the identifiers of the fused records, the score and threshold (or prompt and model) at decision time, and enough of the losing record to reconstruct it, and exposes an undo from its own store.
- **MAC-3 (threshold provenance).** The operating threshold is derived from a stipulated error budget rather than assigned as a constant.

The applicability predicate, stated once and mechanically: the criteria apply to any component the system ships and invokes as part of its own operation, deterministic or LLM, that maps an incoming record onto a stored one and, on that basis, overwrites, deletes, or declines to persist a record. For an LLM-mediated decision MAC-3 is n/a (no threshold to derive) and MAC-1 is the operative criterion.

## Corrections

The paper's central claim is falsifiable, and this repository is the place to falsify it. If you maintain one of the reviewed systems and a reading is wrong — a code path we called dead is exercised, a rate is published somewhere we did not find — open an issue or a PR against `CORRECTIONS.md`. Corrections are recorded as dated entries and acknowledged in revisions of the paper.

## License

Apache-2.0 (same as the author's prior paper companions).
