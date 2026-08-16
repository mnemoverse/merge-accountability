# GraphRAG - evidence excerpts

- System: Microsoft GraphRAG
- Version: v3.1.1
- Commit: `14a00ad88fc33cf2b52f4f113f25807556f8e25e` (release commit "Release v3.1.1 (#2458)", 2026-07-17)
- Upstream license: MIT License (Copyright (c) Microsoft Corporation), per `LICENSE` at the pinned commit
- Extraction date: 2026-08-16

Snippets are short verbatim quotations from the upstream repository at the pinned commit, reproduced for review and criticism; copyright remains with the upstream authors.

All paths are relative to the repository root at the pinned commit.

---

## Finding 1: Exact uppercased string match as entity identity at index time

Paper claim: GraphRAG matches entities by exact uppercased string equality at index time; there is no fuzzy stage and no threshold.

Entity names are uppercased at extraction time, before any grouping:

`packages/graphrag/graphrag/index/operations/extract_graph/graph_extractor.py:145-150`

```python
            if record_type == '"entity"' and len(record_attributes) >= 4:
                entity_name = clean_str(record_attributes[1].upper())
                entity_type = clean_str(record_attributes[2].upper())
                entity_description = clean_str(record_attributes[3])
                entities.append({
                    "title": entity_name,
```

The only normalization besides `.upper()` is HTML unescape plus control-character stripping; no fuzzy comparison of any kind:

`packages/graphrag/graphrag/index/utils/string.py:11-19`

```python
def clean_str(input: Any) -> str:
    """Clean an input string by removing HTML escapes, control characters, and other unwanted characters."""
    # If we get non-string input, just give it back
    if not isinstance(input, str):
        return input

    result = html.unescape(input.strip())
    # https://stackoverflow.com/questions/4324790/removing-control-characters-from-a-string-in-python
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", result)
```

Grouping is a pandas `groupby` on the (already uppercased) title string; equality of that string is the entire matcher:

`packages/graphrag/graphrag/index/operations/extract_graph/extract_graph.py:104-115`

```python
def _merge_entities(entity_dfs) -> pd.DataFrame:
    all_entities = pd.concat(entity_dfs, ignore_index=True)
    return (
        all_entities
        .groupby(["title", "type"], sort=False)
        .agg(
            description=("description", list),
            text_unit_ids=("source_id", list),
            frequency=("source_id", "count"),
        )
        .reset_index()
    )
```

The incremental-update path uses the same identity: a join and a groupby on exact `title` equality (despite the word "resolve" in the function name, no similarity computation occurs):

`packages/graphrag/graphrag/index/update/entities.py:33-39` (and the `groupby("title")` at line 52)

```python
    # If a title exists in A and B, make a dictionary for {B.id : A.id}
    merged = delta_entities_df[["id", "title"]].merge(
        old_entities_df[["id", "title"]],
        on="title",
        suffixes=("_B", "_A"),
    )
    id_mapping = dict(zip(merged["id_B"], merged["id_A"], strict=True))
```

---

## Finding 2: Conflicts get one prompt sentence

Paper claim: conflicts get one sentence in the summarization prompt; at index time an LLM writes a new summary over the collected descriptions.

The one sentence is line 10 of the default summarization prompt:

`packages/graphrag/graphrag/prompts/index/summarize_descriptions.py:6-12` (the sentence is line 10)

```python
SUMMARIZE_PROMPT = """
You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or more entities, and a list of descriptions, all related to the same entity or group of entities.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity names so we have the full context.
Limit the final description length to {max_length} words.
```

The same sentence appears verbatim in the prompt-tuning template at `packages/graphrag/graphrag/prompt_tune/template/entity_summarization.py:11`.

---

## Finding 3: Descriptions arrive alphabetically sorted and undated

Paper claim: the collected entity descriptions arrive at the LLM alphabetically sorted and undated, so the model sees neither temporal order nor arrival order.

Sort 1: arrival order is destroyed before the summarizer is even called; per-entity description lists are deduplicated and sorted:

`packages/graphrag/graphrag/index/operations/summarize_descriptions/summarize_descriptions.py:50-58` (same pattern for edges at line 73)

```python
        node_futures = [
            do_summarize_descriptions(
                str(row.title),  # type: ignore
                sorted(set(row.description)),  # type: ignore
                ticker,
                semaphore,
            )
            for row in nodes.itertuples(index=False)
        ]
```

Sort 2: the extractor sorts again defensively:

`packages/graphrag/graphrag/index/operations/summarize_descriptions/description_summary_extractor.py:85-87`

