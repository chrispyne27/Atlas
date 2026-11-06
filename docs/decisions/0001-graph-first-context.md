# ADR 0001: One graph for agents and humans

Status: accepted for the first implementation milestone.

Use libclang and an explicit compilation database. Compiler USRs identify symbols; qualified signatures distinguish overloads. Preserve byte-accurate excerpts, locations, and provenance. Direct calls are separate from unresolved/dynamic dispatch. Requirement and test links are authored engineering assertions, never fabricated compiler facts.

Retrieval starts at exact symbols or requirement IDs. Traverse selected edges within hop/node limits, then rank and pack complete evidence items under an exact serialized-JSON character budget. Report reasons, omissions, identity, and freshness. Character counts are not model tokens. Unknown or ambiguous seeds and stale inputs are explicit failures.

Cache each translation unit and its include dependencies. Known file edits invalidate dependent units; input membership and compiler-configuration changes conservatively invalidate all units. Rejoin engineering manifests on every build. Validate indexed input hashes before local retrieval.

Vectors will eventually provide candidate IDs. They do not replace graph structure. The explorer consumes the same snapshot as agents. Browser annotations do not silently overwrite authoritative versioned metadata.

References: https://clang.llvm.org/docs/LibClang.html and https://clang.llvm.org/docs/JSONCompilationDatabase.html
