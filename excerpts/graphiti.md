# Graphiti: source excerpts for "Merge Without Measure"

- System: Graphiti (getzep/graphiti), the open-source engine underlying Zep
- Version: 0.29.3 (pyproject.toml line 4: `version = "0.29.3"`)
- Commit (full SHA): `7cf0cab4b43f55d768b64584ffa9829bbeec1e9d` (committed 2026-08-01)
- Upstream license: Apache License 2.0 (repository `LICENSE` file; per-file headers read "Copyright 2024, Zep Software, Inc. Licensed under the Apache License, Version 2.0")
- Extraction date: 2026-08-16

Snippets are short verbatim quotations from the upstream repository at the pinned commit, reproduced for review and criticism; copyright remains with the upstream authors.

All paths are relative to the repository root at the pinned commit. All grep commands below were run from the repository root of the pinned tree.

---

## 1. Blocking window: top-15 candidate search by name embedding at a cosine floor of 0.6

Paper claim: "Candidate generation retrieves the top 15 nodes by name embedding at a cosine floor of 0.6."

`graphiti_core/utils/maintenance/node_operations.py:64-65`

```python
NODE_DEDUP_CANDIDATE_LIMIT = 15
NODE_DEDUP_COSINE_MIN_SCORE = 0.6
```

`graphiti_core/utils/maintenance/node_operations.py:418-446` (search over the name embedding, passing both constants)

```python
async def _semantic_candidate_search(
    clients: GraphitiClients,
    extracted_nodes: list[EntityNode],
) -> list[list[EntityNode]]:
    """Run direct cosine similarity search per extracted node without reranking."""
    ...
    queries = [node.name.replace('\n', ' ') for node in extracted_nodes]
    ...
                node_similarity_search(
                    clients.driver,
                    query_vector,
                    SearchFilters(),
                    [node.group_id],
                    NODE_DEDUP_CANDIDATE_LIMIT,
                    NODE_DEDUP_COSINE_MIN_SCORE,
                )
```

The driver-level default for the same floor, e.g. `graphiti_core/driver/neo4j/operations/search_ops.py:135`: `min_score: float = 0.6,` (same default at lines 293 and 489, and in the falkordb, kuzu, neptune, and search_interface drivers).

---

## 2. dedup_helpers.py pipeline: 3-gram shingles -> MinHash -> LSH banding -> auto-merge at Jaccard >= 0.9

Paper claim: "a deterministic ladder consisting of an entropy gate, then MinHash over 3-gram shingles with LSH banding, then an automatic merge at Jaccard similarity of at least 0.9, with an LLM deciding pairs that fall below it."

`graphiti_core/utils/maintenance/dedup_helpers.py:88-94` (3-gram shingles)

```python
def _shingles(normalized_name: str) -> set[str]:
    """Create 3-gram shingles from the normalized name for MinHash calculations."""
    cleaned = normalized_name.replace(' ', '')
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()

    return {cleaned[i : i + 3] for i in range(len(cleaned) - 2)}
```

`graphiti_core/utils/maintenance/dedup_helpers.py:103-114` (MinHash signature; trimmed)

```python
def _minhash_signature(shingles: Iterable[str]) -> tuple[int, ...]:
    """Compute the MinHash signature for the shingle set across predefined permutations."""
    ...
    seeds = range(_MINHASH_PERMUTATIONS)
    signature: list[int] = []
    for seed in seeds:
        min_hash = min(_hash_shingle(shingle, seed) for shingle in shingles)
        signature.append(min_hash)
```

`graphiti_core/utils/maintenance/dedup_helpers.py:117-128` (LSH banding; trimmed)

```python
def _lsh_bands(signature: Iterable[int]) -> list[tuple[int, ...]]:
    """Split the MinHash signature into fixed-size bands for locality-sensitive hashing."""
    ...
    for start in range(0, len(signature_list), _MINHASH_BAND_SIZE):
        band = tuple(signature_list[start : start + _MINHASH_BAND_SIZE])
        if len(band) == _MINHASH_BAND_SIZE:
            bands.append(band)
    return bands
```

