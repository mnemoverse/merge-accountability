# Letta

- System: Letta (letta-ai/letta)
- Version: 0.16.8 (pyproject.toml line 3: `version = "0.16.8"`)
- Commit: ff19ffeafeb54bd2a7dc5d4a552f10191732a235 (abbreviated ff19ffe in the paper)
- Upstream license: Apache License, Version 2.0 (repository LICENSE file)
- Extraction date: 2026-08-16

Snippets are short verbatim quotations from the upstream repository at the pinned commit, reproduced for review and criticism; copyright remains with the upstream authors.

All paths are relative to the repository root at the pinned commit. All searches below were run over the pinned tree checked out at `ff19ffeafeb54bd2a7dc5d4a552f10191732a235`.

## 1. The OSS write path contains no contradiction check

Paper claim: "The OSS write path contains no contradiction check at all."

Search for contradiction handling across the package (only hit is a prompt line, see finding 9):

```
$ grep -rn "contradict" letta/
letta/prompts/system_prompts/voice_sleeptime.py:62:    -   Update: Remove or correct outdated or contradictory information.
```

Search for conflict, duplicate, or dedup logic in the block write path and the memory tool set:

```
$ grep -in "conflict\|duplicate\|dedup" letta/services/block_manager.py letta/functions/function_sets/base.py
letta/services/block_manager.py:76:        """Bulk insert rows into a pivot table, ignoring conflicts."""
letta/services/block_manager.py:82:            stmt = pg_insert(table).values(rows).on_conflict_do_nothing()
letta/services/block_manager.py:86:            # fallback: filter out exact-duplicate dicts in Python
letta/services/block_manager.py:110:                stmt = stmt.on_conflict_do_nothing()
```

The four hits are SQL upsert mechanics on a tags pivot table (`on_conflict_do_nothing`), not semantic contradiction or identity checks on memory content. No matcher, threshold, or contradiction routine exists in the block write path.

## 2. The agent edits memory via string-edit tools

Paper claim: "Memory edits are string operations performed by the agent through its tools."

letta/functions/function_sets/base.py:263-280 (`core_memory_replace`; `core_memory_append` is at lines 246-261, `memory_replace` at 311, `memory_insert` at 391, `memory_rethink` at 488):

```python
def core_memory_replace(agent_state: "AgentState", label: str, old_content: str, new_content: str) -> str:  # type: ignore
    """
    Replace the contents of core memory. To delete memories, use an empty string for new_content.
    ...
    """
    current_value = str(agent_state.memory.get_block(label).value)
    if old_content not in current_value:
        raise ValueError(f"Old content '{old_content}' not found in memory block '{label}'")
    new_value = current_value.replace(str(old_content), str(new_content))
    agent_state.memory.update_block_value(label=label, value=new_value)
    return new_value
```

letta/functions/function_sets/base.py:311-319 (`memory_replace`):

```python
def memory_replace(agent_state: "AgentState", label: str, old_string: str, new_string: str) -> str:  # type: ignore
    """
    The memory_replace command allows you to replace a specific string in a memory block with a new string. This is used for making precise edits.
    Do NOT attempt to replace long strings, e.g. do not attempt to replace the entire contents of a memory block with a new string.

    Args:
        label (str): Section of the memory to be edited, identified by its label.
        old_string (str): The text to replace (must match exactly, including whitespace and indentation).
        ...
```

## 3. The sleep-time agent runs every 5 turns by default

Paper claim: "a sleep-time agent that runs every 5 turns by default."

letta/server/server.py:756, 774-786 (inside `create_sleeptime_agent_async`):

```python
    async def create_sleeptime_agent_async(self, main_agent: AgentState, actor: User) -> Optional[AgentState]:
        ...
        await self.group_manager.create_group_async(
            group=GroupCreate(
                description="",
                agent_ids=[sleeptime_agent.id],
                manager_config=SleeptimeManager(
                    manager_agent_id=main_agent.id,
                    sleeptime_agent_frequency=5,
                ),
            ),
            actor=actor,
        )
```

