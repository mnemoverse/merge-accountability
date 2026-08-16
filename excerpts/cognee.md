# Cognee: evidence excerpts

- System: Cognee (topoteretes/cognee)
- Version: v1.4.1
- Commit (full SHA): 38eece5bbb0cb9f5706fed908abd16dba0f5505e
- Upstream license: Apache License 2.0 (repository file `LICENSE`)
- Extraction date: 2026-08-16

Snippets are short verbatim quotations from the upstream repository at the pinned commit, reproduced for review and criticism; copyright remains with the upstream authors.

All paths below are relative to the repository root at the pinned commit. Local pinned tree: `/private/tmp/claude-501/-Volumes-SSD960GB-Projects-mnemoverse-mnemoverse-docs/928c2a95-7e21-4084-be8f-3d80f9b1e0ad/scratchpad/upstream-pins/cognee/`.

## Finding 1: Entity identity is a uuid5 of a lowercased name

Paper claim: "Identity is the uuid5 of a lowercased name; equality of that UUID is the entire matcher." (main.tex, subsection Cognee, "Matching threshold and algorithm"; also Table 2 row and Section 1.)

At this commit the derivation is split across three artifacts: a legacy bare-name hasher, the DataPoint identity machinery that stays byte-aligned with it, and the Entity model that declares `name` as its only identity field. The extraction path calls `Entity.id_for(name)`, which is `uuid5(NAMESPACE_OID, "Entity:" + lowercased-normalized-name)`. Accuracy note: at this pin the uuid5 input carries a class-name prefix ("Entity:") in addition to the lowercased name; the substance of the claim (identity is a deterministic uuid5 of a lowercase-normalized name string, and equality of that UUID is the entire matcher) holds unchanged.

`cognee/infrastructure/engine/utils/generate_node_id.py:4-5` (the legacy bare-name form):

```python
def generate_node_id(node_id: str) -> UUID:
    return uuid5(NAMESPACE_OID, node_id.lower().replace(" ", "_").replace("'", ""))
```

`cognee/infrastructure/engine/models/DataPoint.py:146-157` (normalization, docstring trimmed):

```python
    @staticmethod
    def _normalize_identity_value(value: Any) -> str:
        """Normalize a single identity value (lower-case, spaces→_, strip apostrophes).
        ...
        """
        if isinstance(value, str):
            return value.lower().replace(" ", "_").replace("'", "")
        return str(value)
```

`cognee/infrastructure/engine/models/DataPoint.py:159-176` (id derivation, docstring trimmed):

```python
    @classmethod
    def id_for(cls, *values: Any) -> UUID:
        ...
        joined = "|".join(cls._normalize_identity_value(value) for value in values)
        return uuid5(NAMESPACE_OID, f"{cls.__name__}:{joined}")
```

`cognee/modules/engine/models/Entity.py:7-20` (name is the only identity field; comment lines trimmed):

```python
class Entity(DataPoint):
    name: str
    is_a: Optional[EntityType] = None
    description: str
    relations: List[tuple] = []
    ...
    metadata: dict = {"index_fields": ["name"], "identity_fields": ["name"]}
```

`cognee/modules/graph/utils/expand_with_nodes_and_edges.py:192` (the extraction path computes identity rather than searching for it):

```python
    generated_node_id = Entity.id_for(node_id)
```

The stored display name is also lowercased, `cognee/modules/engine/utils/generate_node_name.py:1-2`:

```python
def generate_node_name(name: str) -> str:
    return name.lower().replace("'", "")
```

## Finding 2: The storage write is a blind Cypher SET

Paper claim: "Nobody [decides a conflict]. The storage layer executes a blind Cypher SET on the derived UUID." (main.tex, subsection Cognee, "Who decides a conflict, and when"; Table 2.)

Neo4j adapter, batch write, `cognee/infrastructure/databases/graph/neo4j_driver/adapter.py:380-393`:

```python
        query = f"""
        UNWIND $nodes AS node
        MERGE (n: `{BASE_LABEL}`{{id: node.node_id}})
        WITH n, node, apoc.coll.toSet(
            coalesce(n.belongs_to_set, [])
            + coalesce(node.properties.belongs_to_set, [])
        ) AS merged_belongs_to_set
        SET n += node.properties, n.updated_at = timestamp()
        SET n.belongs_to_set = merged_belongs_to_set
        {fold_clause}
        WITH n, node.label AS label
        CALL apoc.create.addLabels(n, [label]) YIELD node AS labeledNode
        RETURN ID(labeledNode) AS internal_id, labeledNode.id AS nodeId
        """
```