`graphiti_core/utils/maintenance/dedup_helpers.py:255-279` (automatic merge at Jaccard >= 0.9; pairs below the gate go to `state.unresolved_indices`, which `resolve_extracted_nodes` routes to the LLM; trimmed)

```python
        # --- fuzzy matching via MinHash/LSH ---
        shingles = _cached_shingles(normalized_fuzzy)
        signature = _minhash_signature(shingles)
        ...
        if best_candidate is not None and best_score >= _FUZZY_JACCARD_THRESHOLD:
            best_candidate = _promote_resolved_node(node, best_candidate)
            state.resolved_nodes[idx] = best_candidate
            state.uuid_map[node.uuid] = best_candidate.uuid
            if best_candidate.uuid != node.uuid:
                state.duplicate_pairs.append((node, best_candidate))
            continue

        state.unresolved_indices.append(idx)
```

LLM fallback for the unresolved remainder, `graphiti_core/utils/maintenance/node_operations.py:672-689` (trimmed):

```python
    if state.unresolved_indices:
        llm_candidate_nodes = _merge_candidate_nodes(
            ...
        )
        await _resolve_with_llm(
            llm_client,
            extracted_nodes,
            ...
        )
```

---

## 3. Six magic constants, zero citations

Paper claim: "dedup_helpers.py contains six unexplained constants and zero citations."

`graphiti_core/utils/maintenance/dedup_helpers.py:31-36` (the six module constants)

```python
_NAME_ENTROPY_THRESHOLD = 1.5
_MIN_NAME_LENGTH = 6
_MIN_TOKEN_COUNT = 2
_FUZZY_JACCARD_THRESHOLD = 0.9
_MINHASH_PERMUTATIONS = 32
_MINHASH_BAND_SIZE = 4
```

Citation search over the file (the only URL in the file is the Apache license URL in the copyright header):

```
$ grep -n "http\|doi\|arXiv\|et al" graphiti_core/utils/maintenance/dedup_helpers.py
8:    http://www.apache.org/licenses/LICENSE-2.0
```

The full file (297 lines) was read; no reference, citation, or derivation accompanies any of the six constants.

---

## 4. Entropy gate deferring low-entropy names to the LLM

Paper claim: "Graphiti's entropy gate is a de facto abstain path, deferring low-entropy names to the LLM instead of to fuzzy similarity."

`graphiti_core/utils/maintenance/dedup_helpers.py:52-59` (the intent is stated in the docstring)

```python
def _name_entropy(normalized_name: str) -> float:
    """Approximate text specificity using Shannon entropy over characters.

    We strip spaces, count how often each character appears, and sum
    probability * -log2(probability). Short or repetitive names yield low
    entropy, which signals we should defer resolution to the LLM instead of
    trusting fuzzy similarity.
    """
```

`graphiti_core/utils/maintenance/dedup_helpers.py:79-85` (the gate)

```python
def _has_high_entropy(normalized_name: str) -> bool:
    """Filter out very short or low-entropy names that are unreliable for fuzzy matching."""
    token_count = len(normalized_name.split())
    if len(normalized_name) < _MIN_NAME_LENGTH and token_count < _MIN_TOKEN_COUNT:
        return False

    return _name_entropy(normalized_name) >= _NAME_ENTROPY_THRESHOLD
```

`graphiti_core/utils/maintenance/dedup_helpers.py:250-253` (a name failing the gate skips fuzzy matching and joins the unresolved set that goes to the LLM, see finding 2)

```python
        # --- entropy gate (protects fuzzy matching only) ---
        if not _has_high_entropy(normalized_fuzzy):
            state.unresolved_indices.append(idx)
            continue
```

---

## 5. add_episode unpacks resolve_extracted_nodes and discards the third element, the merge record

Paper claim: "add_episode unpacks the return of resolve_extracted_nodes as nodes, uuid_map, _, discarding the third element, the merge record."

