# Typed Observational Memory (TOM)
## Implementation Plan for a Coding Agent

> Status: implementation specification  
> Language: Python  
> Goal: build a research-oriented memory system that combines online observational memory with typed knowledge triage and deterministic context projection.

---

## 1. Project Goal

Implement a Python library for **Typed Observational Memory (TOM)**.

The system must transform a long-running agent event stream into a structured memory ledger and use deterministic retention policies to build compact context.

The core idea is:

```text
raw events
    ↓
Typed Observer (LLM)
    ↓
typed MemoryItem[]
    ↓
append-only Memory Ledger
    ↓
deterministic retention policies
    ↓
Context Projector
    ↓
compact agent context
```

The LLM is responsible for:

- extracting relevant information from event chunks;
- classifying each extracted item;
- assigning metadata such as importance, retention policy, topic and scope.

Python code is responsible for:

- retention policy;
- token budgeting;
- deterministic context projection;
- lifecycle state;
- source-backed recall;
- decomposition;
- retrieval;
- benchmarking.

The final objective is to evaluate whether:

> Online typed observation combined with deterministic type-aware retention reduces information degradation across repeated context compactions while maintaining reasonable cost, latency and context size.

---

# 2. Core Research Hypothesis

Primary hypothesis:

> Typed online observation + deterministic retention preserves critical information across repeated context compactions better than vanilla compaction and traditional observational memory.

The initial experiment must focus on:

```text
constraint recall
vs.
number of compaction cycles
```

Test at:

```text
1
2
4
8
16
32
```

compaction cycles.

Do not optimize for every benchmark before this experiment works.

---

# 3. Non-Goals for the Initial MVP

Do NOT implement initially:

- vector databases;
- Redis;
- PostgreSQL;
- distributed storage;
- web UI;
- LangChain;
- LangGraph;
- complex agent orchestration;
- advanced embeddings;
- automatic graph memory;
- Pi integration;
- production multi-user service;
- elaborate semantic deduplication.

The MVP must remain small enough to evaluate the core hypothesis.

---

# 4. High-Level Architecture

```text
                    EVENT STREAM
          messages / tools / diffs / tests
                        │
                        ▼
                ┌───────────────┐
                │ Chunk Builder │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │ Typed Observer│
                │      LLM      │
                └───────┬───────┘
                        │
                 MemoryItem[]
                        │
                        ▼
                ┌───────────────┐
                │ Memory Ledger │
                └───────┬───────┘
                        │
              deterministic logic
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       preserve     consolidate     archive
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                ┌────────────────┐
                │Context Projector│
                └───────┬────────┘
                        │
                        ▼
                  Agent Context
```

---

# 5. Repository Structure

Create the repository with the following structure.

```text
typed-observational-memory/
│
├── pyproject.toml
├── README.md
├── LICENSE
├── Makefile
├── .env.example
├── .gitignore
│
├── src/
│   └── tom/
│       ├── __init__.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── event.py
│       │   ├── memory.py
│       │   ├── enums.py
│       │   └── config.py
│       │
│       ├── observer/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── typed_observer.py
│       │   ├── safety_scanner.py
│       │   ├── prompts.py
│       │   └── schemas.py
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── ledger.py
│       │   ├── store.py
│       │   ├── sqlite_store.py
│       │   ├── recall.py
│       │   └── lifecycle.py
│       │
│       ├── policies/
│       │   ├── __init__.py
│       │   ├── retention.py
│       │   ├── compaction.py
│       │   ├── decomposition.py
│       │   └── retrieval.py
│       │
│       ├── consolidation/
│       │   ├── __init__.py
│       │   ├── consolidator.py
│       │   ├── deduplication.py
│       │   ├── supersession.py
│       │   └── expiration.py
│       │
│       ├── context/
│       │   ├── __init__.py
│       │   ├── projector.py
│       │   ├── budget.py
│       │   ├── renderer.py
│       │   └── token_counter.py
│       │
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   └── mock.py
│       │
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── generic.py
│       │   └── pi_bridge.py
│       │
│       └── cli/
│           ├── __init__.py
│           └── main.py
│
├── benchmarks/
│   ├── common/
│   │   ├── runner.py
│   │   ├── metrics.py
│   │   ├── costs.py
│   │   └── reports.py
│   │
│   ├── compaction_cliff/
│   ├── longmemeval/
│   ├── locomo/
│   └── agent_behavior/
│
├── experiments/
│   ├── configs/
│   ├── ablations/
│   └── scripts/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── fixtures/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
│
├── results/
│   ├── raw/
│   ├── tables/
│   └── figures/
│
└── paper/
    ├── notes/
    ├── figures/
    ├── tables/
    └── manuscript/
```

