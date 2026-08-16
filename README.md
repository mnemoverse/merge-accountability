# Merge Accountability

Companion repository for **"Merge Without Measure: Entity Resolution and Deduplication in Six Agent-Memory Systems"** (Izgorodin, 2026; arXiv submission pending).

The paper is a dated source review: nothing was executed, and every claim about a named system is a reading of pinned commits, vendor documentation, and maintainer threads. This repository is where those readings are checkable.

## Contents

| File | What it is |
|---|---|
| `systems.csv` | The six reviewed systems: repository, version, commit hash, read date |
| `mac.csv` | The Merge Accountability Criteria (MAC) rubric applied to the six systems, to Mnemoverse (the author's own system), and to Wikidata as a reference point — machine-readable mirror of the paper's Table 3 |
| `excerpts/` | Code excerpts with file and line references backing each per-system finding *(TODO: populate before submission)* |
| `reading-log.md` | Dated log of what was read, when, and by whom *(TODO: populate before submission)* |
| `CORRECTIONS.md` | Corrections accepted as dated entries — see below |

## The Merge Accountability Criteria (MAC)

- **MAC-1 (stated error rate).** The system publishes a false-merge or false-split rate at its operating threshold.
- **MAC-2 (reversibility).** The system records which records were fused and can undo the merge from its own store.
- **MAC-3 (threshold provenance).** The operating threshold is derived from a stipulated error budget rather than assigned as a constant.

The criteria apply to a system that itself asserts identity between stored records, or destroys/overwrites a record on the basis of such an assertion.

## Corrections

The paper's central claim is falsifiable, and this repository is the place to falsify it. If you maintain one of the reviewed systems and a reading is wrong — a code path we called dead is exercised, a rate is published somewhere we did not find — open an issue or a PR against `CORRECTIONS.md`. Corrections are recorded as dated entries and acknowledged in revisions of the paper.

## License

Apache-2.0 (same as the author's prior paper companions).
