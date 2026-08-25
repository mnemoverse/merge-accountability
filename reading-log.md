# Reading log

Dated log of what was read, when, and by whom. Per-finding evidence with file and line references lives in `excerpts/`.

| Date | System | Artifact | Reader |
|---|---|---|---|
| 2026-08-01 | Mem0, Graphiti, Letta, Cognee | pinned commits (see systems.csv) | E.I. |
| 2026-07-18 | GraphRAG | v3.1.1 (`14a00ad`) | E.I. |
| 2026-08-03 | LongMemEval | `src/evaluation/evaluate_qa.py` (grader prompts) | E.I. |
| 2026-08-03 | Mem0, Letta, Zep | vendor documentation pages cited in the paper | E.I. |
| 2026-08-16 | all six | re-fetch at pinned commits; excerpt extraction with caller searches (`excerpts/`) | Sigma (agent), verified against the paper's claims |
| 2026-08-16 | LongMemEval | knowledge-update grader template re-fetched from `main` | Sigma (agent) |
| 2026-08-16 | Wikidata | Help:Merge (unmerge procedure) for the Table 3 reference row | Sigma (agent) |

## Outreach

Findings were sent to the maintainers of all six systems on 2026-08-16, before submission, with a comment window closing 2026-08-30. Responses are recorded verbatim below as they arrive; silence is recorded as silence.

| System | Posted at | Sent | Response |
|---|---|---|---|
| Mem0 | <https://github.com/mem0ai/mem0/issues/7002> | 2026-08-16 | awaiting |
| Graphiti / Zep | <https://github.com/getzep/graphiti/issues/1771> | 2026-08-16 | awaiting |
| Letta | <https://github.com/letta-ai/letta/issues/3431> | 2026-08-16 | responded 2026-08-23; issue closed as not planned and locked (see below) |
| GraphRAG | <https://github.com/microsoft/graphrag/discussions/2501> | 2026-08-16 | awaiting |
| Cognee | <https://github.com/topoteretes/cognee/issues/4532> | 2026-08-16 | acknowledged 2026-08-16 (see below) |
| LangMem | <https://github.com/langchain-ai/langmem/issues/180> | 2026-08-16 | awaiting |

### Responses, verbatim

**Cognee** — 2026-08-16T17:30:29Z, `Vasilije1990` (<https://github.com/topoteretes/cognee/issues/4532#issuecomment-5308714025>):

> @lxobr can we please review this

Classification: acknowledgment; internal review requested. No factual correction yet.

**Letta** — 2026-08-23T20:58:16Z, `cpacker` (<https://github.com/letta-ai/letta/issues/3431#issuecomment-5388425076>); the issue was closed by `cpacker` at the same time (state reason: not planned) and locked by `letta-ai` at 2026-08-23T20:59:40Z:

> Most of this is wrong / outdated, and any academic results published with this repo would be misleading / not representative of "Letta" as it relates to the harness or context management techniques. Please see: https://github.com/letta-ai/letta/blob/main/AGENTS.md#prohibited-uses and use https://github.com/letta-ai/letta-code as a reference implementation for any academic work. If you have questions about benchmarking (using the current representative codebase) please open them in the `letta-code` repo.

Classification: substantive objection, unspecified. The maintainer states that the repository we read is outdated and refers to the AGENTS.md "Prohibited uses" section (which asks that the archived branch, old releases, old packages, and the old Docker image not be used for benchmarks, evaluations, academic research, or comparisons with other memory systems) and to `letta-ai/letta-code` as the current reference implementation. No specific claim in our reading is identified as wrong. The thread is locked, so no follow-up is possible there; the maintainer invites questions in the `letta-code` repository. Recorded verbatim; our response is pending.

**Mem0** — note, 2026-08-17: the issue's metadata shows a comment count of 1, but the comments API returns zero visible comments; a comment appears to have been posted and then deleted or hidden. Recorded as: no visible response.