The turn gate consuming that frequency, letta/groups/sleeptime_multi_agent_v2.py:113-120:

```python
        # Update turns counter
        if self.group.sleeptime_agent_frequency is not None and self.group.sleeptime_agent_frequency > 0:
            turns_counter = await self.group_manager.bump_turns_counter_async(group_id=self.group.id, actor=self.actor)

        # Perform participant steps
        if self.group.sleeptime_agent_frequency is None or (
            turns_counter is not None and turns_counter % self.group.sleeptime_agent_frequency == 0
        ):
```

`sleeptime_agent_frequency=5` at server.py:784 is the only hard-coded frequency in the package (`grep -rn "sleeptime_agent_frequency=5" letta/` returns exactly that line).

## 4. Blocks are overwritten in place by default

Paper claim: "Fate of the losing record: overwritten in place by default."

In-memory overwrite, letta/schemas/memory.py:771-781 (`update_block_value`, called by the string-edit tools above):

```python
    def update_block_value(self, label: str, value: str):
        """Update the value of a block"""
        if not isinstance(value, str):
            raise ValueError("Provided value must be a string")

        for block in self.blocks:
            if block.label == label:
                block.value = value
                return
        raise ValueError(f"Block with label {label} does not exist")
```

Persistence overwrite, letta/services/block_manager.py:211-214 and 242-245 (`update_block_async`; it mutates the row in place and never touches BlockHistory):

```python
    async def update_block_async(self, block_id: str, block_update: BlockUpdate, actor: PydanticUser) -> PydanticBlock:
        """Update a block by its ID with the given BlockUpdate object."""
        ...
            if has_scalar_changes:
                for key, value in update_data.items():
                    setattr(block, key, value)
```

Confirmation that BlockHistory is written only by the checkpoint machinery, never by the update path:

```
$ grep -n "BlockHistory" letta/services/block_manager.py
15:from letta.orm.block_history import BlockHistory
762: ... (helper used by undo/redo)
773:        stmt = select(BlockHistory).filter(
774:            BlockHistory.block_id == block.id,
780:            raise NoResultFound(f"No BlockHistory row found for ...")
869:                current_entry = await session.get(BlockHistory, block.current_history_entry_id)
877:            stmt = select(BlockHistory).filter(BlockHistory.block_id == block.id, ...)
889:            history_entry = BlockHistory(
```

Lines 762-889 all sit inside `checkpoint_block_async`, `undo_checkpoint_block`, `redo_checkpoint_block`, and their private helper; `update_block_async` (lines 211-260) contains none of them.

## 5. BlockHistory table docstring and sequence_number

Paper claim: "A BlockHistory table stores 'a single historical state of a Block for undo/redo functionality,' a full value snapshot with a sequence_number."

letta/orm/block_history.py:12-31 and 46-48:

```python
class BlockHistory(OrganizationMixin, SqlalchemyBase):
    """Stores a single historical state of a Block for undo/redo functionality."""

    __tablename__ = "block_history"

    __table_args__ = (
        # PRIMARY lookup index for finding specific history entries & ordering
        Index("ix_block_history_block_id_sequence", "block_id", "sequence_number", unique=True),
    )
    ...
    # Snapshot State Fields (Copied from Block)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
```

```python
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Monotonically increasing sequence number for the history of a specific block_id, starting from 1."
    )
```

## 6. BlockManager implements checkpoint_block_async, undo_checkpoint_block, redo_checkpoint_block

Paper claim: "BlockManager implements checkpoint_block_async, undo_checkpoint_block, and redo_checkpoint_block over it."

letta/services/block_manager.py:842-858 (checkpoint), 952-961 (undo), 1004-1013 (redo):

