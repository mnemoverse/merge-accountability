# Evidence file: Mem0 (OSS)

- System: Mem0 (open-source Python package `mem0`, repository mem0ai/mem0)
- Version: 2.0.15
- Commit (full SHA): `50bdaaea0c02744720ed374d88584fd01494eeb7` (commit date 2026-08-01)
- Upstream license: Apache License, Version 2.0 (repository `LICENSE` file)
- Extraction date: 2026-08-16

Snippets are short verbatim quotations from the upstream repository at the pinned commit, reproduced for review and criticism; copyright remains with the upstream authors.

Notes on notation: `...` marks trimmed text. A few upstream prompt lines contain punctuation this file's style rules disallow; those segments are elided with `...` without altering any retained text. All paths are relative to the repository root. All line numbers refer to the pinned commit.

---

## Finding 1: Top-10 retrieval window at write

Paper claim: "The write-time decision operates over a top-10 retrieval window."

`mem0/memory/main.py:889-902` (inside `_add_to_vector_store`, the `add()` write path):

```python
        # Phase 0: Context gathering
        session_scope = _build_session_scope(filters)
        last_messages = self.db.get_last_messages(session_scope, limit=10)
        parsed_messages = parse_messages(messages)

        # Phase 1: Existing memory retrieval
        search_filters = {k: v for k, v in filters.items() if k in ("user_id", "agent_id", "run_id") and v}
        query_embedding = self.embedding_model.embed(parsed_messages, "search")
        existing_results = self.vector_store.search(
            query=parsed_messages,
            vectors=query_embedding,
            top_k=10,
            filters=search_filters,
        )
```

The async write path repeats the same window (`top_k=10`) in `async def _add_to_vector_store` starting at `mem0/memory/main.py:2492`. No recall figure for the window is published anywhere in the tree.

---

## Finding 2: MD5 exact-hash dedup at write

Paper claim: an MD5 hash check for exact duplicates is one of three write-time mechanisms.

`mem0/memory/main.py:976-995` (sync add path; the same logic appears in the async path at `mem0/memory/main.py:2637`):

```python
        # Phase 4: Per-memory CPU processing + Phase 5: Hash dedup
        # Build set of existing hashes for dedup
        existing_hashes = set()
        for mem in existing_results:
            h = mem.payload.get("hash") if hasattr(mem, "payload") and mem.payload else None
            if h:
                existing_hashes.add(h)
...
            mem_hash = hashlib.md5(text.encode()).hexdigest()
            if mem_hash in existing_hashes or mem_hash in seen_hashes:
                logger.debug(f"Skipping duplicate memory (hash match): {text[:50]}")
                continue
            seen_hashes.add(mem_hash)
```

Note the hash set is built from `existing_results`, i.e. from the top-10 window of Finding 1, plus duplicates within the current batch.

---

## Finding 3: Extraction-prompt line about duplicates

Paper claim: a line in the extraction prompt is the second write-time dedup mechanism.

`mem0/configs/prompts.py:511` (inside `ADDITIVE_EXTRACTION_PROMPT`, the system/user prompt used by `_add_to_vector_store` at `mem0/memory/main.py:913`):

```text
Use these ONLY for deduplication and linking ... If new information in New Messages is semantically equivalent to an Existing Memory with no meaningful new context, skip it.
```

`mem0/configs/prompts.py:578`:

```text
**When in doubt, extract.** A slightly redundant memory is far less costly than a missing one. The deduplication system downstream will handle true duplicates ...
```

---

## Finding 4: Entity gate, exact name match or cosine >= 0.95; links entities, never merges memories

Paper claim: "an entity gate that matches on exact name or, failing that, cosine similarity of at least 0.95. The gate links entities; it never merges memories."

Single-entity variant, `mem0/memory/main.py:585-598` (inside `_upsert_entity`):

```python
            entity_embedding = self.embedding_model.embed(entity_text, "add")
            search_filters = {k: v for k, v in filters.items() if k in ("user_id", "agent_id", "run_id") and v}
            exact_match = self._existing_entities_by_text(search_filters).get(self._normalize_entity_text(entity_text))

            existing = []
            if exact_match is None:
                existing = self.entity_store.search(
                    query=entity_text,
                    vectors=entity_embedding,
                    top_k=1,
                    filters=search_filters,
                )

            semantic_match = existing[0] if existing and existing[0].score >= 0.95 else None
```

Batch variant on the `add()` path (Phase 7), `mem0/memory/main.py:1119-1131`:

```python
                        entity_type, entity_text, memory_ids = global_entities[key]
                        matches = existing_matches[j] if j < len(existing_matches) else []
                        exact_match = exact_matches.get(key)

                        semantic_match = matches[0] if matches and matches[0].score >= 0.95 else None
                        match = exact_match or semantic_match
                        if match:
                            # Update existing entity
                            payload = match.payload or {}
                            linked = set(payload.get("linked_memory_ids", []))
                            linked |= memory_ids
                            payload["linked_memory_ids"] = sorted(linked)
```