Rules:

1. `src/tom/` must contain only reusable library code.
2. Benchmark-specific code must stay under `benchmarks/`.
3. Experiment outputs must not be mixed with library code.
4. Pi integration must be an adapter, never part of the core memory logic.
5. The core must remain usable without Pi.

---

# 6. Python Stack

Use the smallest stack that supports the MVP. Do not add a dependency before the
corresponding feature exists.

## Required for the MVP

```text
Python        >= 3.12
Packaging     uv
Validation    pydantic >= 2
Token count   tiktoken
Database      sqlite3 (Python standard library)
Testing       pytest
Async tests   pytest-asyncio
Lint          ruff
Typing        pyright
```

The current MVP needs no HTTP client, CLI framework, dataframe library,
statistics package, plotting package or configuration framework. Add those only
with the feature that requires them:

```text
CLI           typer              when a user-facing CLI is implemented
HTTP          httpx              when a remote provider is implemented
Property test hypothesis        when property tests are added
Data          polars             when benchmark tabulation needs it
Statistics    scipy              when statistical analysis is added
Plots         matplotlib         when benchmark figures are added
Config        hydra-core         only for multi-run experiment configuration
```

Keep `sqlite3` instead of adding an ORM or database server. Keep provider
adapters optional so the core remains usable with the mock provider.

Avoid adding large agent frameworks to the core. Do not use LangChain or
LangGraph unless a later integration explicitly requires them.

---

# 7. Core Domain Models

## 7.1 KnowledgeType

Implement:

```python
class KnowledgeType(StrEnum):
    CONSTRAINT = "constraint"
    PROCEDURE = "procedure"
    BELIEF = "belief"
    PREFERENCE = "preference"
    EPISODIC = "episodic"
```

Meanings:

### Constraint

A rule or fact whose loss may allow invalid, unsafe or forbidden behavior.

Examples:

```text
Never modify production data without explicit approval.
Generated files must not be edited manually.
```

### Procedure

A process that should be followed.

Examples:

```text
Run integration tests before merging.
Database schema changes must use migrations.
```

### Belief

A currently believed factual state.

Examples:

```text
The backend uses PostgreSQL.
Authentication is implemented in src/auth/.
```

### Preference

A desired but non-mandatory behavior.

Examples:

```text
Prefer small focused changes.
Prefer concise responses.
```

### Episodic

An event tied to a particular time or interaction.

Examples:

```text
Authentication tests failed after the middleware change.
Migration 184 was already executed in production.
```

---

# 8. Retention Policy Must Be Independent of Knowledge Type

Implement:

```python
class RetentionPolicy(StrEnum):
    EXACT = "exact"
    HIGH_FIDELITY = "high_fidelity"
    COMPRESSIBLE = "compressible"
    DISCARDABLE = "discardable"
```

Do NOT assume:

```text
constraint == exact
episodic == discardable
```

They are correlated but not equivalent.

Example:

```text
"Migration 184 was already executed in production."
```

is:

```text
knowledge_type = episodic
importance = critical
retention = high_fidelity
```

Keep semantic classification and retention policy separate.

---

# 9. Importance

Implement:

```python
class Importance(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

Importance influences budget priority but must not replace retention policy.

---

# 10. Event Model

Create an append-only event model.

```python
class EventType(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_CHANGE = "file_change"
    TEST_RESULT = "test_result"
```

Suggested model:

```python
class Event(BaseModel):
    id: str
    type: EventType
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Requirements:

- events are immutable;
- events are append-only;
- every event has a stable ID;
- original event content must remain recoverable;
- MemoryItems reference source Event IDs.

---

# 11. MemoryItem Model

Implement approximately:

```python
class MemoryItem(BaseModel):
    id: str

    content: str

    knowledge_type: KnowledgeType
    retention: RetentionPolicy
    importance: Importance

    confidence: float = Field(ge=0.0, le=1.0)

    topic: str | None = None
    scope: list[str] = Field(default_factory=list)

    source_ids: list[str]

    created_at: datetime
    event_time: datetime | None = None

    status: MemoryStatus = MemoryStatus.ACTIVE

    supersedes: list[str] = Field(default_factory=list)
```

Add:

```python
class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
```

Critical invariant:

```text
Every MemoryItem MUST reference at least one source Event.
```

---

# 12. Typed Observer

The Typed Observer is the first LLM-based component.

Interface:

```python
class Observer(Protocol):
    async def observe(
        self,
        events: list[Event],
    ) -> list[MemoryItem]:
        ...
```

The implementation must:

1. receive a chunk of events;
2. extract atomic knowledge items;
3. classify them;
4. return structured output;
5. preserve source IDs;
6. prefer recall over precision for critical knowledge.

Do NOT create an intermediate generic `Observation` model in the MVP.

Use:

```text
raw chunk
    ↓
Typed Observer
    ↓
MemoryItem[]
```

not:

```text
raw chunk
    ↓
Observation[]
    ↓
Classifier
    ↓
MemoryItem[]
```

This is an explicit design decision.

---

# 13. Typed Observer Prompt Requirements

The system prompt must clearly instruct the model to:

- extract only information useful for future behavior or reasoning;
- produce atomic items;
- avoid combining unrelated facts;
- distinguish constraints, procedures, beliefs, preferences and episodes;
- separately assign retention policy;
- separately assign importance;
- preserve source IDs;
- assign topic and scope when possible;
- assign confidence;
- favor false positives over false negatives for:
  - constraints;
  - procedures;
  - critical state.

The observer must return a Pydantic-compatible structured object.

Do not parse free-form text.

---

# 14. Structured LLM Provider Interface

Create a provider abstraction.

```python
class StructuredLLM(Protocol):
    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        ...
```

Implement initially:

```text
MockStructuredLLM
OpenAIStructuredLLM
```

Anthropic can come later.

Observer code must not know which provider is being used.

---

# 15. Chunk Builder

Implement chunking before the Observer.

The MVP should support:

```text
max_tokens
```

as the main threshold.

Start with approximately:

```text
8k–12k source tokens
```

configurable.

Requirements:

- do not split individual events;
- preserve event order;
- track source IDs;
- return deterministic chunks;
- expose token counts.

Suggested interface:

```python
class EventChunker:
    def chunk(
        self,
        events: list[Event],
        max_tokens: int,
    ) -> list[list[Event]]:
        ...
```

---

# 16. Memory Store

Create a protocol:

```python
class MemoryStore(Protocol):
    async def add_events(...)
    async def add_memory_items(...)
    async def get_event(...)
    async def get_memory(...)
    async def list_active_memory(...)
    async def update_status(...)
    async def get_sources(...)
```

Initial implementation:

```text
SQLiteMemoryStore
```

Do not introduce PostgreSQL initially.

---

# 17. SQLite Schema

Minimum tables:

## events

```text
id
type
content
timestamp
metadata_json
```

## memory_items

```text
id
content
knowledge_type
retention
importance
confidence
topic
created_at
event_time
status
```

## memory_sources

```text
memory_id
event_id
```

## memory_scopes

```text
memory_id
scope
```

## memory_supersedes

```text
memory_id
superseded_memory_id
```

Add indexes where clearly useful.

Avoid premature optimization.

---

# 18. Source-Backed Recall

Implement:

```python
async def recall(memory_id: str) -> RecallResult:
    ...
```

It must return:

```python
class RecallResult(BaseModel):
    memory: MemoryItem
    sources: list[Event]
```

Expected use:

```text
compact context:

Authentication tests failed after middleware change. [mem:e391]
```

Then:

```text
recall("mem:e391")
```

returns original source events.

Critical requirement:

> Compaction must never destroy the ability to recover original evidence.

---

# 19. Context Projector

Use the name:

```text
ContextProjector
```

rather than `Compactor`.

The projector does not summarize arbitrary history.

It projects structured memory into a token budget.

Interface:

```python
class ContextProjector:
    def project(
        self,
        memories: list[MemoryItem],
        token_budget: int,
    ) -> ProjectedContext:
        ...
```

---

# 20. Projection Priority

Initial priority order:

```text
1. EXACT
2. HIGH_FIDELITY
3. COMPRESSIBLE + CRITICAL
4. COMPRESSIBLE + HIGH
5. recent COMPRESSIBLE
6. DISCARDABLE
```

Within a category, use deterministic ordering.

Suggested tie-breaking:

```text
importance
recency
stable ID
```

No LLM call is allowed inside the base projection algorithm.

---

# 21. Protected Memory Invariant

This is mandatory.

If all `EXACT` memories do not fit inside the token budget:

DO NOT silently summarize them.

Raise:

```python
class UnsafeContextBudget(Exception):
    ...
```

Example:

```python
if exact_tokens > token_budget:
    raise UnsafeContextBudget(...)
```

Later, TypeDecompose may solve this condition.

The MVP must fail explicitly rather than violate the retention contract.

---

# 22. Deterministic Rendering

Create a stable renderer.

Example output:

```markdown
# Constraints

[mem:c102]
Never modify production data without approval.

[mem:c381]
Generated files must not be edited manually.

# Procedures

[mem:p129]
Run integration tests before merging authentication changes.

# Current State

[mem:b991]
The backend currently uses PostgreSQL.

# Preferences

[mem:f122]
Prefer focused changes over broad refactoring.

# Recent Relevant Events

[mem:e331]
Authentication tests failed after middleware changes.
```

Requirements:

- stable order;
- stable section names;
- memory IDs always included;
- no nondeterministic rephrasing;
- same state + same config → same rendered output.

---

# 23. Idempotence Requirement

The projection system must not behave like:

```text
summary(summary(summary(...)))
```

The following conceptual invariant should hold:

```text
project(memory_state)
```

must not mutate `memory_state`.

Repeated projection with the same state/config must produce the same result.

Test:

```python
assert projector.project(state, budget) == projector.project(state, budget)
```

---

# 24. Consolidator

Do NOT implement this before the basic Typed Observer + Ledger + Projector work.

When implemented, its job is narrow:

```text
deduplicate
supersede
merge compressible facts
archive stale items
```

It must NOT rewrite `EXACT` memories.

Candidate logic:

```python
if memory.retention == RetentionPolicy.EXACT:
    never_rewrite()
```

LLM-based consolidation is allowed only for eligible memories.

---

# 25. Supersession

The memory system must represent changing state.

Example:

```text
mem_1:
Backend uses MySQL.

mem_2:
Backend migrated to PostgreSQL.
```

Expected state:

```text
mem_1.status = superseded
mem_2.status = active
mem_2.supersedes = [mem_1.id]
```

Do not delete `mem_1`.

Old knowledge must remain recoverable for audit and temporal reasoning.

---

# 26. Safety Scanner

Implement only after the MVP.

Purpose:

Catch constraints or critical state missed by the Typed Observer.

Pipeline:

```text
                     raw chunk
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
      Typed Observer         Safety Scanner
             │                     │
             └──────────┬──────────┘
                        ▼
                     merge
```

The scanner asks only a narrow question:

> Is there any information in this chunk whose loss could materially alter future agent behavior?

Favor recall over precision.

Its output should be merged with the Typed Observer output and deduplicated.

---

# 27. Decomposition

Implement after the protected memory budget becomes a real problem.

Goal:

Avoid summarizing protected memory when it exceeds the available context.

Example:

```text
protected memory
      ↓
partition by scope
      ↓
global
database
auth
deployment
testing
frontend
```

Constraints can belong to multiple scopes.

A task should receive:

```text
global protected memory
+
relevant scoped protected memory
```

not all protected memory.

---

# 28. Retrieval

Implement two separate operations.

## recall(id)

Exact and source-backed.

```text
memory ID
    ↓
original sources
```

## retrieve(query)

Semantic/contextual retrieval.

Expected order:

```text
1. applicable constraints
2. applicable procedures
3. relevant beliefs/preferences/episodes
```

Constraints and procedures should not rely only on cosine similarity.

Relevant protected memory must be pinned before ordinary retrieval fills remaining budget.

---

# 29. Pi Integration

Do not couple the Python core to Pi.

Pi support should be a thin bridge.

Recommended model:

```text
Pi extension
     │
 JSONL / stdio
     ▼
Python TOM process
```

Example command:

```bash
tom serve --stdio
```

Example request:

```json
{
  "method": "observe",
  "session_id": "abc",
  "events": [...]
}
```

Response:

```json
{
  "memory_items": [...]
}
```

Projection:

```json
{
  "method": "project",
  "session_id": "abc",
  "token_budget": 16000
}
```

Pi integration comes after the core research implementation.

---

# 30. Benchmark Interface

Define a common interface so every memory strategy can be evaluated identically.

```python
class MemorySystem(Protocol):

    async def ingest(
        self,
        session_id: str,
        events: list[Event],
    ) -> None:
        ...

    async def context(
        self,
        session_id: str,
        query: str,
        budget: int,
    ) -> str:
        ...
```

Implement adapters for:

```text
FullContextMemory
VanillaCompactionMemory
ObservationalMemory
KnowledgeTriageMemory
TypedObservationalMemory
```

The benchmark runner must not contain method-specific shortcuts.

---

# 31. Required Baselines

At minimum evaluate:

```text
A. Full context
B. Vanilla LLM compaction
C. Observational Memory
D. Knowledge Triage
E. Typed Observational Memory
F. Typed Observational Memory + Safety Scanner
```

Use the same:

- main model;
- observer model where applicable;
- context budget;
- datasets;
- scoring;
- seeds where possible.

---

# 32. First Benchmark: Compaction Cliff

This is the first mandatory experiment.

Do not start with LongMemEval.

Measure information survival across:

```text
1
2
4
8
16
32
```

compaction cycles.

Primary metric:

```text
constraint recall
```

Secondary metrics:

```text
procedure recall
belief accuracy
memory tokens
total input tokens
total output tokens
LLM calls
estimated cost
latency
```

Produce a plot:

```text
constraint recall
      │
1.0 ── TOM ─────────────────────
      │
0.8 ──
      │
0.6 ───── OM ─────────\
      │                \
0.4 ───────────────────\
      │                  \
0.2 ── vanilla            \__
      │
0.0 ──────────────────────────
       1  2  4  8  16  32
          compaction cycles
```

The exact shape is empirical. Never hard-code expected results.

---

# 33. Additional Benchmarks

After the core hypothesis is validated:

## LongMemEval

Measure:

```text
information extraction
multi-session reasoning
knowledge updates
temporal reasoning
abstention
```

## LoCoMo

Measure:

```text
long conversational memory
episodic recall
temporal recall
multi-hop reasoning
```

## Custom Behavioral Agent Benchmark

This is important because QA benchmarks test:

```text
remember → answer
```

but agents need:

```text
remember → behave correctly
```

Create controlled scenarios such as:

```text
turn 10:
Never change the public API.

turn 1000:
Refactor the API implementation.

Expected:
public API remains unchanged.
```

Also test constraints expressed indirectly:

```text
Generated files are overwritten automatically by CI.
```

Expected behavior:

```text
agent does not edit generated files
```

---

# 34. Metrics

Every experiment must record:

## Quality

```text
constraint recall
procedure recall
belief accuracy
temporal consistency
supersession accuracy
source attribution accuracy
```

## Behavioral

```text
task success
constraint violation rate
procedure compliance
```

## Compression

```text
active memory tokens
projected context tokens
raw source tokens
compression ratio
```

## Cost

```text
observer input tokens
observer output tokens
scanner tokens
consolidator tokens
main agent tokens
LLM call count
estimated USD
```

## Latency

```text
observer p50
observer p95
projection p50
projection p95
retrieval p50
retrieval p95
```

---

# 35. Instrumentation

Instrumentation is mandatory from the beginning.

Each observation cycle should be able to emit:

```json
{
  "observer_input_tokens": 10021,
  "observer_output_tokens": 813,
  "memory_items_created": 17,
  "constraints_created": 2,
  "procedures_created": 3,
  "projected_tokens": 5411,
  "active_memory_tokens": 6932,
  "archived_memory_tokens": 2181,
  "llm_calls": 1,
  "estimated_cost_usd": 0.0041,
  "latency_ms": 912
}
```

Do not postpone cost accounting.

---

# 36. Ablation Studies

Implement experiments that compare:

| Variant | Typed Observer | Safety Scanner | Consolidator | Type-Aware Projection |
|---|---:|---:|---:|---:|
| OM | No | No | Yes | No |
| OM + post-triage | No | No | Yes | Yes |
| Typed Observer | Yes | No | No | Yes |
| Typed + Consolidator | Yes | No | Yes | Yes |
| Typed + Safety | Yes | Yes | No | Yes |
| Full TOM | Yes | Yes | Yes | Yes |

Also compare:

```text
raw → Observer → classifier
```

versus:

```text
raw → joint Typed Observer
```

Measure:

```text
quality
cost
latency
```

---

# 37. Observer Model Ablation

Evaluate at least:

```text
cheap model
medium model
strong model
```

Build a cost-quality frontier.

Research question:

> Can a cheap online memory model preserve long-horizon agent state while the expensive main agent operates on compact context?

---

# 38. Tests

Tests are mandatory before adding benchmark complexity.

## Unit Tests

Cover:

```text
Event validation
MemoryItem validation
SQLite store
source references
recall
budget calculation
projection ordering
rendering
status transitions
supersession
```

## Property Tests

Use Hypothesis for invariants where useful.

Examples:

```text
EXACT memories never silently disappear.
Projected tokens never exceed budget.
Projection never mutates the ledger.
Same input/config yields same projection.
Every MemoryItem has at least one source.
Superseded memory is not rendered as current state.
```

## Integration Tests

Test:

```text
events
→ observer
→ ledger
→ projection
→ recall
```

with `MockStructuredLLM`.

Do not require paid APIs for the normal test suite.

---

# 39. Regression Tests

Every fixed bug that could alter memory semantics must add a regression test.

Examples:

```text
constraint dropped because of budget ordering
superseded belief rendered as current
source IDs lost during merge
nondeterministic ordering
duplicate exact memories
incorrect scope selection
```

---

# 40. CI Requirements

CI must run:

```text
ruff
type checker
pytest
benchmark smoke tests
```

The coding agent must continue fixing failures until CI is green.

Do not finish an implementation task with known failing checks unless the failure is explicitly documented as an external blocker.

---

# 41. Code Quality Rules for the Agent

The coding agent must follow these rules:

1. Keep modules small and cohesive.
2. Avoid large comments explaining confusing code; simplify the code instead.
3. Prefer explicit domain models over unstructured dictionaries.
4. Avoid hidden mutation.
5. Prefer pure functions for retention and projection logic.
6. Keep LLM-dependent logic isolated from deterministic core logic.
7. Add tests with every behavioral change.
8. Do not add dependencies without clear need.
9. Do not over-engineer storage.
10. Preserve backward compatibility once benchmark formats are published.
11. Do not mix benchmark code into core package code.
12. Do not silently degrade protected memory.
13. Do not use free-form LLM parsing when structured output is available.
14. Never delete source evidence as part of compaction.
15. Keep experiment configs versioned.

---

# 42. Implementation Sequence

Follow this order.

---

## PR 1 — Core Models and Ledger

Title:

```text
feat(core): add typed memory models and append-only ledger
```

Implement:

```text
Event
EventType
MemoryItem
KnowledgeType
RetentionPolicy
Importance
MemoryStatus
MemoryStore
SQLiteMemoryStore
recall()
```

Tests:

```text
model validation
event persistence
memory persistence
source references
recall
status updates
```

Acceptance criteria:

- all tests pass;
- no LLM dependency;
- every memory item references source events;
- original event content is recoverable.

---

## PR 2 — Typed Observer

Title:

```text
feat(observer): add structured typed observer
```

Implement:

```text
StructuredLLM protocol
MockStructuredLLM
OpenAIStructuredLLM
TypedObserver
observer Pydantic schemas
event chunking
token accounting
```

Tests:

```text
structured extraction
source ID preservation
chunk determinism
invalid responses
empty chunks
multiple memory items
```

Acceptance criteria:

- raw event chunks produce valid MemoryItems;
- no free-form output parsing;
- test suite uses mock provider by default.

---

## PR 3 — Deterministic Context Projection

Title:

```text
feat(context): add type-aware deterministic projection
```

Implement:

```text
ContextProjector
TokenBudget
Renderer
UnsafeContextBudget
priority ordering
```

Tests:

```text
EXACT preservation
budget enforcement
ordering
deterministic rendering
idempotence
UnsafeContextBudget
```

Acceptance criteria:

- no LLM calls during projection;
- same state/config → same output;
- EXACT items never silently disappear.

---

## PR 4 — Metrics and Experiment Infrastructure

Title:

```text
feat(metrics): add memory instrumentation and experiment logging
```

Implement:

```text
token metrics
latency metrics
LLM call metrics
cost estimation
JSONL experiment logs
experiment run IDs
config snapshot
```

Acceptance criteria:

- every benchmark run produces machine-readable metrics;
- experiment config is stored with the output.

---

## PR 5 — Compaction Cliff Benchmark

Title:

```text
bench: add multi-round compaction cliff evaluation
```

Implement baselines:

```text
FullContextMemory
VanillaCompactionMemory
TypedObservationalMemory
```

Then add:

```text
ObservationalMemory
KnowledgeTriageMemory
```

Evaluate:

```text
1, 2, 4, 8, 16, 32
```

compaction cycles.

Generate:

```text
results/raw/*.jsonl
results/tables/*.csv
results/figures/*.png
```

Acceptance criteria:

- experiment is reproducible;
- metrics include constraint recall and cost;
- plots are generated from raw results, never manually.

---

## PR 6 — Consolidator

Title:

```text
feat(memory): add typed memory consolidation
```

Implement:

```text
deduplication
supersession
expiration
soft-memory consolidation
```

Rules:

- NEVER rewrite EXACT memory;
- never delete source evidence;
- old beliefs become superseded, not deleted.

---

## PR 7 — Safety Scanner

Title:

```text
feat(observer): add high-recall safety scanner
```

Implement:

```text
SafetyScanner
merge logic
deduplication with Typed Observer
scanner metrics
```

Evaluate:

```text
constraint recall
false positives
cost
```

---

## PR 8 — Type-Aware Retrieval

Title:

```text
feat(retrieval): add protected-memory pinning
```

Implement:

```text
scope detection
applicable constraint selection
applicable procedure selection
normal retrieval
budget filling
```

Protected memory is selected before ordinary retrieval.

---

## PR 9 — Decomposition

Title:

```text
feat(memory): add scope-aware protected-memory decomposition
```

Implement:

```text
global scope
topic scope
multi-scope constraints
scope-aware context selection
```

Use when protected memory exceeds budget.

---

## PR 10 — External Benchmarks

Title:

```text
bench: add long-term memory benchmark adapters
```

Integrate:

```text
LongMemEval
LoCoMo
MemEval-compatible adapter if practical
```

Do not modify core logic for benchmark-specific requirements.

---

## PR 11 — Behavioral Agent Benchmark

Title:

```text
bench: add long-horizon behavioral memory benchmark
```

Create synthetic scenarios testing:

```text
constraint retention
procedure compliance
implicit constraints
state updates
temporal facts
supersession
```

This benchmark should test agent behavior, not only QA recall.

---

## PR 12 — Pi Bridge

Title:

```text
feat(integration): add Pi stdio bridge
```

Implement:

```text
tom serve --stdio
observe
project
recall
retrieve
```

Keep Pi-specific code outside the core.

---

# 43. CLI

Eventually expose:

```bash
tom observe
tom project
tom recall
tom inspect
tom benchmark
tom serve --stdio
```

Example:

```bash
tom inspect --session abc
```

should show:

```text
active memories
protected memories
superseded memories
archived memories
token counts
```

---

# 44. Configuration

Create explicit typed configuration.

Example:

```yaml
observer:
  max_chunk_tokens: 10000
  provider: openai
  model: gpt-5-mini

memory:
  database: .tom/memory.db

projection:
  token_budget: 16000

retention:
  exact_first: true

scanner:
  enabled: false
```

Experiment configs must live under:

```text
experiments/configs/
```

and be committed.

---

# 45. Reproducibility Requirements

Every benchmark run must persist:

```text
git commit hash
timestamp
experiment config
model names
model parameters
seed
dataset version
code version
token counts
cost estimates
raw predictions
metrics
```

Do not report only aggregate metrics.

Raw results must remain available for recomputation.

---

# 46. Results Directory Convention

Use:

```text
results/
└── <experiment-name>/
    └── <run-id>/
        ├── config.yaml
        ├── metadata.json
        ├── predictions.jsonl
        ├── metrics.json
        ├── table.csv
        └── figure.png
```

Never overwrite an existing run.

---

# 47. Paper-Oriented Engineering Decisions

Design the code so the future paper can answer:

```text
What exactly is the method?
What part uses an LLM?
What part is deterministic?
How many LLM calls occur?
How much does ingestion cost?
How much does retrieval cost?
How does memory size grow?
How does quality change after repeated compaction?
Which component produces the gain?
```

Every architectural choice should be measurable.

---

# 48. Research Questions

Track at least these questions.

## RQ1

Does typed online observation reduce constraint degradation across repeated compactions?

## RQ2

Does joint extraction + classification outperform Observation → Triage as two separate stages?

## RQ3

How much additional cost is introduced by typed observation?

## RQ4

Can a smaller model perform the memory task without significant quality loss?

## RQ5

Does deterministic retention outperform LLM-based re-summarization under repeated compaction?

## RQ6

Does a high-recall Safety Scanner materially improve constraint retention?

## RQ7

How does TOM perform on general long-term memory benchmarks?

## RQ8

Does improved memory translate into better agent behavior rather than only better QA recall?

---

# 49. Initial Definition of Done

The initial research MVP is complete when all of the following exist:

```text
✓ Event model
✓ MemoryItem model
✓ SQLite append-only ledger
✓ source-backed recall
✓ Typed Observer
✓ structured LLM output
✓ deterministic Context Projector
✓ EXACT preservation invariant
✓ token/cost instrumentation
✓ vanilla compaction baseline
✓ TOM baseline
✓ repeated compaction benchmark
✓ constraint recall plot
✓ reproducible experiment config
```

Do not block the MVP on:

```text
Pi integration
LongMemEval
LoCoMo
vector search
advanced consolidator
web UI
```

---

# 50. First Scientific Milestone

The first question to answer is:

> After N context-compaction cycles, what fraction of the original behavioral constraints remains available to the agent, and at what token/cost overhead?

If TOM does not materially improve this curve, investigate before expanding the system.

If TOM produces a substantially flatter degradation curve, proceed to:

```text
Safety Scanner
Consolidator
LongMemEval
LoCoMo
behavioral benchmark
Pi integration
```

---

# 51. Agent Execution Rules

When implementing this repository, the coding agent must:

1. Work in the PR order described above.
2. Do not implement future phases prematurely.
3. Add or update tests with every behavior change.
4. Run the full relevant test suite after each implementation task.
5. Run lint and type checks before considering a task complete.
6. Continue fixing issues until CI is green.
7. Never silently relax a documented invariant to make a test pass.
8. Prefer changing the implementation over weakening the test unless the specification is demonstrably wrong.
9. Keep the deterministic core independent of any specific LLM provider.
10. Keep benchmark code independent of production core logic.
11. Record architectural deviations in an ADR or clearly documented design note.
12. Avoid speculative abstractions that are not required by the current phase.

---

# 52. First Command Sequence

The coding agent should begin with something equivalent to:

```bash
uv init
uv add pydantic typer httpx
uv add --dev pytest pytest-asyncio hypothesis ruff pyright
```

Then create:

```text
src/tom/models/
src/tom/memory/
tests/unit/
tests/integration/
```

and implement **PR 1 only**.

Do not implement an LLM call until the ledger and source-backed recall are complete and tested.

---

# 53. Guiding Principle

The architecture must preserve the following separation:

```text
LLM:
extract and classify semantic information

Python:
decide deterministic retention and context allocation
```

The system should move the difficult semantic decision to the moment information is observed, rather than trying to reconstruct importance only when the context window is already full.

The long-term target is:

```text
observe continuously
classify once
retain deterministically
retrieve by evidence
compact by projection
```

rather than:

```text
wait until context is full
summarize everything
repeat
lose information progressively
```
