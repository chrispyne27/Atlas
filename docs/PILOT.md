# Milestone 0.3: controlled agent pilot

Six coding-agent runs completed three tasks in separate working copies, one Atlas arm and one text-search arm per task. The recorded runs are real agent executions; the replay command below is deterministic verification of their saved edits.

## Observed results

| Task | Arm | Held-out before → after | Visible tests | Before-edit retrieval characters | All retrieval characters | Relevant methods seen before edit |
|---|---|---|---|---:|---:|---:|
| Reject invalid cache IDs | Atlas | 2/6 → 6/6 | 8/8 | 7,263 | 13,566 | 3/3 |
| Reject invalid cache IDs | Text search | 2/6 → 6/6 | 8/8 | 4,976 | 4,976 | 3/3 |
| Lower dimension ceiling | Atlas | 0/6 → 6/6 | 8/8 | 21,993 | 38,203 | 5/5 |
| Lower dimension ceiling | Text search | 0/6 → 6/6 | 8/8 | 15,424 | 15,424 | 4/5 |
| Suppress unchanged resizes | Atlas | 1/6 → 6/6 | 8/8 | 22,709 | 56,037 | 5/5 |
| Suppress unchanged resizes | Text search | 1/6 → 6/6 | 8/8 | 15,071 | 15,071 | 4/5 |

Both arms satisfied every held-out check. Atlas exposed the event publisher that text-search agents did not fully read on two tasks; this was not needed to pass those checks. Atlas returned approximately 43–51% more characters before the first edit. These results do not establish productivity, accuracy, or token savings. Full workflow character counts also include additional Atlas freshness demonstrations and final queries, so before-edit costs are shown separately.

Every Atlas run rejected retrieval after editing, then refreshed successfully. The cache task reparsed 1/6 translation units; the ceiling task reparsed 5/6 because its shared header changed; the event task reparsed 2/6 including visible tests. This demonstrates actual dependency invalidation, not modeled pipeline costs.

The overload task also exposes a graph limitation: the unused float overload is not reachable through the integer call path. Supplemental symbol or source discovery remains necessary. Requirement prose mentioning an overload does not automatically create a compiler or authored mapping edge.

## Inspect the evidence

Open **Agent pilot** in the hosted explorer. Select a task/arm, expand an operation, and inspect exact requests/responses, code, hashes, reasons, omissions, and errors. Export the full record as JSON. Browser results are recorded local execution; the hosted page does not launch coding agents, execute native code, or inspect a live repository.

`experiments/pilot/report.json` is the evidence record. Adjacent JSONL logs and patches make individual runs easy to inspect. `public/generated/pilot-report.json` is its deployed copy. Detailed methodology and limitations are in ADR 0002 and the report.

## Reproduce saved outcomes

Install the indexer requirements and a C++ compiler, then run from the project root:

```sh
python scripts/pilot.py replay --work /absolute/path/to/new-empty-trial-directory
```

The command creates isolated fixtures, verifies baseline fingerprints, reapplies logged edits, verifies final fingerprints, and reruns held-out and visible tests. It rejects an existing working directory. The recorded agents' conversations are not regenerated.

## Run new agents

```sh
python scripts/pilot.py prepare --work /absolute/path/to/new-pilot-directory
```

The six run directories have `run.json`, identical paired fixture inputs, and (for Atlas) an initial compiler index. Task definitions and hidden checks live in `scripts/pilot.py`. Assign each run to a fresh agent context and provide only its task plus the common/arm tool instructions in the saved report. Do not provide the evaluator or other runs. Use the same model, reasoning setting, and budgets in both arms. Adapt the instruction's absolute wrapper/run paths to the new checkout and directory.

The agent invokes the logged wrapper:

```sh
node scripts/pilot-tools.mjs /absolute/path/to/run '{"operation":"list_files","arguments":{}}'
```

After all agents have called `finish`, collect results:

```sh
python scripts/pilot.py collect --work /absolute/path/to/new-pilot-directory
```

Collection intentionally replaces the local report/export; preserve old experiments on a branch before collecting a new pilot. Native tests execute code from the trusted synthetic fixture. Do not use this harness to run untrusted repositories without an appropriate execution sandbox.

The next evaluation should use a larger fixture with competing implementations, task-specific relevance criteria, repeated runs, and narrower staged retrieval. Vectors and scale validation remain separate work.