```python
        # Sort description lists
        if len(descriptions) > 1:
            descriptions = sorted(descriptions)
```

Sort 3: a third sort at the moment the prompt is formatted for the LLM:

`packages/graphrag/graphrag/index/operations/summarize_descriptions/description_summary_extractor.py:123-130`

```python
        """Summarize descriptions using the LLM."""
        response: LLMCompletionResponse = await self._model.completion_async(
            messages=self._summarization_prompt.format(**{
                ENTITY_NAME_KEY: json.dumps(id, ensure_ascii=False),
                DESCRIPTION_LIST_KEY: json.dumps(
                    sorted(descriptions), ensure_ascii=False
                ),
                MAX_LENGTH_KEY: self._max_summary_length,
```

Undated: descriptions are carried as bare strings with no timestamp attached. The `_merge_entities` aggregation (Finding 1 snippet, `description=("description", list)`) collects plain strings, and the final entity table schema contains no date or timestamp column:

`packages/graphrag/graphrag/data_model/schemas.py:70-79`

```python
ENTITIES_FINAL_COLUMNS = [
    ID,
    SHORT_ID,
    TITLE,
    TYPE,
    DESCRIPTION,
    TEXT_UNIT_IDS,
    NODE_FREQUENCY,
    NODE_DEGREE,
]
```

(For contrast, dates do exist elsewhere in the data model: documents carry `creation_date` and covariates carry `start_date`/`end_date`, `schemas.py:126-160`; entities and their descriptions carry none.)

---

## Finding 4: No entity resolution step at this version

Paper claim: the project previously contained an entity resolution step and removed it; the step is still absent at v3.1.1.

Resolver search 1: names containing "resolution"/"resolve entities" over the pinned tree.

Command (run from the repo root at the pinned commit):

```
grep -rni "entity_resolution\|entity resolution\|resolve_entities\|resolve_entity" packages --include="*.py"
```

Full output:

```
packages/graphrag/graphrag/index/update/entities.py:14:def _group_and_resolve_entities(
packages/graphrag/graphrag/index/workflows/update_entities_relationships.py:23:from graphrag.index.update.entities import _group_and_resolve_entities
packages/graphrag/graphrag/index/workflows/update_entities_relationships.py:73:    merged_entities_df, entity_id_mapping = _group_and_resolve_entities(
```

All three hits are the incremental-update helper `_group_and_resolve_entities`, whose body (Finding 1, last snippet) is exact `title` string equality: a `merge(on="title")` and a `groupby("title")`. It performs no similarity computation and is not an entity resolution step in the record-linkage sense.

Resolver search 2: any fuzzy or similarity matcher anywhere in the Python packages.

Command:

```
grep -rni "levenshtein\|fuzzy\|jaro\|minhash\|jaccard" packages --include="*.py"
```

Full output: (no matches; exit status 1)

Resolver search 3: files containing "resolution" at all.

Command:

```
grep -rli "resolution" packages --include="*.py"
```

Full output:

```
packages/graphrag/graphrag/graphs/hierarchical_leiden.py
packages/graphrag/graphrag/graphs/modularity.py
packages/graphrag-storage/graphrag_storage/tables/cosmos_table_provider.py
```

All three uses are the Leiden clustering "resolution" parameter or unrelated storage code, not entity resolution.

Resolver search 4: the index operations directory contains no resolution module.

Command:

```
ls packages/graphrag/graphrag/index/operations/
```

Full output:

```
__init__.py
build_noun_graph
cluster_graph.py
compute_edge_combined_degree.py
embed_text
extract_covariates
extract_graph
finalize_community_reports.py
finalize_entities.py
finalize_relationships.py
prune_graph.py
snapshot_graphml.py
summarize_communities
summarize_descriptions
```

Conclusion of the search: at commit `14a00ad88fc33cf2b52f4f113f25807556f8e25e` there is no entity resolution step; entity identity is exact uppercased string equality throughout (initial index and incremental update).

---

## Non-code sources

These claims rest on documentation or issue threads; per instructions they were not re-fetched for this file.

1. Maintainer statement that an entity resolution step existed and was removed: GitHub Discussion #778, "left over from an entity resolution step we had in the codebase but were not happy with." URL: https://github.com/microsoft/graphrag/discussions/778. Retrieval date given by the paper: 2026-08-03.

2. The GraphRAG paper's own description "exact string matching for entity matching": Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization," arXiv:2404.16130 (cited in the paper as edge2024graphrag).