```python
    async def checkpoint_block_async(
        self,
        block_id: str,
        actor: PydanticUser,
        agent_id: Optional[str] = None,
        use_preloaded_block: Optional[BlockModel] = None,  # For concurrency tests
    ) -> PydanticBlock:
        """
        Create a new checkpoint for the given Block by copying its
        current state into BlockHistory, using SQLAlchemy's built-in
        version_id_col for concurrency checks.
        ...
```

```python
    async def undo_checkpoint_block(
        self, block_id: str, actor: PydanticUser, use_preloaded_block: Optional[BlockModel] = None
    ) -> PydanticBlock:
        """
        Move the block to the immediately previous checkpoint in BlockHistory.
        ...
```

```python
    async def redo_checkpoint_block(
        self, block_id: str, actor: PydanticUser, use_preloaded_block: Optional[BlockModel] = None
    ) -> PydanticBlock:
        """
        Move the block to the next checkpoint if it exists.
        ...
```

## 7. Nothing outside tests calls checkpoint_block_async (dead-code claim)

Paper claim: "nothing in letta/ calls checkpoint_block_async outside its own definition; the callers are tests, so the default undo stack stays empty."

Caller search restricted to the package:

```
$ grep -rn "checkpoint_block_async" letta/
letta/services/block_manager.py:842:    async def checkpoint_block_async(
```

Caller search over the whole pinned tree, full output:

```
$ grep -rn "checkpoint_block_async" --include="*.py" .
tests/managers/test_block_manager.py:789:    await block_manager.checkpoint_block_async(block_id=created_block.id, actor=default_user)
tests/managers/test_block_manager.py:819:    await block_manager.checkpoint_block_async(block_id=block.id, actor=default_user)
tests/managers/test_block_manager.py:827:    await block_manager.checkpoint_block_async(block_id=block.id, actor=default_user)
tests/managers/test_block_manager.py:864:    await block_manager.checkpoint_block_async(block_id=block.id, actor=default_user, agent_id=sarah_agent.id)
tests/managers/test_block_manager.py:889:    await block_manager.checkpoint_block_async(block_id=block.id, actor=default_user)
tests/managers/test_block_manager.py:891:    await block_manager.checkpoint_block_async(block_id=block.id, actor=default_user)
tests/managers/test_block_manager.py:922:        await block_manager.checkpoint_block_async(
tests/managers/test_block_manager.py:933:            await block_manager.checkpoint_block_async(
tests/managers/test_block_manager.py:951:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:957:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:961:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1001:    await block_manager.checkpoint_block_async(block_id=created_block.id, actor=default_user)
tests/managers/test_block_manager.py:1009:    await block_manager.checkpoint_block_async(block_id=created_block.id, actor=default_user)
tests/managers/test_block_manager.py:1031:#    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1037:#    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1043:#    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1064:#    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1116:    await block_manager.checkpoint_block_async(block_id=block.id, actor=default_user)
tests/managers/test_block_manager.py:1135:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1141:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1147:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1176:    await block_manager.checkpoint_block_async(block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1183:    await block_manager.checkpoint_block_async(block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1229:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1235:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1241:    await block_manager.checkpoint_block_async(block_id=block_v1.id, actor=default_user)
tests/managers/test_block_manager.py:1278:    await block_manager.checkpoint_block_async(b_init.id, actor=default_user)
tests/managers/test_block_manager.py:1284:    await block_manager.checkpoint_block_async(b_init.id, actor=default_user)
tests/managers/test_block_manager.py:1303:    await block_manager.checkpoint_block_async(b_init.id, actor=default_user)
tests/managers/test_block_manager.py:1309:    await block_manager.checkpoint_block_async(b_init.id, actor=default_user)
tests/managers/test_block_manager.py:1315:    await block_manager.checkpoint_block_async(b_init.id, actor=default_user)
tests/managers/test_block_manager.py:1321:    await block_manager.checkpoint_block_async(b_init.id, actor=default_user)
tests/managers/test_block_manager.py:1342:    await block_manager.checkpoint_block_async(block.id, actor=default_user)
tests/managers/test_block_manager.py:1348:    await block_manager.checkpoint_block_async(block.id, actor=default_user)
tests/managers/test_block_manager.py:1354:    await block_manager.checkpoint_block_async(block.id, actor=default_user)
letta/services/block_manager.py:842:    async def checkpoint_block_async(
```

