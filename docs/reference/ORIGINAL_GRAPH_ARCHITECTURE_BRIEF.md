> Historical architecture input, preserved from the October 2026 project brief.
> This is design background. Its proposals and old request to review the architecture
> do not supersede the accepted [ADR 0004](../decisions/0004-evidence-aware-retrieval-migration.md),
> [migration plan](../GRAPH_ARCHITECTURE.md), or [current handoff](../RESUME.md).
> Original archive filename: `Pasted markdown.md`. The duplicate quoted text version
> is omitted. The original brief follows unchanged.

# Atlas Graph Architecture — Implementation Brief

## Purpose

Treat this document as **architectural guidance for the Atlas graph implementation**. First reconcile it with the current Atlas repository, implementation state, existing design decisions, tests, and recent work.

**Do not blindly replace working architecture.** Where Atlas already implements these concepts differently, evaluate the existing approach and preserve it unless there is a concrete reason to change it.

The long-term target is a very large, AI-developed or AI-maintained monorepo ranging from roughly 100K lines to potentially millions of lines. Atlas should enable AI agents to work effectively without loading large portions of the repository into model context.

The central principle is:

**Do not make the model understand the repository by giving it more code. Make retrieval better at identifying the small, evidence-backed portion of the engineering system needed for the current task.**

---

## 1. Architectural model

Atlas should evolve toward an **engineering knowledge layer over the repository**, not merely a graph database or vector RAG system.

Conceptually:

```
Requirements / Design / Hazards / Interfaces
                   │
                   ▼
Source ──► Parsers / AST ──► Canonical Engineering Graph
  │                               │
  ├── Build metadata ─────────────┤
  ├── Tests ──────────────────────┤
  ├── Git ────────────────────────┤
  └── Human / AI metadata ────────┘
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
             Graph Retrieval              Vector Retrieval
           structural/exact              semantic/fuzzy
                   └──────────────┬──────────────┘
                                  ▼
                           Context Builder
                                  ▼
                             AI Agents
```

Retrieval should generally be **graph first, vector second**.

Structural relationships answer questions such as:

- What calls this?
- What does this call?
- What requirement does this implement?
- What tests verify it?
- What depends on this interface?
- What is the blast radius of changing this symbol?

Semantic/vector retrieval fills gaps where structural relationships are insufficient.

---

## 2. Use a canonical typed graph

Define explicit node and edge types rather than treating the graph as generic key/value metadata.

Likely node types include:

```
Repository
Application
Component
File
Namespace
Class
Struct
Function
Method
Variable
Requirement
DesignElement
Interface
Test
TestCase
Hazard
Assumption
Configuration
```

Likely edge types include:

```
CONTAINS
DECLARES
DEFINES
CALLS
READS
WRITES
DEPENDS_ON
IMPLEMENTS
VERIFIES
DERIVED_FROM
SATISFIES
MITIGATES
CONFIGURES
GENERATED_FROM
```

Keep the schema extensible. Systems-engineering artifacts should eventually be first-class graph entities rather than arbitrary text tags.

---

## 3. Stable entity identity is essential

Do not use file locations or line numbers as primary identity.

Entities need identities that survive ordinary source movement and refactoring as much as practical.

Conceptually:

```
symbol://Navigation/Navigation::CalculatePosition
requirement://SYS/NAV/REQ-142
test://NavigationTests/CalculatePositionNominal
```

Source location is metadata associated with the entity, not the identity itself.

A function moving from line 300 to line 450 should not create an entirely new conceptual entity.

Renames/refactors can later use combinations of qualified symbol identity, signatures, AST structure, Git history, and persistent identifiers.

---

## 4. Facts and AI inference must never be equivalent

Every relationship needs provenance.

For example:

```
A --CALLS--> B
source = compiler/static analysis
```

is fundamentally different from:

```
A --IMPLEMENTS--> REQ-142
source = AI inference
confidence = ...
evidence = ...
```

Consider authority categories such as:

```
AUTHORITATIVE
DECLARED
DERIVED
INFERRED
HEURISTIC
```

Example hierarchy:

**AUTHORITATIVE**\
Compiler/AST, requirements authority, build system.

**DECLARED**\
Explicit developer annotations or configuration.

**DERIVED**\
Deterministic static analysis.

**INFERRED**\
AI-generated engineering relationship.

**HEURISTIC**\
Naming, text similarity, embeddings, etc.

Fundamental rule:

**AI proposes knowledge. Deterministic systems establish facts whenever possible.**

Atlas should retain evidence explaining why an inferred or derived relationship exists.

---

## 5. Common graph metadata

Nodes/edges should support a common metadata envelope where appropriate:

```
id
type
schema_version

source/provenance
source_revision

created_at
updated_at

confidence
evidence[]

attributes {}
```

Avoid requiring every field everywhere if doing so produces unnecessary storage overhead. The conceptual capability is more important than blindly materializing every property.

---

## 6. Do not turn the complete AST into the persistent graph

Avoid graph explosion.

Think in three levels:

```
Level 1 — Engineering graph
Requirements, components, interfaces, tests,
hazards, assumptions, designs

Level 2 — Code graph
Files, types, functions, calls, definitions,
dependencies

Level 3 — Detailed syntax
Full AST/compiler information
```

Persist Levels 1 and 2 where useful.

Level 3 should generally remain queryable/reconstructable compiler information unless a demonstrated retrieval requirement justifies persistence.

Don't create permanent nodes for every expression, local variable, or `if` statement simply because the parser exposes them.

---

## 7. Generated code requires explicit treatment

Track origin information such as:

```
HUMAN
AI
GENERATED
THIRD_PARTY
```

Generated artifacts should ideally record:

```
generator
generator_version
source_definition
GENERATED_FROM relationship
```

This allows an agent encountering generated code to navigate to the authoritative generator/source rather than modifying generated output.

Generated code should also be preventable from overwhelming semantic retrieval.

---

## 8. Incremental indexing is mandatory

A large repository cannot rebuild the entire graph and vector index after ordinary changes.

Target:

```
git diff
    ↓
changed files
    ↓
affected translation units
    ↓
affected symbols
    ↓
graph delta
    ↓
dependency invalidation
    ↓
re-embed only changed semantic units
```

Think of graph invalidation similarly to an incremental build system.

Public interface changes may invalidate considerably more downstream knowledge than implementation-only changes.

---

## 9. Fast path and deep path

Prefer eventual consistency over blocking every edit on complete analysis.

Conceptually:

```
EDIT
 │
 ├── FAST PATH
 │     changed-file parsing
 │     symbols
 │     direct structural relationships
 │
 └── DEEP/BACKGROUND PATH
       embeddings
       transitive analysis
       requirements inference
       traceability analysis
       deeper static analysis
```

Query results should eventually expose index freshness, for example:

```
repository_revision
graph_revision
semantic_index_revision
requirements_revision
```

An agent should be able to determine whether it is reasoning from stale information.

---

## 10. Keep graph and vector retrieval logically separate

Do not initially hide both behind one opaque relevance score.

Expose structural operations such as:

```
get_symbol()
get_callers()
get_callees()
get_tests()
get_requirements()
get_dependents()
traverse()
```

Separately expose semantic retrieval:

```
semantic_search(query)
```

A normal retrieval flow should look roughly like:

```
Task
 ↓
Identify exact target
 ↓
Structural graph expansion
 ↓
Requirements/tests/interfaces/dependencies
 ↓
Semantic search for missing conceptual relationships
 ↓
Rank/prune
 ↓
Context package
```

---

## 11. Context construction should become a first-class Atlas capability

The ultimate product is not the graph query itself.

It is the **small context package given to an AI agent**.

Conceptually:

```
ContextPackage
{
    task
    target_entities

    requirements[]
    primary_symbols[]
    dependencies[]
    callers[]
    tests[]
    interfaces[]
    constraints[]
    assumptions[]
    inferred_relationships[]

    omitted_summary
    provenance
    token_count
}
```

Context construction should operate under an explicit token budget.

A future Atlas optimization metric should be something like:

**engineering relevance per context token**

rather than simply number of indexed artifacts or search recall.

---

## 12. Bound graph traversal

Never permit unconstrained recursive traversal to become the default.

Queries should support limits such as:

```
max_depth
max_nodes
max_edges
max_tokens
allowed_edge_types
minimum_authority
minimum_confidence
```

Different relationship types can eventually have different traversal/relevance costs.

For example, `IMPLEMENTS` and `VERIFIED_BY` may often carry considerably more context value than a weak semantic relationship.

---

## 13. Requirements should drive invalidation

Requirements should eventually be active parts of the development workflow rather than passive searchable documents.

Example:

```
REQ-142
   ├── IMPLEMENTED_BY → A
   ├── IMPLEMENTED_BY → B
   └── VERIFIED_BY    → T1
```

If REQ-142 changes, do not automatically declare A/B/T1 incorrect.

Mark affected trace relationships/artifacts as potentially stale or needing review.

This enables tasks such as:

```
REQ-142 changed.

Analyze affected implementation,
verification and design artifacts.

Resolve stale trace relationships.
```

This is one mechanism by which the requirements/specification tree can eventually drive AI development.

---

## 14. Preserve negative engineering knowledge