On a match the code only appends memory IDs to the entity's `linked_memory_ids` and updates the entity row; no memory record is merged, rewritten, or deleted anywhere in this branch. The exact-name side of the gate is normalized lowercased whitespace-collapsed text, `mem0/memory/main.py:558-560`:

```python
    @staticmethod
    def _normalize_entity_text(value: str) -> str:
        return " ".join(value.strip().lower().split())
```

The async equivalents are at `mem0/memory/main.py:2253` and `mem0/memory/main.py:2769` (same `>= 0.95` expression).

---

## Finding 5: update() and delete() exist in the API but are off the add() path

Paper claim: "`update()` and `delete()` exist in the API but are off the `add()` path."

API surface, `mem0/memory/main.py:1786-1793`:

```python
    def update(
        self,
        memory_id,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expiration_date: Any = _UNSET,
        data: Optional[str] = None,
    ):
```

`mem0/memory/main.py:1840`:

```python
    def delete(self, memory_id):
```

Caller search over the pinned tree. The sync add path is `add()` plus `_add_to_vector_store()`, lines 736-1178; the async add path is lines 2399-2824 (boundaries confirmed by the method map: `def get` begins at 1179 and `async def get` at 2825).

Command 1 (sync add path):

```
$ sed -n '736,1178p' mem0/memory/main.py | grep -n "self\.update(\|self\.delete(\|self\._update_memory\|self\._delete_memory"
(no matches, exit status 1)
```

Command 2 (async add path):

```
$ sed -n '2399,2824p' mem0/memory/main.py | grep -n "self\.update(\|self\.delete(\|self\._update_memory\|self\._delete_memory"
(no matches, exit status 1)
```

Command 3 (where the internal mutators ARE called):

```
$ grep -n "self\._update_memory(\|self\._delete_memory(" mem0/memory/main.py
1836:        self._update_memory(memory_id, text, existing_embeddings, update_metadata)
1853:        self._delete_memory(memory_id, existing_memory)
1905:                self._delete_memory(memory.id)
3480:        await self._update_memory(memory_id, text, existing_embeddings, update_metadata)
3497:        await self._delete_memory(memory_id, existing_memory)
3551:                self._delete_memory(memory.id, skip_entity_cleanup=True)
```

Lines 1836 and 3480 are inside `update()`; 1853 and 3497 are inside `delete()`; 1905 and 3551 are inside `delete_all()`. None is inside either add path. (The `entity_store.update()` call inside the add path at line 1132 updates an entity-row payload in the vector store; it is not the memory `update()` API. The sibling calls at lines 606 and 671 sit in entity helpers reached from `_update_memory` and `_delete_memory`, again outside the add path.)

---

## Finding 6: DEFAULT_UPDATE_MEMORY_PROMPT reachable only from tests

Paper claim: "A `DEFAULT_UPDATE_MEMORY_PROMPT` survives in the codebase, reachable only from tests."

Definition, `mem0/configs/prompts.py:176-177`:

```python
DEFAULT_UPDATE_MEMORY_PROMPT = """You are a smart memory manager which controls the memory of a system.
You can perform four operations: (1) add into the memory, (2) update the memory, (3) delete from the memory, and (4) no change.
```

Its only production consumer is the wrapper in the same file, `mem0/configs/prompts.py:406-409`:

```python
def get_update_memory_messages(retrieved_old_memory_dict, response_content, custom_update_memory_prompt=None):
    if custom_update_memory_prompt is None:
        global DEFAULT_UPDATE_MEMORY_PROMPT
        custom_update_memory_prompt = DEFAULT_UPDATE_MEMORY_PROMPT
```

Caller search over the entire pinned tree (all file types, not only Python):

```
$ grep -rn "DEFAULT_UPDATE_MEMORY_PROMPT" .
tests/configs/test_prompts.py:19:    assert result.startswith(prompts.DEFAULT_UPDATE_MEMORY_PROMPT)
mem0/configs/prompts.py:176:DEFAULT_UPDATE_MEMORY_PROMPT = """You are a smart memory manager which controls the memory of a system.
mem0/configs/prompts.py:408:        global DEFAULT_UPDATE_MEMORY_PROMPT
mem0/configs/prompts.py:409:        custom_update_memory_prompt = DEFAULT_UPDATE_MEMORY_PROMPT
```

