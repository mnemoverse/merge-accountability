# LangMem

- System: LangMem (langchain-ai/langmem)
- Version: 0.0.30
- Commit (full SHA): `56d85939d80bb731bd5e237567148d817d7bfd16`
- Upstream license: MIT License (LICENSE, "MIT License / Copyright (c) 2025 LangChain")
- Extraction date: 2026-08-16
- Pin note: the paper's footnote dates this pin by the last `src/` commit, 2025-07-28. Verified against GitHub: the last commit touching `src/` at or before the pin is `f628edf03ee1138b50e15ea521e72569b60de8bf`, committed 2025-07-28T19:40:35Z.

Snippets are short verbatim quotations from the upstream repository at the pinned commit, reproduced for review and criticism; copyright remains with the upstream authors.

All paths below are relative to the repository root at the pinned commit.

---

## Claim 1: LangMem has no store of its own; storage is delegated to LangGraph's `BaseStore`

Paper (Section "Methods", unit read): "LangMem's store operations over LangGraph's `InMemoryStore`". The manager and tools accept any LangGraph `BaseStore` and forward writes to it.

`src/langmem/knowledge/extraction.py:12-15` (import of the store abstraction from the langgraph dependency):

```python
from langgraph.store.base import (
    NOT_PROVIDED,
    BaseStore,
    NotProvided,
)
```

`src/langmem/knowledge/extraction.py:846-850` (the manager takes a `BaseStore`, default top-5 window visible on the adjacent line):

```python
        query_model: str | BaseChatModel | None = None,
        query_limit: int = 5,
        namespace: tuple[str, ...] = ("memories", "{langgraph_user_id}"),
        store: BaseStore | None = None,
        phases: list[MemoryPhase] | None = None,
```

`src/langmem/knowledge/extraction.py:903-912` (when no store is passed, the manager pulls whatever store the LangGraph context provides):

```python
        if self._store is not None:
            return self._store
        try:
            self._store = get_store()
        except RuntimeError as e:
            raise ValueError(
                "Memory Manager's store not configured in LangGraph context. "
                "First use in the graph before calling, or initialize with an instance of the store."
            ) from e
        return self._store
```

## Claim 2: `put()` is a blind overwrite

Paper (Table 2 and Section "Findings by System", LangMem): "the store-level `put` is a blind overwrite"; "Nobody in the store [decides a conflict] (`put` is a blind overwrite)".

`src/langmem/knowledge/extraction.py:1419-1424` and `1464-1470` (`MemoryStoreManager.put`: the entire body after the docstring is a direct forward to the LangGraph store; no read of the prior value, no comparison, no conflict branch):

```python
    def put(
        self,
        key: str,
        value: dict[str, typing.Any],
        index: typing.Optional[typing.Union[typing.Literal[False], list[str]]] = None,
        ...
        return self.store.put(
            self.get_namespace(config),
            key,
            value,
            index=index,
            ttl=ttl,
        )
```

`src/langmem/knowledge/extraction.py:1646-1648` (async variant, same shape):

```python
        return await self.store.aput(
            self.get_namespace(config), key, value, index, ttl=ttl
        )
```