Return type of `resolve_extracted_nodes`, `graphiti_core/utils/maintenance/node_operations.py:627-635` (trimmed): the third element is the list of duplicate pairs.

```python
async def resolve_extracted_nodes(
    clients: GraphitiClients,
    extracted_nodes: list[EntityNode],
    ...
) -> tuple[list[EntityNode], dict[str, str], list[tuple[EntityNode, EntityNode]]]:
```

And its return statement, `graphiti_core/utils/maintenance/node_operations.py:704-708`:

```python
    return (
        [node for node in state.resolved_nodes if node is not None],
        state.uuid_map,
        state.duplicate_pairs,
    )
```

The unpacking inside `add_episode` (method defined at `graphiti_core/graphiti.py:980`), `graphiti_core/graphiti.py:1131-1137`:

```python
                nodes, uuid_map, _ = await resolve_extracted_nodes(
                    self.clients,
                    extracted_nodes,
                    episode,
                    previous_episodes,
                    entity_types,
                )
```

Note on precision: `uuid_map` is retained in memory and used only to re-point edges; the third element, the explicit list of (extracted node, canonical node) duplicate pairs, is bound to `_` and discarded. Neither is persisted to the graph (see findings 7 and 9).

---

## 6. The one helper that preserves duplicates has zero callers (dead-code claim)

Paper claim: "the one helper that preserves duplicates has zero callers."

The helper is `_extract_and_resolve_nodes`, `graphiti_core/graphiti.py:604-629` (trimmed), which unpacks and returns all three elements including `duplicates`:

```python
    async def _extract_and_resolve_nodes(
        self,
        episode: EpisodicNode | list[EpisodicNode],
        ...
    ) -> tuple[
        list[EntityNode], dict[str, str], list[tuple[EntityNode, EntityNode]], dict[str, list[int]]
    ]:
        """Extract nodes from episode(s) and resolve against existing graph."""
        ...
        nodes, uuid_map, duplicates = await resolve_extracted_nodes(
            ...
        )

        return nodes, uuid_map, duplicates, node_episode_index_map
```

Caller search over the pinned tree (full output; the sole hit is the definition itself):

```
$ grep -rn "_extract_and_resolve_nodes" .
graphiti_core/graphiti.py:604:    async def _extract_and_resolve_nodes(
```

---

## 7. The bulk path keeps uuid_map in memory only, to compress UUIDs

Paper claim: "the bulk path keeps duplicate pairs in memory only, to compress UUIDs."

`graphiti_core/utils/bulk_utils.py:374-379` and `404-411` (dedupe_nodes_bulk collects the pairs; trimmed)

```python
async def dedupe_nodes_bulk(
    clients: GraphitiClients,
    extracted_nodes: list[list[EntityNode]],
    episode_tuples: list[tuple[EpisodicNode, list[EpisodicNode]]],
    entity_types: dict[str, type[BaseModel]] | None = None,
) -> tuple[dict[str, list[EntityNode]], dict[str, str]]:
    ...
    per_episode_uuid_maps: list[dict[str, str]] = []
    duplicate_pairs: list[tuple[str, str]] = []

    for (resolved_nodes, uuid_map, duplicates), (episode, _) in zip(
        first_pass_results, episode_tuples, strict=True
    ):
        ...
        duplicate_pairs.extend((source.uuid, target.uuid) for source, target in duplicates)
```

`graphiti_core/utils/bulk_utils.py:459-463` and `486` (pairs are folded into an in-memory union-find map and returned; nothing is written to the graph)

```python
    for uuid_map in per_episode_uuid_maps:
        union_pairs.extend(uuid_map.items())
    union_pairs.extend(duplicate_pairs)

    compressed_map: dict[str, str] = _build_directed_uuid_map(union_pairs)
    ...
    return nodes_by_episode, compressed_map
```

The map's only downstream use is pointer compression, `graphiti_core/utils/bulk_utils.py:627-632`:

```python
def resolve_edge_pointers(edges: list[E], uuid_map: dict[str, str]):
    for edge in edges:
        source_uuid = edge.source_node_uuid
        target_uuid = edge.target_node_uuid
        edge.source_node_uuid = uuid_map.get(source_uuid, source_uuid)
        edge.target_node_uuid = uuid_map.get(target_uuid, target_uuid)
```

Supporting search: `grep -rn "uuid_map" graphiti_core/ --include="*.py"` restricted to files outside `graphiti_core/utils/` and `graphiti_core/graphiti.py` returns only local variables in `graphiti_core/search/search.py` and `search_utils.py` (in-memory lookup dicts inside search reranking, unrelated to dedup); no driver, model, or persistence code receives the dedup uuid_map or duplicate pairs. `grep -rn "duplicate_pairs" graphiti_core/` hits only `bulk_utils.py`, `dedup_helpers.py`, and `node_operations.py`, none of which persist them.

---

## 8. filter_existing_duplicate_of_edges is called only from a test (dead-code claim)

Paper claim: "filter_existing_duplicate_of_edges is called only from a test."

Definition, `graphiti_core/utils/maintenance/edge_operations.py:850-852` (trimmed):

```python
async def filter_existing_duplicate_of_edges(
    driver: GraphDriver, duplicates_node_tuples: list[tuple[EntityNode, EntityNode]]
) -> list[tuple[EntityNode, EntityNode]]:
```

Caller search over the pinned tree (full output; the only call site is `tests/test_graphiti_mock.py:587`):

```
$ grep -rn "filter_existing_duplicate_of_edges" .
tests/test_graphiti_mock.py:56:from graphiti_core.utils.maintenance.edge_operations import filter_existing_duplicate_of_edges
tests/test_graphiti_mock.py:529:async def test_filter_existing_duplicate_of_edges(graph_driver, mock_embedder):
tests/test_graphiti_mock.py:587:    node_tuples = await filter_existing_duplicate_of_edges(graph_driver, duplicate_node_tuples)
graphiti_core/utils/maintenance/edge_operations.py:850:async def filter_existing_duplicate_of_edges(
```

---

## 9. Nothing in graphiti_core creates an IS_DUPLICATE_OF edge (dead-code claim)

Paper claim: "nothing in graphiti_core creates an IS_DUPLICATE_OF edge."

Search over the pinned tree (full output):

```
$ grep -rn "IS_DUPLICATE_OF" graphiti_core/
graphiti_core/utils/maintenance/edge_operations.py:863:            MATCH (n:Entity {uuid: duplicate_tuple.source})-[r:RELATES_TO {name: 'IS_DUPLICATE_OF'}]->(m:Entity {uuid: duplicate_tuple.target})
graphiti_core/utils/maintenance/edge_operations.py:883:                MATCH (n:Entity {uuid: duplicate.src})-[:RELATES_TO]->(e:RelatesToNode_ {name: 'IS_DUPLICATE_OF'})-[:RELATES_TO]->(m:Entity {uuid: duplicate.dst})
graphiti_core/utils/maintenance/edge_operations.py:892:                MATCH (n:Entity {uuid: duplicate_tuple[0]})-[r:RELATES_TO {name: 'IS_DUPLICATE_OF'}]->(m:Entity {uuid: duplicate_tuple[1]})
graphiti_core/utils/maintenance/edge_operations.py:905:    # Remove duplicates that already have the IS_DUPLICATE_OF edge

$ grep -rln "IS_DUPLICATE_OF" .
tests/test_graphiti_mock.py
graphiti_core/utils/maintenance/edge_operations.py
```

All four occurrences in `graphiti_core` are inside `filter_existing_duplicate_of_edges` (itself called only from a test, finding 8), and all are read-only `MATCH` queries. No `CREATE` or `MERGE` of an `IS_DUPLICATE_OF` edge exists anywhere in `graphiti_core` at this commit.

---

## 10. Edges are never deleted; invalidated edges receive invalid_at

Paper claim: "Edges are never deleted; invalidated edges receive an invalid_at timestamp."