```
$ grep -rn "get_update_memory_messages" .
tests/configs/test_prompts.py:4:def test_get_update_memory_messages():
tests/configs/test_prompts.py:11:    result = prompts.get_update_memory_messages(
tests/configs/test_prompts.py:18:    result = prompts.get_update_memory_messages(retrieved_old_memory_dict, response_content, None)
tests/configs/test_prompts.py:22:def test_get_update_memory_messages_empty_memory():
tests/configs/test_prompts.py:24:    result = prompts.get_update_memory_messages(
tests/configs/test_prompts.py:32:    result = prompts.get_update_memory_messages(
tests/configs/test_prompts.py:40:def test_get_update_memory_messages_non_empty_memory():
tests/configs/test_prompts.py:43:    result = prompts.get_update_memory_messages(
mem0/configs/prompts.py:406:def get_update_memory_messages(retrieved_old_memory_dict, response_content, custom_update_memory_prompt=None):
```

Outside `mem0/configs/prompts.py` itself, every reference to the constant or to its wrapper function is in `tests/configs/test_prompts.py`. Static-reading caveat: dynamic dispatch or downstream packages could still invoke it; none was found in this tree.

---

## Finding 7: expiration_date is caller-supplied and never filled by the system

Paper claim: "The `expiration_date` field is caller-supplied and never filled by the system."

Caller-facing parameter, `mem0/memory/main.py:736-746`:

```python
    def add(
        self,
        messages,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[Any] = None,
        expiration_date: Optional[Any] = None,
        infer: bool = True,
```

Persisted only from that parameter, `mem0/memory/main.py:799-800`:

```python
        if normalized_expiration_date is not None:
            processed_metadata["expiration_date"] = normalized_expiration_date
```

Exhaustive search for every write of the field in the package:

```
$ grep -rn 'expiration_date"\] *=\|"expiration_date":' mem0/ --include="*.py"
mem0/memory/main.py:800:            processed_metadata["expiration_date"] = normalized_expiration_date
mem0/memory/main.py:1830:            update_metadata["expiration_date"] = _normalize_expiration_date(expiration_date)
mem0/memory/main.py:2443:            processed_metadata["expiration_date"] = normalized_expiration_date
mem0/memory/main.py:3473:            update_metadata["expiration_date"] = _normalize_expiration_date(expiration_date)
```

All four sites assign from the `expiration_date` parameter of `add()` (800, 2443) or `update()` (1830, 3473). No code path computes or defaults the value. The system itself only reads it, to hide expired rows, `mem0/memory/main.py:418-425`:

```python
def _payload_is_expired(payload: Optional[Dict[str, Any]]) -> bool:
    if not payload:
        return False
    expiration_date = payload.get("expiration_date")
    if not expiration_date:
        return False
    try:
        return date.fromisoformat(str(expiration_date)) < datetime.now(timezone.utc).date()
```

---

## Finding 8: Entity type stored but not consulted in the match decision

Paper claim: "The gate consults no entity type: type is stored but never read in the match decision."

Stored, `mem0/memory/main.py:1143-1148` (batch path; single path stores it identically at 614-618):

```python
                            to_insert_payloads.append({
                                "data": entity_text,
                                "entity_type": entity_type,
                                "linked_memory_ids": sorted(memory_ids),
                                **search_filters,
                            })
```

Not consulted: the entire match decision is the two lines quoted in Finding 4 (`mem0/memory/main.py:1122-1124` batch, 597-598 single), which reference only the normalized text key and the cosine score. Occurrence search for `entity_type` in the module:

```
$ grep -n "entity_type" mem0/memory/main.py
581:    def _upsert_entity(self, entity_text, entity_type, memory_id, filters):
616:                    "entity_type": entity_type,
694:            for entity_type, entity_text in entities:
700:                    self._upsert_entity(entity_text, entity_type, memory_id, filters)
1063:            global_entities = {}  # normalized_key -> (entity_type, entity_text, set of memory_ids)
1066:                for entity_type, entity_text in entities:
1071:                        global_entities[key] = [entity_type, entity_text, {memory_id}]
1119:                        entity_type, entity_text, memory_ids = global_entities[key]
1145:                                "entity_type": entity_type,
2234:    async def _upsert_entity_async(self, entity_text, entity_type, memory_id, filters):
2271:                    "entity_type": entity_type,
2357:            for entity_type, entity_text in entities:
2363:                    await self._upsert_entity_async(entity_text, entity_type, memory_id, filters)
1718:        for entity_type, entity_text in query_entities[:8]:
1722:                deduped.append((entity_type, entity_text))
2234:    async def _upsert_entity_async(self, entity_text, entity_type, memory_id, filters):
2271:                    "entity_type": entity_type,
2357:            for entity_type, entity_text in entities:
2363:                    await self._upsert_entity_async(entity_text, entity_type, memory_id, filters)
2714:                for entity_type, entity_text in entities:
2719:                        global_entities[key] = [entity_type, entity_text, {memory_id}]
2765:                        entity_type, entity_text, memory_ids = global_entities[key]
2790:                                "entity_type": entity_type,
3359:        for entity_type, entity_text in query_entities[:8]:
3363:                deduped.append((entity_type, entity_text))
```