`src/langmem/knowledge/tools.py:297-304` (the `manage_memory` tool's write path: for both "create" and "update" the tool calls `store.aput` on the key with no read-before-write; an "update" is a full-value overwrite of whatever was under that id):

```python
        id = id or uuid.uuid4()
        await store.aput(
            namespace,
            key=str(id),
            value={"content": _ensure_json_serializable(content)},
        )
        return f"{action}d memory {id}"
```

(The synchronous twin is `src/langmem/knowledge/tools.py:331-337`, calling `store.put` with the identical payload.)

Absence search (no conflict or dedup machinery anywhere in the write path). Command and full output over the pinned tree:

```
$ grep -rni "dedup\|duplicate\|conflict\|contradict" src/langmem --include="*.py"
src/langmem/graph_rag.py:44:#       3. Node embedding + search for near-duplicates
src/langmem/graph_rag.py:45:#       4. Merge/dedupe nodes
src/langmem/graph_rag.py:117:#     # 5. For each edge, embed, deduplicate, store
src/langmem/graph_rag.py:139:#         # 5c. search for similar edges to deduplicate
src/langmem/graph_rag.py:146:#         # if we find near-duplicate edges, we might skip or merge. We'll just create new for demonstration
src/langmem/knowledge/extraction.py:475:                    f" Avoid duplicate extractions. {session}"
src/langmem/knowledge/extraction.py:568:            that are outdated or contradicted by new information. Defaults to True.
src/langmem/knowledge/extraction.py:570:            that are outdated or contradicted by new information. Defaults to False.
src/langmem/knowledge/extraction.py:985:                "You are a memory manager. Deduplicate, consolidate, and enrich these memories.",
src/langmem/knowledge/extraction.py:2075:                # Adding a delay lets you **debounce** and deduplicate reflection work
src/langmem/prompts/_layers.py:286:    """Sort and deduplicate search items by score, returning top k results.
```

Reading of the output: every hit is either commented-out code (`graph_rag.py`, see Claim 3), prompt text handed to an LLM (lines 475, 985), docstring prose (568, 570, 1707, 2075), or a score-sort helper in the prompt-optimization module (`_layers.py:286`). No hit is executable conflict logic on the store write path.

```
$ grep -rni "cosine\|jaccard\|threshold\|similarity" src/langmem --include="*.py"
src/langmem/graph_rag.py:81:#         # 3c. Decide if we merge or not. For a simple example, if the top candidate is above some threshold, we treat it as same entity
src/langmem/graph_rag.py:82:#         # We'll skip threshold logic for brevity, but in real code you'd compare embeddings or names
```

Both hits are inside the commented-out file. There is no similarity threshold anywhere in the executable source.

## Claim 3: No entity model

Paper (Table 2, "Entity resolution" column): "None; no entity model". Paper (Findings): "There is no entity model".

The only entity-resolution code in the repository is `src/langmem/graph_rag.py`, which is commented out in its entirety. Verification command and output (count of lines that are neither comment nor blank):

```
$ grep -vc "^\s*#\|^\s*$" src/langmem/graph_rag.py
0
```

`src/langmem/graph_rag.py:1-4` (the file's executable content is zero; it opens as a commented sketch):

```python
# import uuid
# from datetime import datetime
# from langgraph.utils.config import get_store, get_config
# from langchain_core.language_models.chat_models import BaseChatModel
```

Entity-identity search over the executable source (command and full output; the only hits are auth-context identity in `graphs/auth.py`, which is user identity for access control, not record identity):

```
$ grep -rni "entity" src/langmem --include="*.py" | grep -v "^src/langmem/graph_rag.py"
src/langmem/graphs/auth.py:43:        "identity": auth_dict.get("user_id"),
src/langmem/graphs/auth.py:62:    logger.warning(f"Accepting {ctx.user.identity} with {ctx.resource} / {ctx.action}.")
src/langmem/graphs/auth.py:63:    filters = {"owner": ctx.user.identity}
src/langmem/graphs/auth.py:77:        value["namespace"] = (ctx.user.identity,)
src/langmem/graphs/auth.py:78:    elif ctx.user.identity != namespace[0]:
src/langmem/graphs/auth.py:79:        value["namespace"] = (ctx.user.identity, *namespace)
```

## Claim 4: An LLM pass runs over a top-5 retrieval window

Paper (Table 2 and Findings, LangMem): "A top-5 retrieval window, over which an LLM runs"; Section "What Was Read": "LangMem top-5" as a blocking window.

Default top-k. `src/langmem/knowledge/extraction.py:847` (class constructor, shown in Claim 1 snippet) and `src/langmem/knowledge/extraction.py:1666-1677` (the public factory):

```python
def create_memory_store_manager(
    model: str | BaseChatModel,
    /,
    *,
    ...
    query_model: str | BaseChatModel | None = None,
    query_limit: int = 5,
```

The window is enforced twice: as the search limit and as a hard cap after merging result lists. `src/langmem/knowledge/extraction.py:1022-1029` (each store search is capped at `query_limit`):

```python
            search_results_lists = await asyncio.gather(
                *[
                    store.asearch(
                        namespace, **({**tc["args"], "limit": self.query_limit})
                    )
                    for tc in query_req.tool_calls
                ]
            )
```

`src/langmem/knowledge/extraction.py:992-1004` (`_sort_results` slices the merged, score-sorted candidates to `query_limit`, i.e. top-5 by default):

```python
    def _sort_results(
        search_results_lists: list[list[SearchItem]], query_limit: int
    ) -> dict[str, SearchItem]:
        search_results = {}
        for results in search_results_lists:
            for item in results:
                search_results[(tuple(item.namespace), item.key)] = item
        sorted_results = sorted(
            search_results.values(),
            key=lambda it: it.score if it.score is not None else float("-inf"),
            reverse=True,
        )[:query_limit]
        return {MemoryStoreManager._stable_id(item): item for item in sorted_results}
```

The LLM pass over that window. `src/langmem/knowledge/extraction.py:1073-1080` (the trustcall-based `memory_manager`, an LLM extractor, is invoked with the top-5 window as `existing`; this is the only place a duplicate or conflict could be noticed):

```python
        enriched = await self.memory_manager.ainvoke(
            {
                "messages": input["messages"],
                "existing": store_based,
                "max_steps": input.get("max_steps"),
            },
            config=config,
        )
```

## Claim 5: Fate of the losing record; the `created_at` reset lives in the langgraph dependency, not in this repository

Paper (Table 2, "What survives a merge" column): "Destroyed; LangGraph's `InMemoryStore` resets `created_at`". Paper (Findings): "LangGraph's `InMemoryStore` resets `created_at` on overwrite, so even the original timestamp of the replaced record is lost."

Locating this precisely: `InMemoryStore` is not defined in the langmem repository. At this pin it is imported from the `langgraph` dependency; the overwrite semantics of `put`, including any `created_at` handling, are implemented in that dependency's code, not in any file of `langchain-ai/langmem` at commit `56d8593`. The evidence this repository can supply is (a) the import site and (b) the dependency pin; the reset behavior itself must be evidenced against the langgraph codebase, and the companion repository should attach that excerpt under a langgraph pin rather than under this one.

`src/langmem/graphs/semantic.py:2-12` (import from the dependency and use as the shipped graph's store):

```python
from langgraph.store.memory import InMemoryStore
...
store = InMemoryStore(
```

`src/langmem/knowledge/tools.py:92` and `src/langmem/knowledge/extraction.py:737` carry the same `from langgraph.store.memory import InMemoryStore` import in docstring examples and default-store fallbacks.

`pyproject.toml:13` (the dependency declaration):

```toml
    "langgraph>=0.6.0,<2",
```

`uv.lock` (resolved versions in this repo's lockfile at the pin): `langgraph 1.2.6`, `langgraph-checkpoint 4.1.1`. Note the lockfile pins the development environment, not what a user installs; a user resolves `langgraph>=0.6.0,<2` at install time.

What langmem itself destroys: within the manager's own LLM path, records the LLM marks removed are physically deleted, and updated records are re-put with a payload of only `kind` and `content`. `src/langmem/knowledge/extraction.py:1110-1116` and `1132-1135`:

```python
                    final_puts.append(
                        {
                            "namespace": old_art.namespace,
                            "key": old_art.key,
                            "value": {"kind": kind, "content": content},
                        }
                    )
        ...
        await asyncio.gather(
            *(store.aput(**put) for put in final_puts),
            *(store.adelete(ns, key) for (ns, key) in final_deletes),
        )
```

## Claim 6: Nothing is published and nothing is stored about the decision

Paper (Findings, LangMem): "Nothing is published and nothing is stored about the decision."

Stored: the write payloads above are the complete record. The manager path writes `{"kind": ..., "content": ...}` (extraction.py:1110-1123); the tool path writes `{"content": ...}` (tools.py:298-303). Neither payload carries provenance, a predecessor pointer, a score, or any field describing what the write replaced. The deletes at extraction.py:1132-1135 leave no tombstone. The absence greps under Claim 2 show no logging or event machinery for conflicts anywhere in `src/langmem`.

Published: absence of a published error rate is a claim about the project's documentation and papers, not about this tree; it belongs to the paper's documentation review and is not evidenced here.

## Non-code sources

The paper's LangMem findings as read above rest on the pinned source tree alone; no LangMem documentation page or issue-tracker thread is cited for these claims in the "Findings by System" section. The only non-code element used is the pin metadata itself (last `src/` commit date), verified via the GitHub API on 2026-08-16 as recorded in the header.