Neo4j adapter, single-node write, `cognee/infrastructure/databases/graph/neo4j_driver/adapter.py:325-331`:

```python
            f"""MERGE (node: `{BASE_LABEL}`{{id: $node_id}})
                WITH node, apoc.coll.toSet(
                    coalesce(node.belongs_to_set, [])
                    + coalesce($properties.belongs_to_set, [])
                ) AS merged_belongs_to_set
                SET node += $properties, node.updated_at = timestamp()
                SET node.belongs_to_set = merged_belongs_to_set
```

The default embedded graph store (Ladybug, formerly Kuzu) overwrites the same way on match, `cognee/infrastructure/databases/graph/ladybug/adapter.py:1147-1160`:

```python
                merge_query = """
                UNWIND $nodes AS node
                MERGE (n:Node {id: node.id})
                ON CREATE SET
                    n.name = node.name,
                    n.type = node.type,
                    n.properties = node.properties,
                    n.created_at = timestamp(node.created_at),
                    n.updated_at = timestamp(node.updated_at)
                ON MATCH SET
                    n.name = node.name,
                    n.type = node.type,
                    n.properties = node.properties,
                    n.updated_at = timestamp(node.updated_at)
                """
```

Accuracy note: at this pin the SET is not fully blind for two bookkeeping properties in the Neo4j adapter. `belongs_to_set` is written back as a union rather than overwritten, and an optional provenance fold appends run references. Content properties, including the entity `description`, are still replaced with no comparison against the stored value and no record of what they replaced. The claim holds for the record's content.

## Finding 3: First description wins within a run

Paper claim: "Within a single run the first description wins." (main.tex, subsection Cognee, "Fate of the losing record"; Table 2: "First description wins in a run".)

Within one extraction run, when a second mention of the same normalized name arrives, `_create_entity_node` returns the node already built for that uuid and discards the incoming `node_description` argument. `cognee/modules/graph/utils/expand_with_nodes_and_edges.py:192-199`:

```python
    generated_node_id = Entity.id_for(node_id)
    generated_node_name = generate_node_name(node_name)
    entity_node_key = _create_node_key(generated_node_id, "entity")

    if entity_node_key in added_nodes_map or entity_node_key in key_mapping:
        return added_nodes_map.get(entity_node_key) or added_nodes_map.get(
            key_mapping.get(entity_node_key)
        )
```

The description only enters the node on first creation, `cognee/modules/graph/utils/expand_with_nodes_and_edges.py:220-232`:

```python
    entity_node = Entity(
        id=generated_node_id,
        name=generated_node_name,
        is_a=type_node,
        description=node_description,
        ontology_valid=ontology_validated,
        ontology_uri=ontology_uri,
        belongs_to_set=data_chunk.belongs_to_set,
        # TODO add importance_weight calculation if an entity with that id already exits
        importance_weight=data_chunk.importance_weight,
    )

    added_nodes_map[entity_node_key] = entity_node
```

## Finding 4: Last write wins across runs

Paper claim: "Across runs the last write wins." (main.tex, subsection Cognee, "Fate of the losing record"; Table 2: "last write wins across runs".)

Across runs, the per-run in-memory `added_nodes_map` is gone, so a later run reaches the storage layer with a fresh Entity carrying the same derived uuid. The MERGE in Finding 2 matches the stored node on that id and `SET n += node.properties` (Neo4j, adapter.py:387) or `ON MATCH SET ... n.properties = node.properties` (Ladybug, adapter.py:1156-1160) replaces the stored description with the incoming one. Nothing reads the old value first: the write path quoted in Finding 2 contains no comparison, no versioning, and no retained copy of the overwritten property.

Also relevant, "What is published and stored about the decision: Nothing": the same quoted write path is the entire decision surface; there is no merge log, no error rate, and no record of what a SET overwrote at this commit.

## Finding 5: Opt-in difflib matching with cutoff 0.8, off by default

Paper claim: "An opt-in difflib similarity path exists with a cutoff of 0.8." (main.tex, subsection Cognee; also Table 2 "No by default; opt-in difflib at cutoff 0.8" and Table 3 "difflib 0.8 opt-in".)

The matcher and its constant, `cognee/modules/ontology/matching_strategies.py:23-53` (trimmed):

