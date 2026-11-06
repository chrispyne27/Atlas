# ADR 0002: Logged local tools and matched agent trials

Status: accepted for milestone 0.3.

Expose exact/discovery symbol lookup, bounded dependency traversal, task context, and explicit index refresh over the existing local JSONL process. The hosted explorer remains a static inspection surface. Do not call this protocol MCP. Keep model-provider orchestration separate from retrieval so different coding agents can use the same contract through a process or terminal adapter.

All graph queries validate repository inputs before and after retrieval. Refresh invokes the fixed local indexer, not commands from engineering manifests. Responses carry identities, source spans/hashes, provenance, bounded coverage and explicit errors. Optional compact delivery omits generic method descriptions and non-requirement metadata; it preserves source excerpts, requirement metadata, constraints, relationship provenance, reasons, and test evidence. Budget units remain compact JSON characters.

The pilot uses three authored C++ tasks, two independently started agent contexts per task, identical baseline fingerprints, inherited model/reasoning configuration without overrides, and a 40-call ceiling. Both arms get the same literal search, source reads, exact replacements, and native test tools. Atlas additionally exposes graph tools and is asked to demonstrate rejection and refresh. Before-edit discovery is separated from those extra workflow costs.

Tasks and six held-out checks per task were authored before running the agents. Agents were instructed to use only their logged wrapper and not read the evaluator, other trials, or the Site checkout. This is instruction-enforced experimental isolation on a shared filesystem, not a security sandbox. The parent implemented the adapter and evaluator and did not supply solution patches to the agents.

The pilot records exact requests/responses, tool durations, JSON response character counts, patches, and source fingerprints. Model token usage, internal reasoning, and model execution time are unavailable. One small run per arm supports descriptive findings only. Authored method coverage measures exposure to full excerpts, not understanding or necessity. A baseline can pass every acceptance test without reading every method on that checklist.

Keep the successful and unsuccessful calls, including stale errors and budget omissions. Do not change a submitted patch to improve its score. Store replayable results in Git; replay verifies saved edits and tests and must not be described as a new model run. Fixture changes remain isolated per task; the original explorer fixture is unchanged.
