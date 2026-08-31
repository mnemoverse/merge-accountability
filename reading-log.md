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
| 2026-08-25 | Letta (letta-code) | `letta-ai/letta-code` at `a0798e0` (main, 2026-08-25): memory tool, git-backed memory filesystem, reflection and defragmentation subagent prompts, memory CLI, reflection settings; read after the maintainers' response of 2026-08-23 named it the reference implementation | Sigma (agent), four independent readers, key file:line references below |
| 2026-08-25 | Letta (legacy) | `AGENTS.md` history: deprecation notice added 2026-07-03 (`b76da90`), Prohibited-uses section 2026-08-16 (`87fd37a`) | Sigma (agent) |

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

## Outcome at the close of the comment window

The window announced in all six outreach threads closed on **2026-08-30**. State of every thread, checked **2026-08-31**:

| System | Thread | State on 2026-08-31 | Outcome |
|---|---|---|---|
| Mem0 | `mem0#7002` | open, 15 days without a visible comment | no response; see the counter anomaly below |
| Graphiti / Zep | `graphiti#1771` | open, zero comments | no response |
| Letta | `letta#3431` | closed as not planned, locked 2026-08-23 | substantive objection, unspecified; follow-up in `letta-code#4040` open with zero comments since 2026-08-25 |
| GraphRAG | `graphrag/discussions/2501` | open, zero comments | no response |
| Cognee | `cognee#4532` | open, one comment, unchanged since 2026-08-16 | acknowledgment only; the requested internal review has not appeared |
| LangMem | `langmem#180` | open, zero comments | no response |

**One of six responded with an objection, one acknowledged, four were silent.** No factual correction to any reading was received from any maintainer.

### The Mem0 counter anomaly persists

Recorded on 2026-08-17 and re-checked on 2026-08-31, unchanged in fifteen days:

```
GET /repos/mem0ai/mem0/issues/7002          -> comments: 1
GET /repos/mem0ai/mem0/issues/7002/comments -> []
```

The issue metadata reports one comment; the comments endpoint returns none. A comment appears to have been posted and then deleted or hidden. **What it said is unknown to us and this log makes no claim about its content.** It is recorded because the discrepancy is checkable by anyone and because a paper that says silence should say exactly what kind of silence it saw.

### What this changes in the paper

Nothing in the readings. No correction was offered, so v1 carries the readings as sent.

Per the terms stated in every thread, responses arriving after 2026-08-30 go into v2 and are recorded here as dated entries. The threads are left open on purpose: none of them was closed by us, and a late correction is still wanted.


### Responses, verbatim

**Cognee** — 2026-08-16T17:30:29Z, `Vasilije1990` (<https://github.com/topoteretes/cognee/issues/4532#issuecomment-5308714025>):

> @lxobr can we please review this

Classification: acknowledgment; internal review requested. No factual correction yet.

**Letta** — 2026-08-23T20:58:16Z, `cpacker` (<https://github.com/letta-ai/letta/issues/3431#issuecomment-5388425076>); the issue was closed by `cpacker` at the same time (state reason: not planned) and locked by `letta-ai` at 2026-08-23T20:59:40Z:

> Most of this is wrong / outdated, and any academic results published with this repo would be misleading / not representative of "Letta" as it relates to the harness or context management techniques. Please see: https://github.com/letta-ai/letta/blob/main/AGENTS.md#prohibited-uses and use https://github.com/letta-ai/letta-code as a reference implementation for any academic work. If you have questions about benchmarking (using the current representative codebase) please open them in the `letta-code` repo.

Classification: substantive objection, unspecified. **Follow-up 2026-08-25:** letta-code read at `a0798e0`; the paper's Letta section now reports both implementations. Key references (letta-code, a0798e0): write path `src/tools/impl/memory.ts:98-143` (structural validation only, one git commit per call); no similarity primitive in the memory path; reflection default `src/settings-manager.ts:185-186` (`memoryReminderInterval: 25`, `reflectionTrigger: "step-count"`); contradiction rule `src/agent/subagents/builtin/reflection.md:101`; defrag MERGE `src/agent/subagents/builtin/memory.md:140-145`, merge report table `:164-168` (returned to the parent conversation, not written to the store; commit `:200-202`); MemFS default-on and non-disableable `src/agent/memory-filesystem.ts:474-478`; no BlockHistory/checkpoint/undo/redo anywhere; restore only as whole-tree copy `src/cli/subcommands/memory.ts:218-267`; `letta memory resolve` advertised `src/index.ts:201`, unimplemented `src/cli/subcommands/memory.ts:310`; prompt claims revert, supplies `git log` `src/agent/prompts/letta.md:75-79`; `refs/letta-backup/` written `src/agent/memory-git.ts:1134`, never read. The maintainer states that the repository we read is outdated and refers to the AGENTS.md "Prohibited uses" section (which asks that the archived branch, old releases, old packages, and the old Docker image not be used for benchmarks, evaluations, academic research, or comparisons with other memory systems) and to `letta-ai/letta-code` as the current reference implementation. No specific claim in our reading is identified as wrong. The thread is locked, so no follow-up is possible there; the maintainer invites questions in the `letta-code` repository. Recorded verbatim. **Follow-up posted 2026-08-25** in the repository the maintainer named: <https://github.com/letta-ai/letta-code/issues/4040> (one apparent bug, `letta memory resolve` advertised but unimplemented, and three questions on the default reflection trigger, the unpersisted defragmentation merge report, and the absence of a revert surface), with a link to this log.

**Mem0** — note, 2026-08-17: the issue's metadata shows a comment count of 1, but the comments API returns zero visible comments; a comment appears to have been posted and then deleted or hidden. Recorded as: no visible response.