```python
class FuzzyMatchingStrategy(MatchingStrategy):
    """Fuzzy matching strategy using difflib for approximate string matching."""

    def __init__(self, cutoff: float = 0.8):
        ...
        self.cutoff = cutoff

    def find_match(self, name: str, candidates: List[str]) -> Optional[str]:
        ...
        if not candidates:
            return None

        # Check for exact match first
        if name in candidates:
            return name

        # Find fuzzy match
        best_match = difflib.get_close_matches(name, candidates, n=1, cutoff=self.cutoff)
        return best_match[0] if best_match else None
```

The opt-in flag: the difflib path only gets candidates when an ontology file is configured. The env-config default is an empty path, `cognee/modules/ontology/ontology_env_config.py:23-25`:

```python
    ontology_resolver: str = "rdflib"
    matching_strategy: str = "fuzzy"
    ontology_file_path: str = ""
```

The gate that requires the flag, `cognee/modules/graph/utils/expand_with_nodes_and_edges.py:410-419`:

```python
    if ontology_resolver is None:
        ontology_config = get_ontology_env_config()
        if (
            ontology_config.ontology_file_path
            and ontology_config.ontology_resolver
            and ontology_config.matching_strategy
        ):
            ontology_resolver = get_ontology_resolver_from_env(**ontology_config.to_dict())
        else:
            ontology_resolver = get_default_ontology_resolver()
```

The default-off state: the default resolver is constructed with no ontology file, `cognee/modules/ontology/get_default_ontology_resolver.py:6-7`:

```python
def get_default_ontology_resolver() -> BaseOntologyResolver:
    return RDFLibOntologyResolver(ontology_file=None, matching_strategy=FuzzyMatchingStrategy())
```

With `ontology_file=None` the resolver holds no graph, `cognee/modules/ontology/rdf_xml/RDFLibOntologyResolver.py:122-126`:

```python
            else:
                logger.info(
                    "No ontology file provided. No owl ontology will be attached to the graph."
                )
                self.graph = None
```

And with no graph the lookup is empty, `cognee/modules/ontology/rdf_xml/RDFLibOntologyResolver.py:209-221` (trimmed):

```python
    def build_lookup(self) -> None:
        try:
            classes: Dict[str, URIRef] = {}
            individuals: Dict[str, URIRef] = {}

            if not self.graph:
                self.lookup: Dict[str, Dict[str, URIRef]] = {
                    "classes": classes,
                    "individuals": individuals,
                }

                return None
```

So by default `find_match` receives an empty candidate list and returns None (the `if not candidates: return None` branch quoted above): the difflib gate is inert until the operator supplies an ontology file path via the env config.

Configuration-state search (records that no production caller overrides the 0.8 default). Command run over the pinned tree:

```
grep -rn "FuzzyMatchingStrategy(" cognee --include="*.py" | grep -v tests
```

Full output:

```
cognee/modules/ontology/get_default_ontology_resolver.py:7:    return RDFLibOntologyResolver(ontology_file=None, matching_strategy=FuzzyMatchingStrategy())
cognee/modules/ontology/get_default_ontology_resolver.py:41:            matching_strategy=FuzzyMatchingStrategy(), ontology_file=file_paths
cognee/modules/ontology/base_ontology_resolver.py:18:        self.matching_strategy = matching_strategy or FuzzyMatchingStrategy()
cognee/modules/ontology/matching_strategies.py:23:class FuzzyMatchingStrategy(MatchingStrategy):
```

Supporting search showing the only similarity-cutoff assignment in production code is the 0.8 default (all other `cutoff` hits are timestamps or token limits). Command:

```
grep -rn "cutoff" cognee --include="*.py" | grep -v "/tests/" | grep -v "test_"
```

Matching-strategy lines from the output (the remaining hits are in `tasks/cleanup`, `api/v1/activity`, `infrastructure/databases/cache`, `infrastructure/llm/utils.py`, and `modules/cognify/recovery.py`, none of them string similarity):

```
cognee/modules/ontology/matching_strategies.py:26:    def __init__(self, cutoff: float = 0.8):
cognee/modules/ontology/matching_strategies.py:32:        self.cutoff = cutoff
cognee/modules/ontology/matching_strategies.py:52:        best_match = difflib.get_close_matches(name, candidates, n=1, cutoff=self.cutoff)
```

## Non-code sources

None. The paper's Cognee findings rest entirely on code at the pinned commit; the Discussion #778 footnote in the same section of the paper concerns GraphRAG, not Cognee.