Atlas should eventually support explicit rejected/not-applicable relationships.

Examples:

```
Requirement → NOT_APPLICABLE_TO → Component

Test → DOES_NOT_VERIFY → Requirement

Platform → EXCLUDES → Implementation
```

Also consider recording rejected candidate relationships and the reason/evidence for rejection.

This prevents future AI agents from repeatedly rediscovering and reconsidering relationships that engineering analysis already rejected.

---

## 15. Multi-agent graph mutation must be controlled

AI agents should not freely declare authoritative graph facts.

Prefer:

```
Agent
  ↓
Proposed graph mutation
  ↓
Schema validation
  ↓
Authority/evidence/conflict validation
  ↓
Commit
```

AI-inferred relationships may live in a staging or lower-authority layer until validated.

This becomes increasingly important as multiple coding, requirements, QA, and verification agents operate simultaneously.

---

## 16. Graph changes should eventually be diffable

Atlas should eventually support the conceptual equivalent of:

```
atlas diff <revision A> <revision B>
```

Example result:

```
+ Navigation::RecoverGPS
+ RecoverGPS CALLS EstimatePosition

~ REQ-142 implementation set changed

! NavigationNominal verification relationship potentially stale

! HAZ-17 potentially affected through REQ-142
```

Engineering-semantic diffs may ultimately be more useful to AI agents than raw textual diffs alone.

---

## 17. Make the graph temporal without duplicating everything unnecessarily

Atlas should eventually answer questions such as:

- What implemented this requirement at revision X?
- When did its implementation relationship change?
- Which requirements became stale after commit Y?
- What tests verified this behavior before the architecture change?

Git remains source history. Atlas should add **engineering meaning to that history**.

Avoid naïvely storing a complete graph snapshot for every commit if deltas/versioned relationships can provide the necessary capability more efficiently.

---

## 18. Keep the storage backend replaceable

Do not architect Atlas around a particular graph database unless measurements demonstrate the need.

Define a graph-store abstraction around operations Atlas actually requires.

A simple embedded implementation may be preferable initially, particularly because deployment must eventually work in constrained and air-gapped environments.

Storage technology is an implementation detail. The canonical engineering model and query semantics are the important interfaces.

---

## 19. Air-gapped deployment remains an architectural constraint

The eventual target includes a large air-gapped repository/environment.

Therefore favor:

- local/self-contained operation;
- minimal infrastructure dependencies;
- deterministic/reproducible indexing;
- portable indexes where practical;
- offline parsing and retrieval;
- clear resource bounds;
- graceful operation with weaker local AI models;
- strong graph retrieval so those weaker models require less repository context.

Do not introduce cloud dependencies into the core architecture.

---

## 20. Implementation strategy

**Do not attempt to implement this entire architecture at once.**

First inspect the current Atlas implementation and determine which concepts already exist.

Then identify the **smallest next architectural increment** that moves Atlas toward this design while preserving working behavior.

Prefer vertical slices that are testable end-to-end.

For each proposed implementation chunk:

1. State the problem being solved.
2. Identify existing Atlas behavior affected.
3. Describe the minimal design change.
4. Identify schema/API implications.
5. Implement automated tests where practical.
6. Preserve backward compatibility where worthwhile.
7. Validate against the existing viewer/workflows.
8. Commit a coherent checkpoint.
9. Update project/resume documentation so another agent can continue.

Avoid speculative infrastructure that has no immediate retrieval or engineering use case.

---

## Guiding principles

When making architectural decisions, optimize for these principles in roughly this order:

**Correctness and evidence → retrieval relevance → freshness → bounded resource usage → incremental performance → extensibility.**

The graph is **shared engineering memory**, not the authoritative source for everything.

Git remains source history.

Source code remains authoritative for implementation.

Requirements remain authoritative in their requirements source.

Build/compiler/static-analysis information should establish deterministic facts.

Tests provide verification evidence.

AI should connect, interpret, propose, and fill gaps without silently promoting inference into fact.

The ultimate objective is not:

**"Make an AI understand a million-line repository."**

It is:

**"Given a specific engineering task, retrieve the smallest trustworthy slice of a million-line engineering system necessary for an AI agent to reason and act correctly."**

---

## Instruction for the current Atlas work

Before changing code, retrieve/review the existing Atlas project context and inspect the current implementation. Reconcile this brief with what has already been built.

**Do not restart or redesign Atlas from scratch.**

Report:

- which parts of this architecture Atlas already implements;
- which are partially implemented;
- which are absent;
- any conflicts between this brief and existing architecture;
- the smallest sensible next implementation chunk;
- and the reasoning level you recommend for that chunk.

Then continue implementation from the existing project state after reconciling the architecture.