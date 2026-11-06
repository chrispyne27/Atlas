# Milestone 0.3 validation

- Three paired tasks, six actual agent submissions; 36/36 held-out check executions passed. These are 18 distinct checks executed in both arms.
- Each submitted working copy passed all eight visible native tests. The original explorer fixture also remains 8/8.
- Saved-edit replay reconstructed all six final source fingerprints and reproduced the same 36/36 held-out outcomes. Replay is not a new model run.
- Graph/model/retrieval tests passed, including compact-packet evidence retention, exact ambiguity, directional traversal, bounded requests, stale rejection, refresh, and preservation of the prior index on compiler failure.
- Six compiler-indexer tests passed for source/header/configuration invalidation, symbol resolution, compiler failures, dynamic-call uncertainty, and stale test evidence.
- Evidence integrity checks cover identical paired baselines, arm separation, exact JSONL/export parity, character accounting, complete submissions, and recorded freshness demonstrations.
- Cloud browser checks covered the pilot table, task/arm selection, transcript filtering (including empty results), source/reason expansion, explicit budget omissions, and compact/full context retrieval. Full context: 19 items / 25,738 chars; compact: 19 items / 22,506 chars; 8,000-char compact request: 6 items / 7,502 chars with 13 explicit omissions.
- A 390px iframe exercised responsive CSS and controls. Pilot/explorer page widths fit their viewport; the context dialog did not overflow. Original symbol search and depth navigation were checked.
- The browser's download-event observer timed out for both Blob and direct downloads. Export was simplified to a native download link to the packaged report. Link target and report contents were verified; a completed download was not observed by automation.
- Existing app architecture and static build are preserved. Vite is a development-only dependency added to support the supervised browser preview. No API key, remote agent service, or new viewer was added.