Deletion search over the edge write path (no matches; grep exit code 1):

```
$ grep -n "delete\|DELETE" graphiti_core/utils/maintenance/edge_operations.py
exit=1
```

Invalidation instead of deletion, `graphiti_core/utils/maintenance/edge_operations.py:564-571` (inside `resolve_edge_contradictions`):

```python
        elif (
            edge_valid_at_utc is not None
            and resolved_edge_valid_at_utc is not None
            and edge_valid_at_utc < resolved_edge_valid_at_utc
        ):
            edge.invalid_at = resolved_edge.valid_at
            edge.expired_at = edge.expired_at if edge.expired_at is not None else utc_now()
            invalidated_edges.append(edge)
```

The invalidated edges are then written back to the graph rather than removed, `graphiti_core/graphiti.py:1156` (inside `add_episode`):

```python
                entity_edges = resolved_edges + invalidated_edges
```

followed by persistence via `_process_episode_data`, `graphiti_core/graphiti.py:726-733`:

```python
        await add_nodes_and_edges_bulk(
            self.driver,
            episodes,
            episodic_edges,
            nodes,
            entity_edges,
            self.embedder,
        )
```

---

## 11. The losing node is never persisted

Paper claim: "A losing node, however, is never persisted."

When a duplicate is detected, the canonical (existing) node replaces the extracted node in the resolution slot; the extracted node survives only inside the in-memory `duplicate_pairs` list, `graphiti_core/utils/maintenance/dedup_helpers.py:236-243` (exact-match branch; the fuzzy branch at lines 271-277 is identical in structure):

```python
        existing_matches = indexes.normalized_existing.get(normalized_exact, [])
        if len(existing_matches) == 1:
            match = _promote_resolved_node(node, existing_matches[0])
            state.resolved_nodes[idx] = match
            state.uuid_map[node.uuid] = match.uuid
            if match.uuid != node.uuid:
                state.duplicate_pairs.append((node, match))
            continue
```

`add_episode` persists only the resolved winners: `nodes` from finding 5 are hydrated (`graphiti_core/graphiti.py:1160-1168`, `extract_attributes_from_nodes(self.clients, nodes, ...)`) and those hydrated nodes are what `_process_episode_data` saves (finding 10 snippet, the `nodes` argument of `add_nodes_and_edges_bulk`). The extracted losing node appears in no save call; the `duplicate_pairs` that reference it are discarded (finding 5) or kept in memory only (finding 7).

---

## 12. The surviving entity's summary is overwritten

Paper claim: "the surviving entity's summary is overwritten."

`graphiti_core/utils/maintenance/node_operations.py:870-878` (non-LLM path appends edge facts and assigns; trimmed)

```python
        # Build summary with edge facts appended
        summary_with_edges = node.summary
        if node_edges:
            edge_facts = '\n'.join(edge.fact for edge in node_edges if edge.fact)
            summary_with_edges = f'{summary_with_edges}\n{edge_facts}'.strip()

        # If summary is close to the persisted limit, use it directly (append edge facts, no LLM call)
        if summary_with_edges and len(summary_with_edges) <= MAX_SUMMARY_CHARS * 2:
            node.summary = summary_with_edges
```

`graphiti_core/utils/maintenance/node_operations.py:993-999` (LLM path assigns the regenerated summary onto the node; trimmed)

```python
    summaries_response = SummarizedEntities(**llm_response)
    for summarized_entity in summaries_response.summaries:
        matching_nodes = name_to_nodes.get(summarized_entity.name.lower(), [])
        if matching_nodes:
            truncated_summary = truncate_at_sentence(summarized_entity.summary, MAX_SUMMARY_CHARS)
            for node in matching_nodes:
                node.summary = truncated_summary
```

In both paths the assignment replaces `node.summary` in place on the surviving canonical node; no prior summary version is stored.

---

## 13. An LLM nominates contradicted_facts; a rule of roughly thirty lines decides; contradicted_facts drives invalid_at