Lines 1718/1722 and 3359/3363 are query-time entity boosting in `_compute_entity_boosts`, not the write gate. Every occurrence is either a tuple unpack, a passthrough parameter, or a payload write; no occurrence compares `entity_type` values in a match or gate condition. The predicted failure mode built on this (Apple the company fused with apple the fruit at cosine 0.95) is issue mem0#5438; see Non-code sources.

---

## Finding 9: linked_memory_ids links without classification

Paper claim: "contradictions are connected via `linked_memory_ids` to the original memory, but a link is not a classification, and it records no relation between the facts it connects" and (Table 3) "`linked_memory_ids`: a link, no loser, no score."

The stored structure is a bare sorted list of memory UUIDs; there is no relation type field and no score field, `mem0/memory/main.py:1126-1131` (and the insert payload in Finding 8):

```python
                        if match:
                            # Update existing entity
                            payload = match.payload or {}
                            linked = set(payload.get("linked_memory_ids", []))
                            linked |= memory_ids
                            payload["linked_memory_ids"] = sorted(linked)
```

The extraction prompt instructs the LLM to link across several relations, contradiction among them, yet the output schema carries only an ID array, `mem0/configs/prompts.py:694-699`:

```text
When extracting a new memory, check if it relates to any Existing Memory. Add related Existing Memory IDs to "linked_memory_ids". Link when:

- **Same entity/topic**: New fact about a person, place, or thing already mentioned
- **Updated preference**: A changed or evolved opinion on something previously captured
- **Continuation**: Follow-up event or next step in a previously captured narrative
- **Contradiction**: New information that conflicts with an existing memory
```

`mem0/configs/prompts.py:936`:

```text
- **linked_memory_ids** (array of strings, optional): IDs of Existing Memories that this new memory relates to. Use the exact IDs from the Existing Memories list. Omit or pass [] if no existing memories are related.
```

Superseded, concurrent, and contradictory links are therefore stored identically: as members of one untyped array.

---

## Related paper statements covered by the same artifacts

- "Nobody, for conflicts" / "There is no losing record: both facts are stored, and the earlier one is untouched": Findings 2, 5, and 6 jointly evidence the code side (the only write-time suppression is the exact MD5 hash and the prompt line; the LLM conflict-resolution path is not reachable from `add()`); the policy statement itself is documentation, see Non-code sources.
- "Three mechanisms coexist at write time": Findings 2 (MD5), 3 (prompt line), 4 (entity gate).

## Non-code sources (listed per the paper; not fetched for this file)

1. https://github.com/mem0ai/mem0/issues/5438, retrieved 2026-08-03. Argues that with type ignored in the gate, Apple the company and apple the fruit can be fused at cosine 0.95 (a predicted failure mode, not an observed one).
2. https://github.com/mem0ai/mem0/issues/4896, retrieved 2026-08-03. Maintainer closes as by-design: "[b]oth memories being stored is intentional"; "the historical record has value"; contradictions are "connected via linked_memory_ids to the original memory."
3. https://docs.mem0.ai/core-concepts/memory-evaluation, retrieved 2026-08-03. Policy statement: "New facts are stored alongside old ones. Nothing is overwritten or deleted." Also current benchmark figures (92.5 LoCoMo, 94.4 LongMemEval).
4. https://docs.mem0.ai/migration/oss-v2-to-v3, retrieved 2026-08-03. Attributes score gains to a bundle including removal of the UPDATE/DELETE conflict-resolution path plus hybrid BM25, entity boost, and entity linking.
5. https://github.com/mem0ai/memory-benchmarks, retrieved 2026-08-03. Public evaluation harness; no third-party reproduction found among the sources the paper reviewed.
6. Mem0 paper (Chhikara et al. 2025, cited as chhikara2025mem0): the paper's reference list contains no entry on entity resolution, record linkage, deduplication, or data fusion (a count performed during the review, independently checkable).
7. Mem0 Platform "Temporal Reasoning": hosted-platform capability, not inspectable from source; scoped accordingly in the paper.

## Not located / scope notes

- Nothing the paper names for Mem0 failed to locate at this commit. All nine code claims resolved to artifacts quoted above.
- Static-reading caveat (as the paper itself states): dead-path conclusions (Findings 5 and 6) hold under caller search of the pinned tree; dynamic dispatch, plugin registration, or downstream packages could still exercise them.
- The `mem0-ts/` TypeScript client and `server/` directory were included in the whole-tree searches of Findings 5 and 6; no additional callers were found there.