Every occurrence is either the definition (letta/services/block_manager.py:842) or a call in tests/managers/test_block_manager.py (some of them commented out). No production caller exists at this commit. The usual static-analysis caveat applies: dynamic dispatch or downstream packages could invoke it in ways a text search does not see.

## 8. Opt-in git-backed block manager (agent tag git-memory-enabled)

Paper claim: "An opt-in git-backed block manager (agent tag git-memory-enabled) commits every block write, with history and point-in-time reads."

letta/services/block_manager_git.py:26-40:

```python
# Tag that enables git-based memory for an agent
GIT_MEMORY_ENABLED_TAG = "git-memory-enabled"


class GitEnabledBlockManager(BlockManager):
    """Block manager that uses git as source of truth when enabled for an agent.

    For agents with the GIT_MEMORY_ENABLED_TAG:
    - All writes go to git first, then sync to PostgreSQL
    - Reads come from PostgreSQL (cache) for performance
    - Full version history is maintained in git

    For agents without the tag:
    - Behaves exactly like the standard BlockManager
    """
```

Commit on every write, letta/services/block_manager_git.py:194 and 226-234:

```python
        """Update a block. If git-enabled, commits to git first."""
        ...
            commit = await self.memory_repo_manager.update_block_async(
                agent_id=agent_id,
                label=label,
                value=resolved_value,
                actor=actor,
                message=f"Update {label} block",
                ...
            )
```

Point-in-time reads and history, letta/services/block_manager_git.py:510-521 and 533-540:

```python
    async def get_block_at_commit(
        self,
        agent_id: str,
        label: str,
        commit_sha: str,
        actor: PydanticUser,
    ) -> Optional[PydanticBlock]:
        """Get a block's value at a specific commit.

        This is a git-only operation that reads from version history.
        """
```

```python
    async def get_block_history(
        self,
        agent_id: str,
        actor: PydanticUser,
        label: Optional[str] = None,
        limit: int = 50,
    ):
        """Get commit history for an agent's memory blocks.
```

Opt-in wiring via the agent tag, letta/server/server.py:605-607 and 633-634:

```python
        wants_git_memory = bool(request.tags and GIT_MEMORY_ENABLED_TAG in request.tags)
        ...
        if wants_git_memory and isinstance(self.block_manager, GitEnabledBlockManager):
            await self.block_manager.enable_git_memory_for_agent(agent_id=main_agent.id, actor=actor)
```

## 9. The only "contradictory" mention is one line in the voice sleep-time agent system prompt

Paper claim: "the only occurrence of 'contradictory' in the package is a single line in the voice sleep-time agent's system prompt, 'Remove or correct outdated or contradictory information.'"

Grep across the package, full output:

```
$ grep -rn "contradict" letta/
letta/prompts/system_prompts/voice_sleeptime.py:62:    -   Update: Remove or correct outdated or contradictory information.
```

letta/prompts/system_prompts/voice_sleeptime.py:60-63 in context:

```
-   Refinement Principles:
    -   Integrate: Merge new facts and details accurately.
    -   Update: Remove or correct outdated or contradictory information.
    -   Organize: Group related information logically (e.g., preferences, background details, ongoing goals, interaction styles). ...
```

This is prompt text handed to an LLM subagent, not a check in the write path.

## Non-code sources

- Letta sleep-time architecture documentation, cited by the paper for the sleep-time agent's assigned tasks ("splitting large files, merging duplicates, or restructuring the hierarchy"): https://docs.letta.com/guides/agents/architectures/sleeptime, retrieved 2026-08-03 per the paper. Not fetched for this evidence file; the claim rests on documentation, not code.