Paper claim: "an LLM nominates contradicted_facts and a rule of roughly thirty lines decides; contradicted_facts drives invalid_at, so a fact whose contradiction the model misses survives unsurfaced."

The LLM output field, `graphiti_core/prompts/dedupe_edges.py:29-32` (inside `class EdgeDuplicate(BaseModel)`):

```python
    contradicted_facts: list[int] = Field(
        ...,
        description='List of idx values of contradicted facts (from full idx range). Empty list if none.',
    )
```

The nominations become invalidation candidates, `graphiti_core/utils/maintenance/edge_operations.py:754-776` (inside `resolve_extracted_edge`; trimmed):

```python
    # Process contradicted facts (continuous indexing across both lists)
    contradicted_facts: list[int] = response_object.contradicted_facts
    invalidation_candidates: list[EntityEdge] = []
    ...
        # Split contradicted facts into those from related_edges vs existing_edges based on offset
        for idx in contradicted_facts:
            if 0 <= idx < len(related_edges):
                # From EXISTING FACTS (duplicate candidates)
                invalidation_candidates.append(related_edges[idx])
            elif invalidation_idx_offset <= idx <= max_valid_idx:
                # From FACT INVALIDATION CANDIDATES (adjust index by offset)
                invalidation_candidates.append(existing_edges[idx - invalidation_idx_offset])
```

The deciding rule, `graphiti_core/utils/maintenance/edge_operations.py:538-574` (`resolve_edge_contradictions`, 37 lines end to end; header and decision shown, body trimmed):

```python
def resolve_edge_contradictions(
    resolved_edge: EntityEdge, invalidation_candidates: list[EntityEdge]
) -> list[EntityEdge]:
    if len(invalidation_candidates) == 0:
        return []

    # Determine which contradictory edges need to be expired
    invalidated_edges: list[EntityEdge] = []
    for edge in invalidation_candidates:
        ...
            edge.invalid_at = resolved_edge.valid_at
            edge.expired_at = edge.expired_at if edge.expired_at is not None else utc_now()
            invalidated_edges.append(edge)

    return invalidated_edges
```

Wired together at `graphiti_core/utils/maintenance/edge_operations.py:842-844`:

```python
    invalidated_edges: list[EntityEdge] = resolve_edge_contradictions(
        resolved_edge, invalidation_candidates
    )
```

Because `invalidation_candidates` is populated exclusively from `response_object.contradicted_facts`, an edge the model fails to nominate never reaches `resolve_edge_contradictions` and never receives `invalid_at`.

---

## Non-code sources

The following claims in the paper's Graphiti section rest on GitHub issue threads and vendor artifacts, not on code at the pinned commit. Listed with the retrieval dates the paper gives; not fetched for this file.

- Maintainer describes a "small model" classifier, gpt-4.1-nano in Zep's implementation: https://github.com/getzep/graphiti/issues/467 (filed 2025-05-10; maintainer comment posted 2025-05-22; retrieved 2026-08-03).
- Open feature request for surfacing contradictions ("we can identify such contradictions, flag them, and alert on them... Only the owner of the data can say what is the right thing to do"): https://github.com/getzep/graphiti/issues/934 (open since 2025-09-25; retrieved 2026-08-03).
- User report of a paraphrase classified as contradicting news ("Duplicates are categorized as new relationships temporally replacing the older one"): https://github.com/getzep/graphiti/issues/1101 (opened 2025-12-10, no maintainer response as of retrieval; retrieved 2026-08-03).
- User-run evaluation, five cases with three replicates (15 calls), stock schema 7/15 overall and 1/3 on a clear two-fact contradiction, 14/15 for a reasoning-first variant: https://github.com/getzep/graphiti/issues/1666 (filed 2026-07-18; retrieved 2026-08-03).
- The Zep paper's reference list containing no entry on entity resolution, record linkage, deduplication, or data fusion: rasmussen2025zep, cited in the paper's bibliography (a reading of the paper, not of this repository).
